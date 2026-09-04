"""v3.14: Store an integrity checksum for SSH key tokens

SSH key tokens now store a checksum of the SSH key data (serial, key type,
public key and comment) in the encrypted OTP key field of the token. The
checksum is verified whenever the SSH key is fetched, so manipulations of the
database entries (e.g. by a database administrator changing the public key to
gain access to SSH servers) are detected.

This migration computes and stores the checksum for all existing SSH key
tokens. Tokens whose encrypted SSH key cannot be decrypted are skipped with a
warning - these tokens will refuse to hand out the SSH key until they are
re-enrolled.

The migration is idempotent: recomputing the checksum yields the same value,
so it can safely be run multiple times.

Revision ID: b8c9d0e1f2a3
Revises: d9e0f1a2b3c4
Create Date: 2026-08-20 00:00:00.000000

"""
import logging

import sqlalchemy as sa
from alembic import op

log = logging.getLogger("alembic.runtime.migration")

revision = 'b8c9d0e1f2a3'
down_revision = 'd9e0f1a2b3c4'
branch_labels = None
depends_on = None

token_table = sa.table(
    'token',
    sa.column('id', sa.Integer),
    sa.column('serial', sa.Unicode),
    sa.column('tokentype', sa.Unicode),
    sa.column('key_enc', sa.Unicode),
    sa.column('key_iv', sa.Unicode))

tokeninfo_table = sa.table(
    'tokeninfo',
    sa.column('token_id', sa.Integer),
    sa.column('Key', sa.Unicode),
    sa.column('Value', sa.UnicodeText),
    sa.column('Type', sa.Unicode))


def _set_token_otpkey(conn, token_id, otpkey):
    """
    Store the given value encrypted in the OTP key field of the token,
    like Token.set_otpkey() does.
    """
    from privacyidea.lib.crypto import encrypt, geturandom
    from privacyidea.lib.utils import hexlify_and_unicode

    iv = geturandom(16)
    conn.execute(token_table.update().where(token_table.c.id == token_id).values(
        key_enc=encrypt(otpkey, iv),
        key_iv=hexlify_and_unicode(iv)))


def backfill_ssh_key_checksums(conn):
    """
    Compute and store the integrity checksum for all sshkey tokens.

    :param conn: SQLAlchemy connection
    :return: the number of migrated tokens
    """
    from privacyidea.lib.crypto import decryptPassword, FAILED_TO_DECRYPT_PASSWORD
    from privacyidea.lib.tokens.sshkeytoken import compute_ssh_key_checksum

    serial_by_id = {token_id: serial for token_id, serial in
                    conn.execute(sa.select(token_table.c.id, token_table.c.serial)
                                 .where(token_table.c.tokentype == 'sshkey')).fetchall()}
    if not serial_by_id:
        return 0

    # Fetch the relevant token info of all sshkey tokens in a single query
    # (join on tokentype, so we do not run into IN-clause length limits).
    info_by_token = {}
    info_rows = conn.execute(
        sa.select(tokeninfo_table.c.token_id, tokeninfo_table.c.Key,
                  tokeninfo_table.c.Value, tokeninfo_table.c.Type)
        .select_from(tokeninfo_table.join(token_table,
                                          tokeninfo_table.c.token_id == token_table.c.id))
        .where(token_table.c.tokentype == 'sshkey',
               tokeninfo_table.c.Key.in_(['ssh_key', 'ssh_type', 'ssh_comment']))).fetchall()
    for token_id, key, value, value_type in info_rows:
        info_by_token.setdefault(token_id, {})[key] = (value or '', value_type)

    count = 0
    for token_id, serial in serial_by_id.items():
        info = info_by_token.get(token_id, {})
        ssh_key, ssh_key_type = info.get('ssh_key', ('', None))
        if not ssh_key or ssh_key_type != 'password':
            log.warning(f"SSH key token {serial} has no valid encrypted SSH key "
                        "(missing key or not marked as password). Skipping this token. "
                        "It will refuse to hand out the SSH key until it is re-enrolled.")
            continue
        ssh_key = decryptPassword(ssh_key)
        if ssh_key == FAILED_TO_DECRYPT_PASSWORD:
            log.warning(f"Could not decrypt the SSH key of token {serial}. Skipping this token. "
                        "It will refuse to hand out the SSH key until it is re-enrolled.")
            continue
        ssh_type = info.get('ssh_type', ('', None))[0]
        ssh_comment = info.get('ssh_comment', ('', None))[0]
        checksum = compute_ssh_key_checksum(serial, ssh_type, ssh_key, ssh_comment)
        _set_token_otpkey(conn, token_id, checksum)
        count += 1
    return count


def upgrade():
    conn = op.get_bind()
    try:
        count = backfill_ssh_key_checksums(conn)
        log.info(f"Stored the integrity checksum for {count} SSH key tokens.")
    except Exception as exx:
        log.error(f"Failed to store the integrity checksums for SSH key tokens: {exx!r}")
        raise


def downgrade():
    # Reset the OTP key field of all sshkey tokens to the encrypted empty
    # string, as it was before this migration.
    conn = op.get_bind()
    tokens = conn.execute(sa.select(token_table.c.id)
                          .where(token_table.c.tokentype == 'sshkey')).fetchall()
    for (token_id,) in tokens:
        _set_token_otpkey(conn, token_id, "")
