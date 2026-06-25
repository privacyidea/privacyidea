"""v3.14: Encrypt plaintext SMS gateway secrets and challenge data in the database

This migration encrypts sensitive data that was previously stored in plaintext:

1. SMS Gateway options whose key contains PASSWORD or SECRET
  (table: smsgatewayoption)
2. Challenge data field which may contain OTP values
  (table: challenge)

The migration is idempotent: values that are already in encrypted format
(contain a colon separating IV:ciphertext hex) are skipped.

Revision ID: a1b2c3d4e5f6
Revises: c2d3e4f5a6b7
Create Date: 2026-06-22 00:00:00.000000

"""
import logging

from alembic import op
import sqlalchemy as sa

log = logging.getLogger("alembic.runtime.migration")

revision = 'a1b2c3d4e5f6'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None

# Keywords that identify sensitive SMS gateway option keys
SENSITIVE_KEYWORDS = ("PASSWORD", "SECRET")


def _looks_encrypted(value):
    """
    Heuristic to detect if a value is already in encrypted format.
    encryptPassword produces "hexIV:hexCiphertext" where both parts are
    hex strings. A plaintext password is very unlikely to match this pattern.
    """
    if not value or ':' not in value:
        return False
    parts = value.split(':', 1)
    if len(parts) != 2:
        return False
    # Both parts should be valid hex strings (IV is 32 hex chars = 16 bytes)
    try:
        bytes.fromhex(parts[0])
        bytes.fromhex(parts[1])
        # IV should be exactly 32 hex chars
        return len(parts[0]) == 32
    except (ValueError, TypeError):
        return False


def upgrade():
    # We need the crypto module to encrypt values
    from privacyidea.lib.crypto import encryptPassword

    # --- 0. Increase challenge.data column size to accommodate encrypted values ---
    log.info("Increasing challenge.data column size from 512 to 2000...")
    with op.batch_alter_table('challenge', schema=None) as batch_op:
        batch_op.alter_column('data',
                              existing_type=sa.Unicode(length=512),
                              type_=sa.Unicode(length=2000),
                              existing_nullable=True)

    conn = op.get_bind()

    # --- 1. Encrypt sensitive SMS gateway options ---
    log.info("Encrypting sensitive SMS gateway options...")
    smsgatewayoption = sa.table(
        'smsgatewayoption',
        sa.column('id', sa.Integer),
        sa.column('Key', sa.Unicode),
        sa.column('Value', sa.UnicodeText),
    )

    result = conn.execute(
        sa.select(smsgatewayoption.c.id, smsgatewayoption.c.Key, smsgatewayoption.c.Value)
    )
    encrypted_count = 0
    for row in result:
        option_id, key, value = row
        if not value:
            continue
        # Check if this key is sensitive
        upper_key = key.upper()
        if not any(kw in upper_key for kw in SENSITIVE_KEYWORDS):
            continue
        # Skip if already encrypted
        if _looks_encrypted(value):
            log.debug(f"Option id={option_id} key={key} already encrypted, skipping.")
            continue
        # Encrypt the plaintext value
        encrypted_value = encryptPassword(value)
        conn.execute(
            smsgatewayoption.update().where(
                smsgatewayoption.c.id == option_id
            ).values(Value=encrypted_value)
        )
        encrypted_count += 1

    log.info(f"Encrypted {encrypted_count} sensitive SMS gateway option(s).")

    # --- 2. Encrypt challenge data fields ---
    log.info("Encrypting challenge data fields...")
    challenge = sa.table(
        'challenge',
        sa.column('id', sa.Integer),
        sa.column('data', sa.Unicode),
    )

    result = conn.execute(
        sa.select(challenge.c.id, challenge.c.data)
    )
    encrypted_count = 0
    for row in result:
        challenge_id, data = row
        if not data:
            continue
        # Skip if already encrypted
        if _looks_encrypted(data):
            log.debug(f"Challenge id={challenge_id} data already encrypted, skipping.")
            continue
        # Encrypt the plaintext data
        encrypted_data = encryptPassword(data)
        conn.execute(
            challenge.update().where(
                challenge.c.id == challenge_id
            ).values(data=encrypted_data)
        )
        encrypted_count += 1

    log.info(f"Encrypted {encrypted_count} challenge data field(s).")


def downgrade():
    """
    Decrypt previously encrypted values back to plaintext.
    WARNING: This exposes sensitive data in the database again.
    """
    from privacyidea.lib.crypto import decryptPassword

    conn = op.get_bind()

    # --- 1. Decrypt sensitive SMS gateway options ---
    log.info("Decrypting sensitive SMS gateway options (downgrade)...")
    smsgatewayoption = sa.table(
        'smsgatewayoption',
        sa.column('id', sa.Integer),
        sa.column('Key', sa.Unicode),
        sa.column('Value', sa.UnicodeText),
    )

    result = conn.execute(
        sa.select(smsgatewayoption.c.id, smsgatewayoption.c.Key, smsgatewayoption.c.Value)
    )
    for row in result:
        option_id, key, value = row
        if not value:
            continue
        upper_key = key.upper()
        if not any(kw in upper_key for kw in SENSITIVE_KEYWORDS):
            continue
        if not _looks_encrypted(value):
            continue
        decrypted_value = decryptPassword(value)
        if decrypted_value and not decrypted_value.startswith("FAILED TO DECRYPT"):
            conn.execute(
                smsgatewayoption.update().where(
                    smsgatewayoption.c.id == option_id
                ).values(Value=decrypted_value)
            )

    # --- 2. Decrypt challenge data fields ---
    log.info("Decrypting challenge data fields (downgrade)...")
    challenge = sa.table(
        'challenge',
        sa.column('id', sa.Integer),
        sa.column('data', sa.Unicode),
    )

    result = conn.execute(
        sa.select(challenge.c.id, challenge.c.data)
    )
    for row in result:
        challenge_id, data = row
        if not data:
            continue
        if not _looks_encrypted(data):
            continue
        decrypted_data = decryptPassword(data)
        if decrypted_data and not decrypted_data.startswith("FAILED TO DECRYPT"):
            conn.execute(
                challenge.update().where(
                    challenge.c.id == challenge_id
                ).values(data=decrypted_data)
            )

    # --- 3. Revert challenge.data column size back to 512 ---
    log.info("Reverting challenge.data column size from 2000 to 512...")
    with op.batch_alter_table('challenge', schema=None) as batch_op:
        batch_op.alter_column('data',
                              existing_type=sa.Unicode(length=2000),
                              type_=sa.Unicode(length=512),
                              existing_nullable=True)
