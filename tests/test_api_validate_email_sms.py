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
import threading
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from unittest import mock

import responses

import privacyidea.lib.tokens.emailtoken as emailtoken_module
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import set_privacyidea_config, delete_privacyidea_config
from privacyidea.lib.error import ConflictError
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.smsprovider.HttpSMSProvider import HttpSMSProvider
from privacyidea.lib.smsprovider.SMSProvider import delete_smsgateway
from privacyidea.lib.token import get_tokens, init_token, remove_token, get_one_token
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.tokens.emailtoken import EMAILACTION
from privacyidea.lib.tokens.hotptoken import HotpTokenClass
from privacyidea.lib.tokens.sent_otp_validity import SENT_OTP_VALID_UNTIL, SentOtpValidityMixin
from privacyidea.lib.tokens.smstoken import SMSAction
from privacyidea.lib.user import User
from privacyidea.models import db
from . import smtpmock
from .api_validate_common import setup_sms_gateway
from .base import MyApiTestCase, clock_moved_forward
from .test_api_parallel_requests import results_of, run_in_parallel


# The type checker treats _TestHost as the test case class, so self.assertEqual, self.app, self.at, etc. resolve; at
# runtime the base is plain object, because a TestCase base here would be collected and run without a token type.
if TYPE_CHECKING:
    _TestHost = MyApiTestCase
else:
    _TestHost = object


