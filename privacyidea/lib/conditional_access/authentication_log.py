# (c) NetKnights GmbH 2026,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import and_, delete, false, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql import ColumnElement

from privacyidea.models import AuthenticationLog, authentication_log_column_length, db
from privacyidea.lib.conditional_access.authentication_error_codes import AuthEventType
from privacyidea.lib.error import ParameterError
from privacyidea.lib.sqlutils import delete_matching_rows

log = logging.getLogger(__name__)

# Columns that may be used to sort a paginated authentication-log query, keyed by the name accepted from the API.
SORTABLE_COLUMNS: dict[str, InstrumentedAttribute] = {
    "id": AuthenticationLog.id,
    "timestamp": AuthenticationLog.timestamp,
    "event_type": AuthenticationLog.event_type,
    "realm": AuthenticationLog.realm,
    "username": AuthenticationLog.username,
    "source_ip": AuthenticationLog.source_ip,
    "serial": AuthenticationLog.serial,
}
DEFAULT_PAGE_SIZE = 15


class AuthLogUserRole(str, Enum):
    """
    Role of the authenticating principal recorded in the authentication log. The two admin values are kept distinct
    because conditional-access rules may treat them differently: ``admin-external`` admins come from an admin realm
    (an external identity source) and are the everyday admins, while ``admin-internal`` admins are local database
    accounts (created via the CLI, used for initial setup and as fallback/recovery) that authenticate only at the
    ``/auth`` endpoint. Both share the ``admin-`` prefix so a single ``user_role=admin*`` filter matches either.

    ``str`` is used instead of ``StrEnum`` (3.11+) for compatibility with Python 3.10; the ``__str__`` override
    normalizes ``str()``/f-string output to the value across versions (mirrors :class:`AuthEventType`).
    """
    USER = "user"
    ADMIN_INTERNAL = "admin-internal"
    ADMIN_EXTERNAL = "admin-external"

    def __str__(self) -> str:
        return self.value


@dataclass
class AuthenticationLogVisibilityScope:
    """
    One policy's target scope, restricting which authentication-log entries an admin may see/delete. An entry must
    match all dimensions a policy sets (logical AND); across several scopes (from several policies) an entry is
    visible if it matches any one of them (logical OR) -- see :func:`get_authentication_logs_paginate`. Empty lists
    mean "no restriction on that dimension".
    """
    realms: list[str]
    resolvers: list[str]
    usernames: list[str]


@dataclass
class AuthenticationLogPage:
    """One page of an authentication-log query plus its pagination metadata."""
    auth_logs: list[AuthenticationLog]
    count: int
    current: int
    prev: int | None
    next: int | None

    def to_dict(self) -> dict:
        """Serialize the page (entries plus pagination metadata) for the API response."""
        return {
            "auth_logs": [entry.to_dict() for entry in self.auth_logs],
            "count": self.count,
            "current": self.current,
            "prev": self.prev,
            "next": self.next,
        }


def _naive_utc(value: datetime) -> datetime:
    """
    Normalize a datetime to naive UTC, matching how the ``timestamp`` column is stored. A timezone-aware value is
    converted to UTC and stripped of its tzinfo; a naive value is assumed to already be in UTC and returned unchanged.
    This lets callers pass either form without risking a naive-vs-aware comparison against the column.
    """
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


@dataclass
class _TruncatedValue:
    """
    Result of truncating one column value: *stored* goes into the column, *overflow* is the part that did not fit and
    is preserved in the entry's ``other_info`` (see :func:`_store_overflow`) so no information is lost. *overflow* is
    ``None`` when nothing was cut.
    """
    stored: str | None
    overflow: str | None


