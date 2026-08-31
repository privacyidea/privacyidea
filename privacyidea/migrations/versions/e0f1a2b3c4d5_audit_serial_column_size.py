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
import sqlalchemy as sa
from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'e0f1a2b3c4d5'
down_revision = 'd9e0f1a2b3c4'
branch_labels = None
depends_on = None


def upgrade():
    try:
        with op.batch_alter_table('pidea_audit', schema=None) as batch_op:
            batch_op.alter_column('serial',
                                  existing_type=sa.VARCHAR(length=40),
                                  type_=sa.Unicode(length=200),
                                  existing_nullable=True)
    except (OperationalError, ProgrammingError) as exx:
        print("Could not increase 'serial' column size in 'pidea_audit' table.")
        print(exx)


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
