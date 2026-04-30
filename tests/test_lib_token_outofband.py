# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for out-of-band token flows (challenge/response via a separate channel)."""

from privacyidea.lib.token import (init_token,
                                   check_token_list, remove_token)
from privacyidea.lib.user import (User)
from privacyidea.models import (Challenge)
from .base import MyTestCase

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
