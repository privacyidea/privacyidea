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
Management layer for the live conditional-access state: user locks
(:class:`~privacyidea.models.conditional_access_policy.UserLockState`) and the blocklist
(:class:`~privacyidea.models.conditional_access_policy.BlockList`).

The engine (:mod:`privacyidea.lib.conditional_access.engine`) *writes* this state
when a policy stage fires and *reads* it on the authentication pre-check. This
module is the *management* path — listing the current state, imposing a
restriction by administrator decision and clearing single entries — shared by the
REST API (``/conditionalaccess``) and the ``pi-manage conditionalaccess`` CLI, so
both go through one implementation.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, delete, false, func, or_, select, ColumnElement

from privacyidea.lib.conditional_access.authentication_event_types import AuthLogUserRole, RestrictionCause
from privacyidea.lib.conditional_access.authentication_log import match_condition
from privacyidea.lib.conditional_access.engine import (LockSubject, canonical_block_identifier, get_user_lock,
                                                       is_ip_never_block)
from privacyidea.lib.conditional_access.session import get_ca_session, guarded_write
from privacyidea.lib.error import ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.user import User
from privacyidea.models.conditional_access_policy import BlockList, UserLockState
from privacyidea.models.utils import utc_now

log = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 15

# The lock state is derived from lock_expires_at vs. now: permanent means NULL, temporary means the expiry is
# still ahead (in force, lifts on its own), and expired means it has passed (a stale record, no longer enforced).
#: The states a user-lock record can be in, as accepted by the ``states`` query parameter.
LOCK_STATES = ("permanent", "temporary", "expired")

# Who imposed the restriction now in force; see :class:`RestrictionCause`.
#: Who imposed the restriction now in force, as accepted by the ``causes`` query parameter.
LOCK_CAUSES = tuple(cause.value for cause in RestrictionCause)

