# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
import datetime
import json
import logging
import re
import time
from base64 import b32encode
from datetime import timezone
from urllib.parse import quote

import mock
import responses
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from dateutil.tz import tzlocal
from passlib.hash import argon2
from testfixtures import Replace, test_datetime
from testfixtures import log_capture

from privacyidea.lib import _
from privacyidea.lib.applications.offline import REFILLTOKEN_LENGTH
from privacyidea.lib.authcache import _hash_password
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import (set_privacyidea_config,
                                    get_inc_fail_count_on_false_pin,
                                    delete_privacyidea_config, SYSCONF)
from privacyidea.lib.container import init_container, find_container_by_serial, create_container_template
from privacyidea.lib.error import Error
from privacyidea.lib.event import delete_event
from privacyidea.lib.event import set_event
from privacyidea.lib.machine import attach_token, detach_token
from privacyidea.lib.machineresolver import save_resolver as save_machine_resolver
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy, AUTHORIZED
from privacyidea.lib.radiusserver import add_radius
from privacyidea.lib.realm import set_realm, set_default_realm, delete_realm
from privacyidea.lib.resolver import save_resolver, get_resolver_list, delete_resolver
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
from privacyidea.lib.token import (get_tokens, init_token, remove_token,
                                   reset_token, enable_token, revoke_token,
                                   set_pin, get_one_token, unassign_token)
from privacyidea.lib.tokenclass import (ClientMode, FAILCOUNTER_EXCEEDED,
                                        FAILCOUNTER_CLEAR_TIMEOUT, DATE_FORMAT,
                                        AUTH_DATE_FORMAT)
from privacyidea.lib.tokens.passwordtoken import DEFAULT_LENGTH as DEFAULT_LENGTH_PW
from privacyidea.lib.tokens.pushtoken import PushAction, POLL_ONLY, strip_pem_headers
from privacyidea.lib.tokens.registrationtoken import DEFAULT_LENGTH as DEFAULT_LENGTH_REG
from privacyidea.lib.tokens.registrationtoken import RegistrationTokenClass
from privacyidea.lib.tokens.smstoken import SmsTokenClass
from privacyidea.lib.tokens.totptoken import HotpTokenClass
from privacyidea.lib.tokens.yubikeytoken import YubikeyTokenClass
from privacyidea.lib.user import (User)
from privacyidea.lib.users.custom_user_attributes import InternalCustomUserAttributes
from privacyidea.lib.utils import AUTH_RESPONSE
from privacyidea.lib.utils import to_unicode
from privacyidea.models import (Token, Policy, Challenge, AuthCache, db, TokenOwner, Realm, CustomUserAttribute,
                                NodeName)
from . import smtpmock, ldap3mock, radiusmock
from .base import MyApiTestCase
from .test_lib_tokencontainer import MockSmartphone

from .api_validate_common import LDAPDirectory, OTPs, HOSTSFILE, DICT_FILE, setup_sms_gateway


