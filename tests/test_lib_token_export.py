# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for exporting tokens and re-encrypting them with a new key."""

import os
import tempfile
from unittest import mock

import yaml

from privacyidea.lib.error import ParameterError, ResourceNotFoundError, TokenAdminError
from privacyidea.lib.token import (export_tokens, get_one_token, get_tokens, init_token, remove_token,
                                   revoke_token, update_token_from_export)
from privacyidea.lib.crypto import geturandom
from privacyidea.lib.framework import get_app_local_store
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.tokenrolloutstate import RolloutState
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

    def test_01_nothing_changes_when_the_update_fails(self):
        token = init_token({"type": "hotp", "serial": "UPDFAIL", "otpkey": OTPKEY})
        token.token.count = 42
        token.token.failcount = 3
        token.token.save()
        entry = token._to_dict()
        entry["otpkey"] = OTPKE2
        entry["info_list"] = {"secret": "value", "secret.type": "password"}

        # Writing the encrypted token info fails after the OTP key, which resets the OTP counter, was set
        with mock.patch("privacyidea.lib.token.importexport._write_tokeninfo_of_locked_token",
                        side_effect=TokenAdminError("update failed")):
            with self.assertRaises(TokenAdminError):
                update_token_from_export(entry)
        token = get_one_token(serial="UPDFAIL")
        self.assertEqual(OTPKEY, token.token.get_otpkey().getKey().decode())
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


class UpdateFromExportReencryptsTestCase(MyTestCase):
    """
    The token janitors' update writes an export entry back like an import does: after a change of the encryption key,
    every token keeps its secrets (readable with the new key) and its state. No token type fails for want of an
    enrollment parameter, and no token gets a new TAN list, registration code or OCRA suite, or is set to wait for a
    registration.
    """
    sshkey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAm1Bt4KKcsm4aCFCZ2ySYGsJPuyJgEz5pHcPUbkdsWo user@host"

    def setUp(self) -> None:
        super().setUp()
        self.serials = []
        self._add(init_token({"type": "hotp", "serial": "RK_HOTP", "otpkey": OTPKEY}))
        self._add(init_token({"type": "tan", "serial": "RK_TAN", "otpkey": OTPKEY, "tans": "tan01 tan02 tan03"}))
        self._add(init_token({"type": "registration", "serial": "RK_REG"}))
        self._add(init_token({"type": "ocra", "serial": "RK_OCRA", "otpkey": OTPKEY,
                              "ocrasuite": "OCRA-1:HOTP-SHA1-6:QN08"}))
        self._add(init_token({"type": "sshkey", "serial": "RK_SSH", "sshkey": self.sshkey}))
        self._add(init_token({"type": "email", "serial": "RK_MAIL", "otpkey": OTPKEY, "email": "a@example.com"}))
        self._add(init_token({"type": "motp", "serial": "RK_MOTP", "otpkey": "1234567890abcdef", "motppin": "1234"}))
        passkey = init_token({"type": "passkey", "serial": "RK_PASSKEY"})
        # An enrolled passkey: the OTP key holds the credential id
        passkey.token.set_otpkey("bG9uZy1jcmVkZW50aWFsLWlk")
        passkey.token.rollout_state = RolloutState.ENROLLED
        passkey.token.active = True
        passkey.token.save()
        self._add(passkey)
        # One TAN is used before the export
        self.assertEqual(1, get_one_token(serial="RK_TAN").check_otp("tan01"))

    def _add(self, token: TokenClass) -> None:
        self.serials.append(token.get_serial())
        self.addCleanup(remove_token, token.get_serial())

    def _use_new_encryption_key(self) -> None:
        key_directory = tempfile.TemporaryDirectory()
        self.addCleanup(key_directory.cleanup)
        key_file = os.path.join(key_directory.name, "enckey")
        with open(key_file, "wb") as key_file_handle:
            key_file_handle.write(geturandom(96))
        old_key_file = self.app.config["PI_ENCFILE"]
        self.app.config["PI_ENCFILE"] = key_file
        get_app_local_store().pop("pi_hsm", None)

        def restore() -> None:
            self.app.config["PI_ENCFILE"] = old_key_file
            get_app_local_store().pop("pi_hsm", None)
        self.addCleanup(restore)

    @staticmethod
    def _readable(read) -> object:
        try:
            return read()
        except Exception as error:  # nosec B110 # an unreadable secret is part of the comparison
            return f"<{type(error).__name__}>"

    def _state(self, serial: str) -> dict:
        token = get_one_token(serial=serial)
        return {"otpkey": self._readable(lambda: token.token.get_otpkey().getKey()),
                "ssh_key": self._readable(lambda: token.get_tokeninfo("ssh_key")),
                "ocrasuite": token.get_tokeninfo("ocrasuite"),
                "tans": sorted(key for key in token.get_tokeninfo() if key.startswith("tan.tan")),
                "state": (token.is_active(), token.token.rollout_state)}

    def test_01_update_after_key_change_keeps_secrets_and_state(self):
        before = {serial: self._state(serial) for serial in self.serials}
        # The YAML export of the token janitors: _to_dict() and a YAML round trip
        entries = yaml.safe_load(yaml.safe_dump([get_one_token(serial=serial)._to_dict() for serial in self.serials]))

        self._use_new_encryption_key()
        errors = {}
        for entry in entries:
            try:
                update_token_from_export(entry)
            except Exception as error:  # nosec B110 # collected and asserted below
                errors[entry["serial"]] = str(error)[:60]

        problems = {}
        for serial in self.serials:
            after = self._state(serial)
            changed = [key for key in after if after[key] != before[serial][key]]
            if serial in errors or changed:
                problems[serial] = {"error": errors.get(serial), "changed": changed}
        self.assertEqual({}, problems)
        # A TAN used before the export stays used
        self.assertEqual(-1, get_one_token(serial="RK_TAN").check_otp("tan01"))

    def test_02_revoked_token_is_reencrypted(self):
        stored_ssh_key = get_one_token(serial="RK_SSH").get_tokeninfo("ssh_key")
        entry = yaml.safe_load(yaml.safe_dump(get_one_token(serial="RK_SSH")._to_dict()))
        revoke_token("RK_SSH")
        self._use_new_encryption_key()
        update_token_from_export(entry)
        token = get_one_token(serial="RK_SSH")
        self.assertTrue(token.is_revoked())
        self.assertEqual(stored_ssh_key, token.get_tokeninfo("ssh_key"))
