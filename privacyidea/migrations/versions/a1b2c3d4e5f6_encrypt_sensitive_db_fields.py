"""v3.14: Encrypt plaintext SMS gateway secrets, resize challenge.data

This migration:

1. Encrypts SMS Gateway options whose key contains PASSWORD or SECRET
  (table: smsgatewayoption) – adds an ``Encrypted`` boolean column to track
  which values are encrypted.
2. The ``challenge.data`` column becomes a Text column without a length
  limit, so it can hold the encrypted JSON that newly created challenges store
  there, like a challenge cached in Redis. The existing rows themselves are not
  converted here: the very next revision, c3d4e5f6a7b8, unconditionally deletes
  every row of the ``challenge`` table, since challenges are short-lived and
  none of them can be in the new dict-only format yet. Encrypting them here
  first would be pure wasted work. For the same reason, on Oracle, which cannot
  change a VARCHAR2 column into a CLOB, the column is replaced without copying
  its data.

  A downgrade deletes all challenges before it limits the column to 512
  characters again: the code before this revision cannot read their encrypted
  data, and most of it does not fit.

The migration is idempotent: SMS gateway option values that are already in
encrypted format (contain a colon separating IV:ciphertext hex) are skipped.

Revision ID: a1b2c3d4e5f6
Revises: d4f5a6b7c8e9
Create Date: 2026-06-22 00:00:00.000000

"""
import logging

from alembic import op
import sqlalchemy as sa

log = logging.getLogger("alembic.runtime.migration")

revision = 'a1b2c3d4e5f6'
down_revision = 'd4f5a6b7c8e9'
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


def _replace_challenge_data_column(new_type: sa.types.TypeEngine) -> None:
    """
    Replace challenge.data by an empty column of the given type, for Oracle, which cannot convert between VARCHAR2
    and CLOB in place.
    """
    op.drop_column('challenge', 'data')
    op.add_column('challenge', sa.Column('data', new_type, nullable=True))


def upgrade():
    # We need the crypto module to encrypt values
    from privacyidea.lib.crypto import encryptPassword

    # --- 0a. Remove the length limit of challenge.data to accommodate encrypted values ---
    log.info("Changing challenge.data to a text column...")
    if op.get_bind().dialect.name == "oracle":
        _replace_challenge_data_column(sa.Text())
    else:
        with op.batch_alter_table('challenge', schema=None) as batch_op:
            batch_op.alter_column('data',
                                  existing_type=sa.Unicode(length=512),
                                  type_=sa.Text(),
                                  existing_nullable=True)

    # --- 0b. Add Encrypted boolean column to smsgatewayoption ---
    log.info("Adding Encrypted column to smsgatewayoption table...")
    with op.batch_alter_table('smsgatewayoption', schema=None) as batch_op:
        batch_op.add_column(sa.Column('Encrypted', sa.Boolean(),
                                      server_default='0', nullable=False))

    conn = op.get_bind()

    # --- 1. Encrypt sensitive SMS gateway options ---
    log.info("Encrypting sensitive SMS gateway options...")
    smsgatewayoption = sa.table(
        'smsgatewayoption',
        sa.column('id', sa.Integer),
        sa.column('Key', sa.Unicode),
        sa.column('Value', sa.UnicodeText),
        sa.column('Encrypted', sa.Boolean),
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
            log.debug(f"Option id={option_id} key={key} already encrypted, marking Encrypted flag.")
            conn.execute(
                smsgatewayoption.update().where(
                    smsgatewayoption.c.id == option_id
                ).values(Encrypted=True)
            )
            encrypted_count += 1
            continue
        # Encrypt the plaintext value
        encrypted_value = encryptPassword(value)
        conn.execute(
            smsgatewayoption.update().where(
                smsgatewayoption.c.id == option_id
            ).values(Value=encrypted_value, Encrypted=True)
        )
        encrypted_count += 1

    log.info(f"Encrypted {encrypted_count} sensitive SMS gateway option(s).")


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
        sa.column('Encrypted', sa.Boolean),
    )

    result = conn.execute(
        sa.select(smsgatewayoption.c.id, smsgatewayoption.c.Key,
                  smsgatewayoption.c.Value, smsgatewayoption.c.Encrypted)
    )
    for row in result:
        option_id, key, value, encrypted = row
        if not value or not encrypted:
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

    # --- 1b. Drop the Encrypted column ---
    log.info("Dropping Encrypted column from smsgatewayoption table...")
    with op.batch_alter_table('smsgatewayoption', schema=None) as batch_op:
        batch_op.drop_column('Encrypted')

    # --- 2. Revert challenge.data to 512 characters ---
    log.info("Deleting all challenges and reverting challenge.data to 512 characters...")
    op.execute("DELETE FROM challenge")
    if op.get_bind().dialect.name == "oracle":
        _replace_challenge_data_column(sa.Unicode(length=512))
    else:
        with op.batch_alter_table('challenge', schema=None) as batch_op:
            batch_op.alter_column('data',
                                  existing_type=sa.Text(),
                                  type_=sa.Unicode(length=512),
                                  existing_nullable=True)