def _truncate(column: str, value, separator: str | None = None) -> _TruncatedValue:
    """
    Convert *value* to a string and truncate it to the length of the given column of the authentication_log table, so a
    pathological value (e.g. a very long User-Agent or login name) can never overflow the column on insert. The cut-off
    remainder is returned alongside the stored value rather than discarded.

    :param column: the column name, a key of
        :data:`~privacyidea.models.authentication_log.authentication_log_column_length`
    :param value: the value to store, or None
    :param separator: if given, cut on the last separator that fits instead of mid-character, so neither the stored
        value nor the overflow holds a broken item (used for ``serial``, which may carry a separator-joined list, to
        keep whole, filterable serials in the column)
    :return: a :class:`_TruncatedValue` holding the value to store and the overflow (or None if *value* is None)
    """
    if value is None:
        return _TruncatedValue(None, None)
    value = str(value)
    max_length = authentication_log_column_length[column]
    if len(value) <= max_length:
        return _TruncatedValue(value, None)
    log.debug(f"Truncating authentication log column {column!r} to {max_length} characters.")
    if separator:
        cut = value.rfind(separator, 0, max_length + 1)
        if cut > 0:
            return _TruncatedValue(value[:cut], value[cut + len(separator):])
    return _TruncatedValue(value[:max_length], value[max_length:])


def _store_overflow(other_info: dict | None, overflow: dict[str, str]) -> dict | None:
    """
    Fold any truncation overflow into a copy of *other_info* under the ``truncated`` key so it is preserved without
    clobbering caller-supplied keys, merging with overflow already recorded there. Returns *other_info* unchanged when
    nothing overflowed.
    """
    if not overflow:
        return other_info
    merged = dict(other_info) if other_info else {}
    merged["truncated"] = {**merged.get("truncated", {}), **overflow}
    return merged


def log_authentication_event(event_type: AuthEventType,
                             transaction_id: str | None = None,
                             previous_transaction_id: str | None = None,
                             resolver: str | None = None,
                             uid: str | None = None,
                             realm: str | None = None,
                             username: str | None = None,
                             user_role: str | None = None,
                             source_ip: str | None = None,
                             client_label: str | None = None,
                             serial: str | None = None,
                             other_info: dict | None = None) -> int | None:
    """
    Create a new authentication log entry and return its id.

    Writing the authentication log must never break the authentication itself, so a failure to write the entry is
    logged and swallowed: the insert runs inside a SAVEPOINT, so a failure rolls back only the entry while leaving any
    other pending writes of the request untouched, and ``None`` is returned instead of an id.
    """
    fields = {
        "event_type": event_type,
        "transaction_id": transaction_id,
        "previous_transaction_id": previous_transaction_id,
        "resolver": resolver,
        "uid": uid,
        "realm": realm,
        "username": username,
        "user_role": user_role,
        "source_ip": source_ip,
        "client_label": client_label,
        "serial": serial,
    }
    stored: dict[str, str | None] = {}
    overflow: dict[str, str] = {}
    for column, value in fields.items():
        result = _truncate(column, value, separator="," if column == "serial" else None)
        stored[column] = result.stored
        if result.overflow is not None:
            overflow[column] = result.overflow
    entry = AuthenticationLog(**stored, other_info=_store_overflow(other_info, overflow))
    try:
        with db.session.begin_nested():
            db.session.add(entry)
        entry_id = entry.id
    except Exception as ex:
        log.warning(f"Failed to write the authentication log entry: {ex!r}")
        return None
    try:
        db.session.commit()
    except Exception as ex:
        # The savepoint flush succeeded but the outer commit failed: roll back so the session is usable for the rest
        # of the request, and report no id since the entry was not persisted.
        log.warning(f"Failed to commit the authentication log entry: {ex!r}")
        db.session.rollback()
        return None
    return entry_id


def delete_authentication_log_event(event_id: int) -> None:
    """
    Delete a single authentication log entry by id.
    """
    stmt = delete(AuthenticationLog).where(AuthenticationLog.id == event_id)
    db.session.execute(stmt)
    db.session.commit()


