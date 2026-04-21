# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the token PIN-change flow."""
import binascii
import datetime
import hashlib
import json
import logging
import warnings

import mock
from dateutil import parser
from dateutil.tz import tzlocal
from sqlalchemy import select
from testfixtures import log_capture, LogCapture

from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import (set_privacyidea_config, get_token_types,
                                    delete_privacyidea_config)
from privacyidea.lib.container import (init_container, add_token_to_container,
                                       find_container_by_serial)
from privacyidea.lib.error import PolicyError, UserError
from privacyidea.lib.error import (TokenAdminError, ParameterError,
                                   PrivacyIDEAError, ResourceNotFoundError)
from privacyidea.lib.framework import get_app_config
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import (set_policy, SCOPE, PolicyClass,
                                    delete_policy)
from privacyidea.lib.token import (create_tokenclass_object,
                                   get_tokens, list_tokengroups,
                                   get_token_type, check_serial,
                                   get_num_tokens_in_realm,
                                   get_realms_of_token,
                                   token_exist, get_token_owner, is_token_owner,
                                   get_tokenclass_info,
                                   get_tokens_in_resolver, get_otp,
                                   get_token_by_otp, get_serial_by_otp,
                                   gen_serial, init_token,
                                   set_realms, set_defaults, assign_token,
                                   unassign_token, resync_token,
                                   reset_token, set_pin, set_pin_user,
                                   set_pin_so, enable_token,
                                   is_token_active, set_hashlib, set_otplen,
                                   set_count_auth, add_tokeninfo,
                                   set_sync_window, set_count_window,
                                   set_description, get_multi_otp,
                                   set_max_failcount, copy_token_pin,
                                   copy_token_user, lost_token,
                                   check_token_list, check_serial_pass,
                                   check_realm_pass,
                                   check_user_pass,
                                   get_dynamic_policy_definitions,
                                   get_tokens_paginate,
                                   set_validity_period_end,
                                   set_validity_period_start, remove_token, delete_tokeninfo,
                                   import_token, get_one_token, get_tokens_from_serial_or_user,
                                   get_tokens_paginated_generator, assign_tokengroup, unassign_tokengroup,
                                   set_tokengroups)
from privacyidea.lib.token import log as token_log
from privacyidea.lib.token import weigh_token_type, import_tokens, export_tokens
from privacyidea.lib.tokenclass import DATE_FORMAT, RolloutState
from privacyidea.lib.tokenclass import (TokenClass, Tokenkind,
                                        FAILCOUNTER_EXCEEDED,
                                        FAILCOUNTER_CLEAR_TIMEOUT)
from privacyidea.lib.tokengroup import set_tokengroup, delete_tokengroup
from privacyidea.lib.tokens.totptoken import TotpTokenClass
from privacyidea.lib.user import (User)
from privacyidea.lib.utils import b32encode_and_unicode, hexlify_and_unicode
from privacyidea.models import (db, Token, Challenge, TokenRealm, Tokengroup)
from .base import MyTestCase, FakeAudit, FakeFlaskG

