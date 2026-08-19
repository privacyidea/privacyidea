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
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, selectinload
from sqlalchemy.sql import ColumnElement

from privacyidea.models import AuthenticationLog, ConditionalAccessOutcome, authentication_log_column_length
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.session import get_ca_session, guarded_write
from privacyidea.lib.error import ParameterError
from privacyidea.lib.sqlutils import delete_matching_rows

log = logging.getLogger(__name__)

# Columns a paginated authentication-log query can sort by, keyed by the name the API accepts; every scalar column
# is sortable, but ``other_info`` is excluded because JSON column ordering is neither meaningful nor portable.
SORTABLE_COLUMNS: dict[str, InstrumentedAttribute] = {
    "id": AuthenticationLog.id,
    "timestamp": AuthenticationLog.timestamp,
    "event_type": AuthenticationLog.event_type,
    "resolver": AuthenticationLog.resolver,
    "uid": AuthenticationLog.uid,
    "realm": AuthenticationLog.realm,
    "username": AuthenticationLog.username,
    "source_ip": AuthenticationLog.source_ip,
    "client_label": AuthenticationLog.client_label,
    "serial": AuthenticationLog.serial,
    "transaction_id": AuthenticationLog.transaction_id,
    "attempt_id": AuthenticationLog.attempt_id,
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

    *username_case_insensitive* mirrors the originating policy's ``user_case_insensitive`` option and forces a
    case-insensitive match on the ``usernames`` dimension only; realm and resolver always match case-sensitively.

    *user_roles* restricts to entries of those :class:`AuthLogUserRole` values. It is not derived from policy scoping
    (policies do not scope by role); it is used to express a principal's own entries -- a local/internal admin has no
    realm, so their own entries are matched by username plus ``user_role=admin-internal`` instead of by realm.
    """
    realms: list[str]
    resolvers: list[str]
    usernames: list[str]
    username_case_insensitive: bool = False
    user_roles: list[str] = field(default_factory=list)


@dataclass
class AuthenticationLogPage:
    """One page of an authentication-log query plus its pagination metadata."""
    # A Sequence, not a list: this is what Session.scalars(...).all() returns.
    auth_logs: Sequence[AuthenticationLog]
    count: int
    current: int
    prev: int | None
    next: int | None

    def to_dict(self) -> dict:
        """Serialize the page (entries plus pagination metadata) for the API response."""
        return {
            # The entries were loaded with their outcomes (see get_authentication_logs_paginate), so this is the one
            # place that may serialize them.
            "auth_logs": [entry.to_dict(include_outcomes=True) for entry in self.auth_logs],
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


def _truncate(column: str, value: Any, separator: str | None = None) -> _TruncatedValue:
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


@dataclass
class PendingAuthEvent:
    """
    One authentication-log row, described here rather than written straight away.

    The event is the **source of truth for its row**: assigning to a field is all a later request stage has to do,
    whether or not the row exists yet. Until it exists the assignment simply lands in the eventual ``INSERT``; once it
    exists the event is marked :attr:`changed` and the next flush issues an ``UPDATE``. Without that, an assignment
    after the row was written would be lost twice over - skipped by the next flush *and* invisible to the stored row,
    since :func:`_build_entry` copies the values into a separate ORM object.

    The values are held **raw**: truncation to the column lengths happens when the row is built, so a value a later
    stage lengthens - a post-policy extending ``serial``, say - is cut against its final length rather than an
    intermediate one. ``other_info`` is likewise the caller's dict, which the row build merges truncation overflow
    into.
    """
    event_type: AuthEventType
    transaction_id: str | None = None
    resolver: str | None = None
    uid: str | None = None
    realm: str | None = None
    username: str | None = None
    user_role: str | None = None
    source_ip: str | None = None
    client_label: str | None = None
    serial: str | None = None
    attempt_id: str | None = None
    other_info: dict | None = None
    # A point-in-time record another in-flight request has to see (the push_wait challenge trigger) rather than this
    # request's own classification, and must never be reclassified afterwards - see ConditionalAccessContext.amendable.
    immediate: bool = False
    # Id of the stored row, set once it has been committed; None means "not written yet".
    row_id: int | None = None
    # What conditional access did for this request, held here until the row id to record it against exists (see
    # ConditionalAccessContext.flush); it becomes rows in conditional_access_outcome, not columns on this row.
    outcomes: list[ConditionalAccessOutcome] = field(default_factory=list)
    # Set when a field is assigned after the row was written, i.e. the stored row no longer matches this event.
    _changed: bool = field(init=False, default=False, repr=False, compare=False)

    def __setattr__(self, name: str, value: Any) -> None:
        # ``row_id``, ``outcomes``, ``immediate`` and the flag itself are bookkeeping, not row content, so assigning
        # them never marks the event changed. ``self.__dict__`` is read directly because the dataclass __init__ also
        # assigns fields through this method, before ``row_id`` exists.
        if name not in ("row_id", "outcomes", "immediate", "_changed") and self.__dict__.get("row_id") is not None:
            object.__setattr__(self, "_changed", True)
        object.__setattr__(self, name, value)

    @property
    def written(self) -> bool:
        """Whether the row has been committed."""
        return self.row_id is not None

    @property
    def changed(self) -> bool:
        """Whether the stored row is out of date because a field was assigned after it was written."""
        return self.written and self._changed


# The columns of an entry that are truncated to their column length, and the separator to cut on (see _truncate).
_TRUNCATED_COLUMNS = {
    "event_type": None,
    "transaction_id": None,
    "resolver": None,
    "uid": None,
    "realm": None,
    "username": None,
    "user_role": None,
    "source_ip": None,
    "client_label": None,
    # A comma-joined serial list: cut on the last whole serial that fits.
    "serial": ",",
    "attempt_id": None,
}


def _row_values(event: PendingAuthEvent) -> dict:
    """
    The column values to store for *event*: every column truncated to its length, with the cut-off remainder folded
    into ``other_info`` so nothing is silently lost. Shared by the insert and the update path, so an amended event is
    truncated exactly like a fresh one.
    """
    stored: dict[str, str | None] = {}
    overflow: dict[str, str] = {}
    for column, separator in _TRUNCATED_COLUMNS.items():
        result = _truncate(column, getattr(event, column), separator=separator)
        stored[column] = result.stored
        if result.overflow is not None:
            overflow[column] = result.overflow
    return {**stored, "other_info": _store_overflow(event.other_info, overflow)}


def _build_entry(event: PendingAuthEvent) -> AuthenticationLog:
    """Build the :class:`AuthenticationLog` row for *event*."""
    return AuthenticationLog(**_row_values(event))


def write_authentication_events(events: Sequence[PendingAuthEvent]) -> bool:
    """
    Insert *events* as **one** transaction, in the given order, and record each row's id on its event.

    Writing the authentication log must never break the authentication itself, so a failure is logged and swallowed
    and the events keep ``row_id is None`` - which makes them eligible for a later retry. The insert runs on the
    conditional-access session, so neither the commit nor a rollback touches the request's own pending writes.

    :return: whether the transaction was committed
    """
    if not events:
        return True
    entries = [_build_entry(event) for event in events]
    label = ("the authentication log entry" if len(entries) == 1
             else f"the {len(entries)} authentication log entries")
    # Ids are read inside the guarded block from an explicit flush, then published to the events only once the
    # commit has succeeded; reading them after the commit would leave that read unguarded, and a row committed but
    # never stamped would be re-inserted by the next flush.
    row_ids: list[int] = []
    with guarded_write(label) as outcome:
        session = get_ca_session()
        session.add_all(entries)
        session.flush()
        row_ids = [entry.id for entry in entries]
    if not outcome.succeeded:
        return False
    for event, row_id in zip(events, row_ids):
        event.row_id = row_id
    return True


def update_authentication_events(events: Sequence[PendingAuthEvent]) -> bool:
    """
    Re-write the stored rows of *events* that were amended after being written, as **one** transaction, and clear
    their changed flag.

    This is what makes a :class:`PendingAuthEvent` the source of truth for its row: a later request stage - a
    post-policy correcting the classification, say - just assigns to the event, and the row is brought back in line
    here. Like the insert, a failure is logged and swallowed; the events keep their changed flag, so a later flush
    retries them.

    :return: whether the transaction was committed
    """
    if not events:
        return True
    label = ("the amended authentication log entry" if len(events) == 1
             else f"the {len(events)} amended authentication log entries")
    with guarded_write(label) as outcome:
        session = get_ca_session()
        for event in events:
            entry = session.get(AuthenticationLog, event.row_id)
            if entry is None:
                log.info(f"Cannot update authentication log entry {event.row_id!r}: not found.")
                continue
            values = _row_values(event)
            for column, value in values.items():
                setattr(entry, column, value)
    if not outcome.succeeded:
        return False
    for event in events:
        event._changed = False
    return True


def log_authentication_event(event_type: AuthEventType,
                             transaction_id: str | None = None,
                             resolver: str | None = None,
                             uid: str | None = None,
                             realm: str | None = None,
                             username: str | None = None,
                             user_role: str | None = None,
                             source_ip: str | None = None,
                             client_label: str | None = None,
                             serial: str | None = None,
                             attempt_id: str | None = None,
                             other_info: dict | None = None) -> int | None:
    """
    Create a new authentication log entry and return its id, or ``None`` if it could not be written.

    The single-event convenience wrapper over :func:`write_authentication_events`, for callers that have no request
    context to collect on (the CLI, tests, and lib code outside a view).
    """
    event = PendingAuthEvent(event_type=event_type, transaction_id=transaction_id, resolver=resolver, uid=uid,
                             realm=realm, username=username, user_role=user_role, source_ip=source_ip,
                             client_label=client_label, serial=serial, attempt_id=attempt_id, other_info=other_info)
    write_authentication_events([event])
    return event.row_id


def delete_authentication_log_event(event_id: int) -> None:
    """
    Delete a single authentication log entry by id.

    A management operation, so a failure surfaces to the caller instead of being swallowed.
    """
    with guarded_write(f"the deletion of authentication log entry {event_id}", reraise=True):
        session = get_ca_session()
        entry = session.get(AuthenticationLog, event_id)
        if entry is not None:
            # Deleted as an *object*, so the outcomes relationship cascade removes this entry's conditional-access
            # history too, on every backend, since SQLite does not enforce foreign keys.
            session.delete(entry)


def get_authentication_log_event(event_id: int) -> AuthenticationLog | None:
    """
    Return a single AuthenticationLog entry by event_id, or None if not found.
    """
    return get_ca_session().get(AuthenticationLog, event_id)


def _wildcard_pattern(value: str) -> str:
    """
    Turn a filter value into a SQL ``LIKE`` pattern in which only ``*`` is a wildcard. The ``LIKE`` special
    characters ``%`` and ``_`` (and the ``\\`` escape character itself) are escaped so they match literally -- e.g.
    the ``_`` in an event type like ``MFA_FAIL`` is not treated as a single-character wildcard -- and only ``*`` is
    then mapped to the wildcard ``%``. Used with ``like(..., escape="\\")``.
    """
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return escaped.replace("*", "%")


def match_condition(column: InstrumentedAttribute, value: str | list[str] | None,
                     case_insensitive: bool = False) -> ColumnElement[bool] | None:
    """
    Build the match condition for one column from a single value or a list of values, or ``None`` for no filter on
    that field. An entry matches if it equals any plain value, or matches any value containing a ``*`` wildcard;
    ``*`` is the only wildcard (see :func:`_wildcard_pattern`). Plain values are batched into a single ``IN``; only
    wildcard values cost a ``LIKE`` each, so a list without wildcards stays a single indexed ``IN``.

    Plain values are matched with a plain ``IN`` so an index on the column can still be used. The match is
    **case-sensitive on every backend**. Setting *case_insensitive* lowers both sides to match case-insensitively
    instead -- note this defeats the column index (the ``LOWER()`` wrapper prevents an index seek), so it is the slower
    path. Wildcard values always match case-insensitively (via ``ILIKE``), since the DB-default ``LIKE`` case semantics
    differ per backend.
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
                       attempt_id: str | list[str] | None = None,
                       client_label: str | list[str] | None = None,
                       start_time: datetime | None = None,
                       end_time: datetime | None = None,
                       case_insensitive: bool = False) -> list:
    """
    Build the list of SQLAlchemy ``where`` conditions for the provided filters (``None`` means no filter on that
    field). Each scalar filter accepts a single value or a list of values; an entry matches the field if it equals any
    of the values, or (for a value containing a ``*`` wildcard) matches it with a ``LIKE``. Returned as a list so it
    can be applied to both ``select`` and ``delete`` statements. timestamp filters are inclusive on both ends.

    With *case_insensitive* set, plain (non-wildcard) filter values match case-insensitively; wildcard values always
    match case-insensitively (see :func:`match_condition`).
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
        AuthenticationLog.attempt_id: attempt_id,
        AuthenticationLog.client_label: client_label,
    }
    conditions = [condition for column, value in match_filters.items()
                  if (condition := match_condition(column, value, case_insensitive)) is not None]
    if start_time is not None:
        conditions.append(AuthenticationLog.timestamp >= _naive_utc(start_time))
    if end_time is not None:
        conditions.append(AuthenticationLog.timestamp <= _naive_utc(end_time))
    return conditions


def _outcome_condition(ca_action_type: str | list[str] | None = None,
                       ca_policy_name: str | list[str] | None = None,
                       ca_dry_run: bool | None = None,
                       case_insensitive: bool = False) -> ColumnElement[bool] | None:
    """
    Build the condition "this entry has a conditional-access outcome like this", or ``None`` when none of the outcome
    filters is set.

    The string filters behave like every other filter on the log (a value or a list of them, ``*`` as the only
    wildcard, *case_insensitive* for the plain values -- see :func:`match_condition`); ``ca_dry_run`` is a boolean, so
    ``None`` means "either" rather than "unset". ``ca_action_type="*"`` therefore reads as "entries conditional access
    acted on at all".

    **All conditions apply to the same outcome row.** An entry matches when *one* of its outcomes satisfies all of
    them, which is what the filter says: ``ca_action_type=LOCK_USER`` with ``ca_policy_name=Notify`` must not match a
    request where *Notify* sent an email and some other policy locked the user.

    An ``EXISTS`` rather than a join, for the reason the listing reads the outcomes with ``selectinload``
    (:func:`get_authentication_logs_paginate`): a join multiplies an entry by its outcomes, which would break both the
    page's ``LIMIT`` and the ``count`` that shares these conditions -- an entry with three matching outcomes would be
    counted three times and appear three times.

    :param ca_action_type: match outcomes with this ``action_type`` (a ``LockoutAction`` value)
    :param ca_policy_name: match outcomes recorded for this policy name (the denormalized copy, so a deleted policy is
        still matchable)
    :param ca_dry_run: match only dry-run outcomes (``True``) or only enforced ones (``False``)
    :param case_insensitive: match the plain string values case-insensitively
    """
    terms = [condition for column, value in ((ConditionalAccessOutcome.action_type, ca_action_type),
                                             (ConditionalAccessOutcome.policy_name, ca_policy_name))
             if (condition := match_condition(column, value, case_insensitive)) is not None]
    if ca_dry_run is not None:
        terms.append(ConditionalAccessOutcome.dry_run.is_(ca_dry_run))
    if not terms:
        return None
    return (select(1)
            .where(ConditionalAccessOutcome.auth_log_id == AuthenticationLog.id, *terms)
            .exists())


def _visibility_condition(scopes: list[AuthenticationLogVisibilityScope]) -> ColumnElement[bool]:
    """
    Build a single ``where`` condition restricting the visible entries to the given scopes: an entry must match all
    dimensions a scope sets (AND), and is included if it matches any one scope (OR). Entries with a NULL value in a
    restricted dimension are excluded.

    The visibility scope is an authorization boundary (which entries a principal may see). Each dimension matches by
    equality via a plain ``IN`` (which keeps the column index). The boundary columns (realm, resolver, username) are
    pinned to a **case-sensitive collation** at the schema level
    (:func:`~privacyidea.models.authentication_log._case_sensitive_unicode`: ``utf8mb4_bin`` on MySQL/MariaDB; SQLite,
    PostgreSQL and Oracle compare case-sensitively by default), so the match is case-sensitive on every backend rather
    than depending on the server-default collation. This fails closed: an admin scoped to resolver ``res`` or user
    ``alice`` never sees a distinct ``Res`` / ``Alice``.

    The one exception is the **username** dimension when the originating policy set ``user_case_insensitive`` (carried
    on the scope): it is then matched case-insensitively via ``LOWER()`` on both sides -- only this dimension, mirroring
    how that policy option is applied during policy matching. realm and resolver are always case-sensitive (realm is
    additionally always stored lower case, so its casing never varies in practice).

    An empty scope list (or scopes that set no dimension at all) restricts to *nothing*: it returns ``false()`` rather
    than an empty ``or_()``, so the visibility boundary fails closed instead of degrading to "no restriction".
    """
    scope_conditions = []
    for scope in scopes:
        dimensions = []
        if scope.realms:
            dimensions.append(AuthenticationLog.realm.in_(scope.realms))
        if scope.resolvers:
            dimensions.append(AuthenticationLog.resolver.in_(scope.resolvers))
        if scope.usernames:
            if scope.username_case_insensitive:
                dimensions.append(func.lower(AuthenticationLog.username).in_([name.lower()
                                                                              for name in scope.usernames]))
            else:
                dimensions.append(AuthenticationLog.username.in_(scope.usernames))
        if scope.user_roles:
            dimensions.append(AuthenticationLog.user_role.in_([str(role) for role in scope.user_roles]))
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
                            attempt_id: str | list[str] | None = None,
                            client_label: str | list[str] | None = None,
                            start_time: datetime | None = None,
                            end_time: datetime | None = None) -> Sequence[AuthenticationLog]:
    """
    Return authentication log entries matching all provided filter criteria, ordered by id (i.e. chronologically).
    All parameters are optional; omitting a parameter means no filtering on that field. Each scalar filter accepts a
    single value or a list of values; an entry matches the field if it equals any of the listed values, or (for a
    value containing a ``*`` wildcard) matches it with a ``LIKE``. timestamp filters are inclusive on both ends.
    """
    conditions = _filter_conditions(resolver=resolver, uid=uid, realm=realm, username=username, user_role=user_role,
                                    event_type=event_type,
                                    source_ip=source_ip, serial=serial, transaction_id=transaction_id,
                                    attempt_id=attempt_id,
                                    client_label=client_label,
                                    start_time=start_time, end_time=end_time)
    stmt = select(AuthenticationLog).where(*conditions).order_by(AuthenticationLog.id)
    return get_ca_session().scalars(stmt).all()


def get_authentication_logs_paginate(resolver: str | list[str] | None = None,
                                     uid: str | list[str] | None = None,
                                     realm: str | list[str] | None = None,
                                     username: str | list[str] | None = None,
                                     user_role: str | list[str] | None = None,
                                     event_type: str | list[str] | None = None,
                                     source_ip: str | list[str] | None = None,
                                     serial: str | list[str] | None = None,
                                     transaction_id: str | list[str] | None = None,
                                     attempt_id: str | list[str] | None = None,
                                     client_label: str | list[str] | None = None,
                                     ca_action_type: str | list[str] | None = None,
                                     ca_policy_name: str | list[str] | None = None,
                                     ca_dry_run: bool | None = None,
                                     start_time: datetime | None = None,
                                     end_time: datetime | None = None,
                                     visibility_scopes: list[AuthenticationLogVisibilityScope] | None = None,
                                     case_insensitive: bool = False,
                                     page: int = 1,
                                     page_size: int = DEFAULT_PAGE_SIZE,
                                     sort_column: str = "id",
                                     sort_order: str = "desc") -> AuthenticationLogPage:
    """
    Return a single page of authentication log entries matching the given filters.

    The filter parameters -- ``resolver``, ``uid``, ``realm``, ``username``, ``user_role``, ``event_type``,
    ``source_ip``, ``serial``, ``transaction_id``, ``attempt_id``, ``client_label``,
    ``start_time`` and
    ``end_time`` -- behave
    exactly like :func:`get_authentication_logs`. The ``ca_*`` parameters filter on what conditional access *did* to the
    request and are only offered here, since this is the endpoint that reads the outcomes:

    :param ca_action_type: only entries with an outcome of this action type; ``"*"`` reads as "conditional access acted
        on this request at all"
    :param ca_policy_name: only entries with an outcome recorded for this policy name
    :param ca_dry_run: only entries with a dry-run outcome (``True``) or with an enforced one (``False``); ``None``
        does not filter
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
                                    attempt_id=attempt_id,
                                    client_label=client_label,
                                    start_time=start_time, end_time=end_time,
                                    case_insensitive=case_insensitive)
    # An EXISTS over the outcome table, kept out of _filter_conditions because those conditions also apply to DELETE
    # statements (see delete_authentication_logs), and matching an outcome is not a valid reason to delete an entry.
    outcome_condition = _outcome_condition(ca_action_type=ca_action_type, ca_policy_name=ca_policy_name,
                                           ca_dry_run=ca_dry_run, case_insensitive=case_insensitive)
    if outcome_condition is not None:
        conditions.append(outcome_condition)
    if visibility_scopes is not None:
        conditions.append(_visibility_condition(visibility_scopes))
    stmt = select(AuthenticationLog).where(*conditions)

    count = get_ca_session().scalar(select(func.count()).select_from(AuthenticationLog).where(*conditions))

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
    # The only place that eagerly loads conditional-access outcomes: selectinload fetches a whole page's outcomes in
    # one extra statement, so the statement count does not grow with the page size, whereas a JOIN would multiply
    # each entry by its outcomes and break both LIMIT and the count above.
    stmt = stmt.options(selectinload(AuthenticationLog.outcomes))
    auth_logs = get_ca_session().scalars(stmt.limit(page_size).offset(offset)).all()
    return AuthenticationLogPage(auth_logs=auth_logs,
                                 count=count,
                                 current=page,
                                 prev=page - 1 if page > 1 else None,
                                 next=page + 1 if offset + page_size < count else None)