def reclassify_authentication_log_event(event_id: int, event_type: AuthEventType,
                                        serial: str | None = None, transaction_id: str | None = None) -> None:
    """
    Override the classification of an existing entry written earlier in the same request.

    This is for the case where a later request stage changes the outcome of an already-logged event — specifically
    ``enroll_via_multichallenge``, where a successful authentication (logged as ``LOGIN_SUCCESS`` in check()'s finally)
    is turned into an enrollment challenge by a post-policy.

    Like the insert, this must never break the response: a failure is logged and swallowed, and runs inside a
    SAVEPOINT so it rolls back only this update.

    :param event_id: id of the entry to reclassify
    :param event_type: the new event type
    :param serial: the new serial (default None)
    :param transaction_id: the new transaction_id (default None)
    """
    try:
        with db.session.begin_nested():
            entry = db.session.get(AuthenticationLog, event_id)
            if entry is None:
                log.info(f"Cannot reclassify authentication log entry {event_id!r}: not found.")
                return
            overflow: dict[str, str] = {}

            truncated_event_type = _truncate("event_type", event_type)
            entry.event_type = truncated_event_type.stored
            if truncated_event_type.overflow is not None:
                overflow["event_type"] = truncated_event_type.overflow

            if serial is not None:
                truncated_serial = _truncate("serial", serial, separator=",")
                entry.serial = truncated_serial.stored
                if truncated_serial.overflow is not None:
                    overflow["serial"] = truncated_serial.overflow

            if transaction_id:
                truncated_transaction_id = _truncate("transaction_id", transaction_id)
                new_transaction_id = truncated_transaction_id.stored
                if truncated_transaction_id.overflow is not None:
                    overflow["transaction_id"] = truncated_transaction_id.overflow
                old_transaction_id = entry.transaction_id
                if old_transaction_id and new_transaction_id != old_transaction_id:
                    entry.previous_transaction_id = old_transaction_id
                entry.transaction_id = new_transaction_id

            entry.other_info = _store_overflow(entry.other_info, overflow)
    except Exception as ex:
        log.info(f"Failed to reclassify the authentication log entry to {event_type}: {ex!r}")
        return
    try:
        db.session.commit()
    except Exception as ex:
        # The savepoint update succeeded but the outer commit failed: roll back so the session is usable for the rest
        # of the request.
        log.info(f"Failed to commit the reclassified authentication log entry to {event_type}: {ex!r}")
        db.session.rollback()


def get_authentication_log_event(event_id: int) -> AuthenticationLog | None:
    """
    Return a single AuthenticationLog entry by event_id, or None if not found.
    """
    return db.session.get(AuthenticationLog, event_id)


def _wildcard_pattern(value: str) -> str:
    """
    Turn a filter value into a SQL ``LIKE`` pattern in which only ``*`` is a wildcard. The ``LIKE`` special
    characters ``%`` and ``_`` (and the ``\\`` escape character itself) are escaped so they match literally -- e.g.
    the ``_`` in an event type like ``MFA_FAIL`` is not treated as a single-character wildcard -- and only ``*`` is
    then mapped to the wildcard ``%``. Used with ``like(..., escape="\\")``.
    """
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return escaped.replace("*", "%")


def _match_condition(column: InstrumentedAttribute, value: str | list[str] | None,
                     case_insensitive: bool = False) -> ColumnElement[bool] | None:
    """
    Build the match condition for one column from a single value or a list of values, or ``None`` for no filter on
    that field. An entry matches if it equals any plain value, or matches any value containing a ``*`` wildcard;
    ``*`` is the only wildcard (see :func:`_wildcard_pattern`). Plain values are batched into a single ``IN``; only
    wildcard values cost a ``LIKE`` each, so a list without wildcards stays a single indexed ``IN``.

    Plain values are matched with a plain ``IN`` so an index on the column can still be used. The case sensitivity of
    that match is therefore left to the database collation: it is case-sensitive on SQLite (and on a binary collation)
    but case-insensitive on a MySQL/MariaDB ``*_ci`` collation. Setting *case_insensitive* lowers both sides to
    *enforce* case-insensitive matching consistently across backends -- note this defeats the column index (the
    ``LOWER()`` wrapper prevents an index seek), so it is the slower path. There is deliberately no symmetric
    "enforce case-sensitive" option: it would need DB-specific collation and is rarely worth the cost. Wildcard
    values always match case-insensitively (via ``ILIKE``), since the DB-default ``LIKE`` case semantics differ per
    backend.
    """
    if value is None:
        return None
    values = [str(item) for item in value] if isinstance(value, (list, tuple)) else [str(value)]
    if not values:
        return None
    exact = [v for v in values if "*" not in v]
    terms = [column.ilike(_wildcard_pattern(v), escape="\\") for v in values if "*" in v]
    if exact:
        if case_insensitive:
            terms.append(func.lower(column).in_([v.lower() for v in exact]))
        else:
            terms.append(column.in_(exact))
    return or_(*terms) if len(terms) > 1 else terms[0]


