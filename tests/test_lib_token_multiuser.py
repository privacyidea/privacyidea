# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for tokens that are assigned to multiple users."""
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
class TestMultipleUserToken(MyTestCase):
    def test_01_user_with_multiple_token(self):
        self.setUp_user_realms()
        user = User(login="cornelius", realm=self.realm1)
        init_token({"serial": "s1", "otpkey": OTPKEY, "type": "HOTP"},
                   user=user)
        init_token({"serial": "s2", "otpkey": OTPKE2, "type": "HOTP"},
                   user=user)
        # To test whether the password caching works, we need to set the otppin policy to userstore
        set_policy("otppin", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=userstore")

        self.set_default_g_variables()
        self.app_context.g.policy_object = PolicyClass()
        self.app_context.g.audit_object = FakeAudit()
        options = {"g": self.app_context.g}

        logging.getLogger('privacyidea.lib.user').setLevel(logging.DEBUG)

        # First we try authentication with a wrong password
        with LogCapture(level=logging.DEBUG) as lc:
            res, res_data = check_user_pass(user, "wrong122334", options=options)
            self.assertFalse(res)
            self.assertEqual("wrong otp pin", res_data["message"], res_data)
            # There should be two failed password checks, one regular and one from cache
            lc.check_present(
                (
                    'privacyidea.lib.user', 'INFO',
                    "User cornelius from realm realm1 tries to authenticate"),
                (
                    'privacyidea.lib.resolvers.PasswdIdResolver', 'WARNING',
                    'user uid 1000 failed to authenticate'),
                (
                    'privacyidea.lib.user', 'INFO',
                    'User <cornelius.resolver1@realm1> failed to authenticate.'),
                (
                    'privacyidea.lib.user', 'INFO',
                    "User <cornelius.resolver1@realm1> failed to authenticate from request cache."))
            # Check that we have the password check of the resolver only once
            resolver_logs = [x for x in lc.records if x.msg == "user uid 1000 failed to authenticate"]
            self.assertEqual(1, len(resolver_logs), resolver_logs)

        # Now try authentication with the correct password and OTP
        with LogCapture(level=logging.DEBUG) as lc:
            res, res_data = check_user_pass(user, "test122334", options=options)
            self.assertTrue(res)
            self.assertEqual("s2", res_data["serial"], res_data)
            self.assertEqual("matching 1 tokens", res_data["message"], res_data)
            # There should be two successful password checks, one regular and one from cache
            lc.check_present(
                (
                    'privacyidea.lib.user', 'INFO',
                    "User cornelius from realm realm1 tries to authenticate"),
                (
                    'privacyidea.lib.resolvers.PasswdIdResolver', 'INFO',
                    'successfully authenticated user uid 1000'),
                (
                    'privacyidea.lib.user', 'DEBUG',
                    'Successfully authenticated user <cornelius.resolver1@realm1>.'),
                (
                    'privacyidea.lib.user', 'DEBUG',
                    "Successfully authenticated user <cornelius.resolver1@realm1> from request cache."))
            # Check that we have the password check of the resolver only once
            resolver_logs = [x for x in lc.records if x.msg == "successfully authenticated user uid 1000"]
            self.assertEqual(1, len(resolver_logs), resolver_logs)

        # Now we enable the challenge-response policy for HOTP token
        set_policy("chalresp", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")

        # First we try again with a wrong password
        with LogCapture(level=logging.DEBUG) as lc:
            res, res_data = check_user_pass(user, "wrong", options=options)
            self.assertFalse(res)
            self.assertEqual("wrong otp pin", res_data["message"], res_data)
            # There should be two failed password checks, one regular and one from cache.
            # Since the wrong password is too short, the direct authentication
            # isn't even attempted since the split into PIN and OTP fails.
            lc.check_present(
                (
                    'privacyidea.lib.user', 'INFO',
                    "User cornelius from realm realm1 tries to authenticate"),
                (
                    'privacyidea.lib.resolvers.PasswdIdResolver', 'WARNING',
                    'user uid 1000 failed to authenticate'),
                (
                    'privacyidea.lib.user', 'INFO',
                    'User <cornelius.resolver1@realm1> failed to authenticate.'),
                (
                    'privacyidea.lib.user', 'INFO',
                    "User <cornelius.resolver1@realm1> failed to authenticate from request cache."))
            # Check that we have the password check of the resolver only once
            resolver_logs = [x for x in lc.records if x.msg == "user uid 1000 failed to authenticate"]
            self.assertEqual(1, len(resolver_logs), resolver_logs)

        # Now we try again with a long wrong password
        with LogCapture(level=logging.DEBUG) as lc:
            res, res_data = check_user_pass(user, "wrong_password", options=options)
            self.assertFalse(res)
            self.assertEqual("wrong otp pin", res_data["message"], res_data)
            # There should be four failed password checks, two regular and two from cache.
            # For the direct authentication the long password is split and tested as well.
            lc.check_present(
                (
                    'privacyidea.lib.user', 'INFO',
                    "User cornelius from realm realm1 tries to authenticate"),
                (
                    'privacyidea.lib.resolvers.PasswdIdResolver', 'WARNING',
                    'user uid 1000 failed to authenticate'),
                (
                    'privacyidea.lib.user', 'INFO',
                    'User <cornelius.resolver1@realm1> failed to authenticate.'),
                (
                    'privacyidea.lib.resolvers.PasswdIdResolver', 'WARNING',
                    'user uid 1000 failed to authenticate'),
                (
                    'privacyidea.lib.user', 'INFO',
                    'User <cornelius.resolver1@realm1> failed to authenticate.'),
                (
                    'privacyidea.lib.user', 'INFO',
                    "User <cornelius.resolver1@realm1> failed to authenticate from request cache."),
                (
                    'privacyidea.lib.user', 'INFO',
                    "User <cornelius.resolver1@realm1> failed to authenticate from request cache."))
            # Check that we have the password check of the resolver only once
            resolver_logs = [x for x in lc.records if x.msg == "user uid 1000 failed to authenticate"]
            self.assertEqual(2, len(resolver_logs), resolver_logs)

        # Now we try with a correct password to trigger the challenge
        with LogCapture(level=logging.DEBUG) as lc:
            res, res_data = check_user_pass(user, "test", options=options)
            self.assertFalse(res)
            # Check that both token were triggered
            self.assertEqual("please enter otp: ", res_data["message"], res_data)
            self.assertEqual(2, len(res_data["multi_challenge"]), res_data)
            transaction_id = res_data["multi_challenge"][0]["transaction_id"]
            # We should have two password check log entries, one regular and on from cache
            lc.check_present(
                (
                    'privacyidea.lib.user', 'INFO',
                    "User cornelius from realm realm1 tries to authenticate"),
                (
                    'privacyidea.lib.resolvers.PasswdIdResolver', 'INFO',
                    'successfully authenticated user uid 1000'),
                (
                    'privacyidea.lib.user', 'DEBUG',
                    'Successfully authenticated user <cornelius.resolver1@realm1>.'),
                (
                    'privacyidea.lib.user', 'DEBUG',
                    "Successfully authenticated user <cornelius.resolver1@realm1> from request cache."))
            # Check that we have the password check of the resolver only once
            resolver_logs = [x for x in lc.records if x.msg == "successfully authenticated user uid 1000"]
            self.assertEqual(1, len(resolver_logs), resolver_logs)

        # Remove challenges from the database to avoid confusion
        db.session.execute(Challenge.__table__.delete().where(Challenge.transaction_id == transaction_id))
        db.session.commit()

        # Now try to authenticate with a correct password and OTP
        with LogCapture(level=logging.DEBUG) as lc:
            res, res_data = check_user_pass(user, "test410478", options=options)
            self.assertTrue(res)
            # Check that the authentication was successful with token s2
            self.assertEqual("matching 1 tokens", res_data["message"], res_data)
            self.assertEqual("s2", res_data["serial"], res_data)
            # We should have four password check log entries, two regular and on two from cache
            lc.check_present(
                (
                    'privacyidea.lib.user', 'INFO',
                    "User cornelius from realm realm1 tries to authenticate"),
                (
                    'privacyidea.lib.resolvers.PasswdIdResolver', 'WARNING',
                    'user uid 1000 failed to authenticate'),
                (
                    'privacyidea.lib.user', 'INFO',
                    'User <cornelius.resolver1@realm1> failed to authenticate.'),
                (
                    'privacyidea.lib.resolvers.PasswdIdResolver', 'INFO',
                    'successfully authenticated user uid 1000'),
                (
                    'privacyidea.lib.user', 'DEBUG',
                    'Successfully authenticated user <cornelius.resolver1@realm1>.'),
                (
                    'privacyidea.lib.user', 'INFO',
                    "User <cornelius.resolver1@realm1> failed to authenticate from request cache."),
                (
                    'privacyidea.lib.user', 'DEBUG',
                    "Successfully authenticated user <cornelius.resolver1@realm1> from request cache."))
            # We now have two password checks in the resolver, one failed (with OTP) and one successful
            resolver_logs = [x for x in lc.records if x.name == "privacyidea.lib.resolvers.PasswdIdResolver"]
            self.assertEqual(4, len(resolver_logs), resolver_logs)

        # Now set the force_challenge_response policy and try again.
        # We should only have on password check
        set_policy("force_chalresp", scope=SCOPE.AUTH, action=f"{PolicyAction.FORCE_CHALLENGE_RESPONSE}")

        with LogCapture(level=logging.DEBUG) as lc:
            res, res_data = check_user_pass(user, "test376074", options=options)
            self.assertFalse(res, res_data)
            # We should have four password check log entries, two regular and on two from cache
            lc.check_present(
                (
                    'privacyidea.lib.user', 'INFO',
                    "User cornelius from realm realm1 tries to authenticate"),
                (
                    'privacyidea.lib.resolvers.PasswdIdResolver', 'WARNING',
                    'user uid 1000 failed to authenticate'),
                (
                    'privacyidea.lib.user', 'INFO',
                    'User <cornelius.resolver1@realm1> failed to authenticate.'),
                (
                    'privacyidea.lib.token',
                    'INFO',
                    'Skipping authentication try for token s1 because policy '
                    'force_challenge_response is set.'),
                (
                    'privacyidea.lib.user', 'INFO',
                    "User <cornelius.resolver1@realm1> failed to authenticate from request cache."))
            # We now have two password checks in the resolver, one failed (with OTP) and one successful
            resolver_logs = [x for x in lc.records if x.msg == "user uid 1000 failed to authenticate"]
            self.assertEqual(1, len(resolver_logs), resolver_logs)

        delete_policy("otppin")
        delete_policy("chalresp")
        delete_policy("force_chalresp")
        remove_token("s1")
        remove_token("s2")
        self.set_default_g_variables()