def _delete_outcomes_of(criterion: ColumnElement[bool], chunk_size: int | None = None) -> int:
    """
    Delete the conditional-access outcomes of every authentication-log row matching *criterion*, and return how many
    were removed.

    Always called **before** the parent rows: the ``auth_log_id`` foreign key cascades on MySQL/MariaDB and PostgreSQL
    but not on SQLite, where ``PRAGMA foreign_keys`` is off by default and privacyIDEA never enables it. Deleting the
    children explicitly is what makes all supported backends behave the same.

    An ORM ``cascade="all, delete-orphan"`` relationship would **not** do this job. That cascade is only consulted when
    a mapped object is deleted through the session (``session.delete(entry)``); every delete path here is set-based Core
    SQL - ``table.delete().where(...)``, or ``DeleteLimit`` when chunking - which SQLAlchemy does not run relationship
    cascades for. Declaring one would leave the children behind on SQLite while looking like it handled them. Loading
    every doomed parent to delete it object-by-object is the only way to make the cascade fire, and that defeats the
    point of :func:`~privacyidea.lib.sqlutils.delete_matching_rows`: retention has to remove millions of rows with
    bounded memory.

    The children are matched through the parents (``auth_log_id IN (SELECT id FROM authentication_log WHERE …)``).

    This commits separately from the parent delete (:func:`~privacyidea.lib.sqlutils.delete_matching_rows` commits per
    call, and chunked deletes commit per chunk). A failure of the parent delete afterwards therefore leaves entries
    whose history is already gone - acceptable for a management operation, where the alternative is holding one
    transaction open across an unbounded number of chunked deletes.
    """
    return delete_matching_rows(get_ca_session(), ConditionalAccessOutcome.__table__,
                                ConditionalAccessOutcome.auth_log_id.in_(select(AuthenticationLog.id).where(criterion)),
                                chunk_size)


