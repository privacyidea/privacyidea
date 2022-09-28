# -*- coding: utf-8 -*-
"""
This test file tests the lib.token methods.

The lib.token depends on the DB model and lib.user and
all lib.tokenclasses

This tests the token functions on an interface level

We start with simple database functions:

getTokens4UserOrSerial
gettokensoftype
getToken....
"""
from .base import MyTestCase, FakeAudit, FakeFlaskG
from privacyidea.lib.user import (User)
from privacyidea.lib.tokenclass import TokenClass, TOKENKIND, FAILCOUNTER_EXCEEDED, FAILCOUNTER_CLEAR_TIMEOUT
from privacyidea.lib.token import weigh_token_type
from privacyidea.lib.tokens.totptoken import TotpTokenClass
from privacyidea.models import (Token, Challenge, TokenRealm)
from privacyidea.lib.config import (set_privacyidea_config, get_token_types, delete_privacyidea_config, SYSCONF)
from privacyidea.lib.policy import set_policy, SCOPE, ACTION, delete_policy, PolicyClass, delete_policy
from privacyidea.lib.utils import b32encode_and_unicode, hexlify_and_unicode
from privacyidea.lib.error import PolicyError
import datetime
from dateutil import parser
import hashlib
import binascii
import warnings
from privacyidea.lib.token import (create_tokenclass_object,
                                   get_tokens,
                                   get_token_type, check_serial,
                                   get_num_tokens_in_realm,
                                   get_realms_of_token,
                                   token_exist, get_token_owner, is_token_owner,
                                   get_tokenclass_info,
                                   get_tokens_in_resolver, get_otp,
                                   get_token_by_otp, get_serial_by_otp,
                                   gen_serial, init_token, remove_token,
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
                                   get_tokens_paginated_generator)

from privacyidea.lib.error import (TokenAdminError, ParameterError,
                                   privacyIDEAError, ResourceNotFoundError)
from privacyidea.lib.tokenclass import DATE_FORMAT
from dateutil.tz import tzlocal

from privacyidea.lib.tokengroup import set_tokengroup, delete_tokengroup, get_tokengroups
from privacyidea.models import Tokengroup


class TokenTestCase(MyTestCase):

    def test_01_create_tokengroup(self):

        r = set_tokengroup("gruppe1", "my first typo")
        self.assertGreaterEqual(r, 1)
        tg = Tokengroup.query.filter_by(id=r).first()
        self.assertEqual(tg.Description, "my first typo")

        r = set_tokengroup("gruppe1", "my first group")
        self.assertGreaterEqual(r, 1)
        tg = Tokengroup.query.filter_by(id=r).first()
        self.assertEqual(tg.Description, "my first group")

    def test_02_delete_tokengroup(self):
        r = set_tokengroup("gruppe1", "my first group")
        self.assertGreaterEqual(r, 1)

        delete_tokengroup("gruppe1")
        tg = Tokengroup.query.filter_by(name="gruppe1").all()
        self.assertEqual(len(tg), 0)

        r = set_tokengroup("gruppe1", "my other first group")
        self.assertGreaterEqual(r, 1)

        delete_tokengroup(id=r)
        tg = Tokengroup.query.filter_by(name="gruppe1").all()
        self.assertEqual(len(tg), 0)

        self.assertRaises(privacyIDEAError, delete_tokengroup)

    def test_03_get_tokengroups(self):
        r1 = set_tokengroup("gruppe1", "my first group")
        self.assertGreaterEqual(r1, 1)

        r2 = set_tokengroup("gruppe2", "my 2nd group")
        self.assertGreater(r2, r1)

        tgroups = get_tokengroups()
        self.assertEqual(len(tgroups), 2)

        tgroups = get_tokengroups(name="gruppe1")
        self.assertEqual(len(tgroups), 1)

        tgroups = get_tokengroups(id=r2)
        self.assertEqual(len(tgroups), 1)

        self.assertEqual(tgroups[0].name, "gruppe2")





