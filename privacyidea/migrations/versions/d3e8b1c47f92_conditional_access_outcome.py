"""v3.14: Add conditional_access_outcome table

Create the conditional_access_outcome table: the history of what conditional
access did. One row per action the engine executed for a request (LOCK_USER_TEMPORARY,
BLOCK_IP_TEMPORARY, EMAIL_*, and the pre-auth DENY decision), plus dry-run rows recording
what a dry-run policy would have done.

This is the queryable counterpart of the live state in user_lockout_state and
block_list, which show the restriction currently in force and then forget it:
only this table can answer "when was this user locked, by which policy, and for
how long". Each row belongs to the authentication_log row of the request that
caused it and is read together with it, which is why the subject (resolver, uid,
realm, username, source IP) and the timestamp are not repeated here.

Revision ID: d3e8b1c47f92
Revises: b2f5c9e1a7d4
Create Date: 2026-08-07 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import OperationalError, ProgrammingError

# Same type the model uses: BigInteger everywhere, but INTEGER on SQLite so the primary key becomes
# "INTEGER PRIMARY KEY" and SQLite auto-assigns it via rowid. auth_log_id uses it too, so it matches the
# authentication_log.id column it references.
from privacyidea.models.utils import BigIntegerType

# revision identifiers, used by Alembic.
revision = 'd3e8b1c47f92'
down_revision = 'b2f5c9e1a7d4'
branch_labels = None
depends_on = None

TABLE = 'conditional_access_outcome'


def _unicode_case_sensitive(length: int) -> sa.Unicode:
    """
    A case-sensitive string column type (mirrors models.utils.case_sensitive_unicode).

    MySQL/MariaDB's server-default collation is typically case-insensitive (*_ci) while SQLite, PostgreSQL and Oracle
    compare case-sensitively, so an unpinned column would match differently per backend -- e.g. action_type ==
    'lock_user_temporary' hitting a 'LOCK_USER_TEMPORARY' row on one database only. Pinning to utf8mb4_bin gives one
    uniform rule everywhere. Kept self-contained here (not imported from the model) so the migration stays a stable
    snapshot.
    """
    return sa.Unicode(length).with_variant(mysql.VARCHAR(length, charset="utf8mb4", collation="utf8mb4_bin"),
                                           "mysql", "mariadb")


def upgrade():
    try:
        # The column lengths must match
        # privacyidea.models.conditional_access_outcome.conditional_access_outcome_column_length.
        op.create_table(
            TABLE,
            sa.Column('id', BigIntegerType, sa.Identity(always=False), nullable=False),
            sa.Column('auth_log_id', BigIntegerType, nullable=False),
            sa.Column('action_type', _unicode_case_sensitive(100), nullable=False),
            sa.Column('dry_run', sa.Boolean(), nullable=False),
            sa.Column('policy_name', _unicode_case_sensitive(255), nullable=False),
            sa.Column('threshold', sa.Integer(), nullable=False),
            sa.Column('event_count', sa.Integer(), nullable=False),
            sa.Column('stage_name', _unicode_case_sensitive(255), nullable=True),
            sa.Column('info', sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(['auth_log_id'], ['authentication_log.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.Index('ix_ca_outcome_authlog', 'auth_log_id'),
            sa.Index('ix_ca_outcome_action', 'action_type'),
        )
    except (OperationalError, ProgrammingError) as ex:
        if "already exists" in str(ex.orig).lower():
            print(f"Table '{TABLE}' already exists.")
        else:
            print(f"Could not add table '{TABLE}' to database.")
            raise


def downgrade():
    # The indexes, the foreign key and the identity all go with the table.
    try:
        op.drop_table(TABLE)
    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print(f"Table '{TABLE}' already removed.")
        else:
            print(f"Could not remove table '{TABLE}'.")
            raise
