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

from .log import log_with
from .policies.actions import PolicyAction
from .sqlutils import delete_matching_rows
from ..models import Challenge, db

log = logging.getLogger(__name__)


@log_with(log)
def get_challenges(serial=None, transaction_id=None, challenge=None):
    """
    This returns a list of database challenge objects.

    :param serial: challenges for this very serial number
    :param transaction_id: challenges with this very transaction id
    :param challenge: The challenge to be found
    :return: list of objects
    """
    sql_query = Challenge.query

    if serial is not None:
        sql_query = sql_query.filter(Challenge.serial == serial)

    if transaction_id is not None:
        sql_query = sql_query.filter(Challenge.transaction_id == transaction_id)

    if challenge is not None:
        sql_query = sql_query.filter(Challenge.challenge == challenge)

    challenges = sql_query.all()
    return challenges


@log_with(log)
def get_challenges_paginate(serial=None, transaction_id=None,
                            sortby=Challenge.timestamp,
                            sortdir="asc", psize=15, page=1):
    """
    This function is used to retrieve a challenge list, that can be displayed in
    the Web UI. It supports pagination.
    Each retrieved page will also contain a "next" and a "prev", indicating
    the next or previous page. If either does not exist, it is None.

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
    sql_query = _create_challenge_query(serial=serial, transaction_id=transaction_id)

    if isinstance(sortby, str):
        # convert the string to a Challenge column
        cols = Challenge.__table__.columns
        sortby = cols.get(sortby)

    if sortdir == "desc":
        sql_query = sql_query.order_by(sortby.desc())
    else:
        sql_query = sql_query.order_by(sortby.asc())

    pagination = db.paginate(sql_query, page=page, per_page=psize, error_out=False)
    challenges = pagination.items
    prev = None
    if pagination.has_prev:
        prev = page - 1
    next_page = None
    if pagination.has_next:
        next_page = page + 1
    challenge_list = []
    for challenge in challenges:
        challenge_dict = challenge.get()
        challenge_list.append(challenge_dict)

    ret = {"challenges": challenge_list,
           "prev": prev,
           "next": next_page,
           "current": page,
           "count": pagination.total}
    return ret


def _create_challenge_query(serial=None, transaction_id=None):
    """
    This function create the sql query for fetching transaction_ids. It is
    used by get_challenge_paginate.
    :return: An SQLAlchemy sql query
    """
    sql_query = Challenge.query
    if serial is not None and serial.strip("*"):
        # filter for serial
        if "*" in serial:
            # match with "like"
            sql_query = sql_query.filter(Challenge.serial.like(serial.replace(
                "*", "%")))
        else:
            # exact match
            sql_query = sql_query.filter(Challenge.serial == serial)

    if transaction_id is not None and transaction_id.strip("*"):
        # filter for serial
        if "*" in transaction_id:
            # match with "like"
            sql_query = sql_query.filter(Challenge.transaction_id.like(
                transaction_id.replace(
                    "*", "%")))
        else:
            # exact match
            sql_query = sql_query.filter(Challenge.transaction_id == transaction_id)

    return sql_query


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


def delete_challenges(serial: str = None, transaction_id: str = None) -> int:
    """
    This function deletes challenges from the database.

    :param serial: challenges for this very serial number
    :param transaction_id: challenges with this very transaction id
    :return: number of deleted challenges
    """
    challenges = get_challenges(serial=serial, transaction_id=transaction_id)
    for challenge in challenges:
        challenge.delete()
    return len(challenges)


def _build_challenge_criterion(age: int = None) -> 'sqlalchemy.sql.expression.BinaryExpression':
    """
    Return an SQLAlchemy binary expression selecting expired challenges or expired challenges older than a given age.

    :param age: If given, delete challenges older than this many minutes.
    :return: SQLAlchemy binary expression
    """
    utc_now = datetime.datetime.utcnow()
    if age is not None:
        cutoff = utc_now - datetime.timedelta(minutes=age)
        return Challenge.timestamp < cutoff

    return Challenge.expiration < utc_now


def cleanup_expired_challenges(chunk_size: int = None, age: int = None) -> int:
    """
    Delete only expired challenges from the challenge table, or delete expired challenges older than the given age.

    :param chunk_size: Delete entries in chunks of the given size to avoid deadlocks
    :param age: Instead of deleting expired challenges, delete challenge entries older than these number of minutes.
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
        log.warning("No data found in challenge %s for transaction_id %s", challenge.id, transaction_id)
        return False

    if not PolicyAction.ENROLL_VIA_MULTICHALLENGE in data:
        log.warning(
            "Challenge for transaction_id %s contains no information about ENROLL_VIA_MULTICHALLENGE",
            transaction_id
        )
        return False

    if not PolicyAction.ENROLL_VIA_MULTICHALLENGE_OPTIONAL in data:
        log.warning(
            "Challenge for transaction_id %s contains no information about ENROLL_VIA_MULTICHALLENGE_OPTIONAL",
            transaction_id
        )
        return False

    if not data[PolicyAction.ENROLL_VIA_MULTICHALLENGE_OPTIONAL]:
        log.warning(
            "Challenge %s for transaction_id %s does not have the action %s set to True",
            challenge.id, transaction_id, PolicyAction.ENROLL_VIA_MULTICHALLENGE_OPTIONAL
        )
        return False

    # If we reach this point, we can cancel the enrollment, depending on the type
    if "type" in data and data["type"] == "container":
        from .container import delete_container_by_serial
        delete_container_by_serial(challenge.serial)
    else:
        from .token import remove_token
        remove_token(challenge.serial)
    challenge.delete()
    return True
