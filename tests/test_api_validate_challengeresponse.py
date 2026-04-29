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


class AChallengeResponse(MyApiTestCase):
    serial = "hotp1"
    serial_email = "email1"
    serial_sms = "sms1"

    def setUp(self):
        self.setUp_user_realms()

    def test_01_challenge_response_token_deactivate(self):
        # New token for the user "selfservice"
        init_token({"type": "hotp", "serial": "hotp1", "otpkey": self.otpkey},
                   user=User(uid=1004, realm=self.realm1, resolver=self.resolvername1))
        # Define HOTP token to be challenge response
        set_policy(name="pol_cr", scope=SCOPE.AUTH, action="{0!s}=hotp".format(PolicyAction.CHALLENGERESPONSE))
        set_pin(self.serial, "pin")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            self.assertEqual(data.get("result").get("authentication"), "CHALLENGE")
            detail = data.get("detail")
            self.assertTrue("enter otp" in detail.get("message"), detail.get("message"))
            transaction_id = detail.get("transaction_id")

        # Now we try to provide the OTP value
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": self.valid_otp_values[0],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("value"))
            self.assertEqual(data.get("result").get("authentication"), "ACCEPT")

        # Now we send the challenge and then we disable the token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            self.assertEqual(data.get("result").get("authentication"), "CHALLENGE")
            detail = data.get("detail")
            self.assertTrue("enter otp" in detail.get("message"), detail.get("message"))
            transaction_id = detail.get("transaction_id")

        # disable the token
        enable_token(self.serial, False)

        # Now we try to provide the OTP value, but authentication must fail, since the token is disabled
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": self.valid_otp_values[1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertFalse(data.get("result").get("value"))
            self.assertEqual(data.get("result").get("authentication"), "REJECT")
            detail = data.get("detail")
            self.assertEqual("Token is disabled", detail.get("message"))

        # The token is still disabled. We are checking, if we can do a challenge response
        # for a disabled token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            self.assertEqual(data.get("result").get("authentication"), "REJECT")
            detail = data.get("detail")
            self.assertEqual("Token is disabled", detail.get("message"), detail.get("message"))

        delete_policy("pol_cr")

    @smtpmock.activate
    def test_02_two_challenge_response_tokens(self):
        smtpmock.setdata(response={"bla@example.com": (200, 'OK')})
        # We test two challenge response tokens. One is active, one is disabled.
        # Enroll an Email-Token to the user
        init_token(user=User("selfservice", self.realm1),
                   param={"serial": self.serial_email,
                          "type": "email",
                          "email": "bla@example.com",
                          "otpkey": self.otpkey})
        set_pin(self.serial_email, "pin")

        toks = get_tokens(user=User("selfservice", self.realm1))
        self.assertEqual(len(toks), 2)
        self.assertFalse(toks[0].token.active)
        self.assertTrue(toks[1].token.active)

        # Now we create a challenge with two tokens
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "selfservice",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            self.assertEqual(data.get("result").get("authentication"), "CHALLENGE")
            detail = data.get("detail")
            # Only the email token is active and creates a challenge!
            self.assertEqual("Enter the OTP from the Email", detail.get("message"))

        # Now test with triggerchallenge
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": "selfservice"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            # Triggerchallenge returns the numbers of tokens in the "value
            self.assertEqual(data.get("result").get("value"), 1)
            detail = data.get("detail")
            # Only the email token is active and creates a challenge!
            self.assertEqual("Enter the OTP from the Email", detail.get("messages")[0])
        remove_token(self.serial_email)

    @smtpmock.activate
    def test_03_two_challenges_from_one_email_token(self):
        set_privacyidea_config("email.concurrent_challenges", "True")
        smtpmock.setdata(response={"bla@example.com": (200, 'OK')})
        # remove tokens for user cornelius
        remove_token(user=User("cornelius", self.realm1))
        # Enroll an Email-Token to the user
        init_token(user=User("cornelius", self.realm1),
                   param={"serial": self.serial_email,
                          "type": "email",
                          "email": "bla@example.com",
                          "otpkey": self.otpkey})
        set_pin(self.serial_email, "pin")

        toks = get_tokens(user=User("cornelius", self.realm1))
        self.assertEqual(len(toks), 1)

        # Now we create the first challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            # Only the email token is active and creates a challenge!
            self.assertEqual("Enter the OTP from the Email", detail.get("message"))
            transaction_id1 = detail.get("transaction_id")

        # Now we create the second challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            # Only the email token is active and creates a challenge!
            self.assertEqual("Enter the OTP from the Email", detail.get("message"))
            transaction_id2 = detail.get("transaction_id")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id2,
                                                 "pass": OTPs[2]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id1,
                                                 "pass": OTPs[1]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))

        remove_token(self.serial_email)
        delete_privacyidea_config("email.concurrent_challenges")

    @smtpmock.activate
    def test_04_only_last_challenge_from_one_email_token(self):
        set_privacyidea_config("email.concurrent_challenges", "False")
        smtpmock.setdata(response={"bla@example.com": (200, 'OK')})
        # remove tokens for user cornelius
        remove_token(user=User("cornelius", self.realm1))
        # Enroll an Email-Token to the user
        init_token(user=User("cornelius", self.realm1),
                   param={"serial": self.serial_email,
                          "type": "email",
                          "email": "bla@example.com",
                          "otpkey": self.otpkey})
        set_pin(self.serial_email, "pin")

        toks = get_tokens(user=User("cornelius", self.realm1))
        self.assertEqual(len(toks), 1)

        # Now we create the first challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            # Only the email token is active and creates a challenge!
            self.assertEqual("Enter the OTP from the Email", detail.get("message"))
            transaction_id1 = detail.get("transaction_id")

        # Now we create the second challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            # Only the email token is active and creates a challenge!
            self.assertEqual("Enter the OTP from the Email", detail.get("message"))
            transaction_id2 = detail.get("transaction_id")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id1,
                                                 "pass": OTPs[1]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            # The first challenge will not authenticate anymore, since the OTP is not stored in the challenge data
            # and the token counter was increased
            self.assertFalse(data.get("result").get("value"))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id2,
                                                 "pass": OTPs[2]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))

        remove_token(self.serial_email)
        delete_privacyidea_config("email.concurrent_challenges")

    @responses.activate
    def test_05_two_challenges_from_one_sms_token(self):
        # Configure the SMS Gateway
        setup_sms_gateway()

        ### Now do the enrollment and authentication
        set_privacyidea_config("sms.concurrent_challenges", "True")
        # remove tokens for user cornelius
        remove_token(user=User("cornelius", self.realm1))
        # Enroll an SMS-Token to the user
        init_token(user=User("cornelius", self.realm1),
                   param={"serial": self.serial_sms,
                          "type": "sms",
                          "phone": "1234567",
                          "otpkey": self.otpkey})
        set_pin(self.serial_sms, "pin")

        toks = get_tokens(user=User("cornelius", self.realm1))
        self.assertEqual(len(toks), 1)

        # Now we create the first challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual("Enter the OTP from the SMS:", detail.get("message"))
            transaction_id1 = detail.get("transaction_id")

        # Now we create the second challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual("Enter the OTP from the SMS:", detail.get("message"))
            transaction_id2 = detail.get("transaction_id")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id2,
                                                 "pass": OTPs[2]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id1,
                                                 "pass": OTPs[1]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))

        remove_token(self.serial_sms)
        delete_privacyidea_config("sms.concurrent_challenges")

    @responses.activate
    def test_06_only_last_challenges_from_one_sms_token(self):
        # Configure the SMS Gateway
        setup_sms_gateway()

        ### Now do the enrollment and authentication
        try:
            delete_privacyidea_config("sms.concurrent_challenges")
        except AttributeError:
            pass

        # remove tokens for user cornelius
        remove_token(user=User("cornelius", self.realm1))
        # Enroll an SMS-Token to the user
        init_token(user=User("cornelius", self.realm1),
                   param={"serial": self.serial_sms,
                          "type": "sms",
                          "phone": "1234567",
                          "otpkey": self.otpkey})
        set_pin(self.serial_sms, "pin")

        toks = get_tokens(user=User("cornelius", self.realm1))
        self.assertEqual(len(toks), 1)

        # Now we create the first challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual("Enter the OTP from the SMS:", detail.get("message"))
            transaction_id1 = detail.get("transaction_id")

        # Now we create the second challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual("Enter the OTP from the SMS:", detail.get("message"))
            transaction_id2 = detail.get("transaction_id")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id1,
                                                 "pass": OTPs[1]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            # First OTP fails, since the counter increased
            self.assertFalse(data.get("result").get("value"))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id2,
                                                 "pass": OTPs[2]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            # Last value succeeds
            self.assertTrue(data.get("result").get("value"))

        remove_token(self.serial_sms)

    @responses.activate
    def test_07_disabled_sms_token_will_not_trigger_challenge(self):
        # Configure the SMS Gateway
        setup_sms_gateway()

        # remove tokens for user cornelius
        remove_token(user=User("cornelius", self.realm1))
        # Enroll an SMS-Token to the user
        init_token(user=User("cornelius", self.realm1),
                   param={"serial": self.serial_sms,
                          "type": "sms",
                          "phone": "1234567",
                          "otpkey": self.otpkey})
        set_pin(self.serial_sms, "pin")
        # disable the token
        enable_token(self.serial_sms, False)

        toks = get_tokens(user=User("cornelius", self.realm1))
        self.assertEqual(len(toks), 1)

        # Now we try to create a challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual("Token is disabled", detail.get("message"))

        remove_token(self.serial_sms)

    def test_08_challenge_text(self):
        # We create two HOTP tokens for the user as challenge response and run a
        # challenge response request with both tokens.
        set_policy(name="pol_header",
                   scope=SCOPE.AUTH,
                   action="{0!s}=These are your options:<ul>".format(PolicyAction.CHALLENGETEXT_HEADER))
        # Set a policy for the footer
        set_policy(name="pol_footer",
                   scope=SCOPE.AUTH,
                   action="{0!s}=</ul>.<b>Authenticate Now!</b>".format(PolicyAction.CHALLENGETEXT_FOOTER))
        # make HOTP a challenge response token
        set_policy(name="pol_hotp",
                   scope=SCOPE.AUTH,
                   action="{0!s}=hotp".format(PolicyAction.CHALLENGERESPONSE))

        init_token({"serial": "tok1",
                    "otpkey": self.otpkey,
                    "pin": "pin"}, user=User("cornelius", self.realm1))
        init_token({"serial": "tok2",
                    "otpkey": self.otpkey,
                    "pin": "pin"}, user=User("cornelius", self.realm1))

        # Now we try to create a challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual(detail.get("message"),
                             'These are your options:<ul><li>please enter otp: </li>\n</ul>.<b>Authenticate Now!</b>')

        remove_token("tok1")
        remove_token("tok2")
        delete_policy("pol_header")
        delete_policy("pol_footer")
        delete_policy("pol_hotp")

    def test_09_challenge_response_inc_failcounter(self):
        # make HOTP a challenge response token
        set_policy(name="pol_hotp",
                   scope=SCOPE.AUTH,
                   action="{0!s}=hotp".format(PolicyAction.CHALLENGERESPONSE))
        init_token({"serial": "tok1",
                    "otpkey": self.otpkey,
                    "pin": "pin"}, user=User("cornelius", self.realm1))

        # On token fails to challenge response
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            transaction_id = detail.get("transaction_id")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "wrongOTP",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertEqual("tok1", detail.get("serial"))
            self.assertEqual("hotp", detail.get("type"))
            self.assertEqual("Response did not match the challenge.", detail.get("message"))

        init_token({"serial": "tok2",
                    "otpkey": self.otpkey,
                    "pin": "pin"}, user=User("cornelius", self.realm1))

        # Now, two tokens will not match
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            transaction_id = detail.get("transaction_id")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "wrongOTP",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            detail = data.get("detail")
            self.assertTrue("serial" not in detail)
            self.assertEqual("Response did not match for 2 tokens.", detail.get("message"))

        # Now check the fail counters of the tokens
        self.assertEqual(2, get_one_token(serial="tok1").token.failcount)
        self.assertEqual(1, get_one_token(serial="tok2").token.failcount)

        remove_token("tok1")
        remove_token("tok2")
        delete_policy("pol_hotp")

    def test_10_unique_transaction_id(self):
        # Tokens should create a unique transaction id
        # The TiQR token changes the transaction id.

        # Assign token to user:
        r = init_token({"serial": "tok1", "type": "hotp", "otpkey": self.otpkey},
                       user=User("cornelius", self.realm1))
        self.assertTrue(r)
        r = init_token({"serial": "tok2", "type": "tiqr", "otpkey": self.otpkey},
                       user=User("cornelius", self.realm1))
        self.assertTrue(r)

        set_policy("chalresp", scope=SCOPE.ADMIN, action=f"{PolicyAction.TRIGGERCHALLENGE}=hotp")

        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": "cornelius"},
                                           headers={"authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertEqual(data.get("result").get("value"), 2)
            # The two challenges should be the same
            multichallenge = data.get("detail").get("multi_challenge")
            transaction_id = data.get("detail").get("transaction_id")
            self.assertEqual(multichallenge[0].get("transaction_id"), transaction_id)
            self.assertEqual(multichallenge[1].get("transaction_id"), transaction_id)

        delete_policy("chalresp")
        remove_token("tok1")
        remove_token("tok2")

    @radiusmock.activate
    def test_11_validate_radiustoken(self):
        # A RADIUS token with RADIUS challenge response
        # remove all tokens of user Cornelius
        user_obj = User("cornelius", self.realm1)
        remove_token(user=user_obj)

        # We need the Challenge-Response policy
        set_policy(name="radius_chal_resp", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=radius")

        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123", dictionary=DICT_FILE)
        self.assertTrue(r > 0)
        init_token({"type": "radius",
                    "serial": "rad1",
                    "radius.identifier": "myserver",
                    "radius.local_checkpin": False,
                    "radius.user": "nönäscii"},
                   user=user_obj)
        radiusmock.setdata(timeout=False, response=radiusmock.AccessChallenge)
        with self.app.test_request_context('/validate/check',
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "pass": "radiuspassword"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            self.assertEqual(AUTH_RESPONSE.CHALLENGE, data.get("result").get("authentication"))
            transaction_id = data.get("detail").get("transaction_id")
            self.assertIsNotNone(transaction_id)

        # Now we send the response to this request but the wrong response!
        radiusmock.setdata(timeout=False, response=radiusmock.AccessReject)
        with self.app.test_request_context('/validate/check',
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "pass": "wrongPW",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            self.assertEqual(AUTH_RESPONSE.REJECT, data.get("result").get("authentication"))
            # No transaction_id
            self.assertNotIn("transaction_id", data.get("detail"))

        # Finally we succeed
        radiusmock.setdata(timeout=False, response=radiusmock.AccessAccept)
        with self.app.test_request_context('/validate/check',
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "pass": "correctPW",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))
            self.assertEqual(AUTH_RESPONSE.ACCEPT, data.get("result").get("authentication"))
            # No transaction_id
            self.assertNotIn("transaction_id", data.get("detail"))

        # A second request tries to use the same transaction_id, but the RADIUS server
        # responds with a Reject
        radiusmock.setdata(timeout=False, response=radiusmock.AccessReject)
        with self.app.test_request_context('/validate/check',
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "pass": "correctPW",
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))
            self.assertEqual(AUTH_RESPONSE.REJECT, data.get("result").get("authentication"))

        # And finally a single shot authentication, no chal resp, no transaction_id
        radiusmock.setdata(timeout=False, response=radiusmock.AccessAccept)
        with self.app.test_request_context('/validate/check',
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "pass": "correctPW"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))
            self.assertEqual(AUTH_RESPONSE.ACCEPT, data.get("result").get("authentication"))
        remove_token("rad1")
        delete_policy("radius_chal_resp")

    def test_12_polltransaction(self):
        # Assign token to user:
        r = init_token({"serial": "tok1", "type": "hotp", "otpkey": self.otpkey},
                       user=User("cornelius", self.realm1))
        self.assertTrue(r)
        r = init_token({"serial": "tok2", "type": "tiqr", "otpkey": self.otpkey},
                       user=User("cornelius", self.realm1))
        self.assertTrue(r)

        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": "cornelius"},
                                           headers={"authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertEqual(data.get("result").get("value"), 2)
            # The two challenges should be the same
            multichallenge = data.get("detail").get("multi_challenge")
            transaction_id = data.get("detail").get("transaction_id")
            self.assertEqual(transaction_id, multichallenge[0].get("transaction_id"))
            self.assertEqual(transaction_id, multichallenge[1].get("transaction_id"))

        # Check that serials are written to the audit log
        entry = self.find_most_recent_audit_entry(action="*/validate/triggerchallenge*")
        self.assertIn("tok1", entry["serial"])
        self.assertIn("tok2", entry["serial"])

        # add a really old expired challenge for tok1
        old_transaction_id = "1111111111"
        old_challenge = Challenge(serial="tok1", transaction_id=old_transaction_id, challenge="")
        old_challenge_timestamp = datetime.datetime.now() - datetime.timedelta(days=3)
        old_challenge.timestamp = old_challenge_timestamp
        old_challenge.expiration = old_challenge_timestamp + datetime.timedelta(minutes=120)
        old_challenge.save()

        # Check behavior of the polltransaction endpoint
        # POST is not allowed
        with self.app.test_request_context("/validate/polltransaction", method="POST"):
            res = self.app.full_dispatch_request()
            self.assertEqual(405, res.status_code)

        # transaction_id is required
        with self.app.test_request_context("/validate/polltransaction", method="GET"):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code)
            self.assertFalse(res.json["result"]["status"])
            self.assertIn("Missing parameter: transaction_id", res.json["result"]["error"]["message"])

        # wildcards do not work
        with self.app.test_request_context("/validate/polltransaction", method="GET",
                                           query_string={"transaction_id": "*"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])

        # a non-existent transaction_id just returns false
        with self.app.test_request_context("/validate/polltransaction", method="GET",
                                           query_string={"transaction_id": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])

        # check audit log
        entry = self.find_most_recent_audit_entry(action="*/validate/polltransaction*")
        self.assertEqual("transaction_id: 123456", entry["action_detail"])
        self.assertEqual("status: pending", entry["info"])
        self.assertEqual("", entry["serial"])
        # Instead of None the "user" entry is now (v3.11.3) an empty string
        self.assertEqual("", entry["user"])

        # polling the transaction returns false, because no challenge has been answered
        with self.app.test_request_context("/validate/polltransaction", method="GET",
                                           query_string={"transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])

        # but audit log contains both serials and the user
        entry = self.find_most_recent_audit_entry(action="*/validate/polltransaction*")
        self.assertEqual(f"transaction_id: {transaction_id}", entry["action_detail"])
        self.assertEqual("status: pending", entry["info"])
        self.assertIn("tok1", entry["serial"])
        self.assertIn("tok2", entry["serial"])
        self.assertFalse(entry["success"])
        self.assertEqual("cornelius", entry["user"])
        self.assertEqual("resolver1", entry["resolver"])
        self.assertEqual(self.realm1, entry["realm"])

        # polling the expired transaction returns false
        with self.app.test_request_context("/validate/polltransaction", method="GET",
                                           query_string={"transaction_id": old_transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])

        # and the audit log contains no serials and the user
        entry = self.find_most_recent_audit_entry(action="*/validate/polltransaction*")
        self.assertEqual(f"transaction_id: {old_transaction_id}", entry["action_detail"])
        self.assertEqual("status: pending", entry["info"])
        self.assertEqual("", entry["serial"])
        self.assertFalse(entry["success"])

        # Mark one challenge as answered
        Challenge.query.filter_by(serial="tok1", transaction_id=transaction_id).update({"otp_valid": True})
        db.session.commit()

        # polling the transaction returns true, because the challenge has been answered
        with self.app.test_request_context("/validate/polltransaction", method="GET",
                                           query_string={"transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertTrue(res.json["result"]["status"])
            self.assertTrue(res.json["result"]["value"])

        entry = self.find_most_recent_audit_entry(action="*/validate/polltransaction*")
        self.assertEqual(f"transaction_id: {transaction_id}", entry["action_detail"])
        self.assertEqual("status: accept", entry["info"])
        # tok2 is not written to the audit log
        self.assertEqual("tok1", entry["serial"])
        self.assertTrue(entry["success"])
        self.assertEqual("cornelius", entry["user"])
        self.assertEqual("resolver1", entry["resolver"])
        self.assertEqual(self.realm1, entry["realm"])

        # polling the transaction again gives the same result, even with the more REST-y endpoint
        with self.app.test_request_context(f"/validate/polltransaction/{transaction_id}",
                                           method="GET"):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertTrue(res.json["result"]["status"])
            self.assertTrue(res.json["result"]["value"])

        remove_token("tok1")
        remove_token("tok2")

        # polling the transaction now gives false
        with self.app.test_request_context(f"/validate/polltransaction/{transaction_id}",
                                           method="GET",
                                           query_string={"transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            self.assertTrue(res.json["result"]["status"])
            self.assertFalse(res.json["result"]["value"])

    def test_13_chal_resp_indexed_secret(self):
        my_secret = "HelloMyFriend"
        init_token({"otpkey": my_secret,
                    "pin": "test",
                    "serial": "PIIX01",
                    "type": "indexedsecret"},
                   user=User("cornelius", self.realm1))
        # Trigger a challenge
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "pass": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            response = res.json
            self.assertTrue(response.get("result").get("status"))
            self.assertFalse(response.get("result").get("value"))
            transaction_id = response.get("detail").get("transaction_id")
            random_positions = response.get("detail").get("attributes").get("random_positions")
            password_list = [my_secret[x - 1] for x in random_positions]
            password = "".join(password_list)

        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "transaction_id": transaction_id,
                                                 "pass": password}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            response = res.json
            # successful authentication
            self.assertTrue(response.get("result").get("value"))

        # ennroll an empty indexedsecret token and check the raised exception
        remove_token("PIIX01")
        # Clear session before adding new entries to avoid conflicts due to re-adding user cache entry which gets the
        # same primary key ID as the deleted one.
        db.session.expunge_all()
        init_token({"otpkey": "",
                    "pin": "test",
                    "serial": "PIIX01",
                    "type": "indexedsecret"},
                   user=User("cornelius", self.realm1))
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           data={"user": "cornelius",
                                                 "pass": "test"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)
            response = res.json
            result = response.get("result")
            self.assertFalse(result.get("status"))
            self.assertEqual('ERR401: The indexedsecret token has an empty secret '
                             'and can not be used for authentication.',
                             result.get("error").get("message"))
        remove_token("PIIX01")

    def test_14_indexed_secret_multichallenge(self):
        index_secret = "abcdefghijklmn"
        serial = "indx001"
        tok = init_token({"type": "indexedsecret", "otpkey": index_secret, "pin": "index", "serial": serial},
                         user=User("cornelius", self.realm1))
        tok.add_tokeninfo("multichallenge", 1)

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "pass": "index"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            position = detail.get("attributes").get("random_positions")[0]

        # First response
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "pass": index_secret[position - 1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            position = detail.get("attributes").get("random_positions")[0]

        # Second response
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "pass": index_secret[position - 1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            # Successful authentication!
            self.assertTrue(result.get("value"))

        remove_token(serial)

    def test_15_questionnaire_multichallenge(self):
        questionnaire = {"Question1": "Answer1",
                         "Question2": "Answer2",
                         "Question3": "Answer3",
                         "Q4": "A4",
                         "Q5": "A5"}
        serial = "quest001"
        found_questions = []
        init_token({"type": "question", "questions": questionnaire,
                    "pin": "quest", "serial": serial},
                   user=User("cornelius", self.realm1))

        # We want two questions during authentication
        set_policy(name="questpol", scope=SCOPE.AUTH, action="question_number=6")

        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "pass": "quest"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            question = detail.get("message")
            found_questions.append(question)

        # Run 5 responses that require more
        for i in range(0, 5):
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": "cornelius", "pass": questionnaire.get(question),
                                                     "transaction_id": transaction_id}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 200)
                result = res.json['result']
                self.assertFalse(result.get("value"))
                detail = res.json.get("detail")
                transaction_id = detail.get("transaction_id")
                question = detail.get("message")
                found_questions.append(question)

        self.assertEqual(len(set(found_questions)), 5)

        # Now we run the last response. It can be any of the 5 original questions again.

        # Sixth and last response will be successful
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "cornelius", "pass": questionnaire.get(question),
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            # Successful authentication!
            self.assertTrue(result.get("value"))

        # But we still have 5 distinct questions
        self.assertEqual(len(set(found_questions)), 5)
        remove_token(serial)
        delete_policy("questpol")

    def test_16_4eyes_multichallenge_with_pin(self):
        # We require 1 token in realm1 and 2 tokens in realm2
        required_tokens = {"realm1": {"selected": True,
                                      "count": 1},
                           "realm3": {"selected": True,
                                      "count": 2}}
        serial = "4eyes001"
        # We want more than one realm
        self.setUp_user_realm3()
        tok = init_token({"type": "4eyes", "4eyes": required_tokens, "pin": "pin", "serial": serial},
                         user=User("root", self.realm3))
        self.assertTrue(tok.get_tokeninfo("4eyes"), "realm1:1,realm3:2")

        # Now we enroll some tokens for the 3 admins.
        # user: cornelius@realm1
        tok = init_token({"type": "hotp", "otpkey": self.otpkey, "pin": "adminpin1", "serial": "admintok1"},
                         user=User("cornelius", self.realm1))
        self.assertTrue(tok.get_tokeninfo("tokenkind"), "software")
        # user: cornelius@realm3
        tok = init_token({"type": "hotp", "otpkey": self.otpkey, "pin": "adminpin2", "serial": "admintok2"},
                         user=User("cornelius", self.realm3))
        self.assertTrue(tok.get_tokeninfo("tokenkind"), "software")
        # user: privacyidea@realm3
        tok = init_token({"type": "hotp", "otpkey": self.otpkey, "pin": "adminpin3", "serial": "admintok3"},
                         user=User("privacyidea", self.realm3))
        self.assertTrue(tok.get_tokeninfo("tokenkind"), "software")

        # Start the authentication with the PIN of the 4eyes token
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root", "realm": self.realm3, "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            transaction_id = detail.get("transaction_id")
            self.assertTrue(transaction_id)

        # Authenticate with the first admin token
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root@realm3",
                                                 "pass": "adminpin1" + self.valid_otp_values[1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertEqual("Please authenticate with another token from either realm: realm3.",
                             detail.get("message"))

        # Authenticate with the second admin token
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root@realm3",
                                                 "pass": "adminpin2" + self.valid_otp_values[1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertEqual("Please authenticate with another token from either realm: realm3.",
                             detail.get("message"))

        # If we would use the 2nd token *again*, then the authentication fails
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root@realm3",
                                                 "pass": "adminpin2" + self.valid_otp_values[2],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            self.assertNotIn("transaction_id", detail)
            self.assertEqual("Response did not match the challenge.", detail.get("message"))

        # Authenticate with the third admin token
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root@realm3",
                                                 "pass": "adminpin3" + self.valid_otp_values[1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertTrue(result.get("value"))
            detail = res.json.get("detail")

        remove_token(serial)
        remove_token("admintok1")
        remove_token("admintok2")
        remove_token("admintok3")

    def test_17_4eyes_multichallenge(self):
        # We require 1 token in realm1 and 2 tokens in realm2
        required_tokens = {"realm1": {"selected": True,
                                      "count": 1},
                           "realm3": {"selected": True,
                                      "count": 2}}
        serial = "4eyes001"
        # We want more than one realm
        self.setUp_user_realm3()
        # Init 4eyes token without PIN
        tok = init_token({"type": "4eyes", "4eyes": required_tokens, "serial": serial},
                         user=User("root", self.realm3))
        self.assertTrue(tok.get_tokeninfo("4eyes"), "realm1:1,realm3:2")

        # Now we enroll some tokens for the 3 admins.
        # user: cornelius@realm1
        tok = init_token({"type": "hotp", "otpkey": self.otpkey, "pin": "adminpin1", "serial": "admintok1"},
                         user=User("cornelius", self.realm1))
        self.assertTrue(tok.get_tokeninfo("tokenkind"), "software")
        # user: cornelius@realm3
        tok = init_token({"type": "hotp", "otpkey": self.otpkey, "pin": "adminpin2", "serial": "admintok2"},
                         user=User("cornelius", self.realm3))
        self.assertTrue(tok.get_tokeninfo("tokenkind"), "software")
        # user: privacyidea@realm3
        tok = init_token({"type": "hotp", "otpkey": self.otpkey, "pin": "adminpin3", "serial": "admintok3"},
                         user=User("privacyidea", self.realm3))
        self.assertTrue(tok.get_tokeninfo("tokenkind"), "software")

        # Start the authentication with one of the tokens!
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root@realm3",
                                                 "pass": "adminpin2" + self.valid_otp_values[1]}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            transaction_id = detail.get("transaction_id")
            self.assertTrue(transaction_id)

        # Authenticate with the 2nd admin token
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root@realm3",
                                                 "pass": "adminpin1" + self.valid_otp_values[1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertFalse(result.get("value"))
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            self.assertTrue(transaction_id)

        # Authenticate with the second admin token
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "root@realm3",
                                                 "pass": "adminpin3" + self.valid_otp_values[1],
                                                 "transaction_id": transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json['result']
            self.assertTrue(result.get("value"))

        remove_token(serial)
        remove_token("admintok1")
        remove_token("admintok2")
        remove_token("admintok3")

    @smtpmock.activate
    def test_18_email_triggerchallenge_no_pin(self):
        # Test that the HOTP value from an email token without a PIN
        # can not be used in challenge response after the challenge expired.
        smtpmock.setdata(response={"hans@dampf.com": (200, 'OK')})
        self.setUp_user_realms()
        self.setUp_user_realm2()
        serial = "smtp01"
        user = "timelimituser"
        # Create token without PIN
        r = init_token({"type": "email", "serial": serial,
                        "otpkey": self.otpkey,
                        "email": "hans@dampf.com"}, user=User(user, self.realm2))
        self.assertTrue(r)

        # Trigger challenge for the user
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": user, "realm": self.realm2},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), 1)
            self.assertEqual(result.get("authentication"), AUTH_RESPONSE.CHALLENGE)
            detail = res.json.get("detail")
            self.assertEqual(detail.get("messages")[0],
                             _("Enter the OTP from the Email"))
            transaction_id = detail.get("transaction_id")

        # If we wait long enough, the challenge has expired,
        # while the HOTP value 287082 in itself would still be valid.
        # However, the authentication with the expired transaction_id has to fail
        new_utcnow = datetime.datetime.now(tz=timezone.utc).replace(tzinfo=None) + datetime.timedelta(minutes=12)
        new_now = datetime.datetime.now().replace(tzinfo=None) + datetime.timedelta(minutes=12)
        with mock.patch('privacyidea.models.utils.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = new_utcnow
            mock_datetime.now.return_value = new_now
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": user, "realm": self.realm2,
                                                     "transaction_id": transaction_id,
                                                     "pass": self.valid_otp_values[1]}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertFalse(result.get("value"))
                detail = res.json.get("detail")
                self.assertEqual("Response did not match the challenge.", detail.get("message"))

        remove_token(serial)

    def test_19_increase_failcounter_on_challenge(self):
        # Create email token
        init_token({
            "type": "email",
            "serial": self.serial_email,
            "email": "hans@dampf.com",
            "pin": "pin"},
            user=User("cornelius", self.realm1))

        # Create SMS token
        init_token({
            "type": "sms",
            "serial": self.serial_sms,
            "phone": "123456",
            "pin": "pin"},
            user=User("cornelius", self.realm1))

        # Create HOTP token
        init_token({
            "type": "hotp",
            "serial": "hotp_serial",
            "otpkey": "abcde12345",
            "pin": "pin"},
            user=User("cornelius", self.realm1))

        # Now check the fail counters of the tokens, all should be 0
        self.assertEqual(0, get_one_token(serial=self.serial_email).token.failcount)
        self.assertEqual(0, get_one_token(serial=self.serial_sms).token.failcount)
        self.assertEqual(0, get_one_token(serial="hotp_serial").token.failcount)

        # Set the increase_failcounter_on_challenge policy
        set_policy(name="increase_failcounter_on_challenge",
                   scope=SCOPE.AUTH,
                   action=PolicyAction.INCREASE_FAILCOUNTER_ON_CHALLENGE)

        # Now we create the challenges via validate/check
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # The failcounter (email, sms) increased by 1
        self.assertEqual(1, get_one_token(serial=self.serial_email).token.failcount)
        self.assertEqual(1, get_one_token(serial=self.serial_sms).token.failcount)
        self.assertEqual(0, get_one_token(serial="hotp_serial").token.failcount)

        # Trigger a challenge for all token via validate/triggerchallenge
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": "cornelius"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # All failcounter increased by 1
        self.assertEqual(2, get_one_token(serial=self.serial_email).token.failcount)
        self.assertEqual(2, get_one_token(serial=self.serial_sms).token.failcount)
        self.assertEqual(1, get_one_token(serial="hotp_serial").token.failcount)

        # Clean up
        remove_token(self.serial_email)
        remove_token(self.serial_sms)
        remove_token("hotp_serial")
        delete_policy("increase_failcounter_on_challenge")
