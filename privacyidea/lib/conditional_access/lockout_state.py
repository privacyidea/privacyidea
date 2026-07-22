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

from privacyidea.lib.conditional_access.authentication_log import _match_condition
from privacyidea.lib.conditional_access.engine import get_user_lockout
from privacyidea.lib.log import log_with
from privacyidea.lib.user import User
from privacyidea.models import db
from privacyidea.models.lockout_policy import BlockList, UserLockoutState
from privacyidea.models.utils import utc_now

log = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 15

# Columns the locked-users list may be sorted by (any other value falls back to last_updated).
SORTABLE_COLUMNS = {
    "username": UserLockoutState.username,
    "realm": UserLockoutState.realm,
    "resolver": UserLockoutState.resolver,
    "lock_expires_at": UserLockoutState.lock_expires_at,
    "last_updated": UserLockoutState.last_updated,
}


def _seconds_remaining(expires_at: datetime | None, now: datetime) -> int | None:
    if expires_at is None:
        return None
    return max(0, int((expires_at - now).total_seconds()))


def _not_expired_condition(expiry_column, now: datetime):
    # Currently in force: a permanent restriction (NULL expiry) or a timed one whose expiry is still ahead.
    return or_(expiry_column.is_(None), expiry_column > now)


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
        "is_locked": row.is_locked,
        "last_updated": row.last_updated
    }


def _blocklist_dict(row: BlockList, now: datetime) -> dict:
    return {
        "identifier": row.ip,
        "permanent": row.block_expires_at is None,
        "block_expires_at": row.block_expires_at,
        "seconds_remaining": _seconds_remaining(row.block_expires_at, now),
        "is_blocked": row.is_blocked,
        "reason": row.reason,
        "last_updated": row.last_updated,
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
                        usernames: list[str] | None, include_expired: bool,
                        visibility_scopes: list | None, now: datetime,
                        case_insensitive: bool) -> list[ColumnElement[bool]]:
    """
    Build the WHERE conditions for a locked-users query. The realm/resolver/username
    *filters* (user search) use the same wildcard (`*`) + optional case-insensitive
    semantics; they are separate AND clauses from the case-sensitive authorization
    boundary (:func:`_visibility_condition`), so search behaviour never widens the
    visibility scope.
    """
    conditions: list[ColumnElement[bool]] = [UserLockoutState.is_locked.is_(True)]
    for column, value in ((UserLockoutState.realm, realms),
                          (UserLockoutState.resolver, resolvers),
                          (UserLockoutState.username, usernames)):
        condition = _match_condition(column, value, case_insensitive)
        if condition is not None:
            conditions.append(condition)
    if not include_expired:
        conditions.append(_not_expired_condition(UserLockoutState.lock_expires_at, now))
    if visibility_scopes is not None:
        conditions.append(_visibility_condition(visibility_scopes))
    return conditions


@log_with(log)
def list_locked_users(realms: list[str] | None = None, resolvers: list[str] | None = None,
                      usernames: list[str] | None = None, include_expired: bool = False,
                      visibility_scopes: list | None = None, case_insensitive: bool = False,
                      now: datetime | None = None) -> list[dict]:
    """
    Return all matching locked users (no pagination), most recently updated first. See
    :func:`_lockout_conditions` for the filter/scoping semantics and
    :func:`list_locked_users_paginate` for the paginated variant.
    """
    moment = now if now is not None else utc_now()
    conditions = _lockout_conditions(realms, resolvers, usernames, include_expired,
                                     visibility_scopes, moment, case_insensitive)
    stmt = select(UserLockoutState).where(*conditions).order_by(UserLockoutState.last_updated.desc())
    return [_locked_user_dict(row, moment) for row in db.session.scalars(stmt).all()]


@log_with(log)
def list_locked_users_paginate(realms: list[str] | None = None, resolvers: list[str] | None = None,
                               usernames: list[str] | None = None, include_expired: bool = False,
                               visibility_scopes: list | None = None, case_insensitive: bool = False,
                               page: int = 1, page_size: int = DEFAULT_PAGE_SIZE,
                               sort_column: str = "last_updated", sort_order: str = "desc",
                               now: datetime | None = None) -> dict:
    """
    Return one page of matching locked users plus pagination metadata
    ``{locked_users, count, current, prev, next}`` — the counterpart of
    :func:`list_locked_users` for the WebUI table. Filter/scoping semantics are as
    :func:`_lockout_conditions`; sorting is by one of :data:`SORTABLE_COLUMNS`
    (fallback ``last_updated``), always tie-broken by the primary key for a stable
    order across pages.
    """
    moment = now if now is not None else utc_now()
    conditions = _lockout_conditions(realms, resolvers, usernames, include_expired,
                                     visibility_scopes, moment, case_insensitive)
    count = db.session.scalar(
        select(func.count()).select_from(UserLockoutState).where(*conditions))
    order_column = SORTABLE_COLUMNS.get(sort_column)
    if order_column is None:
        log.warning(f"Unknown sort column '{sort_column}'. Using 'last_updated' instead.")
        order_column = UserLockoutState.last_updated
    tiebreak = (UserLockoutState.resolver, UserLockoutState.uid, UserLockoutState.realm)
    direction = (lambda col: col.asc()) if sort_order == "asc" else (lambda col: col.desc())
    stmt = (select(UserLockoutState).where(*conditions)
            .order_by(direction(order_column), *[direction(col) for col in tiebreak]))
    page = max(1, page)
    page_size = max(1, page_size)
    offset = (page - 1) * page_size
    rows = db.session.scalars(stmt.limit(page_size).offset(offset)).all()
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
    row = db.session.get(UserLockoutState, (user.resolver, user.uid, user.realm))
    return _locked_user_dict(row, now if now is not None else utc_now())


