# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for exporting tokens and re-encrypting them with a new key."""

from unittest import mock

from privacyidea.lib.error import ParameterError, ResourceNotFoundError, TokenAdminError
from privacyidea.lib.token import (export_tokens, get_one_token, get_tokens, init_token,
                                   update_token_from_export)
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.tokens.motptoken import MotpTokenClass
from privacyidea.lib.tokens.radiustoken import RadiusTokenClass
from privacyidea.lib.tokens.remotetoken import RemoteTokenClass
from privacyidea.lib.tokens.vascotoken import VascoTokenClass
from privacyidea.lib.tokens.yubicotoken import YubicoTokenClass
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


class ExportUnsupportedTokenTypesTestCase(MyTestCase):

    def test_01_unsupported_token_types_refuse_the_export(self):
        for token_class in (MotpTokenClass, RadiusTokenClass, RemoteTokenClass, VascoTokenClass, YubicoTokenClass):
            with self.subTest(token_class=token_class.__name__):
                with self.assertRaisesRegex(NotImplementedError, "is not supported"):
                    token_class.export_token(None, export_user=True)

        token = init_token({"serial": "EXPMOTP", "type": "motp", "otpkey": "1234567890abcdef", "motppin": "1234"})
        with self.assertLogs("privacyidea.lib.token.importexport", level="ERROR") as logs:
            result = export_tokens([token], export_user=True)
        self.assertEqual(["EXPMOTP"], result.failed_tokens)
        self.assertIn("Export for mOTP token is not supported.", logs.output[0])
        token.delete_token()


class UpdateTokenFromExportTestCase(MyTestCase):

    def test_01_counters_come_back_when_the_update_fails(self):
        token = init_token({"type": "hotp", "serial": "UPDFAIL", "otpkey": OTPKEY})
        token.token.count = 42
        token.token.failcount = 3
        token.token.save()
        entry = token._to_dict()

        def reset_and_fail(self, param, reset_failcount=True):
            # Resetting the counters and then failing, as a real update() can
            self.token.count = 0
            self.token.failcount = 0
            self.token.save()
            raise TokenAdminError("update failed")

        with mock.patch.object(TokenClass, "update", reset_and_fail):
            with self.assertRaises(TokenAdminError):
                update_token_from_export(entry)
        token = get_one_token(serial="UPDFAIL")
        self.assertEqual(42, token.token.count)
        self.assertEqual(3, token.token.failcount)
        token.delete_token()

    def test_02_entry_without_serial_or_unknown_serial(self):
        token = init_token({"type": "hotp", "serial": "UPDOTHER", "otpkey": OTPKEY})
        entry = token._to_dict()
        # Without a serial no token is touched, although a lookup without a serial would find all of them
        entry_without_serial = {key: value for key, value in entry.items() if key != "serial"}
        entry_without_serial["otpkey"] = OTPKE2
        with self.assertRaises(ParameterError):
            update_token_from_export(entry_without_serial)
        self.assertEqual(OTPKEY, get_one_token(serial="UPDOTHER").token.get_otpkey().getKey().decode())

        with self.assertRaises(ResourceNotFoundError):
            update_token_from_export({**entry, "serial": "DOESNOTEXIST"})

        # An entry without an owner is fine
        entry.pop("owner", None)
        self.assertEqual("UPDOTHER", update_token_from_export(entry))
        token.delete_token()


    def test_03_failed_update_does_not_write_the_entry_halfway(self):
        token = init_token({"type": "hotp", "serial": "UPDHALF", "otpkey": OTPKEY, "description": "old"})
        token.token.count = 7
        token.token.save()
        entry = token._to_dict()
        entry["otpkey"] = OTPKE2
        entry["description"] = "new"
        # The OTP length is set after the key and the description and makes the update fail
        entry["otplen"] = "six"
        with self.assertRaises(ValueError):
            update_token_from_export(entry)
        token = get_one_token(serial="UPDHALF")
        self.assertEqual(OTPKEY, token.token.get_otpkey().getKey().decode())
        self.assertEqual("old", token.token.description)
        self.assertEqual(6, token.token.otplen)
        self.assertEqual(7, token.token.count)
        token.delete_token()

    def test_04_counter_that_is_not_a_number(self):
        token = init_token({"type": "hotp", "serial": "UPDCOUNTER", "otpkey": OTPKEY})
        token.token.count = 7
        token.token.save()
        entry = token._to_dict()
        entry["otpkey"] = OTPKE2
        entry["counter"] = "seven"
        with self.assertRaisesRegex(ParameterError, "The counter 'seven' of the entry is not a number"):
            update_token_from_export(entry)
        # The token is not changed
        token = get_one_token(serial="UPDCOUNTER")
        self.assertEqual(OTPKEY, token.token.get_otpkey().getKey().decode())
        self.assertEqual(7, token.token.count)

        # A higher counter of the entry is taken, a lower one is not
        entry["counter"] = "9"
        update_token_from_export(entry)
        self.assertEqual(9, get_one_token(serial="UPDCOUNTER").token.count)
        entry["counter"] = 3
        update_token_from_export(entry)
        self.assertEqual(9, get_one_token(serial="UPDCOUNTER").token.count)
        token.delete_token()