def _delete_entries(criterion: ColumnElement[bool], chunk_size: int | None = None) -> int:
    """
    Delete the authentication-log rows matching *criterion* **together with their conditional-access outcomes**, and
    return how many entries were removed.

    Every set-based delete of authentication-log rows goes through here (the single-row path,
    :func:`delete_authentication_log_event`, does both deletes in one transaction instead). That is deliberate: neither
    an explicit call per delete path nor an ORM cascade is self-enforcing, so the one thing that can be enforced is that
    there is a single place to route through - a new delete path calls this instead of assembling the two halves again.

    :param criterion: the ``where`` clause selecting the entries to delete
    :param chunk_size: delete in chunks of this size to avoid long locks on large tables
    :return: the number of authentication-log entries deleted (the outcome count is logged, not returned: the caller
        asked to delete entries, and their history is part of them)
    """
    outcomes = _delete_outcomes_of(criterion, chunk_size)
    deleted = delete_matching_rows(get_ca_session(), AuthenticationLog.__table__, criterion, chunk_size)
    if outcomes:
        log.debug(f"Deleted {outcomes} conditional-access outcome(s) along with {deleted} authentication log entries.")
    return deleted


def delete_authentication_logs(resolver: str | list[str] | None = None,
                               uid: str | list[str] | None = None,
                               realm: str | list[str] | None = None,
                               username: str | list[str] | None = None,
                               user_role: str | list[str] | None = None,
                               event_type: str | list[str] | None = None,
                               source_ip: str | list[str] | None = None,
                               serial: str | list[str] | None = None,
                               transaction_id: str | list[str] | None = None,
                               attempt_id: str | list[str] | None = None,
                               client_label: str | list[str] | None = None,
                               start_time: datetime | None = None,
                               end_time: datetime | None = None,
                               visibility_scopes: list[AuthenticationLogVisibilityScope] | None = None,
                               chunk_size: int | None = None) -> int:
    """
    Delete all authentication log entries matching the given filters and return the number deleted.

    The filter parameters -- ``resolver``, ``uid``, ``realm``, ``username``, ``user_role``, ``event_type``,
    ``source_ip``, ``serial``, ``transaction_id``, ``attempt_id``, ``client_label``,
    ``start_time`` and
    ``end_time`` -- behave exactly like :func:`get_authentication_logs` (to delete entries older than a point in time,
    pass ``end_time``). The caller must pass at least one filter: with no filter this would delete the entire log,
    which this function refuses.

    :param visibility_scopes: restrict the deletion to entries matching any of these scopes
        (see :func:`_visibility_condition`); ``None`` means no restriction
    :param chunk_size: if given, delete in chunks of this size to avoid long locks on large tables
    :return: the number of deleted entries
    """
    conditions = _filter_conditions(resolver=resolver, uid=uid, realm=realm, username=username, user_role=user_role,
                                    event_type=event_type,
                                    source_ip=source_ip, serial=serial, transaction_id=transaction_id,
                                    attempt_id=attempt_id,
                                    client_label=client_label,
                                    start_time=start_time, end_time=end_time)
    # Guard on the caller's filters before adding the visibility restriction, so a scoped admin also cannot wipe a
    # whole scope with an unfiltered request.
    if not conditions:
        raise ParameterError("Refusing to delete the whole authentication log: at least one filter is required.")
    if visibility_scopes is not None:
        conditions.append(_visibility_condition(visibility_scopes))
    return _delete_entries(and_(*conditions), chunk_size)


def cleanup_authentication_log(older_than: datetime, chunk_size: int | None = None) -> int:
    """
    Delete all authentication log entries with a timestamp strictly older than the given datetime.

    :param older_than: delete entries whose timestamp is older than this (naive or timezone-aware; aware values are
        converted to UTC)
    :param chunk_size: if given, delete in chunks of this size to avoid long locks / deadlocks on large tables
    :return: the number of deleted rows
    """
    return _delete_entries(AuthenticationLog.timestamp < _naive_utc(older_than), chunk_size)
