# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for exporting tokens and re-encrypting them with a new key."""

from privacyidea.lib.token import (get_tokens, init_token)
from .base import MyTestCase

PWFILE = "tests/testdata/passwords"
OTPKEY = "3132333435363738393031323334353637383930"
OTPKE2 = "31323334353637383930313233343536373839AA"
CHANGED_KEY = '31323334353637383930313233343536373839AA'


class ExportAndReencryptTestCase(MyTestCase):

    def test_00_create_tokens(self):

        tokens = [
            ("ser1", "hotp", self.otpkey),
            ("ser2", "totp", self.otpkey),
            ("ser3", "totp", self.otpkey)
        ]

        for t in tokens:
            init_token({"type": t[1],
                        "serial": t[0],
                        "otpkey": t[2],
                        "timeStep": 60})

        # export tokens
        token_dicts = []
        token_objects = get_tokens()
        for tok in token_objects:
            d = tok._to_dict()
            self.assertIn(d.get("type"), ["hotp", "totp"])
            self.assertEqual(self.otpkey, d.get("otpkey"))
            # Change the OTPKey
            d["otpkey"] = CHANGED_KEY
            # Change the timestep
            d["timeStep"] = 30
            token_dicts.append(d)

        # Update the otpkey
        for t in token_dicts:
            token_obj = get_tokens(serial=t.get("serial"))[0]
            # The .update() would re-save the otpkey with the new HSM.
            token_obj.update(t)

        # check for the new otpkey
        token_objects = get_tokens()
        for tok in token_objects:
            d = tok._to_dict()
            # Check that "reencryption" worked
            self.assertEqual(CHANGED_KEY, d.get("otpkey"))
            # Also check, that the tokeninfo for TOTP was updated
            if d.get("type") == "totp":
                tokeninfo = d.get("info_list")
                self.assertEqual("30", tokeninfo.get("timeStep"), d)
