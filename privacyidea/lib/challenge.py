# SPDX-FileCopyrightText: 2015 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
#  privacyIDEA is a fork of LinOTP
#
#  2014-12-07 Cornelius Kölbel <cornelius@privacyidea.org>
#
#  Copyright (C) 2014 Cornelius Kölbel
#  License:  AGPLv3
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
This is a helper module for the challenges database table.
It is used by the lib.tokenclass

The method is tested in test_lib_challenges
"""
import datetime
import logging
from typing import NamedTuple

import sqlalchemy
from sqlalchemy import select, delete
from sqlalchemy.sql import Select

from .cache import (ChallengeDTO, evict_challenge, evict_transaction,
                    evict_challenges_for_serial, get_challenges_from_cache,
                    get_redis, redis_feature_configured, redis_feature_enabled)
from .log import log_with
from .policies.actions import PolicyAction
from .sqlutils import delete_matching_rows
from ..models import Challenge, db
from ..models.utils import utc_now
from privacyidea.models.utils import clob_to_varchar

log = logging.getLogger(__name__)


class DeleteChallengesResult(NamedTuple):
    """
    Outcome of a ``delete_challenges`` call.

    ``removed`` counts entries cleared across both stores. ``cache_available``
    is False only when the operator opted into the cache (PI_REDIS_CACHE_*)
    but this worker couldn't reach Redis at delete time - i.e. the worker
    is inside the retry cooldown after a recent failure. Other workers may
    still be serving the entry from the shared cache until its TTL expires.
    Callers that care to inform end users (e.g. the cancel-challenge API)
    can use this to attach a warning to the response.
    """
    removed: int
    cache_available: bool


@log_with(log)
def get_challenges(serial: str = None, transaction_id: str = None,
                   challenge=None) -> "list[Challenge | ChallengeDTO]":
    """
    Return a list of challenge objects matching the given filters.

    Checks the Redis cache first when available, then falls back to the database
    on a cache miss. Items are either ``Challenge`` (DB) or ``ChallengeDTO``
    (cache); both expose the same duck-typed surface - see ``Challenge`` /
    ``ChallengeDTO`` for the shared methods (``is_valid``, ``get_data``,
    ``set_otp_status``, ``save``, ``delete``, ...) and attributes
    (``transaction_id``, ``serial``, ``timestamp``, ``expiration``, ...).

    :param serial: challenges for this very serial number
    :param transaction_id: challenges with this very transaction id
    :param challenge: The challenge to be found
    :return: list of challenge objects
    """
    cached = get_challenges_from_cache(serial=serial, transaction_id=transaction_id, challenge=challenge)
    if isinstance(cached, list):
        return cached
    # CacheState.MISS or CacheState.UNAVAILABLE: fall through to the DB.
    # MISS still falls through because the DB may legitimately hold
    # challenges created before caching was enabled - the cache is only
    # authoritative for what it has, not for what it claims is absent.

    stmt = select(Challenge)
    if serial is not None:
        stmt = stmt.where(Challenge.serial == serial)
    if transaction_id is not None:
        stmt = stmt.where(Challenge.transaction_id == transaction_id)
    if challenge is not None:
        stmt = stmt.where(clob_to_varchar(Challenge.challenge) == challenge)

    return db.session.execute(stmt).scalars().all()


@log_with(log)
def get_challenges_paginate(serial=None, transaction_id=None,
                            sortby=Challenge.timestamp,
                            sortdir="asc", psize=15, page=1):
    """
    This function is used to retrieve a challenge list, that can be displayed in
    the Web UI. It supports pagination.
    Each retrieved page will also contain a "next" and a "prev", indicating
    the next or previous page. If either does not exist, it is None.

    When Redis is active and a serial or transaction_id filter is provided,
    results are served from the cache.  Unfiltered requests always go to the
    database (Redis has no concept of "list all"); when Redis is active those
    results will be empty since challenges are not written to the DB.

    :param serial: The serial of the token
    :param transaction_id: The transaction_id of the challenge
    :param sortby: Sort by a Challenge DB field. The default is
        Challenge.timestamp.
    :type sortby: A Challenge column or a string.
    :param sortdir: Can be "asc" (default) or "desc"
    :type sortdir: basestring
    :param psize: The size of the page
    :type psize: int
    :param page: The number of the page to view. Starts with 1 ;-)
    :type page: int
    :return: dict with challenges, prev, next and count
    :rtype: dict
    """
    # When Redis is active and a specific exact-match filter is given, serve
    # from cache. Wildcard filters like "*foo*" (sent by the admin "List
    # Challenges" view) cannot be answered by Redis key lookups, so fall
    # through to the DB path - which, when caching is enabled and challenges
    # only live in Redis, will return an empty list. That is a known
    # limitation of the cache-only mode; the unfiltered admin listing
    # requires Redis-side scanning that we don't implement here.
    def _is_exact(v):
        return v is not None and "*" not in v

    if redis_feature_enabled("challenges") and (_is_exact(serial) or _is_exact(transaction_id)):
        cached = get_challenges_from_cache(
            serial=serial if _is_exact(serial) else None,
            transaction_id=transaction_id if _is_exact(transaction_id) else None,
        )
        if isinstance(cached, list):
            # Apply in-memory sort
            reverse = sortdir == "desc"
            sort_key = sortby if isinstance(sortby, str) else sortby.key
            try:
                cached = sorted(cached, key=lambda c: getattr(c, sort_key, c.timestamp),
                                reverse=reverse)
            except TypeError as e:
                # Mixed/incomparable types under sort_key - fall back to the
                # natural insertion order rather than failing the request.
                log.debug("Cannot sort cached challenges by %r: %s", sort_key, e)

            total = len(cached)
            start = (page - 1) * psize
            end = start + psize
            page_items = cached[start:end]

            return {
                "challenges": [c.get() for c in page_items],
                "prev": page - 1 if start > 0 else None,
                "next": page + 1 if end < total else None,
                "current": page,
                "count": total,
                "redis_cache_enabled": True,
            }

    stmt = _create_challenge_query(serial=serial, transaction_id=transaction_id)

    if isinstance(sortby, str):
        cols = Challenge.__table__.columns
        sortby = cols.get(sortby)

    if sortdir == "desc":
        stmt = stmt.order_by(sortby.desc())
    else:
        stmt = stmt.order_by(sortby.asc())

    pagination = db.paginate(stmt, page=page, per_page=psize, error_out=False)
    challenge_list = [challenge.get() for challenge in pagination.items]

    ret = {
        "challenges": challenge_list,
        "prev": page - 1 if pagination.has_prev else None,
        "next": page + 1 if pagination.has_next else None,
        "current": page,
        "count": pagination.total,
        # Surfaced so the admin "List Challenges" view can show a banner
        # explaining why the list is degraded (Redis-stored challenges are
        # not listable in aggregate). The exact-serial case in the token
        # detail page still works via the cache fast-path above.
        "redis_cache_enabled": redis_feature_enabled("challenges"),
    }
    return ret


def _create_challenge_query(serial: str = None, transaction_id: str = None) -> Select:
    """
    This function creates the SQL query for fetching transaction_ids. It is
    used by get_challenge_paginate.

    :return: An SQLAlchemy SQL query
    """
    stmt = select(Challenge)
    if serial is not None and serial.strip("*"):
        if "*" in serial:
            stmt = stmt.where(Challenge.serial.like(serial.replace("*", "%")))
        else:
            stmt = stmt.where(Challenge.serial == serial)
    if transaction_id is not None and transaction_id.strip("*"):
        if "*" in transaction_id:
            stmt = stmt.where(Challenge.transaction_id.like(transaction_id.replace("*", "%")))
        else:
            stmt = stmt.where(Challenge.transaction_id == transaction_id)
    return stmt


def extract_answered_challenges(challenges):
    """
    Given a list of challenge objects, extract and return a list of *answered* challenge.
    A challenge is answered if it is not expired yet *and* if its ``otp_valid`` attribute
    is set to True.

    :param challenges: a list of challenge objects
    :return: a list of answered challenge objects
    """
    answered_challenges = []
    for challenge in challenges:
        # check if we are still in time.
        if challenge.is_valid():
            _, status = challenge.get_otp_status()
            if status is True:
                answered_challenges.append(challenge)
    return answered_challenges


def delete_challenges(serial: str = None, transaction_id: str = None,
                      commit: bool = True) -> DeleteChallengesResult:
    """
    Delete challenges from both the Redis cache (when active) and the
    database. With Redis enabled there are no SQL rows for new challenges,
    so callers that want a token's or container's challenges fully cleared
    on deletion must reach into both stores - this function does so.

    :param serial: challenges for this very serial number
    :param transaction_id: challenges with this very transaction id
    :param commit: When False, the SQL DELETE is staged on the session but
        not committed, so callers can keep this delete inside a larger
        transaction (e.g. ``TokenClass.delete_token``). Redis eviction is
        always performed up-front and is not rolled back if the outer
        transaction aborts; on rollback the DB rows are restored and the
        normal cache-miss -> DB-fallback path takes over.
    :return: a ``DeleteChallengesResult`` carrying the removed count and
        a ``cache_available`` flag. The flag is False only when caching is
        configured but this worker is in cooldown - surfacing it lets the
        API layer warn the caller that the eviction may not have reached
        every node yet (other workers can still serve the cached entry
        until TTL).
    """
    removed = 0
    # Distinguish "feature off" (no cache to worry about - cache_available
    # is True by definition) from "feature on but we can't talk to Redis
    # right now" (cache_available False). redis_feature_enabled collapses
    # both into False, so we check the config flag and connectivity
    # separately to give the caller the operator-meaningful signal.
    cache_available = True
    if redis_feature_configured("challenges"):
        cache_available = get_redis() is not None
    if cache_available and redis_feature_configured("challenges"):
        if transaction_id is not None:
            cached = get_challenges_from_cache(transaction_id=transaction_id)
            if isinstance(cached, list):
                # Apply the optional serial filter the same way the SQL DELETE would.
                if serial is not None:
                    cached = [c for c in cached if c.serial == serial]
                for dto in cached:
                    evict_challenge(dto.transaction_id, dto.serial)
                    removed += 1
            else:
                # MISS or UNAVAILABLE: defensive evict to close the race
                # where another worker's cache_challenge lands between
                # our read and the DB delete. Drop the whole txn hash so a
                # sibling field we never saw is removed too.
                evict_transaction(transaction_id, [serial] if serial else [])
        elif serial is not None:
            # Iterate the serial-set so we can count removed entries.
            # MISS/UNAVAILABLE collapse to an empty list here, the
            # evict_challenges_for_serial call below is idempotent.
            cached = get_challenges_from_cache(serial=serial)
            evict_challenges_for_serial(serial)
            if isinstance(cached, list):
                removed += len(cached)

    delete_stmt = delete(Challenge)
    if serial is not None:
        delete_stmt = delete_stmt.where(Challenge.serial == serial)
    if transaction_id is not None:
        delete_stmt = delete_stmt.where(Challenge.transaction_id == transaction_id)
    result = db.session.execute(delete_stmt)
    if commit:
        db.session.commit()
    # Re-sample after the eviction work: if any eviction tripped
    # _disable_redis mid-pipeline, the client is now None and the cache
    # eviction didn't actually reach Redis. Reporting cache_available=True
    # without this re-check would let cancel_challenge_api skip the
    # stale-cache warning even though other workers may still serve the
    # cached entry.
    if cache_available and redis_feature_configured("challenges"):
        cache_available = get_redis() is not None
    return DeleteChallengesResult(removed=removed + result.rowcount,
                                  cache_available=cache_available)


def cancel_challenge(transaction_id: str) -> DeleteChallengesResult:
    """
    Cancel a single challenge identified by ``transaction_id``, removing it
    from both Redis (if cached) and the database.

    Returns a ``DeleteChallengesResult`` carrying the removed count and a
    ``cache_available`` flag - see ``delete_challenges`` for the meaning
    of the flag and why callers may want to surface it.
    """
    return delete_challenges(transaction_id=transaction_id)


def _build_challenge_criterion(age: int = None) -> 'sqlalchemy.sql.expression.ColumnElement':
    """
    Return an SQLAlchemy binary expression selecting expired challenges or expired challenges older than a given age.

    :param age: If given, delete challenges older than this many minutes.
    :return: SQLAlchemy binary expression
    """
    now = utc_now()
    if age is not None:
        cutoff = now - datetime.timedelta(minutes=age)
        return Challenge.timestamp < cutoff

    return Challenge.expiration < now


def cleanup_expired_challenges(chunk_size: int = None, age: int = None) -> int:
    """
    Delete only expired challenges from the challenge table or delete expired challenges older than the given age.

    :param chunk_size: Delete entries in chunks of the given size to avoid deadlocks
    :param age: Instead of deleting expired challenges, delete challenge entries older than these numbers of minutes.
    :return: number of deleted entries
    """
    criterion = _build_challenge_criterion(age)
    return delete_matching_rows(db.session, Challenge.__table__, criterion, chunk_size)


def cancel_enrollment_via_multichallenge(transaction_id: str) -> bool:
    """
    Cancel the enrollment via multichallenge for a given transaction_id by removing the challenge and the token or
    container. If the challenge does not exist or does not contain the required data
    (enroll_via_multichallenge_optional=true), it returns False.
    """
    challenges = get_challenges(transaction_id=transaction_id)

    if not challenges:
        log.warning("No challenges found for transaction_id %s", transaction_id)
        return False
    if len(challenges) > 1:
        log.warning(
            "Multiple challenges found for transaction_id %s, which should not be possible",
            transaction_id
        )
        return False

    challenge = challenges[0]
    data = challenge.get_data()

    if not data or not isinstance(data, dict):
        log.warning("No data found in challenge for transaction_id %s", transaction_id)
        return False

    if PolicyAction.ENROLL_VIA_MULTICHALLENGE not in data:
        log.warning(
            "Challenge for transaction_id %s contains no information about ENROLL_VIA_MULTICHALLENGE",
            transaction_id
        )
        return False

    if PolicyAction.ENROLL_VIA_MULTICHALLENGE_OPTIONAL not in data:
        log.warning(
            "Challenge for transaction_id %s contains no information about ENROLL_VIA_MULTICHALLENGE_OPTIONAL",
            transaction_id
        )
        return False

    if not data[PolicyAction.ENROLL_VIA_MULTICHALLENGE_OPTIONAL]:
        log.warning(
            "Challenge for transaction_id %s does not have the action %s set to True",
            transaction_id, PolicyAction.ENROLL_VIA_MULTICHALLENGE_OPTIONAL
        )
        return False

    # If we reach this point, we can cancel the enrollment, depending on the type.
    # The challenges will be cleaned up by either function
    if "type" in data and data["type"] == "container":
        from .container import delete_container_by_serial
        delete_container_by_serial(challenge.serial)
    else:
        from .token import remove_token
        remove_token(challenge.serial)
    return True


def get_challenges_for_user(user) -> "list[Challenge | ChallengeDTO]":
    """
    Aggregate every still-valid challenge belonging to any token owned by
    ``user``.

    Fan-out is bounded by the number of tokens the user owns (typically a
    handful), and per-token lookups hit the Redis fast-path when caching is
    enabled. Intended for the old WebUI's user-detail accordion; the new
    WebUI should reimplement this against its own state model.

    Expired entries are filtered out: the Redis TTL has a clock-skew buffer
    beyond ``expiration`` and DB rows live until the cleanup task runs, so
    raw get_challenges() can return entries that have logically expired.
    The accordion shows actionable challenges only.
    """
    from .token import get_tokens
    collected = []
    for token_obj in get_tokens(user=user):
        collected.extend(get_challenges(serial=token_obj.token.serial))
    return [c for c in collected if c.is_valid()]
