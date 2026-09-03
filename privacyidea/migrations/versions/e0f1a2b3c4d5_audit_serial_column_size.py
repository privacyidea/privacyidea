"""v3.14: Increase the audit serial column size to hold a list of serials

One audit entry can name every token that was involved in a request, e.g. all tokens that were
challenged in a challenge-response authentication. With 40 characters, three tokens with default
serials already filled the column and the serials of a fourth one were shortened, which left an
incomplete record of the tokens an authentication was attempted with.

If the audit log is written to a separate database (PI_AUDIT_SQL_URI), this migration does not
reach it - it runs against the token database. Apply the same change to the audit database, see
READ_BEFORE_UPDATE.md.

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-08-17 00:00:00.000000

"""
import time

import sqlalchemy as sa
from alembic import op
from sqlalchemy.exc import DatabaseError

# revision identifiers, used by Alembic.
revision = 'e0f1a2b3c4d5'
down_revision = 'd9e0f1a2b3c4'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # MySQL and MariaDB can not widen the column in place, they copy the whole table. That
    # takes minutes for a large audit log without reporting any progress, so the number of
    # entries is announced beforehand to tell a long-running migration from a hanging one.
    # The other dialects change the column definition alone, where counting the entries
    # would cost more than the migration itself.
    counts_entries = bind.dialect.name in ('mysql', 'mariadb')
    started = time.monotonic()
    try:
        if counts_entries:
            entry_count = bind.execute(sa.text("SELECT COUNT(*) FROM pidea_audit")).scalar()
            print(f"Updating the 'serial' column of {entry_count} audit entries. The table is rebuilt, "
                  f"which can take several minutes for a large audit log.")
        with op.batch_alter_table('pidea_audit', schema=None) as batch_op:
            batch_op.alter_column('serial',
                                  existing_type=sa.VARCHAR(length=40),
                                  type_=sa.Unicode(length=200),
                                  existing_nullable=True)
    except DatabaseError as exx:
        print("Could not increase 'serial' column size in 'pidea_audit' table.")
        print(exx)
        return
    if counts_entries:
        print(f"Updated the 'serial' column of {entry_count} audit entries in "
              f"{time.monotonic() - started:.0f} seconds.")


def downgrade():
    # Narrowing the column fails for every entry that names more tokens than the old column
    # can hold, so the stored values are shortened first. The information that is cut off is
    # lost, which is why this is a downgrade only.
    op.execute(sa.text("UPDATE pidea_audit SET serial = SUBSTR(serial, 1, 40)"
                       " WHERE LENGTH(serial) > 40"))
    with op.batch_alter_table('pidea_audit', schema=None) as batch_op:
        batch_op.alter_column('serial',
                              existing_type=sa.Unicode(length=200),
                              type_=sa.VARCHAR(length=40),
                              existing_nullable=True)
