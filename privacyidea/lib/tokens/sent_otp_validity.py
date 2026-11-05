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

from datetime import datetime, timedelta, timezone
import logging

from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.tokenclass import lock_token_row
from privacyidea.models import Token, db

log = logging.getLogger(__name__)

# Token info holding the counter of the OTP value last sent to the user and until when it may be used
SENT_OTP_VALID_UNTIL = "sent_otp_valid_until"


class SentOtpValidityMixin:
    """
    For token classes that send the OTP value to the user, e.g. by email or SMS. The validity time of a sent value
    is the expiry of its challenge, which only the answer with a transaction_id checks. The mixin records the
    validity of the sent value, so that OTP PIN and OTP value sent together are refused after that time as well.
    """

    owned_tokeninfo_keys = frozenset({SENT_OTP_VALID_UNTIL})

    @staticmethod
    def _sent_otp_valid_until(validity: int) -> datetime:
        """
        Until when a value sent now may be used. The challenge, the record of the sent value and the response share
        this time, so OTP PIN plus OTP value and the answer with the transaction_id expire at the same moment.

        :param validity: The validity time in seconds
        :return: The time, in UTC
        """
        return datetime.now(timezone.utc) + timedelta(seconds=validity)

    @check_token_locked
    def _claim_otp_to_send(self, valid_until: datetime | None) -> str:
        """
        Move the OTP counter on by one for a value that is about to be sent, calculate that value and record until
        when it may be used without a transaction_id. All of it happens under the lock of the token row, so every
        send gets a counter of its own and the record belongs to the last value sent, also while other requests send
        at the same time.

        :param valid_until: Until when the value may be used, the expiry of its challenge. None for a value without a
            time limit, which leaves the record of an earlier value as it is.
        :return: The OTP value to send
        """
        # Serialize on the token row like inc_failcount(): read the id before the commit, reading it afterwards
        # reloads the expired token before the lock is held
        token_id = self.token.id
        db.session.commit()
        lock_token_row(Token.id == token_id)
        db.session.refresh(self.token)
        counter = self.token.count + 1
        self.token.count = counter
        otp = self._calc_otp(counter)
        if valid_until:
            self.write_tokeninfo(SENT_OTP_VALID_UNTIL, f"{counter} {valid_until.isoformat()}",
                                 commit_db_session=False)
        # Stores the counter and the record together and releases the lock
        db.session.commit()
        return otp

    def _remove_sent_otp_validity(self) -> None:
        """
        Remove the record of the last sent OTP value, for a value that has no time limit or after a new key replaced
        the one the value was sent with.
        """
        self.remove_tokeninfo(SENT_OTP_VALID_UNTIL)

    def check_otp(self, anOtpVal: str, counter: int | None = None, window: int | None = None,
                  options: dict | None = None) -> int:
        """
        Check the OTP value like the token class does, and refuse a matched value that was sent with a validity time
        that has passed. With a transaction_id the expiry of the challenge applies instead.

        :param anOtpVal: The OTP value to check
        :param counter: The counter to check from, the token counter if None
        :param window: How many counters to check, the count window of the token if None
        :param options: The request options
        :return: The counter of the matched value, -1 if the value does not match or is refused
        """
        options = options or {}
        # Read before the check moves the counter on, so that a value another request sends meanwhile does not
        # replace the record the check is decided by
        with_transaction_id = options.get("transaction_id") or options.get("state")
        record = None if with_transaction_id else self.get_tokeninfo(SENT_OTP_VALID_UNTIL)
        matched_counter = super().check_otp(anOtpVal, counter, window, options)
        if matched_counter >= 0 and record and self._is_sent_otp_expired(matched_counter, record):
            log.debug(f"The OTP value of token {self.token.serial} was sent longer ago than its validity time.")
            return -1
        return matched_counter

    def _is_sent_otp_expired(self, counter: int, record: str) -> bool:
        """
        Whether the OTP value at the given counter was sent with a validity time that has passed.

        :param counter: The counter of the matched OTP value
        :param record: The record of the last sent OTP value, see _claim_otp_to_send()
        :return: True if the value was sent and its validity time has passed, also if the record can not be read
        """
        try:
            sent_counter, valid_until = record.split(" ", 1)
            return (int(sent_counter) == counter
                    and datetime.now(timezone.utc) > datetime.fromisoformat(valid_until))
        except (ValueError, TypeError):
            log.warning(f"Invalid value '{record}' in the token info {SENT_OTP_VALID_UNTIL} of token "
                        f"{self.token.serial}, the OTP value is refused.")
            return True