def _filter_conditions(resolver: str | list[str] | None = None,
                       uid: str | list[str] | None = None,
                       realm: str | list[str] | None = None,
                       username: str | list[str] | None = None,
                       user_role: str | list[str] | None = None,
                       event_type: str | list[str] | None = None,
                       source_ip: str | list[str] | None = None,
                       serial: str | list[str] | None = None,
                       transaction_id: str | list[str] | None = None,
                       previous_transaction_id: str | list[str] | None = None,
                       client_label: str | list[str] | None = None,
                       start_timestamp: datetime | None = None,
                       end_timestamp: datetime | None = None,
                       case_insensitive: bool = False) -> list:
    """
    Build the list of SQLAlchemy ``where`` conditions for the provided filters (``None`` means no filter on that
    field). Each scalar filter accepts a single value or a list of values; an entry matches the field if it equals any
    of the values, or (for a value containing a ``*`` wildcard) matches it with a ``LIKE``. Returned as a list so it
    can be applied to both ``select`` and ``delete`` statements. timestamp filters are inclusive on both ends.

    With *case_insensitive* set, plain (non-wildcard) filter values match case-insensitively; wildcard values always
    match case-insensitively (see :func:`_match_condition`).
    """
    match_filters: dict[InstrumentedAttribute, str | list[str] | None] = {
        AuthenticationLog.resolver: resolver,
        AuthenticationLog.uid: uid,
        AuthenticationLog.realm: realm,
        AuthenticationLog.username: username,
        AuthenticationLog.user_role: user_role,
        AuthenticationLog.event_type: event_type,
        AuthenticationLog.source_ip: source_ip,
        AuthenticationLog.serial: serial,
        AuthenticationLog.transaction_id: transaction_id,
        AuthenticationLog.previous_transaction_id: previous_transaction_id,
        AuthenticationLog.client_label: client_label,
    }
    conditions = [condition for column, value in match_filters.items()
                  if (condition := _match_condition(column, value, case_insensitive)) is not None]
    if start_timestamp is not None:
        conditions.append(AuthenticationLog.timestamp >= _naive_utc(start_timestamp))
    if end_timestamp is not None:
        conditions.append(AuthenticationLog.timestamp <= _naive_utc(end_timestamp))
    return conditions


def _ci_in(column: InstrumentedAttribute, values: list[str]) -> ColumnElement[bool]:
    """
    Case-insensitive ``IN``: match *column* against *values* with both sides lower-cased. The visibility scope is a
    security boundary (which entries a principal may see), so it must match consistently regardless of the database
    collation -- a case-sensitive backend (e.g. SQLite) would otherwise hide a user's own entries when the policy /
    identity casing differs from the stored ``user.login`` casing.
    """
    return func.lower(column).in_([value.lower() for value in values])


def _visibility_condition(scopes: list[AuthenticationLogVisibilityScope]) -> ColumnElement[bool]:
    """
    Build a single ``where`` condition restricting the visible entries to the given scopes: an entry must match all
    dimensions a scope sets (AND), and is included if it matches any one scope (OR). An entry matches a dimension via
    a case-insensitive ``IN`` on the corresponding column, so entries with a NULL value in a restricted dimension are
    excluded.

    An empty scope list (or scopes that set no dimension at all) restricts to *nothing*: it returns ``false()`` rather
    than an empty ``or_()``, so the visibility boundary fails closed instead of degrading to "no restriction".
    """
    scope_conditions = []
    for scope in scopes:
        dimensions = []
        if scope.realms:
            dimensions.append(_ci_in(AuthenticationLog.realm, scope.realms))
        if scope.resolvers:
            dimensions.append(_ci_in(AuthenticationLog.resolver, scope.resolvers))
        if scope.usernames:
            dimensions.append(_ci_in(AuthenticationLog.username, scope.usernames))
        if dimensions:
            scope_conditions.append(and_(*dimensions))
    if not scope_conditions:
        return false()
    return or_(*scope_conditions)


