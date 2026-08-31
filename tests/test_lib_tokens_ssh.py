"""
This test file tests the lib.tokens.sshkeytoken
This depends on lib.tokenclass
"""
import importlib.util
import os

from privacyidea.config import ConfigKey
from privacyidea.lib.error import TokenAdminError
from privacyidea.lib.token import init_token, import_tokens, get_tokens
from privacyidea.lib.tokenrolloutstate import RolloutState
from privacyidea.lib.tokens.sshkeytoken import (SSHkeyTokenClass, get_allowed_ssh_key_types,
                                                DEFAULT_ALLOWED_SSH_KEY_TYPES,
                                                compute_ssh_key_checksum)
from privacyidea.models import Token, TokenInfo, db
from .base import MyTestCase

MIGRATION_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "privacyidea", "migrations", "versions",
                              "b8c9d0e1f2a3_sshkey_integrity_checksum.py")


class SSHTokenTestCase(MyTestCase):
    otppin = "topsecret"
    serial1 = "ser1"
    serial2 = "ser2"
    serial3 = "ser3"
    serial4 = "ser4"
    sshkey = "ssh-rsa " \
             "AAAAB3NzaC1yc2EAAAADAQABAAACAQDJy0rLoxqc8SsY8DVAFijMsQyCv" \
             "hBu4K40hdZOacXK4O6OgnacnSKN56MP6pzz2+4svzvDzwvkFsvf34pbsgD" \
             "F67PPSCsimmjEQjf0UfamBKh0cl181CbPYsph3UTBOCgHh3FFDXBduPK4DQz" \
             "EVQpmqe80h+lsvQ81qPYagbRW6fpd0uWn9H7a/qiLQZsiKLL07HGB+NwWue4os" \
             "0r9s4qxeG76K6QM7nZKyC0KRAz7CjAf+0X7YzCOu2pzyxVdj/T+KArFcMmq8V" \
             "dz24mhcFFXTzU3wveas1A9rwamYWB+Spuohh/OrK3wDsrryStKQv7yofgnPMs" \
             "TdaL7XxyQVPCmh2jVl5ro9BPIjTXsre9EUxZYFVr3EIECRDNWy3xEnUHk7Rzs" \
             "734Rp6XxGSzcSLSju8/MBzUVe35iXfXDRcqTcoA0700pIb1ANYrPUO8Up05v4" \
             "EjIyBeU61b4ilJ3PNcEVld6FHwP3Z7F068ef4DXEC/d7pibrp4Up61WYQIXV/" \
             "utDt3NDg/Zf3iqoYcJNM/zIZx2j1kQQwqtnbGqxJMrL6LtClmeWteR4420uZx" \
             "afLE9AtAL4nnMPuubC87L0wJ88un9teza/N02KJMHy01Yz3iJKt3Ou9eV6kqO" \
             "ei3kvLs5dXmriTHp6g9whtnN6/Liv9SzZPJTs8YfThi34Wccrw== " \
             "NetKnights GmbH Descröption"
    unsupported_keytype = "ssh-something AAAAA comment"
    sshkey_ecdsa = "ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzd" \
                   "HAyNTYAAABBBHGCdIk0pO1HFr/mF4oLb43ZRyQJ4K7ICLrAhAiQERVa0tUvyY5TE" \
                   "zurWTqxSMx203rY77t6xnHLZBMPPpv8rk0= cornelius@puck"
    sshkey_ed25519 = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC38dIb3tM6nPrT" \
                     "3j1UfsQxOCBbf3JogwsKeVPM893Pi cornelius@puck"
    ecdsa_sk = "sk-ecdsa-sha2-nistp256@openssh.com AAAAInNrLWVjZHNhLXNoYTItbmlz" \
               "dHAyNTZAb3BlbnNzaC5jb20AAAAIbmlzdHAyNTYAAABBBOStamg+GO4TSgtoWjc82p" \
               "OKZIDuOeAt/8PU/jbzEmth6VuNhghRTCPqPMFtR6mB3Pb12yMDRiLH/t1VwkvWWYIA" \
               "AAAEc3NoOg=="
    wrong_sshkey = """---- BEGIN SSH2 PUBLIC KEY ----
    AAAAB3NzaC1kc3MAAACBAKrFC6uDvuxl9vnYL/Fu/Vq+12KJF4
    RyMSQe4mn8oHJma2VzepBRBpLt7Q==
    ---- END SSH2 PUBLIC KEY ----"""
    INVALID_SSH = "ssh-rsa"

    @staticmethod
    def _enroll_sshkey(serial, sshkey):
        """Create and enroll a raw SSHkeyTokenClass token (bypassing init_token)."""
        db_token = Token(serial, tokentype="sshkey")
        db_token.save()
        token = SSHkeyTokenClass(db_token)
        token.update({"sshkey": sshkey})
        return token

    @staticmethod
    def _load_sshkey(serial):
        """Load an existing sshkey token from the DB as an SSHkeyTokenClass."""
        return SSHkeyTokenClass(Token.query.filter(Token.serial == serial).first())

    def test_01_create_token(self):
        db_token = Token(self.serial1, tokentype="sshkey")
        db_token.save()
        token = SSHkeyTokenClass(db_token)

        # Invalid keys raise an exception and mark the token as broken
        for invalid_key in ("InvalidKey", self.INVALID_SSH, self.wrong_sshkey, self.unsupported_keytype):
            self.assertRaises(TokenAdminError, token.update, {"sshkey": invalid_key})
            self.assertEqual(RolloutState.BROKEN, token.rollout_state)

        # Set valid key
        token.update({"sshkey": self.sshkey})
        self.assertEqual(self.serial1, token.token.serial)
        self.assertEqual("sshkey", token.token.tokentype)
        self.assertEqual("sshkey", token.type)
        self.assertEqual("SSHK", token.get_class_prefix())
        self.assertEqual("sshkey", token.get_class_type())

        # The other supported key types can be enrolled as well
        for serial, sshkey in ((self.serial2, self.sshkey_ecdsa),
                               (self.serial3, self.sshkey_ed25519),
                               (self.serial4, self.ecdsa_sk)):
            self._enroll_sshkey(serial, sshkey)

    def test_02_class_methods(self):
        token = self._load_sshkey(self.serial1)

        info = token.get_class_info()
        self.assertEqual("SSHkey Token", info.get("title"))

        info = token.get_class_info("title")
        self.assertEqual("SSHkey Token", info)

    def test_03_get_sshkey(self):
        for serial, expected in ((self.serial1, self.sshkey),
                                 (self.serial2, self.sshkey_ecdsa),
                                 (self.serial3, self.sshkey_ed25519),
                                 (self.serial4, self.ecdsa_sk)):
            sshkey = self._load_sshkey(serial).get_sshkey()
            self.assertEqual(expected, sshkey)
            self.assertIsInstance(sshkey, str)

    def test_04_ssh_token_export(self):
        # Set up the SSHTokenClass for testing
        token = init_token({"type": "sshkey",
                            "serial": self.serial1,
                            "sshkey": self.sshkey,
                            "description": "this is a ssh token export test",
                            "issuer": "privacyIDEA"})

        # Test that all expected keys are present in the exported dictionary
        exported_data = token.export_token()
        expected_keys = ["serial", "type", "description", "issuer"]
        self.assertTrue(set(expected_keys).issubset(exported_data.keys()))

        expected_tokeninfo_keys = ["tokenkind", "ssh_key", "ssh_type", "ssh_comment"]
        self.assertTrue(set(expected_tokeninfo_keys).issubset(exported_data["info_list"].keys()))

        # Test that the exported values match the token's data
        self.assertEqual(exported_data["serial"], "ser1")
        self.assertEqual(exported_data["type"], "sshkey")
        self.assertEqual(exported_data["description"], "this is a ssh token export test")
        self.assertEqual(exported_data["info_list"]["tokenkind"], "software")
        self.assertEqual(exported_data["issuer"], "privacyIDEA")
        self.assertEqual(exported_data["info_list"]["ssh_key"], self.sshkey[8:-28])  # ss_key without type and comment
        self.assertEqual(exported_data["info_list"]["ssh_type"], "ssh-rsa")
        self.assertEqual(exported_data["info_list"]["ssh_comment"], "NetKnights GmbH Descröption")

        # Clean up
        token.delete_token()

    def test_05_ssh_token_import(self):
        # Define the token data to be imported
        token_data = [{'description': 'this is a registration token export test',
                       'issuer': 'privacyIDEA',
                       'serial': 'newserial',
                       'type': 'sshkey',
                       'info_list': {'ssh_comment': 'NetKnights GmbH Descröption',
                                     'ssh_key': self.sshkey[8:-28],  # ss_key without type and comment
                                     'ssh_key.type': 'password',
                                     'ssh_type': 'ssh-rsa',
                                     'tokenkind': 'software'}
                       }]

        # Import the token
        import_tokens(token_data)

        # Retrieve the imported token
        token = get_tokens(serial=token_data[0]["serial"])[0]

        # Verify that the token data matches the imported data
        self.assertEqual(token.token.serial, token_data[0]["serial"])
        self.assertEqual(token.type, token_data[0]["type"])
        self.assertEqual(token.token.description, token_data[0]["description"])
        self.assertEqual(token.get_tokeninfo("tokenkind"), "software")
        self.assertEqual(token.get_tokeninfo("ssh_key"), self.sshkey[8:-28])
        self.assertEqual(token.get_tokeninfo("ssh_type"), "ssh-rsa")
        # The integrity checksum was computed on import, so the key can be fetched
        self.assertEqual(self.sshkey, token.get_sshkey())

        # Clean up
        token.delete_token()

    def test_06_allowed_key_types_from_config(self):
        # Without the config entry only the default key types are allowed
        self.assertEqual(DEFAULT_ALLOWED_SSH_KEY_TYPES, get_allowed_ssh_key_types())

        # A list adds additional key types and duplicates of the defaults are ignored
        self.app.config[ConfigKey.ALLOWED_SSH_KEY_TYPES] = ["ssh-rsa", "ssh-something", "ssh-dss"]
        self.assertEqual(DEFAULT_ALLOWED_SSH_KEY_TYPES + ["ssh-something", "ssh-dss"],
                         get_allowed_ssh_key_types())

        # ... and the token can now be enrolled with such a key
        token = init_token({"type": "sshkey", "serial": "SSHKCONF1",
                            "sshkey": self.unsupported_keytype})
        self.assertEqual("ssh-something", token.get_tokeninfo("ssh_type"))
        self.assertEqual(self.unsupported_keytype, token.get_sshkey())
        token.delete_token()

        # A single string is accepted as well and wrapped into a list
        self.app.config[ConfigKey.ALLOWED_SSH_KEY_TYPES] = "ssh-something"
        self.assertEqual(DEFAULT_ALLOWED_SSH_KEY_TYPES + ["ssh-something"],
                         get_allowed_ssh_key_types())

        # Without the config entry the key type is rejected again
        del self.app.config[ConfigKey.ALLOWED_SSH_KEY_TYPES]
        self.assertRaises(TokenAdminError, init_token,
                          {"type": "sshkey", "serial": "SSHKCONF2",
                           "sshkey": self.unsupported_keytype})
        for broken_token in get_tokens(serial="SSHKCONF2"):
            broken_token.delete_token()

    @staticmethod
    def _set_tokeninfo_value(token_id, key, value):
        """Simulate a database admin changing a tokeninfo entry directly in the DB."""
        info = TokenInfo.query.filter_by(token_id=token_id, Key=key).first()
        old_value = info.Value
        info.Value = value
        db.session.commit()
        return old_value

    def _assert_tamper_detected(self, token, key, bad_value):
        """Tamper with a tokeninfo entry in the DB, assert the integrity check
        fails, then restore the original value and assert the key is readable
        again."""
        original = self._set_tokeninfo_value(token.token.id, key, bad_value)
        self.assertRaises(TokenAdminError, token.get_sshkey)
        self._set_tokeninfo_value(token.token.id, key, original)

    def test_07_integrity_checksum_detects_manipulation(self):
        token_a = init_token({"type": "sshkey", "serial": "SSHTAMPER1", "sshkey": self.sshkey})
        token_b = init_token({"type": "sshkey", "serial": "SSHTAMPER2", "sshkey": self.sshkey_ed25519})
        # Sanity check: the keys can be fetched
        self.assertEqual(self.sshkey, token_a.get_sshkey())
        self.assertEqual(self.sshkey_ed25519, token_b.get_sshkey())

        # A database admin changes the plaintext key type in the database
        self._assert_tamper_detected(token_a, "ssh_type", "ssh-dss")
        self.assertEqual(self.sshkey, token_a.get_sshkey())

        # A database admin changes the plaintext comment in the database
        self._assert_tamper_detected(token_a, "ssh_comment", "root@evil")
        self.assertEqual(self.sshkey, token_a.get_sshkey())

        # A database admin copies the encrypted ssh_key of another token
        # (substitution attack): they cannot decrypt it, but they can copy the
        # ciphertext. This is detected as well.
        ciphertext_b = TokenInfo.query.filter_by(token_id=token_b.token.id, Key="ssh_key").first().Value
        self._assert_tamper_detected(token_a, "ssh_key", ciphertext_b)
        self.assertEqual(self.sshkey, token_a.get_sshkey())

        # A corrupt encrypted ssh_key that cannot be decrypted must raise a
        # TokenAdminError instead of handing out the decryption sentinel as the
        # public key.
        self._assert_tamper_detected(token_a, "ssh_key", "not-a-valid-ciphertext")
        self.assertEqual(self.sshkey, token_a.get_sshkey())

        # A missing checksum is not accepted either
        token_a.token.set_otpkey("")
        token_a.token.save()
        self.assertRaises(TokenAdminError, token_a.get_sshkey)

        # Unreadable OTP key material (e.g. a token the migration skipped, whose
        # key_enc/key_iv stay NULL) must map to the integrity TokenAdminError,
        # not to a low-level decoding error. As the token was never migrated,
        # the message hints at running the migration.
        token_a.token.key_enc = None
        token_a.token.key_iv = None
        token_a.token.save()
        with self.assertRaises(TokenAdminError) as cm:
            token_a.get_sshkey()
        self.assertIn("missing", str(cm.exception).lower())

        # Malformed (non-hex) OTP key material is present but unreadable: this
        # is a corruption, not a missing checksum, so the message must not tell
        # the admin to (uselessly) rerun the migration.
        token_a.token.key_enc = "not-hex!"
        token_a.token.key_iv = "not-hex!"
        token_a.token.save()
        with self.assertRaises(TokenAdminError) as cm:
            token_a.get_sshkey()
        self.assertIn("corrupt", str(cm.exception).lower())
        self.assertNotIn("migration", str(cm.exception).lower())

        token_a.delete_token()
        token_b.delete_token()

    def test_08_migration_backfills_checksum(self):
        # Create "legacy" tokens: enrolled tokens whose OTP key field does not
        # contain the integrity checksum, like tokens enrolled before the update.
        token_a = init_token({"type": "sshkey", "serial": "SSHMIG1", "sshkey": self.sshkey})
        token_b = init_token({"type": "sshkey", "serial": "SSHMIG2", "sshkey": self.sshkey_ecdsa})
        for token in (token_a, token_b):
            token.token.set_otpkey("")
            token.token.save()
            self.assertRaises(TokenAdminError, token.get_sshkey)
        # A non-sshkey token must not be touched by the migration
        spass = init_token({"type": "spass", "serial": "SSHMIG3"})
        spass_key_enc = spass.token.key_enc

        # Load the migration module and run the backfill
        spec = importlib.util.spec_from_file_location("sshkey_checksum_migration", MIGRATION_FILE)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        count = migration.backfill_ssh_key_checksums(db.session.connection())
        db.session.commit()
        # All sshkey tokens in the DB are migrated (previous tests may have left some)
        self.assertGreaterEqual(count, 2)

        # Now the keys can be fetched again
        token_a = get_tokens(serial="SSHMIG1")[0]
        token_b = get_tokens(serial="SSHMIG2")[0]
        self.assertEqual(self.sshkey, token_a.get_sshkey())
        self.assertEqual(self.sshkey_ecdsa, token_b.get_sshkey())
        # The migration is idempotent
        second_count = migration.backfill_ssh_key_checksums(db.session.connection())
        db.session.commit()
        self.assertEqual(count, second_count)
        self.assertEqual(self.sshkey, get_tokens(serial="SSHMIG1")[0].get_sshkey())
        # The spass token was not modified
        self.assertEqual(spass_key_enc, get_tokens(serial="SSHMIG3")[0].token.key_enc)

        # The downgrade removes the checksums again
        checksum = compute_ssh_key_checksum("SSHMIG1", "ssh-rsa", self.sshkey[8:-28],
                                            "NetKnights GmbH Descröption")
        self.assertEqual(checksum, token_a.token.get_otpkey().getKey().decode())
        migration._set_token_otpkey(db.session.connection(), token_a.token.id, "")
        db.session.commit()
        self.assertRaises(TokenAdminError, get_tokens(serial="SSHMIG1")[0].get_sshkey)

        token_a.delete_token()
        token_b.delete_token()
        spass.delete_token()

    def test_09_checksum_binds_field_boundaries(self):
        # The checksum must uniquely bind the field boundaries. Moving text
        # across the key/comment boundary must yield a different checksum,
        # which a naive "\n".join() encoding would not (both would serialize
        # to "...\nAAA\nX\nY" / "...\nAAA\nX\nY").
        checksum_1 = compute_ssh_key_checksum("SSHBOUND", "ssh-rsa", "AAA", "X\nY")
        checksum_2 = compute_ssh_key_checksum("SSHBOUND", "ssh-rsa", "AAA\nX", "Y")
        self.assertNotEqual(checksum_1, checksum_2)
        # It is also stable (idempotent) for the same input.
        self.assertEqual(checksum_1, compute_ssh_key_checksum("SSHBOUND", "ssh-rsa", "AAA", "X\nY"))

    def test_10_a_token_without_a_key_gets_no_checksum(self):
        token = init_token({"type": "sshkey", "serial": "SSHEMPTY", "sshkey": self.sshkey})
        checksum = token.token.get_otpkey().getKey()

        # Removing the public key must not store a checksum over the empty key
        # data, otherwise a key-less token would pass its own integrity check.
        token.delete_tokeninfo("ssh_key")
        self.assertEqual(checksum, token.token.get_otpkey().getKey())
        self.assertRaises(TokenAdminError, token.get_sshkey)

        # An import without any SSH key data gets no checksum either
        imported = init_token({"type": "sshkey", "serial": "SSHEMPTY2", "sshkey": self.sshkey})
        imported.delete_tokeninfo()
        imported.token.key_enc = None
        imported.token.key_iv = None
        imported.token.save()
        imported.import_token({"description": "no key data"})
        self.assertRaises(TokenAdminError, imported.get_sshkey)

        token.delete_token()
        imported.delete_token()

    def test_11_the_public_key_is_always_stored_encrypted(self):
        token = init_token({"type": "sshkey", "serial": "SSHENC", "sshkey": self.sshkey})
        key_part = self.sshkey.split()[1]

        # Callers such as the generic settokeninfo endpoint do not pass a value
        # type. The token class enforces it, so the key stays encrypted at rest
        # and is still read back in clear text.
        token.add_tokeninfo("ssh_key", key_part)
        info = token.get_tokeninfo()
        self.assertEqual("password", info.get("ssh_key.type"))
        self.assertNotEqual(key_part, info.get("ssh_key"))
        self.assertEqual(self.sshkey, token.get_sshkey())

        token.delete_token()
