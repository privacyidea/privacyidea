# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
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
"""
Management layer for the live conditional-access state: user lockouts
(:class:`~privacyidea.models.lockout_policy.UserLockoutState`) and the blocklist
(:class:`~privacyidea.models.lockout_policy.BlockList`).

The engine (:mod:`privacyidea.lib.conditional_access.engine`) *writes* this state
when a policy stage fires and *reads* it on the authentication pre-check. This
module is the *management* path — listing the current state and clearing single
entries — shared by the REST API (``/conditionalaccess``) and the
``pi-manage conditionalaccess`` CLI, so both go through one implementation.
"""
import logging
from datetime import datetime

from sqlalchemy import and_, delete, false, func, or_, select, ColumnElement

from privacyidea.lib.conditional_access.authentication_log import match_condition
from privacyidea.lib.conditional_access.engine import get_user_lockout
from privacyidea.lib.conditional_access.session import get_ca_session, guarded_write
from privacyidea.lib.error import ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.user import User
from privacyidea.models.lockout_policy import BlockList, UserLockoutState
from privacyidea.models.utils import utc_now

log = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 15

# The lock "state" is derived from lock_expires_at vs. now:
#   permanent  -> lock_expires_at IS NULL
#   temporary  -> lock_expires_at in the future  (actively locked, will lift on its own)
#   expired    -> lock_expires_at in the past     (stale record, no longer enforced)
LOCK_STATES = ("permanent", "temporary", "expired")

# Columns the locked-users list may be sorted by (any other value falls back to locked_at).
SORTABLE_COLUMNS = {
    "username": UserLockoutState.username,
    "realm": UserLockoutState.realm,
    "resolver": UserLockoutState.resolver,
    "lock_expires_at": UserLockoutState.lock_expires_at,
    "locked_at": UserLockoutState.locked_at,
}


def _delete_and_commit(stmt) -> int:
    """
    Execute a ``DELETE`` on the conditional-access session, commit it, and return the number of rows removed.

    The engine's delete helpers swallow failures because they run while an authentication response is
    still in flight. These are management operations instead: the caller reports the outcome back to an
    admin, so a failure has to surface rather than be indistinguishable from "nothing matched" — hence
    ``reraise``. The rollback still leaves the session usable for the rest of the request (which has its
    audit entry to write).
    """
    with guarded_write("a conditional-access state deletion", reraise=True):
        count = get_ca_session().execute(stmt).rowcount
    return count


def _seconds_remaining(expires_at: datetime | None, now: datetime) -> int | None:
    if expires_at is None:
        return None
    return max(0, int((expires_at - now).total_seconds()))


def _not_expired_condition(expiry_column, now: datetime):
    # Currently in force: a permanent restriction (NULL expiry) or a timed one whose expiry is still ahead.
    return or_(expiry_column.is_(None), expiry_column > now)


def _state_condition(states: list[str] | None, now: datetime) -> ColumnElement[bool] | None:
    """
    WHERE clause selecting the requested lock *states* (see :data:`LOCK_STATES`), OR-ed together. An
    unknown value is a :class:`ParameterError` rather than a silently ignored term: ignoring it would
    widen the result to *all* states, so a typo would return more than the caller asked for. ``None`` is
    returned only when no state is requested at all (no state restriction — all states, incl. expired).

    :raises ParameterError: if *states* contains a value outside :data:`LOCK_STATES`
    """
    unknown = [state for state in (states or []) if state not in LOCK_STATES]
    if unknown:
        raise ParameterError(f"Unknown lock state(s) {', '.join(sorted(unknown))}. "
                             f"Allowed values: {', '.join(LOCK_STATES)}.")
    clauses = []
    for state in (states or []):
        if state == "permanent":
            clauses.append(UserLockoutState.lock_expires_at.is_(None))
        elif state == "temporary":
            clauses.append(and_(UserLockoutState.lock_expires_at.isnot(None),
                                UserLockoutState.lock_expires_at > now))
        elif state == "expired":
            clauses.append(and_(UserLockoutState.lock_expires_at.isnot(None),
                                UserLockoutState.lock_expires_at <= now))
    return or_(*clauses) if clauses else None


def _locked_user_dict(row: UserLockoutState, now: datetime) -> dict:
    return {
        "resolver": row.resolver,
        "uid": row.uid,
        "realm": row.realm,
        # Denormalized login captured at lock time (survives resolver deletion).
        "username": row.username,
        "permanent": row.lock_expires_at is None,
        "lock_expires_at": row.lock_expires_at,
        "seconds_remaining": _seconds_remaining(row.lock_expires_at, now),
        "locked_at": row.locked_at
    }


