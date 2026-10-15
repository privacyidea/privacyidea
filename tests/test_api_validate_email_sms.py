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
import responses

from privacyidea.lib.config import set_privacyidea_config, delete_privacyidea_config
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.smsprovider.SMSProvider import delete_smsgateway
from privacyidea.lib.token import get_tokens, init_token, remove_token, get_one_token
from privacyidea.lib.tokens.emailtoken import EMAILACTION
from privacyidea.lib.tokens.sent_otp_validity import SENT_OTP_VALID_UNTIL
from privacyidea.lib.tokens.smstoken import SMSAction
from privacyidea.lib.user import User
from . import smtpmock
from .api_validate_common import setup_sms_gateway
from .base import MyApiTestCase, clock_moved_forward


class SentOtpValidityTests:
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


class EmailSentOtpValidityTestCase(SentOtpValidityTests, MyApiTestCase):
    token_type = "email"
    validity_key = "email.validtime"
    autosend_action = EMAILACTION.EMAILAUTO
    contact = {"email": "hans@dampf.com"}

    def setUp(self) -> None:
        super().setUp()
        self.enterContext(smtpmock.mock)
        smtpmock.setdata(response={"hans@dampf.com": (200, "OK")})


class SmsSentOtpValidityTestCase(SentOtpValidityTests, MyApiTestCase):
    token_type = "sms"
    validity_key = "sms.providerTimeout"
    autosend_action = SMSAction.SMSAUTO
    contact = {"phone": "123456"}

    def setUp(self) -> None:
        super().setUp()
        self.enterContext(responses.mock)
        setup_sms_gateway()

    def tearDown(self) -> None:
        delete_smsgateway("myGW")
        delete_privacyidea_config("sms.identifier")
        super().tearDown()
