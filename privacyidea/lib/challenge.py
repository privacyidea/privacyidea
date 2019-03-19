# -*- coding: utf-8 -*-
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

import logging
import six
from .log import log_with
from ..models import Challenge
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
        # filter for serial
        sql_query = sql_query.filter(Challenge.serial == serial)

    if transaction_id is not None:
        # filter for transaction id
        sql_query = sql_query.filter(Challenge.transaction_id ==
                                     transaction_id)

    if challenge is not None:
        # filter for this challenge
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
    sql_query = _create_challenge_query(serial=serial,
                                        transaction_id=transaction_id)

    if isinstance(sortby, six.string_types):
        # convert the string to a Challenge column
        cols = Challenge.__table__.columns
        sortby = cols.get(sortby)

    if sortdir == "desc":
        sql_query = sql_query.order_by(sortby.desc())
    else:
        sql_query = sql_query.order_by(sortby.asc())

    pagination = sql_query.paginate(page, per_page=psize,
                                    error_out=False)
    challenges = pagination.items
    prev = None
    if pagination.has_prev:
        prev = page-1
    next = None
    if pagination.has_next:
        next = page + 1
    challenge_list = []
    for challenge in challenges:
        challenge_dict = challenge.get()
        challenge_list.append(challenge_dict)

    ret = {"challenges": challenge_list,
           "prev": prev,
           "next": next,
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
