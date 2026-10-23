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

from datetime import datetime, timezone
import logging

from sqlalchemy import select

from privacyidea.lib.error import ConflictError
from privacyidea.lib.tokenclass import lock_token_row
from privacyidea.models import Token, TokenInfo, db

log = logging.getLogger(__name__)

# Token info holding the counter of the OTP value last sent to the user and until when it may be used
SENT_OTP_VALID_UNTIL = "sent_otp_valid_until"
# How often a send tries to claim a counter while other requests keep moving it on
CLAIM_ATTEMPTS = 10


class SentOtpValidityMixin:
    """
    For token classes that send the OTP value to the user, e.g. by email or SMS. The validity time of a sent value
    is the expiry of its challenge, which only the answer with a transaction_id checks. The mixin records the
    validity of the sent value, so that OTP PIN and OTP value sent together are refused after that time as well.
    """

    owned_tokeninfo_keys = frozenset({SENT_OTP_VALID_UNTIL})

    def _claim_otp_count_to_send(self) -> int:
        """
        Move the OTP counter on by one for a value that is about to be sent and return the counter of that value. The
        conditional update gives every send a counter of its own and never moves the counter backwards, also when
        several requests send at the same time.

        :return: The counter of the value to send
        :raises ConflictError: If other requests kept moving the counter on
        """
        token_id = self.token.id
        for _ in range(CLAIM_ATTEMPTS):
            current = db.session.scalar(select(Token.count).where(Token.id == token_id))
            if self.advance_otp_count(current + 1):
                return current + 1
        raise ConflictError(f"Could not claim an OTP counter for token {self.token.serial}.")

    def _record_sent_otp_validity(self, counter: int, valid_until: datetime) -> None:
        """
        Store until when the sent OTP value at the given counter may be used without a transaction_id. A send that
        claimed its counter earlier can finish later than another one, so the record of a higher counter is kept.

        A send records only a counter it claimed, and the claim moves the token counter there, so the counter of a
        record of the current key is never above the token counter. Only a re-initialization moves the token counter
        back: nothing is stored for a counter above the token counter, which was claimed with the replaced key, and a
        record with a counter above the token counter, which belongs to the replaced key, is replaced.

        :param counter: The counter of the sent value, see _claim_otp_count_to_send()
        :param valid_until: Until when the value may be used, the expiry of its challenge
        """
        # Serialize on the token row like inc_failcount(), so the comparison and the write are not interleaved with
        # those of another send. write_tokeninfo() commits and releases the lock.
        token_id = self.token.id
        db.session.commit()
        lock_token_row(Token.id == token_id)
        token_count = db.session.scalar(select(Token.count).where(Token.id == token_id))
        recorded = db.session.scalar(select(TokenInfo.Value).where(TokenInfo.token_id == token_id,
                                                                   TokenInfo.Key == SENT_OTP_VALID_UNTIL))
        if token_count < counter or (recorded and counter < self._recorded_counter(recorded) <= token_count):
            db.session.commit()
            return
        self.write_tokeninfo(SENT_OTP_VALID_UNTIL, f"{counter} {valid_until.isoformat()}")

    def _remove_sent_otp_validity(self) -> None:
        """
        Remove the record of the last sent OTP value, for a value that has no time limit.
        """
        self.remove_tokeninfo(SENT_OTP_VALID_UNTIL)

    def _remove_sent_otp_validity_of_replaced_key(self) -> None:
        """
        Remove the record of a value sent with the key the token had before it was re-initialized. A value the new key
        sent since then keeps its record: its counter is not above the reset token counter, unlike the counter of a
        value sent with the old key.
        """
        # Serialize on the token row like _record_sent_otp_validity(), so a send of the new key is not interleaved
        token_id = self.token.id
        db.session.commit()
        lock_token_row(Token.id == token_id)
        token_count = db.session.scalar(select(Token.count).where(Token.id == token_id))
        recorded = db.session.scalar(select(TokenInfo.Value).where(TokenInfo.token_id == token_id,
                                                                   TokenInfo.Key == SENT_OTP_VALID_UNTIL))
        recorded_counter = self._recorded_counter(recorded) if recorded else None
        if recorded_counter is not None and (recorded_counter < 0 or recorded_counter > token_count):
            # remove_tokeninfo() commits and releases the lock
            self.remove_tokeninfo(SENT_OTP_VALID_UNTIL)
        else:
            db.session.commit()

    @staticmethod
    def _recorded_counter(record: str) -> int:
        """
        The counter of a record of a sent OTP value.

        :param record: The record, see _record_sent_otp_validity()
        :return: The counter, -1 if the record can not be read
        """
        try:
            return int(record.split(" ", 1)[0])
        except ValueError:
            return -1

    def _get_sent_otp_record(self, options: dict) -> str | None:
        """
        Read the record of the last sent OTP value for a check without a transaction_id. It is read before the OTP
        check moves the counter on, so that a value another request sends meanwhile does not replace the record the
        check is decided by. With a transaction_id the expiry of the challenge applies instead.

        :param options: The request options
        :return: The record, None if there is none or the request has a transaction_id
        """
        if options.get("transaction_id") or options.get("state"):
            return None
        return self.get_tokeninfo(SENT_OTP_VALID_UNTIL)

    def _is_sent_otp_expired(self, counter: int, record: str) -> bool:
        """
        Whether the OTP value at the given counter was sent with a validity time that has passed.

        :param counter: The counter of the matched OTP value
        :param record: The record of the last sent OTP value, see _get_sent_otp_record()
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

    def _refuse_expired_sent_otp(self, counter: int, record: str | None) -> int:
        """
        Refuse a matched OTP value that was sent with a validity time that has passed.

        :param counter: The counter of the matched OTP value, or -1
        :param record: The record read before the OTP check, see _get_sent_otp_record()
        :return: The counter, or -1 if the value is refused
        """
        if counter >= 0 and record and self._is_sent_otp_expired(counter, record):
            log.debug(f"The OTP value of token {self.token.serial} was sent longer ago than its validity time.")
            return -1
        return counter