def _blocklist_dict(row: BlockList, now: datetime) -> dict:
    return {
        "identifier": row.ip,
        "permanent": row.block_expires_at is None,
        "block_expires_at": row.block_expires_at,
        "seconds_remaining": _seconds_remaining(row.block_expires_at, now),
        "blocked_at": row.blocked_at,
    }


def _visibility_condition(scopes: list) -> ColumnElement[bool]:
    """
    Build a WHERE clause restricting the lockout query to the admin's visibility
    *scopes*: a row matches all dimensions a scope sets (AND) and is included if
    it matches any scope (OR); an empty/unsatisfiable boundary returns ``false()``
    so it fails closed.

    Realm, resolver and username are all enforced (username via the denormalized
    ``UserLockoutState.username`` column, honoring the policy's
    ``user_case_insensitive`` option like the auth log).
    """
    scope_conditions = []
    for scope in scopes:
        dimensions = []
        if scope.realms:
            dimensions.append(UserLockoutState.realm.in_(scope.realms))
        if scope.resolvers:
            dimensions.append(UserLockoutState.resolver.in_(scope.resolvers))
        if scope.usernames:
            if scope.username_case_insensitive:
                dimensions.append(func.lower(UserLockoutState.username).in_(
                    [name.lower() for name in scope.usernames]))
            else:
                dimensions.append(UserLockoutState.username.in_(scope.usernames))
        if dimensions:
            scope_conditions.append(and_(*dimensions))
    if not scope_conditions:
        return false()
    return or_(*scope_conditions)


def user_matches_scopes(user: User, scopes: list | None) -> bool:
    """
    Whether a fully-resolved *user* falls within any of the admin's visibility
    *scopes* (``None`` = unrestricted).
    """
    if scopes is None:
        return True
    for scope in scopes:
        if scope.realms and user.realm not in scope.realms:
            continue
        if scope.resolvers and user.resolver not in scope.resolvers:
            continue
        if scope.usernames:
            login = user.login or ""
            if scope.username_case_insensitive:
                if login.lower() not in [name.lower() for name in scope.usernames]:
                    continue
            elif login not in scope.usernames:
                continue
        return True
    return False


def _lockout_conditions(realms: list[str] | None, resolvers: list[str] | None,
                        usernames: list[str] | None, states: list[str] | None,
                        visibility_scopes: list | None, now: datetime,
                        case_insensitive: bool) -> list[ColumnElement[bool]]:
    """
    Build the WHERE conditions for a locked-users query.

    The realm/resolver/username *filters* are separate AND clauses from the case-sensitive authorization
    boundary (``visibility_scopes``), so search behaviour never widens the visibility scope.

    :param realms: realm(s) to match (wildcard ``*`` per value); ``None``/empty means no realm filter
    :param resolvers: resolver(s) to match (wildcard ``*`` per value); ``None``/empty means no resolver filter
    :param usernames: login(s) to match (wildcard ``*`` per value); ``None``/empty means no username filter
    :param states: lock state(s) to include (see :func:`_state_condition`); ``None``/empty means no state
        filter (all states, including expired)
    :param visibility_scopes: the admin's policy visibility boundary (see :func:`_visibility_condition`);
        ``None`` means unrestricted
    :param now: the reference time used to classify temporary vs. expired
    :param case_insensitive: match the realm/resolver/username filter values case-insensitively
    :return: the list of SQLAlchemy ``where`` conditions (AND-ed by the caller)
    """
    conditions: list[ColumnElement[bool]] = []
    for column, value in ((UserLockoutState.realm, realms),
                          (UserLockoutState.resolver, resolvers),
                          (UserLockoutState.username, usernames)):
        condition = match_condition(column, value, case_insensitive)
        if condition is not None:
            conditions.append(condition)
    state_condition = _state_condition(states, now)
    if state_condition is not None:
        conditions.append(state_condition)
    if visibility_scopes is not None:
        conditions.append(_visibility_condition(visibility_scopes))
    return conditions


