"""
Data transformation test for migration b8c9d0e1f2a3
v3.14: Store an integrity checksum for SSH key tokens

The migration stores a checksum of the SSH key data (serial, key type, public
key and comment) in the encrypted OTP key field (``key_enc``/``key_iv``) of
every existing ``sshkey`` token, so that later tampering with the SSH key data
in the database is detected.

upgrade()   — for every sshkey token: decrypt ssh_key, compute the checksum
              and store it encrypted in key_enc/key_iv
downgrade() — reset key_enc/key_iv of every sshkey token to the encrypted
              empty string

Tokens of other tokentypes must be untouched. A token whose encrypted ssh_key
cannot be decrypted is skipped (its OTP key field stays as it was).
"""

import binascii
import os

import pytest

from tests.migration_test_utils import MigrationTestBase, quote_identifier

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]

# A full RSA public key (the comment intentionally contains spaces).
SSHKEY_RSA = (
    "ssh-rsa "
    "AAAAB3NzaC1yc2EAAAADAQABAAACAQDJy0rLoxqc8SsY8DVAFijMsQyCv"
    "hBu4K40hdZOacXK4O6OgnacnSKN56MP6pzz2+4svzvDzwvkFsvf34pbsgD"
    "F67PPSCsimmjEQjf0UfamBKh0cl181CbPYsph3UTBOCgHh3FFDXBduPK4DQz"
    "EVQpmqe80h+lsvQ81qPYagbRW6fpd0uWn9H7a/qiLQZsiKLL07HGB+NwWue4os"
    "0r9s4qxeG76K6QM7nZKyC0KRAz7CjAf+0X7YzCOu2pzyxVdj/T+KArFcMmq8V"
    "dz24mhcFFXTzU3wveas1A9rwamYWB+Spuohh/OrK3wDsrryStKQv7yofgnPMs"
    "TdaL7XxyQVPCmh2jVl5ro9BPIjTXsre9EUxZYFVr3EIECRDNWy3xEnUHk7Rzs"
    "734Rp6XxGSzcSLSju8/MBzUVe35iXfXDRcqTcoA0700pIb1ANYrPUO8Up05v4"
    "EjIyBeU61b4ilJ3PNcEVld6FHwP3Z7F068ef4DXEC/d7pibrp4Up61WYQIXV/"
    "utDt3NDg/Zf3iqoYcJNM/zIZx2j1kQQwqtnbGqxJMrL6LtClmeWteR4420uZx"
    "afLE9AtAL4nnMPuubC87L0wJ88un9teza/N02KJMHy01Yz3iJKt3Ou9eV6kqO"
    "ei3kvLs5dXmriTHp6g9whtnN6/Liv9SzZPJTs8YfThi34Wccrw== "
    "NetKnights GmbH Descröption")

SSHKEY_ED25519 = (
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC38dIb3tM6nPrT"
    "3j1UfsQxOCBbf3JogwsKeVPM893Pi cornelius@puck")