PWFILE = "tests/testdata/passwords"
OTPKEY = "3132333435363738393031323334353637383930"
OTPKE2 = "31323334353637383930313233343536373839AA"
CHANGED_KEY = '31323334353637383930313233343536373839AA'
class PINChangeTestCase(MyTestCase):
    """
    Test the check_token_list from lib.token on an interface level
    """

    def test_00_create_realms(self):
        self.setUp_user_realms()
        # Set a policy to change the pin every 10d
        set_policy("every10d", scope=SCOPE.ENROLL, action="{0!s}=10d".format(PolicyAction.CHANGE_PIN_EVERY))
        # set policy for chalresp
        set_policy("chalresp", scope=SCOPE.AUTH, action="{0!s}=hotp".format(PolicyAction.CHALLENGERESPONSE))
        # Change PIN via validate
        set_policy("viaValidate", scope=SCOPE.AUTH, action=PolicyAction.CHANGE_PIN_VIA_VALIDATE)

    def test_01_successfully_change_pin(self):
        """
        Authentication per challenge response with an HOTP token and then
        do a successful PIN reset
        """
        g = FakeFlaskG()
        g.client_ip = "10.0.0.1"
        g.policy_object = PolicyClass()
        g.audit_object = FakeAudit()
        user_obj = User("cornelius", realm=self.realm1)
        # remove all tokens of cornelius
        remove_token(user=user_obj)
        tok = init_token({"type": "hotp",
                          "otpkey": self.otpkey, "pin": "test",
                          "serial": "PINCHANGE"}, tokenrealms=["r1"], user=user_obj)
        tok2 = init_token({"type": "hotp",
                           "otpkey": self.otpkey, "pin": "fail",
                           "serial": "NOTNEEDED"}, tokenrealms=["r1"], user=user_obj)
        # Set, that the token needs to change the pin
        tok.set_next_pin_change("-1d")
        # Check it
        self.assertTrue(tok.is_pin_change())

        # Trigger the first auth challenge by sending the PIN
        r, reply_dict = check_token_list([tok, tok2], "test", user=user_obj, options={"g": g})
        self.assertFalse(r)
        self.assertEqual('please enter otp: ', reply_dict.get("message"))
        transaction_id = reply_dict.get("transaction_id")

        # Now send the correct OTP value
        r, reply_dict = check_token_list([tok, tok2], self.valid_otp_values[1], user=user_obj,
                                         options={"transaction_id": transaction_id,
                                                  "g": g})
        self.assertFalse(r)
        self.assertEqual("Please enter a new PIN", reply_dict.get("message"))
        transaction_id = reply_dict.get("transaction_id")
        self.assertEqual("interactive", reply_dict.get('multi_challenge')[0].get('client_mode'))

        # Now send a new PIN
        newpin = "test2"
        r, reply_dict = check_token_list([tok, tok2], newpin, user=user_obj,
                                         options={"transaction_id": transaction_id,
                                                  "g": g})
        self.assertFalse(r)
        self.assertEqual("Please enter the new PIN again", reply_dict.get("message"))
        transaction_id = reply_dict.get("transaction_id")

        # Now send the new PIN a 2nd time
        r, reply_dict = check_token_list([tok, tok2], newpin, user=user_obj,
                                         options={"transaction_id": transaction_id,
                                                  "g": g})
        self.assertTrue(r)
        self.assertEqual("PIN successfully set.", reply_dict.get("message"))

        self.assertFalse(tok.is_pin_change())

        # Run an authentication with the new PIN
        r, reply_dict = check_token_list([tok, tok2], "{0!s}{1!s}".format(newpin, self.valid_otp_values[2]),
                                         user=user_obj, options={"g": g})
        self.assertTrue(r)
        self.assertFalse(reply_dict.get("pin_change"))
        self.assertTrue("next_pin_change" in reply_dict)

    def test_02_failed_change_pin(self):
        """
        Authentication with an HOTP token and then fail to
        change pin, since we present two different PINs.
        """
        g = FakeFlaskG()
        g.client_ip = "10.0.0.1"
        g.policy_object = PolicyClass()
        g.audit_object = FakeAudit()
        user_obj = User("cornelius", realm=self.realm1)
        # remove all tokens of cornelius
        remove_token(user=user_obj)
        tok = init_token({"type": "hotp",
                          "otpkey": self.otpkey, "pin": "test",
                          "serial": "PINCHANGE"}, tokenrealms=["r1"], user=user_obj)
        tok2 = init_token({"type": "hotp",
                           "otpkey": self.otpkey, "pin": "fail",
                           "serial": "NOTNEEDED"}, tokenrealms=["r1"], user=user_obj)
        # Set, that the token needs to change the pin
        tok.set_next_pin_change("-1d")
        # Check it
        self.assertTrue(tok.is_pin_change())

        # successfully authenticate, but thus trigger a PIN change
        r, reply_dict = check_token_list([tok, tok2], "test{0!s}".format(self.valid_otp_values[1]),
                                         user=user_obj, options={"g": g})
        self.assertFalse(r)
        self.assertEqual("Please enter a new PIN", reply_dict.get("message"))
        transaction_id = reply_dict.get("transaction_id")

        # Now send a new PIN
        newpin = "test2"
        r, reply_dict = check_token_list([tok, tok2], newpin, user=user_obj,
                                         options={"transaction_id": transaction_id,
                                                  "g": g})
        self.assertFalse(r)
        self.assertEqual("Please enter the new PIN again", reply_dict.get("message"))
        transaction_id = reply_dict.get("transaction_id")

        # Now send the new PIN a 2nd time
        r, reply_dict = check_token_list([tok, tok2], "falsePIN", user=user_obj,
                                         options={"transaction_id": transaction_id,
                                                  "g": g})
        self.assertFalse(r)
        self.assertEqual("PINs do not match", reply_dict.get("message"))

        # The PIN still needs to be changed!
        self.assertTrue(tok.is_pin_change())

    def test_03_failed_change_pin(self):
        """
        Authentication with an HOTP token and then fail to
        change pin, since we do not comply to the PIN policies :-)
        """
        g = FakeFlaskG()
        g.client_ip = "10.0.0.1"
        g.policy_object = PolicyClass()
        g.audit_object = FakeAudit()
        user_obj = User("cornelius", realm=self.realm1)
        # remove all tokens of cornelius
        remove_token(user=user_obj)
        tok = init_token({"type": "hotp",
                          "otpkey": self.otpkey, "pin": "test",
                          "serial": "PINCHANGE"}, tokenrealms=["r1"], user=user_obj)
        tok2 = init_token({"type": "hotp",
                           "otpkey": self.otpkey, "pin": "fail",
                           "serial": "NOTNEEDED"}, tokenrealms=["r1"], user=user_obj)
        # Set, that the token needs to change the pin
        tok.set_next_pin_change("-1d")
        # Check it
        self.assertTrue(tok.is_pin_change())
        # Require minimum length of 5
        set_policy("minpin", scope=SCOPE.USER, action="{0!s}=5".format(PolicyAction.OTPPINMINLEN))

        # successfully authenticate, but thus trigger a PIN change
        r, reply_dict = check_token_list([tok, tok2], "test{0!s}".format(self.valid_otp_values[1]),
                                         user=user_obj, options={"g": g})
        self.assertFalse(r)
        self.assertEqual("Please enter a new PIN", reply_dict.get("message"))
        transaction_id = reply_dict.get("transaction_id")

        # Now send a new PIN, which has only length 4 :-/
        newpin = "test"
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=DeprecationWarning)
            self.assertRaisesRegex(
                PolicyError, "The minimum OTP PIN length is 5", check_token_list,
                [tok, tok2], newpin, user=user_obj,
                options={"transaction_id": transaction_id,
                         "g": g})

        delete_policy("minpin")