@log_with(log)
def list_locked_users(realms: list[str] | None = None, resolvers: list[str] | None = None,
                      usernames: list[str] | None = None, states: list[str] | None = None,
                      visibility_scopes: list | None = None, case_insensitive: bool = False,
                      now: datetime | None = None) -> list[dict]:
    """
    Return all matching locked users (no pagination), most recently updated first. See
    :func:`_lockout_conditions` for the filter/scoping semantics and
    :func:`list_locked_users_paginate` for the paginated variant.
    """
    moment = now if now is not None else utc_now()
    conditions = _lockout_conditions(realms, resolvers, usernames, states,
                                     visibility_scopes, moment, case_insensitive)
    stmt = select(UserLockoutState).where(*conditions).order_by(UserLockoutState.locked_at.desc())
    return [_locked_user_dict(row, moment) for row in get_ca_session().scalars(stmt).all()]


@log_with(log)
def list_locked_users_paginate(realms: list[str] | None = None, resolvers: list[str] | None = None,
                               usernames: list[str] | None = None, states: list[str] | None = None,
                               visibility_scopes: list | None = None, case_insensitive: bool = False,
                               page: int = 1, page_size: int = DEFAULT_PAGE_SIZE,
                               sort_column: str = "locked_at", sort_order: str = "desc",
                               now: datetime | None = None) -> dict:
    """
    Return one page of matching locked users plus pagination metadata
    ``{locked_users, count, current, prev, next}`` — the counterpart of
    :func:`list_locked_users` for the WebUI table. Filter/scoping semantics are as
    :func:`_lockout_conditions`; sorting is by one of :data:`SORTABLE_COLUMNS`
    (fallback ``locked_at``), always tie-broken by the primary key for a stable
    order across pages.
    """
    moment = now if now is not None else utc_now()
    conditions = _lockout_conditions(realms, resolvers, usernames, states,
                                     visibility_scopes, moment, case_insensitive)
    count = get_ca_session().scalar(
        select(func.count()).select_from(UserLockoutState).where(*conditions))
    order_column = SORTABLE_COLUMNS.get(sort_column)
    if order_column is None:
        log.warning(f"Unknown sort column '{sort_column}'. Using 'locked_at' instead.")
        order_column = UserLockoutState.locked_at
    tiebreak = (UserLockoutState.resolver, UserLockoutState.uid, UserLockoutState.realm)
    direction = (lambda col: col.asc()) if sort_order == "asc" else (lambda col: col.desc())
    stmt = (select(UserLockoutState).where(*conditions)
            .order_by(direction(order_column), *[direction(col) for col in tiebreak]))
    page = max(1, page)
    page_size = max(1, page_size)
    offset = (page - 1) * page_size
    rows = get_ca_session().scalars(stmt.limit(page_size).offset(offset)).all()
    return {
        "locked_users": [_locked_user_dict(row, moment) for row in rows],
        "count": count,
        "current": page,
        "prev": page - 1 if page > 1 else None,
        "next": page + 1 if offset + page_size < count else None,
    }


def get_user_lockout_dict(user: User, now: datetime | None = None) -> dict | None:
    """
    Return *user*'s current lock in the same shape as :func:`list_locked_users`,
    or ``None`` if the user is not currently locked. The active/expiry decision
    is delegated to :func:`~privacyidea.lib.conditional_access.engine.get_user_lockout`
    so this always agrees with the authentication pre-check.
    """
    status = get_user_lockout(user, now=now)
    if status is None:
        return None
    row = get_ca_session().get(UserLockoutState, (user.resolver, user.uid, user.realm))
    return _locked_user_dict(row, now if now is not None else utc_now())


@log_with(log)
def unlock_user_by_id(uid: str, realm: str, resolver: str | None = None,
                      visibility_scopes: list | None = None) -> bool:
    """
    Delete the lock(s) for a ``(uid, realm[, resolver])`` identity. Returns
    ``True`` if any row was removed, ``False`` if there was no lock. Like
    :func:`unlock_user_by_username`, this performs **no** live resolver lookup —
    it matches the stored row columns directly, so it works even for a user that
    no longer resolves or whose login has since changed.

    ``resolver`` is optional and only narrows the match when supplied — mirroring
    :func:`unlock_user_by_username` (resolver is always a disambiguator, never a
    required part of the key). Omitting the resolver clears the lock for **every**
    matching uid in the realm; pass a resolver to target exactly one.

    ``visibility_scopes`` is the caller's authorization boundary (see
    :func:`_visibility_condition`); ``None`` means unrestricted. It is part of the
    ``DELETE`` criterion rather than a pre-flight check because one call may match
    several rows: a scoped admin must not clear a row outside their boundary via a
    call that also matches one inside it. An out-of-scope target is therefore
    indistinguishable from an absent lock — both return ``False``.
    """
    conditions = [UserLockoutState.uid == uid, UserLockoutState.realm == realm]
    if resolver:
        conditions.append(UserLockoutState.resolver == resolver)
    if visibility_scopes is not None:
        conditions.append(_visibility_condition(visibility_scopes))
    return _delete_and_commit(delete(UserLockoutState).where(*conditions)) > 0