class SentOtpValidityTests(_TestHost):
    """
    The validity time of a sent OTP value also applies when the user sends OTP PIN and OTP value together, without a
    transaction_id. The tests run for every token class that sends the OTP value, the subclass sets up the token type
    and the transport it sends with.
    """
    pin = "pin"
    token_type: str
    validity_key: str
    autosend_action: str
    contact: dict[str, str]
    # The object and the name of the function that hands the message to the transport
    transport: object
    transport_send: str

    def setUp(self) -> None:
        super().setUp()
        self.setUp_user_realms()
        self.serials = []
        self.policies = []

    def tearDown(self) -> None:
        for serial in self.serials:
            if get_tokens(serial=serial):
                remove_token(serial)
        for policy in self.policies:
            delete_policy(policy)
        delete_privacyidea_config(self.validity_key)
        super().tearDown()

    def _enroll(self) -> str:
        serial = f"VALIDITY_{self.token_type.upper()}"
        init_token({"serial": serial, "type": self.token_type, "otpkey": self.otpkey, "pin": self.pin, **self.contact},
                   user=User("cornelius", self.realm1))
        self.serials.append(serial)
        return serial

    def _trigger(self, serial: str) -> tuple[str, str]:
        with self.app.test_request_context("/validate/triggerchallenge", method="POST", data={"serial": serial},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res.json)
        # The token counter now points at the value that was sent
        return res.json["detail"]["transaction_ids"][0], get_one_token(serial=serial).get_otp()[2]

    def _check(self, data: dict) -> bool:
        with self.app.test_request_context("/validate/check", method="POST",
                                           data={"user": "cornelius", "realm": self.realm1, **data}):
            res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res.json)
        return res.json["result"]["value"]

    def test_expired_value_is_refused(self):
        serial = self._enroll()
        set_privacyidea_config(self.validity_key, 1)
        _, otp = self._trigger(serial)
        with clock_moved_forward(2):
            self.assertFalse(self._check({"pass": self.pin + otp}))
        # The answer with the transaction_id is refused as before
        transaction_id, otp = self._trigger(serial)
        with clock_moved_forward(2):
            self.assertFalse(self._check({"pass": otp, "transaction_id": transaction_id}))

    def test_valid_value_is_accepted(self):
        serial = self._enroll()
        set_privacyidea_config(self.validity_key, 120)
        _, otp = self._trigger(serial)
        self.assertTrue(self._check({"pass": self.pin + otp}))

    def test_autosend_value_has_no_time_limit(self):
        # Autosend sends the next value after a successful login, for the next login whenever that is
        serial = self._enroll()
        set_privacyidea_config(self.validity_key, 1)
        set_policy("validity_autosend", scope=SCOPE.AUTH, action=self.autosend_action)
        self.policies.append("validity_autosend")
        transaction_id, otp = self._trigger(serial)
        self.assertTrue(self._check({"pass": otp, "transaction_id": transaction_id}))
        autosent_otp = get_one_token(serial=serial).get_otp()[2]
        with clock_moved_forward(2):
            self.assertTrue(self._check({"pass": self.pin + autosent_otp}))

    def test_record_without_timezone_is_refused(self):
        serial = self._enroll()
        self._trigger(serial)
        token = get_one_token(serial=serial)
        token.write_tokeninfo(SENT_OTP_VALID_UNTIL, f"{token.token.count} 2099-01-01T00:00:00")
        self.assertFalse(self._check({"pass": self.pin + token.get_otp()[2]}))

    def test_reinit_removes_record(self):
        serial = self._enroll()
        self._trigger(serial)
        self.assertIsNotNone(get_one_token(serial=serial).get_tokeninfo(SENT_OTP_VALID_UNTIL))
        with self.app.test_request_context("/token/init", method="POST",
                                           data={"serial": serial, "type": self.token_type, "otpkey": self.otpkey,
                                                 **self.contact},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res.json)
        token = get_one_token(serial=serial)
        self.assertEqual(0, token.token.count)
        self.assertIsNone(token.get_tokeninfo(SENT_OTP_VALID_UNTIL))

    def test_value_sent_during_the_check_keeps_the_limit(self):
        # Another request sends a value after the expired one matched and moved the counter on, but before its time
        # limit is checked. The check is still decided by the record of the matched value.
        serial = self._enroll()
        set_privacyidea_config(self.validity_key, 1)
        _, otp = self._trigger(serial)
        hotp_check_otp = HotpTokenClass.check_otp

        def check_otp_while_another_request_sends(token, *args, **kwargs):
            result = hotp_check_otp(token, *args, **kwargs)
            get_one_token(serial=serial).create_challenge()
            return result

        with (clock_moved_forward(2),
              mock.patch.object(HotpTokenClass, "check_otp", check_otp_while_another_request_sends)):
            self.assertFalse(self._check({"pass": self.pin + otp}))

    def test_lost_counter_claim_is_retried(self):
        # Another request moved the counter on between the read and the conditional update of this send
        serial = self._enroll()
        advance = TokenClass.advance_otp_count
        lost = []

        def lose_first_claim(token, new_count):
            if not lost:
                lost.append(new_count)
                return False
            return advance(token, new_count)

        with mock.patch.object(TokenClass, "advance_otp_count", lose_first_claim):
            _, otp = self._trigger(serial)
        token = get_one_token(serial=serial)
        self.assertListEqual([1], lost)
        self.assertEqual(1, token.token.count)
        self.assertEqual("1", token.get_tokeninfo(SENT_OTP_VALID_UNTIL).split(" ")[0])
        self.assertTrue(self._check({"pass": self.pin + otp}))

    def test_send_fails_when_no_counter_can_be_claimed(self):
        serial = self._enroll()
        with mock.patch.object(TokenClass, "advance_otp_count", return_value=False):
            with self.app.test_request_context("/validate/triggerchallenge", method="POST",
                                               data={"serial": serial}, headers={"Authorization": self.at}):
                res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res.json)
        self.assertFalse(res.json["result"]["value"], res.json)
        token = get_one_token(serial=serial)
        self.assertEqual(0, token.token.count)
        self.assertIsNone(token.get_tokeninfo(SENT_OTP_VALID_UNTIL))

    def test_autosend_without_a_counter_keeps_the_login(self):
        # The authentication succeeded before autosend claims the counter of the next value
        serial = self._enroll()
        set_policy("validity_autosend", scope=SCOPE.AUTH, action=self.autosend_action)
        self.policies.append("validity_autosend")
        _, otp = self._trigger(serial)
        with mock.patch.object(SentOtpValidityMixin, "_claim_otp_count_to_send",
                               side_effect=ConflictError("counter moved on")):
            self.assertTrue(self._check({"pass": self.pin + otp}))
        self.assertEqual(2, get_one_token(serial=serial).token.count)

    def test_overlapping_sends_keep_the_time_limit_of_the_later_value(self):
        # The second send claims its counter and records its value after the first one claimed its counter and before
        # the first one records
        if db.engine.dialect.name == "sqlite":
            self.skipTest("SQLite serializes the writers, the interleaving cannot be reproduced")
        serial = self._enroll()
        set_privacyidea_config(self.validity_key, 1)
        first_has_claimed = threading.Event()
        second_has_recorded = threading.Event()
        real_record = SentOtpValidityMixin._record_sent_otp_validity

        def record_after_the_other(token: SentOtpValidityMixin, *args, **kwargs) -> None:
            if not first_has_claimed.is_set():
                first_has_claimed.set()
                second_has_recorded.wait(10)
                real_record(token, *args, **kwargs)
            else:
                real_record(token, *args, **kwargs)
                second_has_recorded.set()

        def trigger() -> dict:
            with self.app.test_client() as client:
                return client.post("/validate/triggerchallenge", data={"serial": serial},
                                   headers={"Authorization": self.at}).json

        def second_trigger() -> dict:
            first_has_claimed.wait(10)
            return trigger()

        with mock.patch.object(SentOtpValidityMixin, "_record_sent_otp_validity", record_after_the_other):
            results = results_of(run_in_parallel(self.app, [trigger, second_trigger]))

        self.assertTrue(all(isinstance(result, dict) and result.get("status") for result in results), results)
        token = get_one_token(serial=serial)
        self.assertEqual(2, token.token.count)
        self.assertEqual("2", token.get_tokeninfo(SENT_OTP_VALID_UNTIL).split(" ")[0])
        with clock_moved_forward(2):
            self.assertFalse(self._check({"pass": self.pin + token._calc_otp(2)}))

    def test_challenge_and_record_share_the_deadline(self):
        serial = self._enroll()
        transaction_id, _ = self._trigger(serial)
        record = get_one_token(serial=serial).get_tokeninfo(SENT_OTP_VALID_UNTIL)
        challenge = get_challenges(serial=serial, transaction_id=transaction_id)[0]
        self.assertEqual(challenge.expiration, datetime.fromisoformat(record.split(" ", 1)[1]).replace(tzinfo=None),
                         record)

    def test_send_from_before_a_reinit_does_not_extend_the_new_value(self):
        # An old-key send claims counter 1, the token is re-initialized and the new key sends its value at counter 1.
        # The old-key send records only after that value expired: it keeps the deadline it computed before its claim.
        serial = self._enroll()
        set_privacyidea_config(self.validity_key, 1)
        real_record = SentOtpValidityMixin._record_sent_otp_validity
        new_key = "3031323334353637383930313233343536373839"
        old_key_counters = []

        def reinit_and_record_late(token: SentOtpValidityMixin, counter: int, *args, **kwargs) -> None:
            if old_key_counters:
                real_record(token, counter, *args, **kwargs)
                return
            old_key_counters.append(counter)
            init_token({"serial": serial, "type": self.token_type, "otpkey": new_key, **self.contact},
                       user=User("cornelius", self.realm1))
            get_one_token(serial=serial).create_challenge()
            with clock_moved_forward(2):
                real_record(token, counter, *args, **kwargs)

        with mock.patch.object(SentOtpValidityMixin, "_record_sent_otp_validity", reinit_and_record_late):
            get_one_token(serial=serial).create_challenge()
        token = get_one_token(serial=serial)
        self.assertListEqual([1], old_key_counters)
        self.assertEqual(1, token.token.count)
        with clock_moved_forward(2):
            self.assertFalse(self._check({"pass": self.pin + token._calc_otp(1)}))

    def test_send_from_before_a_reinit_does_not_block_the_new_key(self):
        # An old-key send claims its counter, then the token is re-initialized and the new key sends its first value,
        # then the old-key send records
        serial = self._enroll()
        set_privacyidea_config(self.validity_key, 1)
        for _ in range(3):
            self._trigger(serial)
        real_record = SentOtpValidityMixin._record_sent_otp_validity
        new_key = "3031323334353637383930313233343536373839"
        old_key_counters = []

        def reinit_before_the_old_key_records(token: SentOtpValidityMixin, counter: int, *args, **kwargs) -> None:
            if not old_key_counters:
                old_key_counters.append(counter)
                init_token({"serial": serial, "type": self.token_type, "otpkey": new_key, **self.contact},
                           user=User("cornelius", self.realm1))
                get_one_token(serial=serial).create_challenge()
            real_record(token, counter, *args, **kwargs)

        with mock.patch.object(SentOtpValidityMixin, "_record_sent_otp_validity", reinit_before_the_old_key_records):
            get_one_token(serial=serial).create_challenge()
        token = get_one_token(serial=serial)
        self.assertListEqual([4], old_key_counters)
        self.assertEqual(1, token.token.count)
        self.assertEqual("1", token.get_tokeninfo(SENT_OTP_VALID_UNTIL).split(" ")[0])
        with clock_moved_forward(2):
            self.assertFalse(self._check({"pass": self.pin + token._calc_otp(1)}))

    def test_value_delivered_before_the_transport_fails_keeps_its_time_limit(self):
        # The transport delivers the value and then fails, e.g. SMTP quit or a gateway response that times out
        serial = self._enroll()
        set_privacyidea_config(self.validity_key, 1)
        real_send = getattr(self.transport, self.transport_send)

        def deliver_then_fail(*args, **kwargs):
            real_send(*args, **kwargs)
            raise ConnectionError("connection lost after delivery")

        with mock.patch.object(self.transport, self.transport_send, deliver_then_fail):
            with self.app.test_request_context("/validate/triggerchallenge", method="POST",
                                               data={"serial": serial}, headers={"Authorization": self.at}):
                res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res.json)
        token = get_one_token(serial=serial)
        self.assertEqual(1, token.token.count)
        self.assertEqual("1", token.get_tokeninfo(SENT_OTP_VALID_UNTIL).split(" ")[0])
        with clock_moved_forward(2):
            self.assertFalse(self._check({"pass": self.pin + token._calc_otp(1)}))

    def test_older_send_keeps_the_record_of_a_newer_one(self):
        # A send that claimed its counter earlier finishes after a send that claimed a higher one. The sends claimed
        # their counters, so the token counter is at the highest of them.
        serial = self._enroll()
        token = get_one_token(serial=serial)
        token.set_otp_count(6)
        valid_until = datetime.now(timezone.utc) + timedelta(seconds=120)
        token._record_sent_otp_validity(5, valid_until)
        token._record_sent_otp_validity(4, valid_until)
        self.assertEqual("5", get_one_token(serial=serial).get_tokeninfo(SENT_OTP_VALID_UNTIL).split(" ")[0])
        token._record_sent_otp_validity(6, valid_until)
        self.assertEqual("6", get_one_token(serial=serial).get_tokeninfo(SENT_OTP_VALID_UNTIL).split(" ")[0])

    def test_failed_reinit_keeps_record(self):
        # A re-initialization that fails keeps the old key and counter, so the sent value keeps its time limit
        serial = self._enroll()
        set_privacyidea_config(self.validity_key, 120)
        before_send = datetime.now(timezone.utc)
        _, otp = self._trigger(serial)
        after_send = datetime.now(timezone.utc)
        record = get_one_token(serial=serial).get_tokeninfo(SENT_OTP_VALID_UNTIL)
        sent_counter, valid_until = record.split(" ", 1)
        self.assertEqual(get_one_token(serial=serial).token.count, int(sent_counter), record)
        self.assertTrue(before_send + timedelta(seconds=120) <= datetime.fromisoformat(valid_until)
                        <= after_send + timedelta(seconds=120), record)

        with self.app.test_request_context("/token/init", method="POST",
                                           data={"serial": serial, "type": self.token_type, "otpkey": self.otpkey,
                                                 "otpkeyformat": "unknown", **self.contact},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
        self.assertEqual(400, res.status_code, res.json)
        self.assertEqual(record, get_one_token(serial=serial).get_tokeninfo(SENT_OTP_VALID_UNTIL))
        self.assertTrue(self._check({"pass": self.pin + otp}))


class EmailSentOtpValidityTestCase(SentOtpValidityTests, MyApiTestCase):
    token_type = "email"
    validity_key = "email.validtime"
    autosend_action = EMAILACTION.EMAILAUTO
    contact = {"email": "hans@dampf.com"}
    transport = emailtoken_module
    transport_send = "send_email_data"

    def setUp(self) -> None:
        super().setUp()
        smtpmock.mock.__enter__()
        self.addCleanup(smtpmock.mock.__exit__, None, None, None)
        smtpmock.setdata(response={"hans@dampf.com": (200, "OK")})


class SmsSentOtpValidityTestCase(SentOtpValidityTests, MyApiTestCase):
    token_type = "sms"
    validity_key = "sms.providerTimeout"
    autosend_action = SMSAction.SMSAUTO
    contact = {"phone": "123456"}
    transport = HttpSMSProvider
    transport_send = "submit_message"

    def setUp(self) -> None:
        super().setUp()
        responses.mock.__enter__()
        self.addCleanup(responses.mock.__exit__, None, None, None)
        setup_sms_gateway()

    def tearDown(self) -> None:
        delete_smsgateway("myGW")
        delete_privacyidea_config("sms.identifier")
        super().tearDown()
