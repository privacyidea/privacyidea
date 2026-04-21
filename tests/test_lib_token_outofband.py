# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for out-of-band token flows (challenge/response via a separate channel)."""
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
class TokenOutOfBandTestCase(MyTestCase):

    def test_00_create_realms(self):
        self.setUp_user_realms()

    def test_01_failcounter_no_increase(self):
        # The fail counter for tiqr tokens will not increase, since this
        # is a tokenmode outofband.
        user = User(login="cornelius", realm=self.realm1)
        pin1 = "pin1"
        token1 = init_token({"serial": pin1, "pin": pin1,
                             "type": "tiqr", "genkey": 1}, user=user)

        r = token1.get_failcount()
        self.assertEqual(r, 0)

        r, r_dict = check_token_list([token1], pin1, user=user, options={})
        self.assertFalse(r, r_dict)
        transaction_id = r_dict.get("transaction_id")

        # Now we check the status of the challenge several times and verify that the
        # failcounter is not increased:
        for i in range(1, 10):
            r, r_dict = check_token_list([token1], "", user=user,
                                         options={"transaction_id": transaction_id})
            self.assertFalse(r, r_dict)
            self.assertEqual(r_dict.get("type"), "tiqr", r_dict)

        r = token1.get_failcount()
        self.assertEqual(r, 0)

        # Now set the challenge to be answered and recheck:
        Challenge.query.filter(Challenge.transaction_id == transaction_id).update({"otp_valid": True})
        r, r_dict = check_token_list([token1], "", user=user, options={"transaction_id": transaction_id})
        self.assertTrue(r, r_dict)
        self.assertEqual(r_dict.get("message"), "Found matching challenge", r_dict)

        remove_token(pin1)
