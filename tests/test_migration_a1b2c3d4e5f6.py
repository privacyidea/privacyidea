"""
Tests for the database migration script a1b2c3d4e5f6 that encrypts
sensitive plaintext data (SMS gateway options and challenge data fields).

This tests the helper functions and data transformation logic without
running the full alembic migration (which requires TEST_DATABASE_URL).
"""
from sqlalchemy import select

from privacyidea.lib.crypto import encryptPassword, decryptPassword
from privacyidea.models import SMSGateway, SMSGatewayOption, Challenge, db
from privacyidea.models.challenge import Challenge as ChallengeModel
from .base import MyTestCase


class MigrationEncryptionTestCase(MyTestCase):
    """
    Test the migration logic for encrypting existing plaintext data.
    """

    def test_01_looks_encrypted_detection(self):
        """The _looks_encrypted heuristic correctly detects encrypted values."""
        from privacyidea.migrations.versions.a1b2c3d4e5f6_encrypt_sensitive_db_fields import (
            _looks_encrypted
        )

        # Encrypted values have format: 32-hex-char-IV : hex-ciphertext
        encrypted_sample = encryptPassword("test_value")
        self.assertTrue(_looks_encrypted(encrypted_sample),
                        f"Should detect encrypted value: {encrypted_sample}")

        # Plaintext values should NOT be detected as encrypted
        self.assertFalse(_looks_encrypted("my_password"))
        self.assertFalse(_looks_encrypted(""))
        self.assertFalse(_looks_encrypted(None))
        self.assertFalse(_looks_encrypted("no-colon-here"))
        # A colon in a value is not enough - needs hex on both sides
        self.assertFalse(_looks_encrypted("user:password"))
        self.assertFalse(_looks_encrypted("http://example.com"))

    def test_02_migration_encrypts_smsgateway_options(self):
        """
        Simulate the migration logic: plaintext PASSWORD options get encrypted,
        non-sensitive options are left alone.
        """
        from privacyidea.migrations.versions.a1b2c3d4e5f6_encrypt_sensitive_db_fields import (
            _looks_encrypted, SENSITIVE_KEYWORDS
        )

        identifier = "migration_test_gw"
        provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider"

        # Create a gateway and manually insert a plaintext PASSWORD
        # (simulating pre-migration state)
        gw = SMSGateway(identifier, provider_module, description="migration test")
        db.session.add(gw)
        db.session.flush()

        # Insert options directly (bypassing encryption in set_smsgateway)
        plaintext_pw = "plaintext_password_123"
        pw_option = SMSGatewayOption(gateway_id=gw.id, Key="PASSWORD",
                                     Value=plaintext_pw, Type="option")
        url_option = SMSGatewayOption(gateway_id=gw.id, Key="URL",
                                      Value="https://api.example.com", Type="option")
        db.session.add(pw_option)
        db.session.add(url_option)
        db.session.commit()

        # Verify plaintext is in DB
        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw.id, Key="PASSWORD")
        opt = db.session.execute(stmt).scalar_one()
        self.assertEqual(opt.Value, plaintext_pw)

        # Simulate the migration: find and encrypt sensitive options
        all_options = db.session.scalars(select(SMSGatewayOption).filter_by(gateway_id=gw.id)).all()
        for option in all_options:
            upper_key = option.Key.upper()
            if any(kw in upper_key for kw in SENSITIVE_KEYWORDS):
                if option.Value and not _looks_encrypted(option.Value):
                    option.Value = encryptPassword(option.Value)
        db.session.commit()

        # Verify PASSWORD is now encrypted in DB
        db.session.expire_all()
        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw.id, Key="PASSWORD")
        opt = db.session.execute(stmt).scalar_one()
        self.assertNotEqual(opt.Value, plaintext_pw)
        self.assertIn(":", opt.Value)
        self.assertEqual(decryptPassword(opt.Value), plaintext_pw)

        # URL should be unchanged
        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw.id, Key="URL")
        opt = db.session.execute(stmt).scalar_one()
        self.assertEqual(opt.Value, "https://api.example.com")

        # Clean up
        gw.delete()

    def test_03_migration_encrypts_challenge_data(self):
        """
        Simulate the migration logic: plaintext challenge data gets encrypted.
        """
        from privacyidea.migrations.versions.a1b2c3d4e5f6_encrypt_sensitive_db_fields import (
            _looks_encrypted
        )

        # Create a challenge and manually set plaintext data (pre-migration state)
        c = Challenge(serial="MIGTEST01", transaction_id="mig_tid001",
                      validitytime=300)
        c.save()

        # Write plaintext OTP directly to _data column (simulating pre-migration DB)
        plaintext_otp = "987654"
        c._data = plaintext_otp
        db.session.commit()

        # Simulate migration logic: read raw _data, encrypt if plaintext
        db.session.expire_all()
        stmt = select(Challenge).filter_by(transaction_id="mig_tid001")
        db_challenge = db.session.execute(stmt).scalar_one()
        raw_data = db_challenge._data
        if raw_data and not _looks_encrypted(raw_data):
            db_challenge._data = encryptPassword(raw_data)
        db.session.commit()

        # Verify _data is now encrypted in DB
        db.session.expire_all()
        stmt = select(Challenge).filter_by(transaction_id="mig_tid001")
        db_challenge = db.session.execute(stmt).scalar_one()
        self.assertNotEqual(db_challenge._data, plaintext_otp)
        self.assertIn(":", db_challenge._data)
        # And the data property transparently decrypts
        self.assertEqual(db_challenge.data, plaintext_otp)

        # Clean up
        db.session.delete(db_challenge)
        db.session.commit()

    def test_04_migration_skips_already_encrypted(self):
        """Migration is idempotent - already encrypted values are skipped."""
        from privacyidea.migrations.versions.a1b2c3d4e5f6_encrypt_sensitive_db_fields import (
            _looks_encrypted
        )

        # Create a gateway with an already-encrypted password
        identifier = "idempotent_test_gw"
        provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider"

        gw = SMSGateway(identifier, provider_module)
        db.session.add(gw)
        db.session.flush()

        already_encrypted = encryptPassword("already_encrypted_pw")
        pw_option = SMSGatewayOption(gateway_id=gw.id, Key="PASSWORD",
                                     Value=already_encrypted, Type="option")
        db.session.add(pw_option)
        db.session.commit()

        # Simulate migration - should skip this option
        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw.id, Key="PASSWORD")
        opt = db.session.execute(stmt).scalar_one()
        self.assertTrue(_looks_encrypted(opt.Value))

        # Value should remain the same after "migration"
        original_value = opt.Value
        if opt.Value and not _looks_encrypted(opt.Value):
            opt.Value = encryptPassword(opt.Value)
        db.session.commit()

        db.session.expire_all()
        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw.id, Key="PASSWORD")
        opt = db.session.execute(stmt).scalar_one()
        self.assertEqual(opt.Value, original_value)

        # And the original password is still recoverable
        self.assertEqual(decryptPassword(opt.Value), "already_encrypted_pw")

        # Clean up
        gw.delete()

    def test_05_challenge_data_column_size_accommodates_encryption(self):
        """
        The challenge data column must be large enough to store encrypted values.
        Encrypted output (hex IV + colon + hex ciphertext) is much larger than
        the original plaintext. Verify a 512-char plaintext can be encrypted
        and stored without truncation.
        """
        from sqlalchemy import inspect

        # Verify the model column size is 2000
        mapper = inspect(ChallengeModel)
        data_col = mapper.columns['data']
        self.assertEqual(data_col.type.length, 2000)

        # Create a challenge with a large data payload (up to original 512 chars)
        large_data = "x" * 512
        c = Challenge(serial="COLSIZE01", transaction_id="colsize_tid001",
                      data=large_data, validitytime=300)
        c.save()

        # Verify encrypted value fits and can be decrypted
        db.session.expire_all()
        stmt = select(Challenge).filter_by(transaction_id="colsize_tid001")
        db_challenge = db.session.execute(stmt).scalar_one()
        # The raw _data should be encrypted (longer than original)
        self.assertGreater(len(db_challenge._data), 512)
        # Should decrypt correctly
        self.assertEqual(db_challenge.data, large_data)

        # Clean up
        db.session.delete(db_challenge)
        db.session.commit()