# Columns the locked-users list may be sorted by (any other value falls back to locked_at).
#: The columns a paginated locked-users query may sort by, keyed by the name the API accepts.
SORTABLE_COLUMNS = {
    "username": UserLockState.username,
    "realm": UserLockState.realm,
    "resolver": UserLockState.resolver,
    "lock_expires_at": UserLockState.lock_expires_at,
    "lock_cause": UserLockState.lock_cause,
    "locked_at": UserLockState.locked_at,
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
            clauses.append(UserLockState.lock_expires_at.is_(None))
        elif state == "temporary":
            clauses.append(and_(UserLockState.lock_expires_at.isnot(None),
                                UserLockState.lock_expires_at > now))
        elif state == "expired":
            clauses.append(and_(UserLockState.lock_expires_at.isnot(None),
                                UserLockState.lock_expires_at <= now))
    return or_(*clauses) if clauses else None


def _locked_user_dict(row: UserLockState, now: datetime) -> dict:
    return {
        "resolver": row.resolver,
        "uid": row.uid,
        "realm": row.realm,
        # Denormalized login captured at lock time (survives resolver deletion).
        "username": row.username,
        # Which kind of principal this row locks. A local database admin is keyed by login name alone, so their row
        # carries an empty resolver and realm - this is what says the row means that, rather than a user whose
        # realm has gone missing.
        "user_role": row.user_role,
        "permanent": row.lock_expires_at is None,
        "lock_expires_at": row.lock_expires_at,
        "seconds_remaining": _seconds_remaining(row.lock_expires_at, now),
        # Whether a policy or an administrator imposed the lock now in force.
        "lock_cause": row.lock_cause,
        "locked_at": row.locked_at,
        # The error message this user is being shown, as stored when the lock was written - a snapshot, so it can differ
        # from what the policy says now. Empty when the stage configured none, which is the silent default.
        "error_message": row.error_message
    }


def _blocklist_dict(row: BlockList, now: datetime) -> dict:
    # Reported as "identifier", not "ip": the API shape is already the generic one the table will grow into when
    # non-IP entries (device, API key) become blockable.
    return {
        "identifier": row.ip,
        "permanent": row.block_expires_at is None,
        "block_expires_at": row.block_expires_at,
        "seconds_remaining": _seconds_remaining(row.block_expires_at, now),
        "block_cause": row.block_cause,
        "blocked_at": row.blocked_at,
        # See _locked_user_dict: the wording stored on the row, not what the policy carries now.
        "error_message": row.error_message,
    }


def _visibility_condition(scopes: list) -> ColumnElement[bool]:
    """
    Build a WHERE clause restricting the lock query to the admin's visibility
    *scopes*: a row matches all dimensions a scope sets (AND) and is included if
    it matches any scope (OR); an empty/unsatisfiable boundary returns ``false()``
    so it fails closed.

    Realm, resolver, uid and username are all enforced (username via the
    denormalized ``UserLockState.username`` column, honoring the policy's
    ``user_case_insensitive`` option like the auth log).

    A scope that names no ``user_roles`` does not reach the rows of a **local database administrator**. Realm,
    resolver and user are userstore terms, and none of them describes such an account, whose row carries a login
    name and nothing else, so a boundary drawn only in those terms does not contain one. Without this, a policy
    scoped to a user name would reach a local admin of that name - by coincidence of the shared ``username``
    column rather than by anyone's intent, and the admin policy the boundary comes from has no way to say
    otherwise, carrying only realm, resolver and user (see
    :func:`~privacyidea.lib.policies.helper.get_policy_visibility_scopes`). A local admin's rows are therefore
    reachable only by a caller that is unscoped altogether, or by a scope naming the role outright - which is how
    a scoped admin still sees their **own** entries.
    """
    scope_conditions = []
    for scope in scopes:
        dimensions = []
        if scope.realms:
            dimensions.append(UserLockState.realm.in_(scope.realms))
        if scope.resolvers:
            dimensions.append(UserLockState.resolver.in_(scope.resolvers))
        if scope.uids:
            dimensions.append(UserLockState.uid.in_(scope.uids))
        if scope.usernames:
            if scope.username_case_insensitive:
                dimensions.append(func.lower(UserLockState.username).in_(
                    [name.lower() for name in scope.usernames]))
            else:
                dimensions.append(UserLockState.username.in_(scope.usernames))
        if scope.user_roles:
            dimensions.append(UserLockState.user_role.in_([str(role) for role in scope.user_roles]))
        elif dimensions:
            # Stated as "not a local admin" rather than "is a user", as the auth log states it: this column is
            # never null, but the boundary is about the one role that must stay out of reach, not about the rest.
            dimensions.append(UserLockState.user_role != str(AuthLogUserRole.ADMIN_INTERNAL))
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
        if scope.uids and str(user.uid or "") not in scope.uids:
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


def _cause_condition(causes: list[str] | None) -> ColumnElement[bool] | None:
    """
    WHERE clause selecting the requested lock *causes* (see :data:`LOCK_CAUSES`). An unknown value is a
    :class:`ParameterError` for the same reason :func:`_state_condition` rejects one: silently ignoring it
    would widen the result to every cause, so a typo would return more than the caller asked for.

    :raises ParameterError: if *causes* contains a value outside :data:`LOCK_CAUSES`
    """
    unknown = [cause for cause in (causes or []) if cause not in LOCK_CAUSES]
    if unknown:
        raise ParameterError(f"Unknown lock cause(s) {', '.join(sorted(unknown))}. "
                             f"Allowed values: {', '.join(LOCK_CAUSES)}.")
    return UserLockState.lock_cause.in_(causes) if causes else None


def _lock_conditions(realms: list[str] | None, resolvers: list[str] | None,
                        usernames: list[str] | None, states: list[str] | None,
                        visibility_scopes: list | None, now: datetime,
                        case_insensitive: bool,
                        causes: list[str] | None = None,
                        error_messages: list[str] | None = None) -> list[ColumnElement[bool]]:
    """
    Build the WHERE conditions for a locked-users query.

    The realm/resolver/username *filters* are separate AND clauses from the case-sensitive authorization
    boundary (``visibility_scopes``), so search behaviour never widens the visibility scope.

    :param realms: realm(s) to match (wildcard ``*`` per value); ``None``/empty means no realm filter
    :param resolvers: resolver(s) to match (wildcard ``*`` per value); ``None``/empty means no resolver filter
    :param usernames: login(s) to match (wildcard ``*`` per value); ``None``/empty means no username filter
    :param error_messages: wording to match (wildcard ``*`` per value); ``None``/empty means no message filter.
        Matches the text stored on the row - what those users are actually being shown - so an admin can find
        every lock still quoting a message they have since changed.
    :param states: lock state(s) to include (see :func:`_state_condition`); ``None``/empty means no state
        filter (all states, including expired)
    :param causes: lock cause(s) to include (see :func:`_cause_condition`); ``None``/empty means no cause
        filter (both policy and manual locks)
    :param visibility_scopes: the admin's policy visibility boundary (see :func:`_visibility_condition`);
        ``None`` means unrestricted
    :param now: the reference time used to classify temporary vs. expired
    :param case_insensitive: match the realm/resolver/username filter values case-insensitively
    :return: the list of SQLAlchemy ``where`` conditions (AND-ed by the caller)
    """
    conditions: list[ColumnElement[bool]] = []
    for column, value in ((UserLockState.realm, realms),
                          (UserLockState.resolver, resolvers),
                          (UserLockState.username, usernames),
                          (UserLockState.error_message, error_messages)):
        condition = match_condition(column, value, case_insensitive)
        if condition is not None:
            conditions.append(condition)
    state_condition = _state_condition(states, now)
    if state_condition is not None:
        conditions.append(state_condition)
    cause_condition = _cause_condition(causes)
    if cause_condition is not None:
        conditions.append(cause_condition)
    if visibility_scopes is not None:
        conditions.append(_visibility_condition(visibility_scopes))
    return conditions


@log_with(log)
def list_locked_users(realms: list[str] | None = None, resolvers: list[str] | None = None,
                      usernames: list[str] | None = None, states: list[str] | None = None,
                      visibility_scopes: list | None = None, case_insensitive: bool = False,
                      now: datetime | None = None, causes: list[str] | None = None,
                      error_messages: list[str] | None = None) -> list[dict]:
    """
    Return all matching locked users (no pagination), most recently updated first. See
    :func:`_lock_conditions` for the filter/scoping semantics and
    :func:`list_locked_users_paginate` for the paginated variant.
    """
    moment = now if now is not None else utc_now()
    conditions = _lock_conditions(realms, resolvers, usernames, states,
                                     visibility_scopes, moment, case_insensitive, causes, error_messages)
    stmt = select(UserLockState).where(*conditions).order_by(UserLockState.locked_at.desc())
    return [_locked_user_dict(row, moment) for row in get_ca_session().scalars(stmt).all()]


@log_with(log)
def list_locked_users_paginate(realms: list[str] | None = None, resolvers: list[str] | None = None,
                               usernames: list[str] | None = None, states: list[str] | None = None,
                               visibility_scopes: list | None = None, case_insensitive: bool = False,
                               page: int = 1, page_size: int = DEFAULT_PAGE_SIZE,
                               sort_column: str = "locked_at", sort_order: str = "desc",
                               now: datetime | None = None, causes: list[str] | None = None,
                               error_messages: list[str] | None = None) -> dict:
    """
    Return one page of matching locked users plus pagination metadata
    ``{locked_users, count, current, prev, next}`` — the counterpart of
    :func:`list_locked_users` for the WebUI table. Filter/scoping semantics are as
    :func:`_lock_conditions`; sorting is by one of :data:`SORTABLE_COLUMNS`
    (fallback ``locked_at``), always tie-broken by the primary key for a stable
    order across pages.
    """
    moment = now if now is not None else utc_now()
    conditions = _lock_conditions(realms, resolvers, usernames, states,
                                     visibility_scopes, moment, case_insensitive, causes, error_messages)
    count = get_ca_session().scalar(
        select(func.count()).select_from(UserLockState).where(*conditions))
    order_column = SORTABLE_COLUMNS.get(sort_column)
    if order_column is None:
        log.warning(f"Unknown sort column '{sort_column}'. Using 'locked_at' instead.")
        order_column = UserLockState.locked_at
    tiebreak = (UserLockState.resolver, UserLockState.uid, UserLockState.realm)
    direction = (lambda col: col.asc()) if sort_order == "asc" else (lambda col: col.desc())
    stmt = (select(UserLockState).where(*conditions)
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


def get_user_lock_dict(user: User, now: datetime | None = None) -> dict | None:
    """
    Return *user*'s current lock in the same shape as :func:`list_locked_users`,
    or ``None`` if the user is not currently locked. The active/expiry decision
    is delegated to :func:`~privacyidea.lib.conditional_access.engine.get_user_lock`
    so this always agrees with the authentication pre-check.
    """
    status = get_user_lock(user, now=now)
    if status is None:
        return None
    row = get_ca_session().get(UserLockState, (user.resolver, user.uid, user.realm))
    return _locked_user_dict(row, now if now is not None else utc_now())


def _restriction_expiry(duration_seconds: int | None, moment: datetime) -> datetime | None:
    """
    The expiry of a manually imposed restriction: ``None`` for a permanent one, otherwise *moment* plus the
    duration. A non-positive or non-integer duration is a :class:`ParameterError` rather than a silently
    permanent restriction - the two are the opposite of each other, so guessing is not an option.
    """
    if duration_seconds is None:
        return None
    if isinstance(duration_seconds, bool) or not isinstance(duration_seconds, int) or duration_seconds <= 0:
        raise ParameterError("'duration_seconds' must be a positive number of seconds, or be omitted for a "
                             "restriction that does not expire.")
    return moment + timedelta(seconds=duration_seconds)


@log_with(log)
def lock_user(user: User, duration_seconds: int | None = None, now: datetime | None = None) -> dict:
    """
    Lock *user* by administrator decision, replacing whatever lock is currently on record, and return the new
    lock in the shape of :func:`_locked_user_dict`.

    ``duration_seconds`` omitted writes a permanent lock (only an unlock clears it); a positive value writes a
    timed one. Permanent is the default because an administrator locking by hand is normally reacting to an
    incident: a lock that quietly expires on its own is the surprising outcome.

    Unlike the engine's ``_upsert_user_lock_state`` this write is **authoritative**: it never declines as a
    weakening, so an admin may replace a permanent policy lock with a two-hour one. The engine's never-weaken
    rule exists so that the order in which two automatic policies happen to fire cannot decide the outcome; an
    administrator setting a lock by hand *is* the decision. It is also not defensive - a management caller is
    waiting for the result, so a failed write raises instead of being indistinguishable from success.

    The row is stamped :attr:`RestrictionCause.MANUAL`. Nothing else is needed to enforce it: the
    authentication pre-check reads the state row whoever wrote it.

    :param user: the user to lock; must resolve to a ``(resolver, uid, realm)`` identity, which is the row's key
    :param duration_seconds: how long the lock lasts, or ``None`` for a permanent lock
    :param now: the reference time; defaults to :func:`utc_now`
    :raises ParameterError: if the user does not resolve, or the duration is not a positive integer
    """
    if not (user and user.resolver and user.uid and user.realm):
        raise ParameterError(f"Cannot lock {user!r}: the lock is keyed on a resolved user "
                             f"(resolver, uid, realm).")
    moment = now if now is not None else utc_now()
    lock_expires_at = _restriction_expiry(duration_seconds, moment)
    with guarded_write(f"the manual user lock for {user!r}", reraise=True):
        session = get_ca_session()
        state = session.get(UserLockState, (user.resolver, user.uid, user.realm))
        if state is None:
            state = UserLockState(resolver=user.resolver, uid=user.uid, realm=user.realm)
            session.add(state)
        state.username = user.login
        state.lock_expires_at = lock_expires_at
        state.lock_cause = RestrictionCause.MANUAL
    log.info(f"Locked {user!r} by administrator decision "
             f"({'permanently' if lock_expires_at is None else f'until {lock_expires_at}'}).")
    return _locked_user_dict(state, moment)


@log_with(log)
def lock_internal_admin(login: str, duration_seconds: int | None = None, now: datetime | None = None) -> dict:
    """
    Lock the local database admin *login* by administrator decision, and return the new lock in the shape of
    :func:`_locked_user_dict`. The local-admin counterpart of :func:`lock_user`, with the same authoritative,
    non-defensive write and the same permanent default; see there.

    A local admin has no ``(resolver, uid, realm)`` to key a row on - only a login name - so the row is keyed as
    :class:`~privacyidea.lib.conditional_access.engine.LockSubject` keys it, and under the spelling the ``admin``
    table holds rather than the one that was typed: the authentication path counts and locks that name, so a lock
    written under any other would never be met (see
    :func:`~privacyidea.lib.auth.canonical_db_admin_login`).

    Only an existing account can be locked. Locking a name that is not one would leave a row nothing ever reads,
    which for a management call is a silent no-op rather than the refusal it should be - and unlike a userstore
    user, whose realm may simply have gone away, there is exactly one place a local admin can be looked up.

    :param login: the login name of the local database admin to lock
    :param duration_seconds: how long the lock lasts, or ``None`` for a permanent lock
    :param now: the reference time; defaults to :func:`utc_now`
    :raises ParameterError: if no such local admin exists, or the duration is not a positive integer
    """
    # Deferred: lib.auth pulls in the token machinery, and importing it at module level would risk an
    # import-order cycle during app startup.
    from privacyidea.lib.auth import get_db_admin
    # One lookup answers both questions this needs: whether the account exists, and the spelling it is stored
    # under.
    admin = get_db_admin(login) if login else None
    if admin is None:
        raise ParameterError(f"Cannot lock {login!r}: there is no local administrator of that name.")
    subject = LockSubject.for_internal_admin(admin.username)
    moment = now if now is not None else utc_now()
    lock_expires_at = _restriction_expiry(duration_seconds, moment)
    with guarded_write(f"the manual lock for {subject}", reraise=True):
        session = get_ca_session()
        state = session.get(UserLockState, subject.state_key)
        if state is None:
            state = UserLockState(resolver=subject.resolver, uid=subject.uid, realm=subject.realm,
                                  user_role=str(AuthLogUserRole.ADMIN_INTERNAL))
            session.add(state)
        state.username = subject.username
        state.lock_expires_at = lock_expires_at
        state.lock_cause = RestrictionCause.MANUAL
    log.info(f"Locked {subject} by administrator decision "
             f"({'permanently' if lock_expires_at is None else f'until {lock_expires_at}'}).")
    return _locked_user_dict(state, moment)


@log_with(log)
def unlock_internal_admin(login: str, visibility_scopes: list | None = None) -> bool:
    """
    Delete the lock of the local database admin named *login*, whichever spelling of that name it stands under.
    Returns ``True`` if a row was removed, ``False`` if there was no lock. The by-name counterpart of
    :func:`unlock_internal_admin_by_uid`, which removes one row by its own key; this is for a caller holding a
    typed name rather than a listed row, such as ``pi-manage conditionalaccess unlock-user --admin``.

    Both the canonical spelling and the one given are matched, and for the same reason the lock is written under
    the canonical one: where the ``admin`` table folds case, every spelling authenticates the same account, so
    every row standing under one of them bars that account from logging in and all of them have to go. Matching
    only the canonical spelling would strand a row whose account was since removed and recreated under a different
    one - and a lock outliving its admin is exactly the row an operator needs to be able to clear.

    ``visibility_scopes`` restricts the delete to the caller's authorization boundary as elsewhere. A local admin's
    row carries no realm or resolver, so a realm- or resolver-scoped administrator matches none of it and cannot
    lift such a lock - which is the intended answer: the account is outside their boundary.
    """
    # Deferred for the same reason as in lock_internal_admin.
    from privacyidea.lib.auth import canonical_db_admin_login
    # dict.fromkeys rather than a set: order is irrelevant to the query but keeps the log line stable, and the two
    # collapse to one whenever the name was already spelled as the account is.
    logins = [name for name in dict.fromkeys((canonical_db_admin_login(login), login)) if name]
    if not logins:
        return False
    return _delete_internal_admin_locks(logins, visibility_scopes)


@log_with(log)
def unlock_internal_admin_by_uid(uid: str, visibility_scopes: list | None = None) -> bool:
    """
    Delete the one local-admin lock row keyed on *uid*. Returns ``True`` if it was removed, ``False`` if there was
    no such row.

    The exact-key counterpart of :func:`unlock_internal_admin`, for a caller that already holds the row - the
    locked-users table, which lists it and then acts on what it listed. Nothing is derived and nothing else is
    touched: the name is not looked up in the ``admin`` table, so a row cannot be missed because the account it
    belongs to is gone or now spelled differently, and a second row under a second spelling is left alone rather
    than removed along with the one that was asked for.
    """
    if not uid:
        return False
    return _delete_internal_admin_locks([uid], visibility_scopes)


def _delete_internal_admin_locks(uids: list[str], visibility_scopes: list | None) -> bool:
    """
    Delete the local-admin lock rows keyed on any of *uids*, within *visibility_scopes*. Shared by the two
    unlock entry points, which differ only in how they arrive at the names.
    """
    # The empty resolver and realm a local admin's row carries are taken from the subject rather than spelled out
    # again here, so the two stay one definition; only the uid differs between the names.
    subject = LockSubject.for_internal_admin(uids[0])
    conditions = [UserLockState.resolver == subject.resolver, UserLockState.realm == subject.realm,
                  UserLockState.uid.in_(uids)]
    if visibility_scopes is not None:
        conditions.append(_visibility_condition(visibility_scopes))
    return _delete_and_commit(delete(UserLockState).where(*conditions)) > 0


@log_with(log)
def block_ip(ip: str, duration_seconds: int | None = None, now: datetime | None = None) -> dict:
    """
    Block *ip* by administrator decision, replacing whatever block is currently on record, and return the new
    block in the shape of :func:`_blocklist_dict`. The user-lock counterpart is :func:`lock_user`, and the same
    authoritative-write reasoning applies.

    A never-block address (loopback, or one covered by ``PI_CONDITIONAL_ACCESS_NEVER_BLOCK``) is **refused
    loudly**. The engine skips such an address silently, which is right for an automatic action - it must not
    break an authentication over an allowlisted proxy - but wrong here: an administrator who asks for a block
    and gets a silent no-op has no way to tell it apart from success.

    :param ip: the source IP to block
    :param duration_seconds: how long the block lasts, or ``None`` for a permanent block
    :param now: the reference time; defaults to :func:`utc_now`
    :raises ParameterError: if the IP is unparsable or on the never-block list, or the duration is not a
        positive integer
    """
    # Stored the way the pre-check will look it up rather than the way it was typed: an IPv6 address has many
    # spellings and the engine looks blocks up by primary key, so the typed spelling would file a block that
    # never matches - and let a later engine block of the same address add a second row for it. This is also
    # the validation: an identifier that is no IP address at all cannot be canonicalized.
    canonical = canonical_block_identifier(ip)
    if canonical is None:
        raise ParameterError(f"{ip!r} is not a valid IP address.")
    ip = canonical
    if is_ip_never_block(ip):
        raise ParameterError(f"{ip} is on the never-block list (loopback, or "
                             f"PI_CONDITIONAL_ACCESS_NEVER_BLOCK) and cannot be blocked.")
    moment = now if now is not None else utc_now()
    block_expires_at = _restriction_expiry(duration_seconds, moment)
    with guarded_write(f"the manual IP block for {ip}", reraise=True):
        session = get_ca_session()
        state = session.get(BlockList, ip)
        if state is None:
            state = BlockList(ip=ip)
            session.add(state)
        state.block_expires_at = block_expires_at
        state.block_cause = RestrictionCause.MANUAL
    log.info(f"Blocked IP {ip} by administrator decision "
             f"({'permanently' if block_expires_at is None else f'until {block_expires_at}'}).")
    return _blocklist_dict(state, moment)


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
    conditions = [UserLockState.uid == uid, UserLockState.realm == realm]
    if resolver:
        conditions.append(UserLockState.resolver == resolver)
    if visibility_scopes is not None:
        conditions.append(_visibility_condition(visibility_scopes))
    return _delete_and_commit(delete(UserLockState).where(*conditions)) > 0


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
    conditions = [UserLockState.username == username, UserLockState.realm == realm]
    if resolver:
        conditions.append(UserLockState.resolver == resolver)
    if visibility_scopes is not None:
        conditions.append(_visibility_condition(visibility_scopes))
    return _delete_and_commit(delete(UserLockState).where(*conditions)) > 0


@log_with(log)
def list_blocklist(include_expired: bool = True, now: datetime | None = None) -> list[dict]:
    """
    Return the blocklist entries, most recently updated first. Each row carries the
    expiry fields (``permanent`` / ``block_expires_at`` / ``seconds_remaining``),
    so the caller can tell a currently-enforced block from a stale, expired record.
    The never-block allowlist is an enforcement-time concern and is *not* applied
    here, so an admin can see a row even for a never-enforced IP - until the next
    authentication from that IP, which drops it (see
    :func:`~privacyidea.lib.conditional_access.engine.get_ip_block`).

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

    Both the canonical spelling of *entry* and *entry* as it was typed are removed: canonicalizing alone
    would leave a row some other path filed under a different spelling undeletable, and it is the same
    address either way (see
    :func:`~privacyidea.lib.conditional_access.engine.canonical_block_identifier`).
    """
    identifiers = {entry, canonical_block_identifier(entry) or entry}
    return _delete_and_commit(delete(BlockList).where(BlockList.ip.in_(identifiers))) > 0


@log_with(log)
def purge_expired_user_locks(now: datetime | None = None, visibility_scopes: list | None = None) -> int:
    """
    Delete user-lock rows that are no longer in force — a timed lock past its
    expiry. Permanent locks (``lock_expires_at IS NULL``) and active timed locks
    are kept. Nothing writes these rows off on its own, so this is the
    housekeeping that clears stale records. Returns the number of rows removed.

    ``visibility_scopes`` restricts the purge to the caller's authorization
    boundary (see :func:`_visibility_condition`); ``None`` means unrestricted.
    A scoped admin only clears the stale rows they can see, so the returned count
    is the number they were allowed to remove.
    """
    now = now or utc_now()
    conditions = [UserLockState.lock_expires_at.isnot(None), UserLockState.lock_expires_at <= now]
    if visibility_scopes is not None:
        conditions.append(_visibility_condition(visibility_scopes))
    return _delete_and_commit(delete(UserLockState).where(and_(*conditions)))


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