def get_authentication_logs(resolver: str | list[str] | None = None,
                            uid: str | list[str] | None = None,
                            realm: str | list[str] | None = None,
                            username: str | list[str] | None = None,
                            user_role: str | list[str] | None = None,
                            event_type: str | list[str] | None = None,
                            source_ip: str | list[str] | None = None,
                            serial: str | list[str] | None = None,
                            transaction_id: str | list[str] | None = None,
                            previous_transaction_id: str | list[str] | None = None,
                            client_label: str | list[str] | None = None,
                            start_timestamp: datetime | None = None,
                            end_timestamp: datetime | None = None) -> list[AuthenticationLog]:
    """
    Return authentication log entries matching all provided filter criteria, ordered by id (i.e. chronologically).
    All parameters are optional; omitting a parameter means no filtering on that field. Each scalar filter accepts a
    single value or a list of values; an entry matches the field if it equals any of the listed values, or (for a
    value containing a ``*`` wildcard) matches it with a ``LIKE``. timestamp filters are inclusive on both ends.
    """
    conditions = _filter_conditions(resolver=resolver, uid=uid, realm=realm, username=username, user_role=user_role,
                                    event_type=event_type,
                                    source_ip=source_ip, serial=serial, transaction_id=transaction_id,
                                    previous_transaction_id=previous_transaction_id, client_label=client_label,
                                    start_timestamp=start_timestamp, end_timestamp=end_timestamp)
    stmt = select(AuthenticationLog).where(*conditions).order_by(AuthenticationLog.id)
    return db.session.scalars(stmt).all()


def get_authentication_logs_paginate(resolver: str | list[str] | None = None,
                                     uid: str | list[str] | None = None,
                                     realm: str | list[str] | None = None,
                                     username: str | list[str] | None = None,
                                     user_role: str | list[str] | None = None,
                                     event_type: str | list[str] | None = None,
                                     source_ip: str | list[str] | None = None,
                                     serial: str | list[str] | None = None,
                                     transaction_id: str | list[str] | None = None,
                                     previous_transaction_id: str | list[str] | None = None,
                                     client_label: str | list[str] | None = None,
                                     start_timestamp: datetime | None = None,
                                     end_timestamp: datetime | None = None,
                                     visibility_scopes: list[AuthenticationLogVisibilityScope] | None = None,
                                     case_insensitive: bool = False,
                                     page: int = 1,
                                     page_size: int = DEFAULT_PAGE_SIZE,
                                     sort_column: str = "id",
                                     sort_order: str = "desc") -> AuthenticationLogPage:
    """
    Return a single page of authentication log entries matching the given filters.

    The filter parameters -- ``resolver``, ``uid``, ``realm``, ``username``, ``user_role``, ``event_type``, ``source_ip``,
    ``serial``, ``transaction_id``, ``previous_transaction_id``, ``client_label``, ``start_timestamp`` and
    ``end_timestamp`` -- behave
    exactly like :func:`get_authentication_logs`. The remaining parameters control visibility scoping and pagination:

    :param visibility_scopes: restrict the result to entries matching any of these scopes
        (see :func:`_visibility_condition`); ``None`` means no restriction
    :param case_insensitive: if set, plain (non-wildcard) filter values match case-insensitively; wildcard values
        always match case-insensitively
    :param page: the page number to return, 1-indexed
    :param page_size: the number of entries per page
    :param sort_column: the column to sort by; one of :data:`SORTABLE_COLUMNS` (falling back to ``id``), always
        tie-broken by id so the order is stable across pages
    :param sort_order: ``asc`` or ``desc``
    :return: an :class:`AuthenticationLogPage` with the page's entries and the pagination metadata
    """
    conditions = _filter_conditions(resolver=resolver, uid=uid, realm=realm, username=username, user_role=user_role,
                                    event_type=event_type,
                                    source_ip=source_ip, serial=serial, transaction_id=transaction_id,
                                    previous_transaction_id=previous_transaction_id, client_label=client_label,
                                    start_timestamp=start_timestamp, end_timestamp=end_timestamp,
                                    case_insensitive=case_insensitive)
    if visibility_scopes is not None:
        conditions.append(_visibility_condition(visibility_scopes))
    stmt = select(AuthenticationLog).where(*conditions)

    count = db.session.scalar(select(func.count()).select_from(AuthenticationLog).where(*conditions))

    order_column = SORTABLE_COLUMNS.get(sort_column)
    if order_column is None:
        log.warning(f"Unknown sort column '{sort_column}'. Using 'id' instead.")
        order_column = AuthenticationLog.id
    if sort_order == "asc":
        stmt = stmt.order_by(order_column.asc(), AuthenticationLog.id.asc())
    else:
        stmt = stmt.order_by(order_column.desc(), AuthenticationLog.id.desc())

    page = max(1, page)
    page_size = max(1, page_size)
    offset = (page - 1) * page_size
    auth_logs = db.session.scalars(stmt.limit(page_size).offset(offset)).all()
    return AuthenticationLogPage(auth_logs=auth_logs,
                                 count=count,
                                 current=page,
                                 prev=page - 1 if page > 1 else None,
                                 next=page + 1 if offset + page_size < count else None)