class TestMigrationB8c9d0e1f2a3(MigrationTestBase):
    REVISION = "b8c9d0e1f2a3"
    PARENT_REVISION = "d9e0f1a2b3c4"

    # -----------------------------------------------------------------
    # helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _split_key(sshkey: str):
        """Return (type, body, comment) of a full SSH public key string."""
        key_type, key_body, key_comment = sshkey.split(None, 2)
        return key_type, key_body, key_comment

    def _insert_sshkey_token(self, engine, token_id: int, serial: str, sshkey: str) -> None:
        """
        Insert an sshkey token exactly like an enrolled (but not yet migrated)
        token looks: encrypted ssh_key plus plaintext ssh_type/ssh_comment, and
        no checksum in the OTP key field yet.
        """
        from privacyidea.lib.crypto import encryptPassword
        key_type, key_body, key_comment = self._split_key(sshkey)
        self._insert_rows(engine, "token", [{
            "id": token_id,
            "serial": serial,
            "tokentype": "sshkey",
            "active": True,
        }])
        self._insert_rows(engine, "tokeninfo", [
            {"token_id": token_id, "Key": "ssh_key", "Value": encryptPassword(key_body),
             "Type": "password", "Description": ""},
            {"token_id": token_id, "Key": "ssh_type", "Value": key_type,
             "Type": "", "Description": ""},
            {"token_id": token_id, "Key": "ssh_comment", "Value": key_comment,
             "Type": "", "Description": ""},
        ])

    def _insert_other_token(self, engine, token_id: int, serial: str, tokentype: str,
                            key_enc: str | None = None, key_iv: str | None = None) -> None:
        self._insert_rows(engine, "token", [{
            "id": token_id,
            "serial": serial,
            "tokentype": tokentype,
            "active": True,
            "key_enc": key_enc,
            "key_iv": key_iv,
        }])

    def _fetch_token_column(self, engine, token_id: int, column: str):
        col = quote_identifier(column)
        return self._fetch_scalar(engine, f"SELECT {col} FROM token WHERE id = :tid",
                                  {"tid": token_id})

    def _stored_otpkey(self, engine, token_id: int) -> str | None:
        """Decrypt the value stored in the OTP key field (key_enc/key_iv)."""
        from privacyidea.lib.crypto import decrypt
        key_enc = self._fetch_token_column(engine, token_id, "key_enc")
        key_iv = self._fetch_token_column(engine, token_id, "key_iv")
        if not key_enc or not key_iv:
            return None
        plain = decrypt(binascii.unhexlify(key_enc), binascii.unhexlify(key_iv))
        return plain.decode("utf-8")

    def _expected_checksum(self, serial: str, sshkey: str) -> str:
        from privacyidea.lib.tokens.sshkeytoken import compute_ssh_key_checksum
        key_type, key_body, key_comment = self._split_key(sshkey)
        return compute_ssh_key_checksum(serial, key_type, key_body, key_comment)

    # -----------------------------------------------------------------
    # upgrade() tests
    # -----------------------------------------------------------------

    def test_upgrade_stores_checksum_for_sshkey_tokens(self, flask_app):
        """upgrade() must store the integrity checksum of every sshkey token."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_sshkey_token(engine, 5001, "SSHMIGR_RSA", SSHKEY_RSA)
            self._insert_sshkey_token(engine, 5002, "SSHMIGR_ED", SSHKEY_ED25519)

            self._upgrade()

            assert self._stored_otpkey(engine, 5001) == \
                   self._expected_checksum("SSHMIGR_RSA", SSHKEY_RSA)
            assert self._stored_otpkey(engine, 5002) == \
                   self._expected_checksum("SSHMIGR_ED", SSHKEY_ED25519)
        finally:
            engine.dispose()

    def test_upgrade_leaves_other_tokentypes_untouched(self, flask_app):
        """upgrade() must not modify the OTP key field of non-sshkey tokens."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_sshkey_token(engine, 5001, "SSHMIGR_RSA", SSHKEY_RSA)
            # An hotp token with an existing (unrelated) encrypted OTP key.
            self._insert_other_token(engine, 5003, "HOTP_MIGR", "hotp",
                                     key_enc="abcdef", key_iv="123456")

            self._upgrade()

            # sshkey token got its checksum ...
            assert self._stored_otpkey(engine, 5001) == \
                   self._expected_checksum("SSHMIGR_RSA", SSHKEY_RSA)
            # ... while the hotp token keeps its original key material verbatim.
            assert self._fetch_token_column(engine, 5003, "key_enc") == "abcdef"
            assert self._fetch_token_column(engine, 5003, "key_iv") == "123456"
        finally:
            engine.dispose()

    def test_upgrade_skips_undecryptable_key(self, flask_app):
        """
        A token whose encrypted ssh_key cannot be decrypted must be skipped:
        its OTP key field stays empty (NULL) instead of receiving a checksum
        computed over garbage.
        """
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            # A healthy token next to the broken one, to prove the migration
            # continues past the skipped token.
            self._insert_sshkey_token(engine, 5001, "SSHMIGR_RSA", SSHKEY_RSA)
            # Broken token: ssh_key marked as password but not actually encrypted.
            self._insert_rows(engine, "token", [{
                "id": 5004, "serial": "SSHMIGR_BROKEN", "tokentype": "sshkey", "active": True}])
            self._insert_rows(engine, "tokeninfo", [
                {"token_id": 5004, "Key": "ssh_key", "Value": "not-a-valid-ciphertext",
                 "Type": "password", "Description": ""},
                {"token_id": 5004, "Key": "ssh_type", "Value": "ssh-rsa",
                 "Type": "", "Description": ""},
                {"token_id": 5004, "Key": "ssh_comment", "Value": "broken",
                 "Type": "", "Description": ""},
            ])

            self._upgrade()  # must not raise

            assert self._stored_otpkey(engine, 5001) == \
                   self._expected_checksum("SSHMIGR_RSA", SSHKEY_RSA)
            # The broken token was skipped: no checksum was written.
            assert self._fetch_token_column(engine, 5004, "key_enc") is None
        finally:
            engine.dispose()

    def test_upgrade_is_noop_without_sshkey_tokens(self, flask_app):
        """upgrade() must not fail when there are no sshkey tokens at all."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_other_token(engine, 5003, "HOTP_MIGR", "hotp")

            self._upgrade()  # must not raise

            assert self._fetch_token_column(engine, 5003, "tokentype") == "hotp"
        finally:
            engine.dispose()

    # -----------------------------------------------------------------
    # downgrade() tests
    # -----------------------------------------------------------------

    def test_downgrade_resets_checksum(self, flask_app):
        """downgrade() must reset the OTP key field to the encrypted empty string."""
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_sshkey_token(engine, 5001, "SSHMIGR_RSA", SSHKEY_RSA)

            self._upgrade()
            assert self._stored_otpkey(engine, 5001) == \
                   self._expected_checksum("SSHMIGR_RSA", SSHKEY_RSA)

            self._downgrade()

            # The checksum is gone: the OTP key field decrypts to the empty string.
            assert self._stored_otpkey(engine, 5001) == ""
        finally:
            engine.dispose()

    def test_upgrade_is_idempotent_across_round_trip(self, flask_app):
        """
        Re-running the migration (upgrade → downgrade → upgrade) yields the same
        checksum, because it is deterministically derived from the key data.
        """
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
            self._insert_sshkey_token(engine, 5001, "SSHMIGR_RSA", SSHKEY_RSA)

            self._upgrade()
            first = self._stored_otpkey(engine, 5001)

            self._downgrade()
            self._upgrade()
            second = self._stored_otpkey(engine, 5001)

            assert first == second == self._expected_checksum("SSHMIGR_RSA", SSHKEY_RSA)
        finally:
            engine.dispose()
