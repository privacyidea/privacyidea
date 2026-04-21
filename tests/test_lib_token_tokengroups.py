# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for assigning tokens to tokengroups and managing tokengroup membership."""
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
class TokenGroupTestCase(MyTestCase):

    @log_capture()
    def test_01_add_tokengroups(self, capture):
        # Create tokens
        serials = ["s1", "s2"]
        for s in serials:
            init_token({"serial": s, "type": "spass"})

        # create tokengroups
        groups = [("g1", "Test A"), ("g2", "test B")]
        for g in groups:
            set_tokengroup(g[0], g[1])

        assign_tokengroup("s1", "g1")
        assign_tokengroup("s1", "g2")
        assign_tokengroup("s2", "g2")

        # Check the tokengroups of the first token
        tok1 = get_one_token(serial="s1")
        self.assertSetEqual({"g1", "g2"}, {tg.name for tg in tok1.token.tokengroup_list})

        # check the tokengroups of the 2nd token
        tok2 = get_one_token(serial="s2")
        self.assertSetEqual({"g2"}, {tg.name for tg in tok2.token.tokengroup_list})

        # Try to add an already added group
        logger = logging.getLogger('privacyidea.lib.tokenclass')
        logger.setLevel(logging.DEBUG)
        assign_tokengroup("s1", "g1")
        expected_message = "Token s1 is already assigned to tokengroup g1."
        actual_messages = [record.getMessage() for record in capture.records]
        self.assertIn(expected_message, actual_messages, msg=f"Available log messages: {actual_messages}")

        # Try to add non-existing group
        with self.assertRaises(ResourceNotFoundError) as exception:
            assign_tokengroup("s1", "random")
        self.assertEqual("The tokengroup does not exist.", exception.exception.message)
        expected_message = "Tokengroup random does not exist. Cannot add it to token s1."
        actual_messages = [record.getMessage() for record in capture.records]
        self.assertIn(expected_message, actual_messages, msg=f"Available log messages: {actual_messages}")

        # Test a missing group information
        self.assertRaises(ResourceNotFoundError, assign_tokengroup, "s1")

        # list tokengroup assignments
        grouplist = list_tokengroups()
        self.assertEqual(len(grouplist), 3)
        # one token in group1
        grouplist = list_tokengroups("g1")
        self.assertEqual(len(grouplist), 1)
        group_g1 = db.session.scalar(select(Tokengroup).where(Tokengroup.name == "g1"))
        self.assertEqual(1, len(group_g1.tokens))
        self.assertEqual("s1", group_g1.tokens[0].serial)
        # two tokens in group2
        grouplist = list_tokengroups("g2")
        self.assertEqual(len(grouplist), 2)

        # Remove tokengroup "g1" from token "s1"
        tok1.delete_tokengroup("g1")
        # Only the 2nd group remains
        self.assertEqual(tok1.token.tokengroup_list[0].name, "g2")
        # Remove it from token "s2"
        unassign_tokengroup("s2", "g2")
        tok2 = get_one_token(serial="s2")
        self.assertEqual(len(tok2.token.tokengroup_list), 0)

        # Check that deleting a tokengroup with tokens still assigned results in an error
        self.assertRaises(PrivacyIDEAError, delete_tokengroup, name='g2')

        # Remove all tokengroups from token "s1"
        tok1.delete_tokengroup()
        self.assertEqual(len(tok1.token.tokengroup_list), 0)

        # Cleanup
        for s in serials:
            remove_token(s)
        delete_tokengroup('g1')
        delete_tokengroup('g2')

    @log_capture()
    def test_02_set_token_groups(self, capture):
        # Create token
        token = init_token({"serial": "s1", "type": "spass"})

        # create token groups
        groups = [("g1", "Test A"), ("g2", "test B"), ("g3", "test C")]
        for g in groups:
            set_tokengroup(g[0], g[1])

        # Set two groups
        set_tokengroups("s1", ["g1", "g2"])
        token = get_one_token(serial="s1")
        self.assertSetEqual({"g1", "g2"}, {tg.name for tg in token.token.tokengroup_list})

        # Set one different group
        set_tokengroups("s1", ["g3", "g1"])
        token = get_one_token(serial="s1")
        self.assertSetEqual({"g1", "g3"}, {tg.name for tg in token.token.tokengroup_list})

        # Set empty list removes all groups
        set_tokengroups("s1", [])
        token = get_one_token(serial="s1")
        self.assertSetEqual(set(), {tg.name for tg in token.token.tokengroup_list})

        # Set non-existing group
        set_tokengroups("s1", ["random", "g2"])
        token = get_one_token(serial="s1")
        self.assertSetEqual({"g2"}, {tg.name for tg in token.token.tokengroup_list})
        expected_message = "Tokengroup random does not exist. Cannot add it to token s1."
        actual_messages = [record.getMessage() for record in capture.records]
        self.assertIn(expected_message, actual_messages, msg=f"Available log messages: {actual_messages}")

        token.delete_token()
        delete_tokengroup('g1')
        delete_tokengroup('g2')
        delete_tokengroup('g3')

    def test_03_delete_token_group(self):
        # Create token
        token = init_token({"serial": "s1", "type": "spass"})

        # create token groups
        g1_id = set_tokengroup("g1", "Test A")
        g2_id = set_tokengroup("g2", "Test B")
        g3_id = set_tokengroup("g3", "Test C")

        # Set two groups
        set_tokengroups("s1", ["g1", "g2"])
        token = get_one_token(serial="s1")
        self.assertSetEqual({"g1", "g2"}, {tg.name for tg in token.token.tokengroup_list})

        # delete one group by name
        unassign_tokengroup("s1", tokengroup="g1")
        token = get_one_token(serial="s1")
        self.assertSetEqual({"g2"}, {tg.name for tg in token.token.tokengroup_list})

        # delete one token by id
        unassign_tokengroup("s1", tokengroup_id=g2_id)
        token = get_one_token(serial="s1")
        self.assertSetEqual(set(), {tg.name for tg in token.token.tokengroup_list})

        # Set two groups
        set_tokengroups("s1", ["g1", "g2"])
        token = get_one_token(serial="s1")
        self.assertSetEqual({"g1", "g2"}, {tg.name for tg in token.token.tokengroup_list})

        # Remove all groups
        unassign_tokengroup("s1")
        token = get_one_token(serial="s1")
        self.assertSetEqual(set(), {tg.name for tg in token.token.tokengroup_list})

        token.delete_token()
        delete_tokengroup('g1')
        delete_tokengroup('g2')
        delete_tokengroup('g3')