def delete_authentication_logs(resolver: str | list[str] | None = None,
                               uid: str | list[str] | None = None,
                               realm: str | list[str] | None = None,
                               username: str | list[str] | None = None,
                               user_role: str | list[str] | None = None,
                               event_type: str | list[str] | None = None,
                               source_ip: str | list[str] | None = None,
                               serial: str | list[str] | None = None,
                               transaction_id: str | list[str] | None = None,
                               previous_transaction_id: str | list[str] | None = None,
                               client_label: str | list[str] | None = None,
                               start_timestamp: datetime | None = None,
                               end_timestamp: datetime | None = None,
                               visibility_scopes: list[AuthenticationLogVisibilityScope] | None = None,
                               chunk_size: int | None = None) -> int:
    """
    Delete all authentication log entries matching the given filters and return the number deleted.

    The filter parameters -- ``resolver``, ``uid``, ``realm``, ``username``, ``user_role``, ``event_type``, ``source_ip``,
    ``serial``, ``transaction_id``, ``previous_transaction_id``, ``client_label``, ``start_timestamp`` and
    ``end_timestamp`` -- behave
    exactly like :func:`get_authentication_logs` (to delete entries older than a point in time, pass
    ``end_timestamp``). The caller must pass at least one filter: with no filter this would delete the entire log,
    which this function refuses.

    :param visibility_scopes: restrict the deletion to entries matching any of these scopes
        (see :func:`_visibility_condition`); ``None`` means no restriction
    :param chunk_size: if given, delete in chunks of this size to avoid long locks on large tables
    :return: the number of deleted entries
    """
    conditions = _filter_conditions(resolver=resolver, uid=uid, realm=realm, username=username, user_role=user_role,
                                    event_type=event_type,
                                    source_ip=source_ip, serial=serial, transaction_id=transaction_id,
                                    previous_transaction_id=previous_transaction_id, client_label=client_label,
                                    start_timestamp=start_timestamp, end_timestamp=end_timestamp)
    # Guard on the caller's filters before adding the visibility restriction, so a scoped admin also cannot wipe a
    # whole scope with an unfiltered request.
    if not conditions:
        raise ParameterError("Refusing to delete the whole authentication log: at least one filter is required.")
    if visibility_scopes is not None:
        conditions.append(_visibility_condition(visibility_scopes))
    return delete_matching_rows(db.session, AuthenticationLog.__table__, and_(*conditions), chunk_size)


def cleanup_authentication_log(older_than: datetime, chunk_size: int | None = None) -> int:
    """
    Delete all authentication log entries with a timestamp strictly older than the given datetime.

    :param older_than: delete entries whose timestamp is older than this (naive or timezone-aware; aware values are
        converted to UTC)
    :param chunk_size: if given, delete in chunks of this size to avoid long locks / deadlocks on large tables
    :return: the number of deleted rows
    """
    criterion = AuthenticationLog.timestamp < _naive_utc(older_than)
    return delete_matching_rows(db.session, AuthenticationLog.__table__, criterion, chunk_size)
