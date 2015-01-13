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
"""

import logging
from log import log_with
from ..models import Challenge
from datetime import datetime
log = logging.getLogger(__name__)


@log_with(log)
def get_challenges(serial=None, transaction_id=None):
    """
    This returns a list of database challenge objects.

    :param serial: challenges for this very serial number
    :param transaction_id: challenges with this very transaction id
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

    challenges = sql_query.all()
    return challenges
