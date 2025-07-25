# SPDX-FileCopyrightText: (C) 2025 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2025 Paul Lettich <paul.lettich@netknights.it>
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

from datetime import datetime, timedelta
import json
import logging
from sqlalchemy import Sequence

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin
from privacyidea.lib.crypto import get_rand_digit_str
from privacyidea.lib.utils import convert_column_to_unicode
from privacyidea.lib.log import log_with

log = logging.getLogger(__name__)


class Challenge(MethodsMixin, db.Model):
    """
    Table for handling of the generic challenges.
    """
    __tablename__ = "challenge"
    id = db.Column(db.Integer(), Sequence("challenge_seq"), primary_key=True,
                   nullable=False)
    transaction_id = db.Column(db.Unicode(64), nullable=False, index=True)
    data = db.Column(db.Unicode(512), default='')
    challenge = db.Column(db.Unicode(512), default='')
    session = db.Column(db.Unicode(512), default='', quote=True, name="session")
    # The token serial number
    serial = db.Column(db.Unicode(40), default='', index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow(), index=True)
    expiration = db.Column(db.DateTime, index=True)
    received_count = db.Column(db.Integer(), default=0)
    otp_valid = db.Column(db.Boolean, default=False)

    @log_with(log)
    def __init__(self, serial, transaction_id=None,
                 challenge='', data='', session='', validitytime=120):

        self.transaction_id = transaction_id or self.create_transaction_id()
        self.challenge = challenge
        self.serial = serial
        self.data = data
        self.timestamp = datetime.utcnow()
        self.session = session
        self.received_count = 0
        self.otp_valid = False
        self.expiration = datetime.utcnow() + timedelta(seconds=validitytime)

    @staticmethod
    def create_transaction_id(length=20):
        return get_rand_digit_str(length)

    def is_valid(self):
        """
        Returns true, if the expiration time has not passed, yet.

        :return: True if valid
        :rtype: bool
        """
        ret = False
        c_now = datetime.utcnow()
        if self.timestamp <= c_now < self.expiration:
            ret = True
        return ret

    def set_data(self, data):
        """
        set the internal data of the challenge

        :param data: unicode data
        :type data: string, length 512
        """
        if isinstance(data, str):
            self.data = data
        else:
            self.data = convert_column_to_unicode(data)

    def get_data(self):
        try:
            data = json.loads(self.data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = self.data
        return data

    def get_session(self):
        return self.session

    def set_session(self, session):
        self.session = convert_column_to_unicode(session)

    def set_challenge(self, challenge):
        self.challenge = convert_column_to_unicode(challenge)

    def get_challenge(self):
        return self.challenge

    def set_otp_status(self, valid=False):
        self.received_count += 1
        self.otp_valid = valid

    def get_otp_status(self):
        """
        This returns how many OTPs were already received for this challenge.
        and if a valid OTP was received.

        :return: tuple of count and True/False
        :rtype: tuple
        """
        return self.received_count, self.otp_valid

    def get_transaction_id(self):
        return self.transaction_id

    def get(self, timestamp=False):
        """
        return a dictionary of all vars in the challenge class

        :param timestamp: if true, the timestamp will be returned in a readable
                          format like "2014-11-29 21:56:43.057293"
        :type timestamp: bool
        :return: dict of vars
        """
        descr = {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'challenge': self.challenge,
            'serial': self.serial,
            'data': self.get_data(),
            'otp_received': self.received_count > 0,
            'received_count': self.received_count,
            'otp_valid': self.otp_valid,
            'expiration': self.expiration,
        }
        if timestamp is True:
            descr['timestamp'] = f"{self.timestamp}"
        else:
            descr['timestamp'] = self.timestamp
        return descr

    def __str__(self):
        descr = self.get()
        return "{0!s}".format(descr)


def cleanup_challenges(serial):
    """
    Delete all challenges, that have expired.

    :return: None
    """
    c_now = datetime.utcnow()
    Challenge.query.filter(Challenge.expiration < c_now, Challenge.serial == serial).delete()
    db.session.commit()
