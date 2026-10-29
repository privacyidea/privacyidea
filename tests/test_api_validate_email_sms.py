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
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.smsprovider.HttpSMSProvider import HttpSMSProvider
from privacyidea.lib.smsprovider.SMSProvider import delete_smsgateway
from privacyidea.lib.token import get_tokens, init_token, remove_token, get_one_token
from privacyidea.lib.tokens.emailtoken import EMAILACTION
from privacyidea.lib.tokens.hotptoken import HotpTokenClass
from privacyidea.lib.tokens.sent_otp_validity import SENT_OTP_VALID_UNTIL, SentOtpValidityMixin
from privacyidea.lib.tokens.smstoken import SMSAction
from privacyidea.lib.user import User
from . import smtpmock
from .api_validate_common import setup_sms_gateway
from .base import MyApiTestCase, clock_moved_forward, results_of, run_in_parallel


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
        # Long enough for the first value, which is checked without moving the clock
        set_privacyidea_config(self.validity_key, 120)
        set_policy("validity_autosend", scope=SCOPE.AUTH, action=self.autosend_action)
        self.policies.append("validity_autosend")
        transaction_id, otp = self._trigger(serial)
        self.assertTrue(self._check({"pass": otp, "transaction_id": transaction_id}))
        autosent_otp = get_one_token(serial=serial).get_otp()[2]
        with clock_moved_forward(121):
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

    def _trigger_in_thread(self, serial: str) -> dict:
        with self.app.test_client() as client:
            return client.post("/validate/triggerchallenge", data={"serial": serial},
                               headers={"Authorization": self.at}).json

    def test_parallel_sends_get_a_counter_each(self):
        # Two sends reach the token at the same time. Each one sends the value of a counter of its own, and the
        # record belongs to the value sent last.
        serial = self._enroll()
        set_privacyidea_config(self.validity_key, 1)
        both_sending = threading.Barrier(2, timeout=5)
        claim = SentOtpValidityMixin._claim_otp_to_send
        sent_otps = []

        def claim_together(token: SentOtpValidityMixin, valid_until: datetime | None) -> str:
            both_sending.wait()
            otp = claim(token, valid_until)
            sent_otps.append(otp)
            return otp

        with mock.patch.object(SentOtpValidityMixin, "_claim_otp_to_send", claim_together):
            results = results_of(run_in_parallel(self.app, [lambda: self._trigger_in_thread(serial)] * 2))

        self.assertTrue(all(isinstance(result, dict) and result.get("status") for result in results), results)
        token = get_one_token(serial=serial)
        self.assertEqual(2, token.token.count)
        self.assertEqual("2", token.get_tokeninfo(SENT_OTP_VALID_UNTIL).split(" ")[0])
        self.assertSetEqual({token._calc_otp(1), token._calc_otp(2)}, set(sent_otps))
        with clock_moved_forward(2):
            self.assertFalse(self._check({"pass": self.pin + token._calc_otp(2)}))

    def test_challenge_and_record_share_the_deadline(self):
        serial = self._enroll()
        transaction_id, _ = self._trigger(serial)
        record = get_one_token(serial=serial).get_tokeninfo(SENT_OTP_VALID_UNTIL)
        challenge = get_challenges(serial=serial, transaction_id=transaction_id)[0]
        self.assertEqual(challenge.expiration, datetime.fromisoformat(record.split(" ", 1)[1]).replace(tzinfo=None),
                         record)

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