@log_with(log)
def unlock_user_by_id(resolver: str, uid: str, realm: str) -> bool:
    """
    Delete the lock for a raw ``(resolver, uid, realm)`` identity. Returns
    ``True`` if a row was removed, ``False`` if there was no lock. Works even for
    a user that no longer resolves in its resolver.
    """
    row = db.session.get(UserLockoutState, (resolver, uid, realm))
    if not row:
        return False
    db.session.delete(row)
    db.session.commit()
    return True


@log_with(log)
def unlock_user_by_username(username: str, realm: str, resolver: str) -> bool:
    """
    Delete the lock for a raw ``(resolver, uid, realm)`` identity. Returns
    ``True`` if a row was removed, ``False`` if there was no lock.
    """
    stmt = delete(UserLockoutState).where(UserLockoutState.username == username,
                                          UserLockoutState.realm == realm,
                                          UserLockoutState.resolver == resolver)
    result = db.session.execute(stmt)
    db.session.commit()
    return result.rowcount == 1


@log_with(log)
def list_blocklist(include_expired: bool = False, now: datetime | None = None) -> list[dict]:
    """
    Return the blocklist entries, most recently updated first. Each row carries its
    raw ``is_blocked`` flag plus the expiry fields (``permanent`` /
    ``block_expires_at`` / ``seconds_remaining``), so the caller can tell a
    currently-enforced block from a stale, expired record. The never-block
    allowlist is an enforcement-time concern and is *not* applied here, so an admin
    can see and clean up a row even for a never-enforced IP.

    :param include_expired: also return stale rows whose timed block has expired
        (``is_expired=True``); by default only currently-enforced blocks are returned
    :param now: reference time; defaults to :func:`utc_now`
    """
    moment = now if now is not None else utc_now()
    conditions: list[ColumnElement[bool]] = [BlockList.is_blocked.is_(True)]
    if not include_expired:
        conditions.append(_not_expired_condition(BlockList.block_expires_at, moment))
    stmt = select(BlockList).where(*conditions).order_by(BlockList.last_updated.desc())
    return [_blocklist_dict(row, moment) for row in db.session.scalars(stmt).all()]


@log_with(log)
def remove_blocklist_entry(entry: str) -> bool:
    """
    Remove a single blocklist entry by its identifier (a source IP today).
    Returns ``True`` if a row was removed, ``False`` if there was no entry.
    """
    row = db.session.get(BlockList, entry)
    if not row:
        return False
    db.session.delete(row)
    db.session.commit()
    return True


@log_with(log)
def purge_expired_user_lockouts(now: datetime | None = None) -> int:
    """
    Delete user-lockout rows that are no longer in force — explicitly unlocked
    (``is_locked=False``) or a timed lock past its expiry. Permanent locks
    (``lock_expires_at IS NULL`` and still locked) and active timed locks are
    kept. Nothing writes these rows off on its own, so this is the housekeeping
    that clears stale records. Returns the number of rows removed.
    """
    now = now or utc_now()
    stmt = delete(UserLockoutState).where(
        or_(UserLockoutState.is_locked.is_(False),
            and_(UserLockoutState.lock_expires_at.isnot(None), UserLockoutState.lock_expires_at <= now)))
    count = db.session.execute(stmt).rowcount
    db.session.commit()
    return count


@log_with(log)
def purge_expired_blocklist(now: datetime | None = None) -> int:
    """
    Delete blocklist rows that are no longer in force — explicitly unblocked
    (``is_blocked=False``) or a timed block past its expiry. Permanent blocks
    and active timed blocks are kept. Returns the number of rows removed.
    """
    now = now or utc_now()
    stmt = delete(BlockList).where(
        or_(BlockList.is_blocked.is_(False),
            and_(BlockList.block_expires_at.isnot(None),
                 BlockList.block_expires_at <= now)))
    count = db.session.execute(stmt).rowcount
    db.session.commit()
    return count