@log_with(log)
def unlock_user_by_username(username: str, realm: str, resolver: str | None = None,
                            visibility_scopes: list | None = None) -> bool:
    """
    Delete the lock(s) for a ``(username, realm[, resolver])`` identity. Returns
    ``True`` if any row was removed, ``False`` if there was no lock. ``username``
    is the denormalized login and is not unique, so more than one row may match
    (e.g. a stale row from a since-recreated login, or the same login across
    resolvers); all matches are removed. ``resolver`` is optional and only
    narrows the match when supplied.

    ``visibility_scopes`` restricts the delete to the caller's authorization
    boundary exactly as in :func:`unlock_user_by_id`.
    """
    conditions = [UserLockoutState.username == username, UserLockoutState.realm == realm]
    if resolver:
        conditions.append(UserLockoutState.resolver == resolver)
    if visibility_scopes is not None:
        conditions.append(_visibility_condition(visibility_scopes))
    return _delete_and_commit(delete(UserLockoutState).where(*conditions)) > 0


@log_with(log)
def list_blocklist(include_expired: bool = True, now: datetime | None = None) -> list[dict]:
    """
    Return the blocklist entries, most recently updated first. Each row carries the
    expiry fields (``permanent`` / ``block_expires_at`` / ``seconds_remaining``),
    so the caller can tell a currently-enforced block from a stale, expired record.
    The never-block allowlist is an enforcement-time concern and is *not* applied
    here, so an admin can see and clean up a row even for a never-enforced IP.

    :param include_expired: also return stale rows whose timed block has expired.
        Defaults to ``True``: a management view lists what is *on record* and the
        caller tells the two apart from the expiry fields. Pass ``False`` to get
        only the blocks still in force.
    :param now: reference time; defaults to :func:`utc_now`
    """
    moment = now if now is not None else utc_now()
    conditions: list[ColumnElement[bool]] = []
    if not include_expired:
        conditions.append(_not_expired_condition(BlockList.block_expires_at, moment))
    stmt = select(BlockList).where(*conditions).order_by(BlockList.blocked_at.desc())
    return [_blocklist_dict(row, moment) for row in get_ca_session().scalars(stmt).all()]


@log_with(log)
def remove_blocklist_entry(entry: str) -> bool:
    """
    Remove a single blocklist entry by its identifier (a source IP today).
    Returns ``True`` if a row was removed, ``False`` if there was no entry.
    """
    return _delete_and_commit(delete(BlockList).where(BlockList.ip == entry)) > 0


@log_with(log)
def purge_expired_user_lockouts(now: datetime | None = None, visibility_scopes: list | None = None) -> int:
    """
    Delete user-lockout rows that are no longer in force — a timed lock past its
    expiry. Permanent locks (``lock_expires_at IS NULL``) and active timed locks
    are kept. Nothing writes these rows off on its own, so this is the
    housekeeping that clears stale records. Returns the number of rows removed.

    ``visibility_scopes`` restricts the purge to the caller's authorization
    boundary (see :func:`_visibility_condition`); ``None`` means unrestricted.
    A scoped admin only clears the stale rows they can see, so the returned count
    is the number they were allowed to remove.
    """
    now = now or utc_now()
    conditions = [UserLockoutState.lock_expires_at.isnot(None), UserLockoutState.lock_expires_at <= now]
    if visibility_scopes is not None:
        conditions.append(_visibility_condition(visibility_scopes))
    return _delete_and_commit(delete(UserLockoutState).where(and_(*conditions)))


@log_with(log)
def purge_expired_blocklist(now: datetime | None = None) -> int:
    """
    Delete blocklist rows that are no longer in force — a timed block past its
    expiry. Permanent blocks and active timed blocks are kept. Returns the number
    of rows removed.
    """
    now = now or utc_now()
    return _delete_and_commit(delete(BlockList).where(
        and_(BlockList.block_expires_at.isnot(None),
             BlockList.block_expires_at <= now)))
