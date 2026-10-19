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

    def _record_sent_otp_validity(self, validity_seconds: int | None) -> None:
        """
        Store until when the OTP value at the current counter, which was just sent to the user, may be used without
        a transaction_id.

        :param validity_seconds: The validity time of the value, None for a value without a time limit, e.g. one
            that is sent for a later login
        """
        if validity_seconds is None:
            self.remove_tokeninfo(SENT_OTP_VALID_UNTIL)
        else:
            valid_until = datetime.now(timezone.utc) + timedelta(seconds=validity_seconds)
            self.write_tokeninfo(SENT_OTP_VALID_UNTIL, f"{self.token.count} {valid_until.isoformat()}")

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