class ValidateAPITestCase(MyApiTestCase):
    """
    test the api.validate endpoints
    """

    def test_00_setup(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()

        # create a  token and assign it to the user
        db_token = Token(self.serials[0], tokentype="hotp")
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        token = HotpTokenClass(db_token)
        self.assertTrue(token.token.serial == self.serials[0], token)
        token.add_user(User("cornelius", self.realm1))
        token.set_pin("pin")
        self.assertEqual(token.token.first_owner.user_id, "1000")

    def test_02_validate_check(self):
        # is the token still assigned?
        tokenbject_list = get_tokens(serial=self.serials[0])
        tokenobject = tokenbject_list[0]
        self.assertEqual(tokenobject.token.first_owner.user_id, "1000")

        """                  Truncated
           Count    Hexadecimal    Decimal        HOTP
           0        4c93cf18       1284755224     755224
           1        41397eea       1094287082     287082
           2         82fef30        137359152     359152
           3        66ef7655       1726969429     969429
           4        61c5938a       1640338314     338314
           5        33c083d4        868254676     254676
           6        7256c032       1918287922     287922
           7         4e5b397         82162583     162583
           8        2823443f        673399871     399871
           9        2679dc69        645520489     520489
        """
        # test for missing parameter user
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # test for missing parameter serial
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # test for missing parameter "pass"
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(404, res.status_code)

    def test_03_check_user(self):
        # get the original counter
        tokenobject_list = get_tokens(serial=self.serials[0])
        hotp_tokenobject = tokenobject_list[0]
        count_1 = hotp_tokenobject.token.count

        # test successful authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("otplen"), 6)
            # check if serial has been added to g
            self.assertTrue(self.app_context.g.serial, detail["serial"])

        # Check that the counter is increased!
        tokenobject_list = get_tokens(serial=self.serials[0])
        hotp_tokenobject = tokenobject_list[0]
        count_2 = hotp_tokenobject.token.count
        self.assertTrue(count_2 > count_1, (hotp_tokenobject.token.serial,
                                            hotp_tokenobject.token.count,
                                            count_1,
                                            count_2))

        # test authentication fails with the same OTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)
            # This is the same OTP value, so we get the "previous otp value" message
            detail = res.json.get("detail")
            self.assertIn("previous otp used again", detail.get("message"))

    def test_03a_check_user_get(self):
        # Reset the counter!
        count_1 = 0
        tokenobject_list = get_tokens(serial=self.serials[0])
        hotp_tokenobject = tokenobject_list[0]
        hotp_tokenobject.token.count = count_1
        hotp_tokenobject.token.save()

        # test successful authentication
        with self.app.test_request_context('/validate/check',
                                           method='GET',
                                           query_string={"user": "cornelius",
                                                         "pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("otplen"), 6)

        # Check that the counter is increased!
        tokenobject_list = get_tokens(serial=self.serials[0])
        hotp_tokenobject = tokenobject_list[0]
        count_2 = hotp_tokenobject.token.count
        self.assertTrue(count_2 > count_1, (hotp_tokenobject.token.serial,
                                            hotp_tokenobject.token.count,
                                            count_1,
                                            count_2))

        # test authentication fails with the same OTP
        with self.app.test_request_context('/validate/check',
                                           method='GET',
                                           query_string={"user": "cornelius",
                                                         "pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)

    def test_04_check_serial(self):
        # test authentication successful with serial
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": self.serials[0],
                                                 "pass": "pin969429"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)

        # test authentication fails with serial with same OTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": self.serials[0],
                                                 "pass": "pin969429"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            details = res.json.get("detail")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)
            self.assertEqual(details.get("message"), "wrong otp value. "
                                                     "previous otp used again")

    def test_05_check_serial_with_no_user(self):
        # Check a token per serial when the token has no user assigned.
        init_token({"serial": "nouser",
                    "otpkey": self.otpkey,
                    "pin": "pin"})
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "nouser",
                                                 "pass": "pin359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("status"), True)
            self.assertEqual(result.get("value"), True)

    def test_05a_check_otp_only(self):
        # Check the OTP of the token without PIN
        init_token({"serial": "otponly",
                    "otpkey": self.otpkey,
                    "pin": "pin"})
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "otponly",
                                                 "otponly": "1",
                                                 "pass": "359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("status"), True)
            self.assertEqual(result.get("value"), True)

    def test_06_fail_counter(self):
        # test if a user has several tokens that the fail counter is increased
        # reset the failcounter
        reset_token(serial="SE1")
        init_token({"serial": "s2",
                    "genkey": 1,
                    "pin": "test"}, user=User("cornelius", self.realm1))
        init_token({"serial": "s3",
                    "genkey": 1,
                    "pin": "test"}, user=User("cornelius", self.realm1))
        # Now the user cornelius has 3 tokens.
        # SE1 with pin "pin"
        # token s2 with pin "test" and
        # token s3 with pin "test".

        self.assertTrue(get_inc_fail_count_on_false_pin())
        # We give an OTP PIN that does not match any token.
        # The failcounter of all tokens will be increased
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "XXXX123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            # if there is NO matching token, g.serial is set to None
            self.assertTrue(self.app_context.g.serial is None)

        tok = get_tokens(serial="SE1")[0]
        self.assertEqual(tok.token.failcount, 1)
        tok = get_tokens(serial="s2")[0]
        self.assertEqual(tok.token.failcount, 1)
        tok = get_tokens(serial="s3")[0]
        self.assertEqual(tok.token.failcount, 1)

        # Now we give the matching OTP PIN of one token.
        # Only one failcounter will be increased
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(detail.get("serial"), "SE1")
            self.assertEqual(detail.get("message"), "wrong otp value")

        # Only the failcounter of SE1 (the PIN matching token) is increased!
        tok = get_tokens(serial="SE1")[0]
        self.assertEqual(tok.token.failcount, 2)
        tok = get_tokens(serial="s2")[0]
        self.assertEqual(tok.token.failcount, 1)
        tok = get_tokens(serial="s3")[0]
        self.assertEqual(tok.token.failcount, 1)

        set_privacyidea_config(SYSCONF.INCFAILCOUNTER, False)
        self.assertFalse(get_inc_fail_count_on_false_pin())
        reset_token(serial="SE1")
        reset_token(serial="s2")
        reset_token(serial="s3")
        # If we try to authenticate with an OTP PIN that does not match any
        # token NO failcounter is increased!
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "XXXX123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))

        tok = get_tokens(serial="SE1")[0]
        self.assertEqual(tok.token.failcount, 0)
        tok = get_tokens(serial="s2")[0]
        self.assertEqual(tok.token.failcount, 0)
        tok = get_tokens(serial="s3")[0]
        self.assertEqual(tok.token.failcount, 0)

        # Now we give the matching OTP PIN of one token.
        # Only one failcounter will be increased
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(detail.get("serial"), "SE1")
            self.assertEqual(detail.get("message"), "wrong otp value")

        # Only the failcounter of SE1 (the PIN matching token) is increased!
        tok = get_tokens(serial="SE1")[0]
        self.assertEqual(tok.token.failcount, 1)
        tok = get_tokens(serial="s2")[0]
        self.assertEqual(tok.token.failcount, 0)
        tok = get_tokens(serial="s3")[0]
        self.assertEqual(tok.token.failcount, 0)

        # clean up
        remove_token("s2")
        remove_token("s3")
        set_privacyidea_config(SYSCONF.INCFAILCOUNTER, True)

    def test_07_authentication_counter_exceeded(self):
        token_obj = init_token({"serial": "pass1", "pin": "123456",
                                "type": "spass"})
        token_obj.set_count_auth_max(5)

        for i in range(0, 5):
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"serial": "pass1",
                                                     "pass": "123456"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertEqual(result.get("value"), True)

        # The 6th authentication will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "pass1",
                                                 "pass": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), False)
            self.assertTrue("Authentication counter exceeded"
                            in detail.get("message"))

    def test_08_failcounter_counter_exceeded(self):
        token = init_token({"serial": "pass2", "pin": "123456", "type": "spass"})
        token.set_maxfail(5)
        token.set_failcount(5)
        past = datetime.datetime.now(tzlocal()) - datetime.timedelta(minutes=10)
        token.add_tokeninfo(FAILCOUNTER_EXCEEDED, past.strftime(DATE_FORMAT))
        # a valid authentication will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "pass2",
                                                 "pass": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual("Failcounter exceeded", detail.get("message"))
        self.assertEqual(5, token.get_failcount())
        # invalid authentication fails with same message
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "pass2",
                                                 "pass": "000000"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual("Failcounter exceeded", detail.get("message"))
        self.assertEqual(5, token.get_failcount())

        # set timeout
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 30)
        # timeout not expired: same behaviour
        # a valid authentication will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "pass2",
                                                 "pass": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual("Failcounter exceeded", detail.get("message"))
        self.assertEqual(5, token.get_failcount())
        # invalid authentication fails with same message
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "pass2",
                                                 "pass": "000000"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual("Failcounter exceeded", detail.get("message"))
        self.assertEqual(5, token.get_failcount())

        # timeout expired
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 5)
        # a valid authentication succeeds and resets failcount to 0
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "pass2",
                                                 "pass": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertTrue(result.get("value"))
            self.assertEqual("matching 1 tokens", detail.get("message"))
        self.assertEqual(0, token.get_failcount())
        # an invalid auth also resets the failcount and increase it directly to one due to the invalid auth
        token.set_failcount(5)
        token.add_tokeninfo(FAILCOUNTER_EXCEEDED, past.strftime(DATE_FORMAT))
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "pass2",
                                                 "pass": "000000"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual("wrong otp pin", detail.get("message"))
        token = get_one_token(serial=token.get_serial())
        self.assertEqual(1, token.get_failcount())

        token.delete_token()
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 0)

    def test_10_saml_check(self):
        # test successful authentication
        set_privacyidea_config("ReturnSamlAttributes", "0")
        with self.app.test_request_context('/validate/samlcheck',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin338314"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            attributes = value.get("attributes")
            self.assertEqual(value.get("auth"), True)
            # No SAML return attributes
            self.assertEqual(attributes.get("email"), None)

        set_privacyidea_config("ReturnSamlAttributes", "1")

        with self.app.test_request_context('/validate/samlcheck',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin254676"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["authentication"], AUTH_RESPONSE.ACCEPT, result)
            value = result.get("value")
            attributes = value.get("attributes")
            self.assertEqual(value.get("auth"), True)
            self.assertEqual(attributes.get("email"),
                             "user@localhost.localdomain")
            self.assertEqual(attributes.get("givenname"), "Cornelius")
            self.assertEqual(attributes.get("mobile"), "+491111111")
            self.assertEqual(attributes.get("phone"), "+491234566")
            self.assertEqual(attributes.get("realm"), "realm1")
            self.assertEqual(attributes.get("username"), "cornelius")

        # Return SAML attributes On Fail
        with self.app.test_request_context('/validate/samlcheck',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin254676"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["authentication"], AUTH_RESPONSE.REJECT, result)
            value = result.get("value")
            attributes = value.get("attributes")
            self.assertEqual(value.get("auth"), False)
            self.assertEqual(attributes.get("email"), None)
            self.assertEqual(attributes.get("givenname"), None)
            self.assertEqual(attributes.get("mobile"), None)
            self.assertEqual(attributes.get("phone"), None)
            self.assertEqual(attributes.get("realm"), None)
            self.assertEqual(attributes.get("username"), None)

        set_privacyidea_config("ReturnSamlAttributesOnFail", "1")
        with self.app.test_request_context('/validate/samlcheck',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin254676"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertEqual(result["authentication"], AUTH_RESPONSE.REJECT, result)
            attributes = value.get("attributes")
            self.assertEqual(value.get("auth"), False)
            self.assertEqual(attributes.get("email"),
                             "user@localhost.localdomain")
            self.assertEqual(attributes.get("givenname"), "Cornelius")
            self.assertEqual(attributes.get("mobile"), "+491111111")
            self.assertEqual(attributes.get("phone"), "+491234566")
            self.assertEqual(attributes.get("realm"), "realm1")
            self.assertEqual(attributes.get("username"), "cornelius")

    def test_10b_samlcheck_challenge_response(self):
        self.setUp_user_realms()
        init_token({'serial': "ChalResp1",
                    'type': 'hotp',
                    'otpkey': self.otpkey,
                    'pin': "1234"},
                   user=User("cornelius", self.realm1))
        set_policy(name="add_user_detail", scope=SCOPE.AUTHZ, action=PolicyAction.ADDUSERINRESPONSE)
        # First check with pi only fails without challenge-response policy
        with self.app.test_request_context('/validate/samlcheck',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(result["authentication"], AUTH_RESPONSE.REJECT, result)
            detail = res.json.get("detail")
            # Check that there is no user information in the details
            self.assertEqual(detail["message"], "wrong otp pin", detail)
            self.assertNotIn("user", detail, detail)

        # Add the challenge response policy and try again
        set_policy(name="hotp_chal_resp", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")
        with self.app.test_request_context('/validate/samlcheck',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(result["authentication"], AUTH_RESPONSE.CHALLENGE, result)
            detail = res.json.get("detail")
            # Check that there is no user information in the details
            self.assertIn("multi_challenge", detail, detail)
            self.assertNotIn("user", detail, detail)
            transaction_id = detail["transaction_id"]

        # Finish challenge
        with self.app.test_request_context('/validate/samlcheck',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": OTPs[0],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(result["authentication"], AUTH_RESPONSE.ACCEPT, result)
            detail = res.json.get("detail")
            # Check that there is no user information in the details
            self.assertIn("user", detail, detail)
            self.assertEqual(detail["serial"], "ChalResp1", detail)
            self.assertEqual(detail["user"]["username"], "cornelius", detail)

        delete_policy("add_user_detail")
        delete_policy("hotp_chal_resp")
        remove_token(serial="ChalResp1")

    def test_11_challenge_response_hotp(self):
        """
        Verify that HOTP token work with the challenge_response policy. Also verify that the challenge_text policy is
        applied correctly.
        """
        set_privacyidea_config(SYSCONF.INCFAILCOUNTER, False)
        serial = "CHALRESP1"
        pin = "chalresp1"
        # create a token and assign to the user
        db_token = Token(serial, tokentype="hotp")
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        token = HotpTokenClass(db_token)
        token.add_user(User("cornelius", self.realm1))
        token.set_pin(pin)
        token.set_failcount(5)
        db_token.save()

        # try to do challenge response without a policy.
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), _("wrong otp pin"))
            self.assertNotIn("transaction_id", detail)
            self.assertEqual(5, token.get_failcount())

        # Policy to enable challenge-response and the text
        challenge_text = "custom challenge text"
        set_policy("challengetext", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGETEXT}={challenge_text}")
        set_policy("challenge_response_hotp", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")

        # Create the challenge by authenticating with the OTP PIN. The failcounter will not increase.
        # The challenge message will be taken from the policy action value
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual("CHALLENGE", result.get("authentication"))
            self.assertEqual(challenge_text, detail.get("message"))
            transaction_id = detail.get("transaction_id")
            self.assertEqual(5, token.get_failcount())

        # OTP value will be accepted and reset the failcounter
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": "359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))
            self.assertEqual("ACCEPT", result.get("authentication"))

        self.assertEqual(token.get_failcount(), 0)
        # delete the token and policies
        remove_token(serial=serial)
        delete_policy("challengetext")
        delete_policy("challenge_response_hotp")
        set_privacyidea_config(SYSCONF.INCFAILCOUNTER, True)

    def test_11a_challenge_response_registration(self):
        serial = "CHALRESP1"
        pin = "chalresp1"
        # create a token and assign to the user
        db_token = Token(serial, tokentype="registration", otpkey="regcode")
        db_token.save()
        token = RegistrationTokenClass(db_token)
        token.add_user(User("cornelius", self.realm1))
        token.set_pin(pin)

        # try to do challenge response without a policy. It will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), _("wrong otp pin"))
            self.assertNotIn("transaction_id", detail)

        # set a chalresp policy for Registration Token
        with self.app.test_request_context('/policy/pol_chal_resp',
                                           data={'action': "challenge_response=registration",
                                                 'scope': "authentication",
                                                 'realm': '',
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertGreaterEqual(result['value']['setPolicy pol_chal_resp'], 1, result)

        # create the challenge by authenticating with the OTP PIN
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), _("please enter otp: "))
            transaction_id = detail.get("transaction_id")

        # use the regcode to authenticate
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id,
                                                 "pass": "regcode"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # check, that the tokenowner table does not contain a NULL entry
        r = db.session.query(TokenOwner).filter(TokenOwner.token_id == None).first()
        self.assertIsNone(r)

        # delete the policy
        delete_policy("pol_chal_resp")

    def test_11b_challenge_response_multiple_hotp_failcounters(self):
        # Check behavior of Challenge-Response with multiple tokens
        # set a chalresp policy for HOTP
        with self.app.test_request_context('/policy/pol_chal_resp',
                                           data={'action': "challenge_response=hotp",
                                                 'scope': "authentication",
                                                 'realm': '',
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertGreaterEqual(result['value']['setPolicy pol_chal_resp'], 1, result)

        chalresp_serials = ["CHALRESP1", "CHALRESP2"]
        chalresp_pins = ["chalresp1", "chalresp2"]
        tokens = []

        # create two C/R tokens with different PINs for the same user
        for serial, pin in zip(chalresp_serials, chalresp_pins):
            # create a token and assign to the user
            db_token = Token(serial, tokentype="hotp")
            db_token.update_otpkey(self.otpkey)
            db_token.save()
            token = HotpTokenClass(db_token)
            token.add_user(User("cornelius", self.realm1))
            token.set_pin(pin)
            # Set the failcounter
            token.set_failcount(5)
            token.save()
            tokens.append(token)

        # create a challenge for the first token by authenticating with the OTP PIN
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": chalresp_pins[0]}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), _("please enter otp: "))
            transaction_id = detail.get("transaction_id")

        # Failcounters are unchanged
        self.assertEqual(tokens[0].get_failcount(), 5)
        self.assertEqual(tokens[1].get_failcount(), 5)

        # send an incorrect OTP value
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": "111111"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))

        # Failcounter for the first token is increased
        # Failcounter for the second token is unchanged
        self.assertEqual(tokens[0].get_failcount(), 6)
        self.assertEqual(tokens[1].get_failcount(), 5)

        # send the correct OTP value
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": "359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertTrue(result.get("value"))

        # Failcounter for the first token is reset
        # Failcounter for the second token is unchanged
        self.assertEqual(tokens[0].get_failcount(), 0)
        self.assertEqual(tokens[1].get_failcount(), 5)

        # Set the same failcount for both tokens
        tokens[0].set_failcount(5)
        tokens[0].save()

        # trigger a challenge for both tokens
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": "cornelius"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")

        # send an incorrect OTP value
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id,
                                                 "pass": "111111"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))

        # Failcounter for both tokens are increased
        self.assertEqual(tokens[0].get_failcount(), 6)
        self.assertEqual(tokens[1].get_failcount(), 6)

        # delete the tokens
        for serial in chalresp_serials:
            remove_token(serial=serial)

    def test_11c_challenge_response_timezone(self):
        # Since we write the challenge timestamps in UTC there is no easy way
        # to test servers in different timezones with mocking.
        # We would need to verify some timestamp the server emits in local time.
        self.setUp_user_realms()
        serial = "CHALRESP1"
        pin = "chalresp1"
        # create a token and assign to the user
        init_token({'serial': serial,
                    'type': 'hotp',
                    'otpkey': self.otpkey,
                    'pin': pin},
                   user=User("cornelius", self.realm1))

        # set a chalresp policy for HOTP
        pol = Policy('pol_chal_resp_tz', action='challenge_response=hotp',
                     scope='authentication', realm='', active=True)
        pol.save()

        # create the challenge by authenticating with the OTP PIN
        with Replace('privacyidea.models.utils.datetime',
                     test_datetime(2020, 6, 13, 1, 2, 3,
                                   tzinfo=datetime.timezone(datetime.timedelta(hours=+5)))):
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "pass": pin}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                detail = res.json.get("detail")
                self.assertFalse(result.get("value"))
                self.assertEqual(detail.get("message"), _("please enter otp: "))
                transaction_id = detail.get("transaction_id")

        # send the OTP value while being an hour too early (timezone +1)
        # This should not happen unless there is a server misconfiguration
        # The transaction should not be removed by the janitor
        with Replace('privacyidea.models.challenge.datetime',
                     test_datetime(2020, 6, 13, 1, 2, 4,
                                   tzinfo=datetime.timezone(datetime.timedelta(hours=+6)))):
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "transaction_id": transaction_id,
                                                     "pass": "755224"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertFalse(result.get("value"))

        # send the OTP value while being an hour too late (timezone -1)
        with Replace('privacyidea.models.challenge.datetime',
                     test_datetime(2020, 6, 13, 1, 2, 4,
                                   tzinfo=datetime.timezone(datetime.timedelta(hours=+1)))):
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "transaction_id": transaction_id,
                                                     "pass": "755224"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertFalse(result.get("value"))

        # check that the challenge is removed
        self.assertFalse(get_challenges(transaction_id=transaction_id))

        # delete the token
        remove_token(serial=serial)
        pol.delete()

    def test_12_challenge_response_sms(self):
        unassign_token(self.serials[0])
        # set a chalresp policy for SMS
        with self.app.test_request_context('/policy/pol_chal_resp',
                                           data={'action': "challenge_response=sms",
                                                 'scope': "authentication",
                                                 'realm': '',
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertGreaterEqual(result['value']['setPolicy pol_chal_resp'], 1, result)

        serial = "CHALRESP2"
        pin = "chalresp2"
        # create a token and assign to the user
        init_token({"serial": serial,
                    "type": "sms",
                    "otpkey": self.otpkey,
                    "phone": "123456",
                    "pin": pin}, user=User("cornelius", self.realm1))
        # create the challenge by authenticating with the OTP PIN
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertIn("The PIN was correct, but the SMS could not be sent", detail.get("message"),
                          detail.get("message"))

        # disable the token. The detail->message should be empty
        r = enable_token(serial=serial, enable=False)
        self.assertEqual(r, True)
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual("Token is disabled", detail.get("message"))

        # delete the token
        remove_token(serial=serial)

    @smtpmock.activate
    def test_13_challenge_response_email(self):
        smtpmock.setdata(response={"hans@dampf.com": (200, 'OK')})
        # set a chalresp policy for Email
        with self.app.test_request_context('/policy/pol_chal_resp',
                                           data={'action': "challenge_response=email",
                                                 'scope': "authentication",
                                                 'realm': '',
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertGreaterEqual(result['value']['setPolicy pol_chal_resp'], 1, result)

        serial = "CHALRESP3"
        pin = "chalresp3"
        # create a token and assign to the user
        init_token({"serial": serial,
                    "type": "email",
                    "otpkey": self.otpkey,
                    "email": "hans@dampf.com",
                    "pin": pin}, user=User("cornelius", self.realm1))
        # create the challenge by authenticating with the OTP PIN
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), _("Enter the OTP from the Email"))
            transaction_id = detail.get("transaction_id")

        # send the OTP value
        # Test with parameter state.
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "state": transaction_id,
                                                 "pass": "359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # delete the token
        remove_token(serial=serial)

    def test_14_check_validity_period(self):
        serial = "VP001"
        password = serial
        init_token({"serial": serial,
                    "type": "spass",
                    "pin": password}, user=User("cornelius", self.realm1))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": password}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # Set validity period
        token_obj = get_tokens(serial=serial)[0]
        token_obj.set_validity_period_end("2015-01-01T10:00+0200")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": password}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertFalse(result.get("value"))
            details = res.json.get("detail")
            self.assertTrue("Outside validity period" in details.get("message"))

        token_obj.set_validity_period_end("1999-01-01T10:00+0200")
        token_obj.set_validity_period_start("1998-01-01T10:00+0200")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": password}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertFalse(result.get("value"))
            details = res.json.get("detail")
            self.assertTrue("Outside validity period" in details.get("message"))

        # delete the token
        remove_token(serial="VP001")

    def test_15_validate_at_sign(self):
        serial1 = "Split001"
        serial2 = "Split002"
        init_token({"serial": serial1,
                    "type": "spass",
                    "pin": serial1}, user=User("cornelius", self.realm1))

        init_token({"serial": serial2,
                    "type": "spass",
                    "pin": serial2}, user=User("cornelius", self.realm2))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": serial1}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        set_privacyidea_config("splitAtSign", "0")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius@" + self.realm2,
                                                 "pass": serial2}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        set_privacyidea_config("splitAtSign", "1")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius@" + self.realm2,
                                                 "pass": serial2}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # Also test url-encoded parameters
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius%40" + self.realm2,
                                                 "pass": serial2}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # The default behaviour - if the config entry does not exist,
        # is to split the @Sign
        delete_privacyidea_config("splitAtSign")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius@" + self.realm2,
                                                 "pass": serial2}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

    def test_16_autoresync_hotp(self):
        serial = "autosync1"
        token = init_token({"serial": serial,
                            "otpkey": self.otpkey,
                            "pin": "async"}, User("cornelius", self.realm2))
        set_privacyidea_config("AutoResync", True)
        token.set_sync_window(10)
        token.set_count_window(5)
        # counter = 8, is out of sync
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius@" + self.realm2,
                                                 "pass": "async399871"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), False)

        # counter = 9, will be autosynced.
        # Authentication is successful
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius@" + self.realm2,
                                                 "pass": "async520489"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        delete_privacyidea_config("AutoResync")
        remove_token(serial)

    def test_16_autoresync_hotp_via_multichallenge(self):
        serial = "autosync1"
        token = init_token({"serial": serial,
                            "otpkey": self.otpkey,
                            "pin": "async"}, User("cornelius", self.realm2))
        set_privacyidea_config("AutoResync", True)
        set_policy(name="mcr_resync", scope=SCOPE.AUTH, action=PolicyAction.RESYNC_VIA_MULTICHALLENGE)
        token.set_sync_window(10)
        token.set_count_window(5)
        # counter = 8, is out of sync
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius@" + self.realm2,
                                                 "pass": "async399871"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(detail.get('multi_challenge')[0].get("message"),
                             'To resync your token, please enter the next OTP value')
            self.assertEqual(result.get("value"), False)
            transaction_id = res.json.get("detail").get("transaction_id")
            self.assertTrue(transaction_id)

        # A false response will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius@" + self.realm2,
                                                 "transaction_id": transaction_id,
                                                 "pass": "520111"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertFalse(result.get("value"))

        # counter = 9, will be autosynced.
        # Authentication is successful
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius@" + self.realm2,
                                                 "transaction_id": transaction_id,
                                                 "pass": "520489"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        delete_privacyidea_config("AutoResync")
        remove_token(serial)
        delete_policy("mcr_resync")

    def test_17_auth_timelimit_success(self):
        user = User("timelimituser", realm=self.realm2)
        pin = "spass"
        # create a token
        token = init_token({"type": "spass",
                            "pin": pin}, user=user)

        # set policy for timelimit
        set_policy(name="pol_time1",
                   scope=SCOPE.AUTHZ,
                   action="{0!s}=2/20s".format(PolicyAction.AUTHMAXSUCCESS))

        for i in [1, 2]:
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "timelimituser",
                                                     "realm": self.realm2,
                                                     "pass": pin}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertEqual(result.get("value"), True)

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "timelimituser",
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), False)

        delete_policy("pol_time1")
        remove_token(token.token.serial)

    def test_18_auth_timelimit_fail(self):
        user = User("timelimituser", realm=self.realm2)
        pin = "spass"
        # create a token
        token = init_token({"type": "spass", "pin": pin}, user=user)

        # set policy for timelimit
        set_policy(name="pol_time1",
                   scope=SCOPE.AUTHZ,
                   action="{0!s}=2/20s".format(PolicyAction.AUTHMAXFAIL))

        for i in [1, 2]:
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "timelimituser",
                                                     "realm": self.realm2,
                                                     "pass": "wrongpin"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertEqual(result.get("value"), False)

        # Now we do the correct authentication, but
        # as already two authentications failed, this will fail, too
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "timelimituser",
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), False)
            details = res.json.get("detail")
            self.assertEqual(details.get("message"),
                             "Only 2 failed authentications per 0:00:20 allowed.")

        delete_policy("pol_time1")
        remove_token(token.token.serial)

    def test_19_validate_passthru(self):
        # user passthru, realm: self.realm2, passwd: pthru
        set_policy(name="pthru", scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU)

        # Passthru with GET request
        with self.app.test_request_context(
                '/validate/check',
                method='GET',
                query_string={"user": "passthru",
                              "realm": self.realm2,
                              "pass": "pthru"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        # Passthru with POST Request
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "passthru",
                                                 "realm": self.realm2,
                                                 "pass": "pthru"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        # Test if the policies "reset_all_tokens" and "passthru" work out fine at the same time
        set_policy(name="reset_all_tokens", scope=SCOPE.AUTH, action=PolicyAction.RESETALLTOKENS)
        # Passthru with POST Request
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "passthru",
                                                 "realm": self.realm2,
                                                 "pass": "pthru"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        delete_policy("reset_all_tokens")
        delete_policy("pthru")

    def test_20_questionnaire(self):
        pin = "pin"
        serial = "QUST1234"
        questions = {"frage1": "antwort1",
                     "frage2": "antwort2",
                     "frage3": "antwort3"}
        j_questions = json.dumps(questions)

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "question",
                                                 "pin": pin,
                                                 "serial": serial,
                                                 "questions": j_questions},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        set_privacyidea_config("question.num_answers", 2)
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "question",
                                                 "pin": pin,
                                                 "serial": serial,
                                                 "questions": j_questions},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertEqual(value, True)

        # Start a challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": serial,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            question = detail.get("message")
            self.assertTrue(question in questions)

        # Respond to the challenge
        answer = questions[question]
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": serial,
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": answer}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

    def test_21_validate_disabled(self):
        # test a user with two tokens and otppin=userstore.
        # One token is disabled. But the user must be able to login with the
        # 2nd token
        # user disableduser, realm: self.realm2, passwd: superSecret
        set_policy(name="disabled",
                   scope=SCOPE.AUTH,
                   action="{0!s}={1!s}".format(PolicyAction.OTPPIN, "userstore"))
        # enroll two tokens
        r = init_token({"type": "spass", "serial": "spass1d"},
                       user=User("disableduser", self.realm2))
        r = init_token({"type": "spass", "serial": "spass2d"},
                       user=User("disableduser", self.realm2))
        # disable first token
        r = enable_token("spass1d", False)
        self.assertEqual(r, True)
        # Check that the user still can authenticate with the 2nd token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "disableduser",
                                                 "realm": self.realm2,
                                                 "pass": "superSecret"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        # disable 2nd token
        r = enable_token("spass2d", False)
        r = enable_token("spass1d")
        self.assertEqual(r, True)
        # Check that the user still can authenticate with the first token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "disableduser",
                                                 "realm": self.realm2,
                                                 "pass": "superSecret"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        delete_policy("disabled")

    def test_22_validate_locked(self):
        # test a user with two tokens
        # One token is locked/revoked.
        #  But the user must be able to login with the 2nd token
        # user lockeduser, realm: self.realm2
        # enroll two tokens
        user = "lockeduser"
        set_policy(name="locked",
                   scope=SCOPE.AUTH,
                   action="{0!s}={1!s}".format(PolicyAction.OTPPIN, "tokenpin"))
        r = init_token({"type": "spass", "serial": "spass1l",
                        "pin": "locked"},
                       user=User(user, self.realm2))
        r = init_token({"type": "spass", "serial": "spass2l",
                        "pin": "locked"},
                       user=User(user, self.realm2))
        # disable first token
        r = revoke_token("spass1l")
        self.assertEqual(r, True)
        # Check that the user still can authenticate with the 2nd token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user,
                                                 "realm": self.realm2,
                                                 "pass": "locked"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        remove_token("spass1l")
        remove_token("spass2l")
        delete_policy("locked")

    def test_23_pass_no_user_and_pass_no_token(self):
        # Test with pass_no_user AND with pass_no_token.
        user = "passthru"
        user_no_token = "usernotoken"
        pin = "mypin"
        serial = "t23"
        set_policy(name="pass_no",
                   scope=SCOPE.AUTH,
                   action="{0!s},{1!s}".format(PolicyAction.PASSONNOTOKEN,
                                               PolicyAction.PASSONNOUSER))

        r = init_token({"type": "spass", "serial": serial,
                        "pin": pin}, user=User(user, self.realm2))
        self.assertTrue(r)

        r = get_tokens(user=User(user, self.realm2), count=True)
        self.assertEqual(r, 1)
        # User can authenticate with his SPASS token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user,
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("serial"), serial)

        # User that does not exist, can authenticate
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "doesNotExist",
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("message"),
                             "user does not exist, accepted "
                             "due to 'pass_no'")

        # Creating a notification event. The non-existing user must
        # still be able to pass!
        eid = set_event("notify", event=["validate_check"], action="sendmail",
                        handlermodule="UserNotification", conditions={"token_locked": True})

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "doesNotExist",
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("message"),
                             "user does not exist, accepted "
                             "due to 'pass_no'")

        delete_event(eid)

        r = get_tokens(user=User(user, self.realm2), count=True)
        self.assertEqual(r, 1)
        # User with no token can authenticate
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user_no_token,
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("message"),
                             "user has no token, "
                             "accepted due to 'pass_no'")

        r = get_tokens(user=User(user, self.realm2), count=True)
        self.assertEqual(r, 1)

        # user with wrong password fails to authenticate
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user,
                                                 "realm": self.realm2,
                                                 "pass": "wrongPiN"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), False)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("message"),
                             "wrong otp pin")

        delete_policy("pass_no")
        remove_token(serial)

        # User that does not exist, can NOT authenticate after removing the
        # policy
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "doesNotExist",
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            detail = res.json.get("detail")
            self.assertEqual(detail, None)

    def test_23a_pass_no_user_resolver(self):
        # Now we set a policy, that a non existing user will authenticate
        set_policy(name="pol1",
                   scope=SCOPE.AUTH,
                   action="{0}, {1}, {2}, {3}=none".format(
                       PolicyAction.RESETALLTOKENS,
                       PolicyAction.PASSONNOUSER,
                       PolicyAction.PASSONNOTOKEN,
                       PolicyAction.OTPPIN
                   ),
                   realm=self.realm1)
        # Check that the non existing user MisterX is allowed to authenticate
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "MisterX",
                                                 "realm": self.realm1,
                                                 "pass": "secret"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("message"),
                             'user does not exist, accepted due to \'pol1\'')
        delete_policy("pol1")

    @responses.activate
    def test_24_trigger_challenge(self):
        setup_sms_gateway()

        self.setUp_user_realms()
        self.setUp_user_realm2()
        serial = "sms01"
        pin = "pin"
        user = "passthru"
        r = init_token({"type": "sms", "serial": serial,
                        "otpkey": self.otpkey,
                        "phone": "123456",
                        "pin": pin}, user=User(user, self.realm2))
        self.assertTrue(r)

        # Trigger challenge for serial number
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"serial": serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), 1)
            self.assertEqual(result.get("authentication"), AUTH_RESPONSE.CHALLENGE)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("messages")[0],
                             _("Enter the OTP from the SMS:"))
            transaction_id = detail.get("transaction_ids")[0]
            # check if serial has been added to g
            self.assertTrue(self.app_context.g.serial, detail["serial"])

        # Check authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user,
                                                 "realm": self.realm2,
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": "287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        # Trigger challenge for user
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": user,
                                                 "realm": self.realm2},
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), 1)
            self.assertEqual(result.get("authentication"), AUTH_RESPONSE.CHALLENGE)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("messages")[0],
                             _("Enter the OTP from the SMS:"))
            transaction_id = detail.get("transaction_ids")[0]
            # check if serial has been added to g
            self.assertTrue(self.app_context.g.serial, detail["serial"])

        # Check authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user,
                                                 "realm": self.realm2,
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": "969429"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        remove_token(serial)

    @smtpmock.activate
    def test_25_trigger_challenge_smtp(self):
        smtpmock.setdata(response={"hans@dampf.com": (200, 'OK')})
        from privacyidea.lib.tokens.emailtoken import EMAILACTION

        self.setUp_user_realms()
        self.setUp_user_realm2()
        serial = "smtp01"
        pin = "pin"
        user = "passthru"
        r = init_token({"type": "email", "serial": serial,
                        "otpkey": self.otpkey,
                        "email": "hans@dampf.com",
                        "pin": pin}, user=User(user, self.realm2))
        self.assertTrue(r)

        set_policy("emailtext", scope=SCOPE.AUTH,
                   action="{0!s}=Dein <otp>".format(EMAILACTION.EMAILTEXT))
        set_policy("emailsubject", scope=SCOPE.AUTH,
                   action="{0!s}=Dein OTP".format(EMAILACTION.EMAILSUBJECT))

        # Trigger challenge for serial number
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"serial": serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), 1)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("messages")[0], _("Enter the OTP from the Email"))
            # check the send message
            sent_message = smtpmock.get_sent_message().decode('utf-8')
            self.assertTrue("RGVpbiAyODcwODI=" in sent_message)
            self.assertTrue("Subject: Dein OTP" in sent_message)

        remove_token(serial)
        delete_policy("emailtext")

    def test_26_multiple_challenge_response(self):
        # Test the challenges for multiple active tokens
        self.setUp_user_realms()
        OTPKE2 = "31323334353637383930313233343536373839AA"
        user = User("multichal", self.realm1)
        pin = "test49"
        init_token({"serial": "CR2A",
                    "type": "hotp",
                    "otpkey": OTPKE2,
                    "pin": pin}, user)
        init_token({"serial": "CR2B",
                    "type": "hotp",
                    "otpkey": self.otpkey,
                    "pin": pin}, user)
        set_policy("test49", scope=SCOPE.AUTH, action="{0!s}=hotp".format(
            PolicyAction.CHALLENGERESPONSE))
        # both tokens will be a valid challenge response token!

        transaction_id = None
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "multichal",
                                                 "realm": self.realm1,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), False)
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            multi_challenge = detail.get("multi_challenge")
            self.assertEqual(multi_challenge[0].get("serial"), "CR2A")
            self.assertEqual(transaction_id,
                             multi_challenge[0].get("transaction_id"))
            self.assertEqual("interactive", multi_challenge[0].get("client_mode"))
            self.assertEqual(transaction_id,
                             multi_challenge[1].get("transaction_id"))
            self.assertEqual(multi_challenge[1].get("serial"), "CR2B")
            self.assertEqual("interactive", multi_challenge[1].get("client_mode"))

        # There are two challenges in the database
        r = Challenge.query.filter(Challenge.transaction_id ==
                                   transaction_id).all()
        self.assertEqual(len(r), 2)

        # check that both serials appear in the audit log
        ae = self.find_most_recent_audit_entry(action='* /validate/check')
        self.assertEqual({"CR2A", "CR2B"}, set(ae.get('serial').split(',')), ae)

        # Check the second response to the challenge, the second step in
        # challenge response:

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "multichal",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "realm": self.realm1,
                                                 "pass": "287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            serial = detail.get("serial")
            self.assertEqual(serial, "CR2B")

        # No challenges in the database
        r = Challenge.query.filter(Challenge.transaction_id ==
                                   transaction_id).all()
        self.assertEqual(len(r), 0)

        remove_token("CR2A")
        remove_token("CR2B")
        delete_policy("test49")

    def test_27_multiple_challenge_response_different_pin(self):
        # Test the challenges for multiple active tokens with different PINs
        # Test issue #649
        self.setUp_user_realms()
        OTPKE2 = "31323334353637383930313233343536373839AA"
        user = User("multichal", self.realm1)
        pinA = "testA"
        pinB = "testB"
        init_token({"serial": "CR2A",
                    "type": "hotp",
                    "otpkey": OTPKE2,
                    "pin": pinA}, user)
        init_token({"serial": "CR2B",
                    "type": "hotp",
                    "otpkey": self.otpkey,
                    "pin": pinB}, user)
        set_policy("test48", scope=SCOPE.AUTH, action="{0!s}=hotp".format(
            PolicyAction.CHALLENGERESPONSE))
        # both tokens will be a valid challenge response token!

        transaction_id = None
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "multichal",
                                                 "realm": self.realm1,
                                                 "pass": pinB}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), False)
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            multi_challenge = detail.get("multi_challenge")
            self.assertEqual(multi_challenge[0].get("serial"), "CR2B")
            self.assertEqual(transaction_id,
                             multi_challenge[0].get("transaction_id"))
            self.assertEqual(len(multi_challenge), 1)

        # There is ONE challenge in the database
        r = Challenge.query.filter(Challenge.transaction_id ==
                                   transaction_id).all()
        self.assertEqual(len(r), 1)

        # Check the second response to the challenge, the second step in
        # challenge response:

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "multichal",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "realm": self.realm1,
                                                 "pass": "287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            serial = detail.get("serial")
            self.assertEqual(serial, "CR2B")

        # No challenges in the database
        r = Challenge.query.filter(Challenge.transaction_id ==
                                   transaction_id).all()
        self.assertEqual(len(r), 0)

        remove_token("CR2A")
        remove_token("CR2B")
        delete_policy("test48")

    def test_28_validate_radiuscheck(self):
        # setup a spass token
        init_token({"serial": "pass3", "pin": "123456", "type": "spass"})

        # test successful authentication
        with self.app.test_request_context('/validate/radiuscheck',
                                           method='POST',
                                           data={"serial": "pass3",
                                                 "pass": "123456"}):
            res = self.app.full_dispatch_request()
            # HTTP 204 status code signals a successful authentication
            self.assertEqual(res.status_code, 204)
            self.assertEqual(res.data, b'')

        # test authentication fails with wrong PIN
        with self.app.test_request_context('/validate/radiuscheck',
                                           method='POST',
                                           data={"serial": "pass3",
                                                 "pass": "wrong"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)
            self.assertEqual(res.data, b'')

        # test authentication fails with an unknown user
        # here, we get an ordinary JSON response
        with self.app.test_request_context('/validate/radiuscheck',
                                           method='POST',
                                           data={"user": "unknown",
                                                 "pass": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)
            result = res.json.get("result")
            self.assertFalse(result.get("status"))
        # Check that we have a failed attempt with the username in the audit
        ae = self.find_most_recent_audit_entry(action='* /validate/radiuscheck')
        self.assertEqual(0, ae.get("success"), ae)
        self.assertEqual("unknown", ae.get("user"), ae)

    def test_29_several_CR_one_locked(self):
        # A user has several CR tokens. One of the tokens is locked.
        self.setUp_user_realms()
        user = User("multichal", self.realm1)
        pin = "test"
        init_token({"serial": "CR2A",
                    "type": "hotp",
                    "otpkey": self.otpkey,
                    "pin": pin}, user)
        init_token({"serial": "CR2B",
                    "type": "hotp",
                    "otpkey": self.otpkey,
                    "pin": pin}, user)
        set_policy("test48", scope=SCOPE.AUTH, action="{0!s}=hotp".format(
            PolicyAction.CHALLENGERESPONSE))
        # both tokens will be a valid challenge response token!

        # One token is locked
        revoke_token("CR2B")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "multichal",
                                                 "realm": self.realm1,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            # This is a challene, the value is False
            self.assertEqual(result.get("value"), False)
            detail = res.json.get("detail")
            serial = detail.get("serial")
            self.assertEqual(serial, "CR2A")
            # Only one challenge, the 2nd token was revoked.
            self.assertEqual(len(detail.get("multi_challenge")), 1)

        delete_policy("test48")
        remove_token("CR2A")
        remove_token("CR2B")

    def test_30_return_different_tokentypes(self):
        """
        Return different tokentypes

        If there are more than one matching tokens, the check_token_list in lib/token.py
        returns a tokentype:
        1. a specific tokentype if all matching tokens are of the same type
        2. an "undetermined" tokentype, if the matching tokens are of
           different type.
        """
        self.setUp_user_realms()
        user = User("cornelius", self.realm1)

        # Authenticate with PW token
        init_token({"serial": "PW1",
                    "type": "pw",
                    "otpkey": "123",
                    "pin": "hallo"}, user)
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "hallo123"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("type"), "pw")
            # check if serial has been added to g
            self.assertEqual(self.app_context.g.serial, 'PW1')

        # two different token types result in "undetermined
        init_token({"serial": "SPASS1",
                    "type": "spass",
                    "pin": "hallo123"}, user)

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "hallo123"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("type"), "undetermined")
            # check if serial has been added to g
            self.assertTrue(self.app_context.g.serial is None)

        # Remove PW token, and authenticate with spass
        remove_token("PW1")
        init_token({"serial": "SPASS2",
                    "type": "spass",
                    "pin": "hallo123"}, user)

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "hallo123"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("type"), "spass")

        # A user has one HOTP token and two spass tokens.
        init_token({"serial": "HOTP1",
                    "type": "hotp",
                    "otpkey": self.otpkey,
                    "pin": "hallo"}, user)
        # Without policy he can authenticate with the spass token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "hallo123"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("type"), "spass")

        # policy only allows HOTP.
        set_policy("onlyHOTP", scope=SCOPE.AUTHZ,
                   action="{0!s}=hotp".format(PolicyAction.TOKENTYPE))

        # He can not authenticate with the spass token!
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "hallo123"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json.get("result")
            self.assertEqual(result.get("status"), False)
            self.assertEqual(result.get("error").get("code"), Error.POLICY)
            detail = res.json.get("detail")
            self.assertEqual(detail, None)

        # Define a passthru policy
        set_policy("passthru", scope=SCOPE.AUTH,
                   action="{0!s}=userstore".format(PolicyAction.PASSTHRU))

        # A user with a passthru policy can authenticate, since he has not tokentype
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "passthru",
                                                 "pass": "pthru"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), True)

        delete_policy("onlyHOTP")
        delete_policy("passthru")
        remove_token("SPASS1")
        remove_token("SPASS2")
        remove_token("HOTP1")

    @responses.activate
    @smtpmock.activate
    def test_30_challenge_text(self):
        """
        Set a policy for a different challengetext and run a C/R for sms and email.
        :return:
        """
        smtpmock.setdata(response={"hallo@example.com": (200, 'OK')})

        # Configure the SMS Gateway
        setup_sms_gateway()

        self.setUp_user_realms()
        user = User("cornelius", self.realm1)

        # two different token types
        init_token({"serial": "CHAL1",
                    "type": "sms",
                    "phone": "123456",
                    "pin": "sms"}, user)
        init_token({"serial": "CHAL2",
                    "type": "email",
                    "email": "hallo@example.com",
                    "pin": "email"}, user)

        set_policy("chalsms", SCOPE.AUTH, "sms_{0!s}=check your sms".format(PolicyAction.CHALLENGETEXT))
        set_policy("chalemail", SCOPE.AUTH, "email_{0!s}=check your email".format(PolicyAction.CHALLENGETEXT))

        # Challenge Response with email
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "email"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            resp = res.json
            self.assertEqual(resp.get("detail").get("message"), "check your email")

        # Challenge Response with SMS
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "sms"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            resp = res.json
            self.assertEqual(resp.get("detail").get("message"), "check your sms")

        # Two different token types that are triggered by the same PIN:
        init_token({"serial": "CHAL3",
                    "type": "sms",
                    "phone": "123456",
                    "pin": "PIN"}, user)
        init_token({"serial": "CHAL4",
                    "type": "email",
                    "email": "hallo@example.com",
                    "pin": "PIN"}, user)

        # Challenge Response with SMS and Email. The challenge message contains both hints
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "PIN"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            resp = res.json
            self.assertIn("check your sms", resp.get("detail").get("message"))
            self.assertIn("check your email", resp.get("detail").get("message"))

        delete_policy("chalsms")
        delete_policy("chalemail")

        # Challenge_text with tags
        set_policy("chalsms", SCOPE.AUTH, "sms_challenge_text=Hello {user}\, please enter "
                                          "the otp sent to {phone},  increase_failcounter_on_challenge")
        set_policy("chalemail", SCOPE.AUTH, "email_challenge_text=Hello {user}\, please enter "
                                            "the otp sent to {email},  increase_failcounter_on_challenge")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "PIN"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            resp = res.json
            self.assertIn("Hello Cornelius, please enter the otp sent to 123456",
                          resp.get("detail").get("message"))
            self.assertIn("Hello Cornelius, please enter the otp sent to hallo@example.com",
                          resp.get("detail").get("message"))

        with self.app.test_request_context('/policy/chalsms',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'], res.json)
            value = res.json['result']['value']
            sms_policy = value[0]
            self.assertEqual(sms_policy.get("action").get("increase_failcounter_on_challenge"), True, sms_policy)
            self.assertIn("Hello {user}\\, please enter", sms_policy.get("action").get("sms_challenge_text"),
                          sms_policy)

        remove_token("CHAL1")
        remove_token("CHAL2")
        remove_token("CHAL4")
        delete_policy("chalsms")
        delete_policy("chalemail")

        # unknown tag
        set_policy("chalsms", SCOPE.AUTH, "sms_challenge_text=This {tag} should disappear")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "PIN"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            resp = res.json
            self.assertIn("This  should disappear",
                          resp.get("detail").get("message"))

        remove_token("CHAL3")
        delete_policy("chalsms")

    def test_01_check_invalid_input(self):
        # Empty username
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": " ",
                                                 "pass": ""}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            error_msg = result.get("error").get("message")
            self.assertEqual("ERR905: You need to specify a serial, user or credential_id.", error_msg)

        # wrong username
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "h%h",
                                                 "pass": ""}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            error_msg = result.get("error").get("message")
            self.assertEqual("ERR905: Invalid user.", error_msg)

        # wrong serial
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "*",
                                                 "pass": ""}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            error_msg = result.get("error").get("message")
            self.assertEqual("ERR905: Invalid serial number.", error_msg)

    def test_31_count_auth(self):

        serial = "authcount001"
        tok = init_token({"serial": serial,
                          "type": "spass",
                          "pin": "spass"})
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": serial,
                                                 "pass": "spass"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        self.assertEqual(int(tok.get_tokeninfo("count_auth")), 1)

        set_privacyidea_config("no_auth_counter", "True")
        # Now an authentication does not increase the counter!
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": serial,
                                                 "pass": "spass"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        self.assertEqual(int(tok.get_tokeninfo("count_auth")), 1)
        remove_token(serial)
        delete_privacyidea_config("no_auth_counter")

    @ldap3mock.activate
    def test_32_secondary_login_attribute(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        # First we create an LDAP resolver
        rid = save_resolver({"resolver": "myLDAPres",
                             "type": "ldapresolver",
                             'LDAPURI': 'ldap://localhost',
                             'LDAPBASE': 'o=test',
                             'BINDDN': 'cn=manager,ou=example,o=test',
                             'BINDPW': 'ldaptest',
                             'LOGINNAMEATTRIBUTE': 'cn, sn',
                             'LDAPSEARCHFILTER': '(cn=*)',
                             'USERINFO': '{ "username": "cn",'
                                         '"phone" : "telephoneNumber", '
                                         '"mobile" : "mobile"'
                                         ', "email" : "mail", '
                                         '"surname" : "sn", '
                                         '"givenname" : "givenName" }',
                             'UIDTYPE': 'DN',
                             'CACHE_TIMEOUT': 0
                             })
        self.assertTrue(rid)
        added, failed = set_realm("tr", [{'name': "myLDAPres"}])
        self.assertEqual(added, ["myLDAPres"])
        self.assertEqual(failed, [])

        params = {"type": "spass",
                  "pin": "spass"}
        token = init_token(params, User("alice", "tr"))

        # Alice Cooper is in the LDAP directory, but Cooper is the secondary login name
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "Cooper",
                                                 "realm": "tr",
                                                 "pass": "spass"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # Now check the audit!
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={"action": "*check*", "user": "alice"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get("count"), 1)
            self.assertTrue(
                "logged in as Cooper." in json_response.get("result").get("value").get("auditdata")[0].get("info"),
                json_response.get("result").get("value").get("auditdata"))

        token.delete_token()
        self.assertTrue(delete_realm("tr"))
        self.assertTrue(delete_resolver("myLDAPres"))

    def test_33_auth_cache(self):
        init_token({"otpkey": self.otpkey},
                   user=User("cornelius", self.realm1))
        set_policy(name="authcache", action="{0!s}=4m".format(PolicyAction.AUTH_CACHE), scope=SCOPE.AUTH)
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": OTPs[1]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # Check that there is an entry with this OTP value in the auth_cache
        cached_auths = AuthCache.query.filter(AuthCache.username == "cornelius", AuthCache.realm == self.realm1).all()
        found = False
        for cached_auth in cached_auths:
            if argon2.verify(OTPs[1], cached_auth.authentication):
                found = True
                break
        self.assertTrue(found)

        # Authenticate again with the same OTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": OTPs[1]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            detail = res.json.get("detail")
            self.assertEqual(detail.get("message"), "Authenticated by AuthCache.")

        delete_policy("authcache")

        # If there is no policy authenticating again with the same OTP fails.
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": OTPs[1]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            self.assertEqual(detail.get("message"), "wrong otp value. previous otp used again")

        # If there is no authcache, the same value must not be used again!
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": OTPs[2]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # Check that there is no entry with this OTP value in the auth_cache
        r = AuthCache.query.filter(AuthCache.authentication == _hash_password(OTPs[2])).first()
        self.assertFalse(bool(r))

        # Authenticate again with the same OTP value will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": OTPs[2]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))

    def test_34_validate_user_and_serial(self):
        # create a new token
        db_token = Token(self.serials[1], tokentype="hotp")
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        token = HotpTokenClass(db_token)
        self.assertEqual(token.token.serial, self.serials[1], token)
        # try to authenticate a given user with a given unassigned token serial
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "serial": self.serials[1],
                                                 "pass": OTPs[3]}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400, res)
            result = res.json['result']
            self.assertEqual(result['error']['message'],
                             "ERR905: Given serial does not belong to given user!",
                             result)

        # try to authenticate with a token assigned to a different user
        token.add_user(User("nönäscii", self.realm2))
        token.set_pin("pin")
        self.assertEqual(token.token.owners.first().user_id, "1116")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "serial": self.serials[1],
                                                 "pass": OTPs[3]}):
            res = self.app.full_dispatch_request()
            result = res.json['result']
            self.assertEqual(result['error']['message'],
                             "ERR905: Given serial does not belong to given user!",
                             result)
            self.assertEqual(res.status_code, 400, res)

    def test_35_application_tokentype(self):
        # The user has two tokens
        init_token({"type": "hotp",
                    "genkey": 1,
                    "pin": "trigpin",
                    "serial": "tok_hotp"},
                   user=User("cornelius", self.realm1))
        init_token({"type": "totp",
                    "genkey": 1,
                    "pin": "trigpin",
                    "serial": "tok_totp"},
                   user=User("cornelius", self.realm1))
        # Hotp and totp are allowed for trigger challenge
        set_policy(name="pol_chalresp", scope=SCOPE.AUTH,
                   action="{0!s}=hot totp".format(PolicyAction.CHALLENGERESPONSE))

        # trigger a challenge for both tokens
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": "cornelius", "type": "hotp"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")

        # check, that both challenges were triggered, although
        # the application tried to trigger only hotp
        triggered_serials = [item['serial'] for item in detail.get("multi_challenge")]
        self.assertTrue("tok_hotp" in triggered_serials and "tok_totp" in triggered_serials)

        # check that both serials appear in the audit log
        ae = self.find_most_recent_audit_entry(action='POST /validate/triggerchallenge')
        self.assertTrue({"tok_hotp", "tok_totp"}.issubset(set(ae.get('serial').split(','))), ae)

        # Set a policy, that the application is allowed to specify tokentype
        set_policy(name="pol_application_tokentype",
                   scope=SCOPE.AUTHZ,
                   action=PolicyAction.APPLICATION_TOKENTYPE)

        # Trigger another challenge for HOTP
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": "cornelius", "type": "hotp"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")

        # check that only HOTP was triggered
        triggered_serials = [item['serial'] for item in detail.get("multi_challenge")]
        self.assertTrue("tok_hotp" in triggered_serials and "tok_totp" not in triggered_serials)

        # Delete tokens and policies
        remove_token("tok_hotp")
        remove_token("tok_totp")
        delete_policy("pol_chalresp")
        delete_policy("pol_application_tokentype")

    def test_36_authorize_by_tokeninfo_condition(self):

        init_token({"type": "spass", "serial": "softwareToken", "pin": "software1"},
                   tokenkind="software", user=User("cornelius", self.realm1))
        init_token({"type": "spass", "serial": "hardwareToken", "pin": "hardware1"},
                   tokenkind="hardware", user=User("cornelius", self.realm1))
        set_policy(name="always_deny_access", action="{0!s}=deny_access".format(PolicyAction.AUTHORIZED),
                   scope=SCOPE.AUTHZ, priority=100)
        # policy to allow tokens, condition is deactivated. All tokens will be authorized
        set_policy(name="allow_hardware_tokens", action="{0!s}=grant_access".format(PolicyAction.AUTHORIZED),
                   scope=SCOPE.AUTHZ, priority=1,
                   conditions=[("tokeninfo", "tokenkind", "equals", "hardware", False)])

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "software1"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "hardware1"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # activate condition, only hardware tokens will be authorized
        set_policy(name="allow_hardware_tokens",
                   conditions=[("tokeninfo", "tokenkind", "equals", "hardware", True)])

        # token with tokenkind = software is not authorized
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "software1"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            # User is not authorized under these conditions (tokenkind = software)
            self.assertEqual(result.get("error").get("code"), 401)
            self.assertFalse(result.get("status"))

        # token with tokenkind = hardware is authorized
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "hardware1"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # wrong password raises exception since the tokeninfo policy cannot be checked
        # because there is not token serial in the result
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "wrongpassword"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 403, res)
            result = res.json.get("result")
            # Policy has tokeninfo, but no token object available
            self.assertEqual(result.get("error").get("code"), 303)
            self.assertFalse(result.get("status"))

        delete_policy("always_deny_access")
        delete_policy("allow_hardware_tokens")
        remove_token("softwareToken")
        remove_token("hardwareToken")

    def test_03b_check_previous_otp_with_totp(self):
        token = init_token({"type": "totp",
                            "serial": "totp_previous",
                            "otpkey": self.otpkey},
                           user=User("cornelius", self.realm1))
        # get the OTP
        counter = token._time2counter(time.time(), timeStepping=30)
        otp_now = token._calc_otp(counter)

        # test successful authentication
        with self.app.test_request_context('/validate/check',
                                           method='GET',
                                           query_string={"user": "cornelius",
                                                         "pass": otp_now}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # check the same OTP value again
        with self.app.test_request_context('/validate/check',
                                           method='GET',
                                           query_string={"user": "cornelius",
                                                         "pass": otp_now}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            self.assertIn("previous otp used again", detail.get("message"))
        # clean up
        remove_token("totp_previous")

    def test_37_challenge_response_hotp_with_container(self):
        serial = "CHALRESP1"
        pin = "chalresp1"
        # create a token and assign to the user
        db_token = Token(serial, tokentype="hotp")
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        token = HotpTokenClass(db_token)
        token.add_user(User("cornelius", self.realm1))
        token.set_pin(pin)
        container_serial = init_container({"type": "smartphone"})["container_serial"]
        container = find_container_by_serial(container_serial)
        container.add_token(token)

        # Set the failcounter
        token.set_failcount(5)
        token.save()

        # set a chalresp policy for HOTP
        set_policy("policy", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")

        # create the challenge by authenticating with the OTP PIN
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            transaction_id = detail.get("transaction_id")

        # Authentication is not yet successfully, hence the last_authentication time stamp shall not be updated yet
        self.assertIsNone(container.last_authentication)

        # send the OTP value
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": "359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))

        # check last authentication
        auth_time = datetime.datetime.now(datetime.timezone.utc)
        last_auth = container.last_authentication
        time_diff = abs((auth_time - last_auth).total_seconds())
        self.assertLessEqual(time_diff, 2)

        # delete the token
        remove_token(serial=serial)

    def test_38_disable_token_types_for_auth(self):
        """A spass token is accepted and a HOTP token triggers the challenge response,
        then a policy disables both types."""
        self.setUp_user_realms()
        serial_1 = "SPASS1"
        serial_2 = "HOTP1"

        # Create a working Simple-Pass token and HOTP token
        init_token({"serial": serial_1,
                    "type": "spass",
                    "pin": "1"},
                   user=User("cornelius", self.realm1))

        init_token({"serial": serial_2,
                    "type": "hotp",
                    "pin": "2",
                    "otpkey": self.otpkey},
                   user=User("cornelius", self.realm1))

        # It authenticates successfully before the policy is set
        with self.app.test_request_context(
                "/validate/check",
                method="POST",
                data={"user": "cornelius", "realm": self.realm1, "pass": "1"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json["result"]
            self.assertEqual(result["authentication"], "ACCEPT")

        # Set a policy to trigger challenge response for HOTP
        set_policy(name="challenge_response", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")

        with self.app.test_request_context(
                "/validate/check",
                method="POST",
                data={"user": "cornelius", "realm": self.realm1, "pass": "2"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json["result"]
            self.assertEqual(result["authentication"], "CHALLENGE")

        # Disable the spass and hotp token for authentication
        set_policy(name="disable_some_token", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.DISABLED_TOKEN_TYPES}=spass hotp")

        # The very same auth attempt must now be rejected
        with self.app.test_request_context(
                "/validate/check",
                method="POST",
                data={"user": "cornelius", "realm": self.realm1, "pass": "1"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json["result"]
            self.assertEqual(result["authentication"], "REJECT")

        with self.app.test_request_context(
                "/validate/check",
                method="POST",
                data={"user": "cornelius", "realm": self.realm1, "pass": "2"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json["result"]
            self.assertEqual(result["authentication"], "REJECT")

        # Clean-up
        remove_token(serial=serial_1)
        remove_token(serial=serial_2)
        delete_policy("challenge_response")
        delete_policy("disable_some_token")

    def test_39_invalid_user(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()
        set_default_realm(self.realm3)
        # User exist in realm1 (default realm) and realm3
        user = User("cornelius", self.realm1)
        token = init_token({"type": "spass", "pin": "1234"}, user=user)
        user_realm1 = User("hans", self.realm1)
        token_realm1 = init_token({"type": "spass", "pin": "1234"}, user=user_realm1)

        # successful authentication
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={"user": user.login, "realm": user.realm, "pass": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)

        # --- User does not exist in realm ---
        # only pass username uses default realm (username does not exist in default realm)
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={"user": "eve", "pass": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)
            error = res.json.get("result").get("error")
            self.assertEqual(904, error.get("code"), error)
            self.assertEqual(f"ERR904: User <eve@{self.realm3}> does not exist.", error.get("message"),
                             error)

        # Pass username and realm
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={"user": "eve", "realm": self.realm1, "pass": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)
            error = res.json.get("result").get("error")
            self.assertEqual(904, error.get("code"), error)
            self.assertEqual(f"ERR904: User <eve@{self.realm1}> does not exist.", error.get("message"),
                             error)

        # Pass username and resolver (sets default realm)
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={"user": "eve", "resolver": self.resolvername1, "pass": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)
            error = res.json.get("result").get("error")
            self.assertEqual(904, error.get("code"), error)
            self.assertEqual(f"ERR904: User <eve.{self.resolvername1}@{self.realm3}> does not exist.",
                             error.get("message"),
                             error)

        # Pass username, realm, and resolver
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={"user": "eve", "realm": self.realm1, "resolver": self.resolvername1,
                                                 "pass": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)
            error = res.json.get("result").get("error")
            self.assertEqual(904, error.get("code"), error)
            self.assertEqual(f"ERR904: User <eve.{self.resolvername1}@{self.realm1}> does not exist.",
                             error.get("message"),
                             error)

        # --- Realm of user was deleted ---
        realm = Realm.query.filter_by(name=self.realm1).first()
        for user_attribute in CustomUserAttribute.query.filter_by(realm_id=realm.id).all():
            user_attribute.delete()
        realm.delete()

        # only pass username uses default realm: same username exist in defrealm
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={"user": user.login, "pass": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json["detail"]
            self.assertEqual("The user has no tokens assigned", result["message"], result)

        # only pass username uses default realm: username does not exist in defrealm
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={"user": user_realm1.login, "pass": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)
            error = res.json.get("result").get("error")
            self.assertEqual(904, error.get("code"), error)
            self.assertEqual(f"ERR904: User <{user_realm1.login}@{self.realm3}> does not exist.", error.get("message"),
                             error)

        # pass username and realm
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={"user": user.login, "realm": user.realm, "pass": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)
            error = res.json.get("result").get("error")
            self.assertEqual(904, error.get("code"), error)
            self.assertEqual(f"ERR904: User <{user.login}@{user.realm}> does not exist.", error.get("message"), error)

        # pass username, realm, and resolver
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={"user": user.login, "realm": user.realm, "resolver": user.resolver,
                                                 "pass": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)
            error = res.json.get("result").get("error")
            self.assertEqual(904, error.get("code"), error)
            self.assertEqual(f"ERR904: User <{user.login}.{user.resolver}@{user.realm}> does not exist.",
                             error.get("message"), error)

        # Pass user and serial
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={"user": user.login, "realm": user.realm, "serial": token.get_serial(),
                                                 "pass": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)
            error = res.json.get("result").get("error")
            self.assertEqual(904, error.get("code"), error)
            self.assertIn("ERR904", error.get("message"))
            self.assertIn("user can not be found in any resolver in this realm", error.get("message"))

        # --- Resolver is not in realm ---
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={"user": user.login, "realm": user.realm,
                                                 "resolver": self.resolvername3, "pass": "1234"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)
            error = res.json.get("result").get("error")
            self.assertEqual(904, error.get("code"), error)
            self.assertEqual(f"ERR904: User <{user.login}.{self.resolvername3}@{user.realm}> does not exist.",
                             error.get("message"), error)

        token.delete_token()
        token_realm1.delete_token()

    def test_40_set_realm(self):
        self.setUp_user_realms()
        set_default_realm(self.realm1)
        self.setUp_user_realm3()

        token = init_token({"type": "spass", "pin": "test"}, user=User("corny", self.realm3))

        # auth without realm fails (as user is not in default realm)
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "corny",
                                                 "pass": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # set policy for auth realm
        set_policy("realm_auth", scope=SCOPE.AUTH, action=f"{PolicyAction.SET_REALM}={self.realm3}")

        # pass no realm
        self.set_default_g_variables()
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "corny",
                                                 "pass": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            self.assertEqual("ACCEPT", result.get("authentication"), result)

        # pass a different realm
        self.set_default_g_variables()
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "corny",
                                                 "realm": self.realm1,
                                                 "pass": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            self.assertEqual("ACCEPT", result.get("authentication"), result)

        # pass non-existing different realm
        self.set_default_g_variables()
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "corny",
                                                 "realm": "random",
                                                 "pass": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            self.assertEqual("ACCEPT", result.get("authentication"), result)

        # set_realm takes precedence over mangle and setrealm policy
        set_policy("mangle", scope=SCOPE.AUTH, action=f"{PolicyAction.MANGLE}=realm/.*/mangledRealm/")
        set_policy("setrealm", scope=SCOPE.AUTHZ, action=f"{PolicyAction.SETREALM}=setrealm")
        self.set_default_g_variables()
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "corny",
                                                 "realm": self.realm1,
                                                 "pass": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            self.assertEqual("ACCEPT", result.get("authentication"), result)

        token.delete_token()
        delete_policy("realm_auth")
        delete_policy("mangle")
        delete_policy("setrealm")

    def test_41_set_realm_conditions(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()
        token_corny = init_token({"type": "spass", "pin": "test"}, user=User("corny", self.realm3))
        token_hans = init_token({"type": "spass", "pin": "test1234"}, user=User("hans", self.realm1))

        # set policy for auth realm with condition on IP address
        set_policy("realm_auth", scope=SCOPE.AUTH, action=f"{PolicyAction.SET_REALM}={self.realm3}",
                   client="6.7.8.9")

        # auth with different realm from different IP works
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "hans",
                                                 "realm": self.realm1,
                                                 "pass": "test1234"},
                                           environ_base={"REMOTE_ADDR": "1.2.3.4"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            self.assertEqual("ACCEPT", result.get("authentication"), result)
            self.assertEqual(token_hans.get_serial(), res.json.get("detail").get("serial"))

        # auth from matching IP enforces realm3
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "corny",
                                                 "pass": "test"},
                                           environ_base={"REMOTE_ADDR": "6.7.8.9"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            self.assertEqual("ACCEPT", result.get("authentication"), result)
            self.assertEqual(token_corny.get_serial(), res.json.get("detail").get("serial"))

        # set policy for auth realm with condition on user agent
        delete_policy("realm_auth")
        set_policy("realm_auth", scope=SCOPE.AUTH, action=f"{PolicyAction.SET_REALM}={self.realm3}",
                   user_agents="privacyIDEA-Keycloak")

        # auth with different realm from different User Agent works
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "hans",
                                                 "realm": self.realm1,
                                                 "pass": "test1234"},
                                           headers={"User-Agent": "PAM"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            self.assertEqual("ACCEPT", result.get("authentication"), result)
            self.assertEqual(token_hans.get_serial(), res.json.get("detail").get("serial"))

        # auth from matching User-Agent enforces realm3
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "corny",
                                                 "pass": "test"},
                                           headers={"User-Agent": "privacyIDEA-Keycloak"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            self.assertEqual("ACCEPT", result.get("authentication"), result)
            self.assertEqual(token_corny.get_serial(), res.json.get("detail").get("serial"))

        # set policy for auth realm with condition on node
        delete_policy("realm_auth")
        # Use merge() rather than add() because the app's create_app() already
        # inserts Node1 at startup (PI_NODE_UUID in config.py). On Postgres a
        # plain INSERT here aborts the whole transaction; merge() is idempotent.
        # Re-bind the names to the merge() return values — the original transient
        # instances are not added to the session, and later db.session.delete()
        # would fail with "Instance is not persisted".
        node1 = db.session.merge(NodeName(id="8e4272a9-9037-40df-8aa3-976e4a04b5a9", name="Node1"))
        node2 = db.session.merge(NodeName(id="d1d7fde6-330f-4c12-88f3-58a1752594bf", name="Node2"))
        set_policy("realm_auth", scope=SCOPE.AUTH, action=f"{PolicyAction.SET_REALM}={self.realm3}",
                   pinode="Node1")

        # auth with different realm on different node
        with mock.patch("privacyidea.lib.policy.get_privacyidea_node") as mock_node:
            mock_node.return_value = "Node2"
            with self.app.test_request_context("/validate/check",
                                               method="POST",
                                               data={"user": "hans",
                                                     "realm": self.realm1,
                                                     "pass": "test1234"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertTrue(result.get("status"), result)
                self.assertTrue(result.get("value"), result)
                self.assertEqual("ACCEPT", result.get("authentication"), result)
                self.assertEqual(token_hans.get_serial(), res.json.get("detail").get("serial"))

        # auth on matching node
        with mock.patch("privacyidea.lib.policy.get_privacyidea_node") as mock_node:
            mock_node.return_value = "Node1"
            with self.app.test_request_context("/validate/check",
                                               method="POST",
                                               data={"user": "corny",
                                                     "pass": "test"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertTrue(result.get("status"), result)
                self.assertTrue(result.get("value"), result)
                self.assertEqual("ACCEPT", result.get("authentication"), result)
                self.assertEqual(token_corny.get_serial(), res.json.get("detail").get("serial"))

        # set policy for auth realm with condition on user
        delete_policy("realm_auth")
        set_policy("realm_auth", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.SET_REALM}={self.realm3}",
                   user="corny")

        # auth with different realm from different User Agent works
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "hans",
                                                 "realm": self.realm1,
                                                 "pass": "test1234"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            self.assertEqual("ACCEPT", result.get("authentication"), result)
            self.assertEqual(token_hans.get_serial(), res.json.get("detail").get("serial"))

        # auth from matching User-Agent enforces realm3
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "corny",
                                                 "pass": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            self.assertEqual("ACCEPT", result.get("authentication"), result)
            self.assertEqual(token_corny.get_serial(), res.json.get("detail").get("serial"))

        # set policy for auth realm with condition on user agent
        delete_policy("realm_auth")
        set_policy("realm_auth", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.SET_REALM}={self.realm3}",
                   user_agents="privacyIDEA-Keycloak")

        token_corny.delete_token()
        token_hans.delete_token()
        delete_policy("realm_auth")
        db.session.delete(node1)
        db.session.delete(node2)

    def test_42_hide_specific_error_message(self):
        """
        Currently, the HTTP Status codes that are returned are mixed 200 and 401.
        # TODO we need to consistently apply 401 for any kind of authentication failure, 403 for authorization failure
        # TODO and 200 only for successful requests

        This test checks that the message is generic, but the status code checks are not worth much currently.
        """
        set_policy(name="hide_error_message", scope=SCOPE.AUTH, action=f"{PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE}")
        # User does not exist: 401
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={
                                               "user": "cornelius2",
                                               "pass": "1234"
                                           }):
            res = self.app.full_dispatch_request()
            self._assert_unspecific_message_with_401(res)

        # User cornelius is in the realm that will be created
        self.setUp_user_realms()
        # Undo changes from other tests...
        set_default_realm(self.realm1)
        # User has no tokens assigned, currently returns 200 should be 401
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={
                                               "user": "cornelius",
                                               "pass": "1234"
                                           }):
            res = self.app.full_dispatch_request()
            self._assert_unspecific_message_with_200(res)

        token = init_token({"type": "spass", "pin": "21"}, user=User("cornelius", self.realm1))

        # Wrong OTP: currently 200, should be 401
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={
                                               "user": "cornelius",
                                               "pass": "1234"
                                           }):
            res = self.app.full_dispatch_request()
            self._assert_unspecific_message_with_200(res)

        token.set_failcount(10)
        token.save()
        # Failcount exceeded: currently 200, should be 401
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={
                                               "user": "cornelius",
                                               "pass": "21"
                                           }):
            res = self.app.full_dispatch_request()
            self._assert_unspecific_message_with_200(res)

        token.set_failcount(0)
        token.save()

        # lastauth: currently 200, should be 401
        now = datetime.datetime.now(datetime.timezone.utc)
        thirty_days_ago = now - datetime.timedelta(days=30)
        token.add_tokeninfo(PolicyAction.LASTAUTH, thirty_days_ago.strftime(AUTH_DATE_FORMAT))
        set_policy("lastauth", scope=SCOPE.AUTHZ, action=f"{PolicyAction.LASTAUTH}=7d")
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={
                                               "user": "cornelius",
                                               "pass": "21"
                                           }):
            res = self.app.full_dispatch_request()
            self._assert_unspecific_message_with_200(res)
        delete_policy("lastauth")

        # Successful authentication to double-check: currently 200, should be 200
        with self.app.test_request_context('/validate/check', method="POST",
                                           data={
                                               "user": "cornelius",
                                               "pass": "21"
                                           }):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual("ACCEPT", result.get("authentication"))
            self.assertTrue(result.get("value"))

        delete_policy("hide_error_message")

    def _assert_unspecific_message_with_401(self, response):
        self.assertEqual(401, response.status_code, response.json)
        result = response.json.get("result")
        error = result.get("error")
        self.assertEqual(4031, error.get("code"))
        self.assertEqual("Authentication failed.", error.get("message"))
        self.assertEqual(2, len(error))
        detail = response.json.get("detail")
        self.assertEqual("Authentication failed.", detail.get("message"))
        self.assertIn("threadid", detail)
        self.assertEqual(2, len(detail))

    def _assert_unspecific_message_with_200(self, response):
        """
        Responses with 200 do not contain the error section.
        """
        self.assertEqual(200, response.status_code, response.json)
        detail = response.json.get("detail")
        self.assertEqual("Authentication failed.", detail.get("message"), detail)
        self.assertIn("threadid", detail)
        self.assertEqual(2, len(detail), detail)

        result = response.json.get("result")
        self.assertEqual("REJECT", result.get("authentication"))
        self.assertFalse(result.get("value"))
