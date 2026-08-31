"""v3.14: Move the authentication log's reason into a table of its own

An authentication request rarely fails for exactly one reason - a user with
three tokens can have one revoked, one past its failcount and one that simply
got the wrong OTP - so the log now records *every* reason it classified,
ordered by precedence (highest signal first), instead of only the top-ranked
one.

Creates authentication_log_reason (one row per reason, cascading on its entry),
copies the existing authentication_log.reason values into it, and drops that
column.

Revision ID: f4a1c2b6d8e3
Revises: d3e8b1c47f92
Create Date: 2026-08-31 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import OperationalError, ProgrammingError

# Same type the model uses: BigInteger everywhere, but INTEGER on SQLite, so the primary key becomes
# "INTEGER PRIMARY KEY" and SQLite auto-assigns it via rowid; auth_log_id uses it too, matching the
# authentication_log.id column it references.
from privacyidea.models.utils import BigIntegerType

# revision identifiers, used by Alembic.
revision = 'f4a1c2b6d8e3'
down_revision = 'd3e8b1c47f92'
branch_labels = None
depends_on = None

TABLE = 'authentication_log_reason'
PARENT = 'authentication_log'


def _unicode_case_sensitive(length: int) -> sa.Unicode:
    """
    A case-sensitive string column type (mirrors models.utils.case_sensitive_unicode).

    MySQL/MariaDB's server-default collation is typically case-insensitive (*_ci) while SQLite, PostgreSQL and Oracle
    compare case-sensitively, so an unpinned column would match differently per backend. Kept self-contained here (not
    imported from the model) so the migration stays a stable snapshot.
    """
    return sa.Unicode(length).with_variant(mysql.VARCHAR(length, charset="utf8mb4", collation="utf8mb4_bin"),
                                           "mysql", "mariadb")


def upgrade():
    try:
        # The column length must match
        # privacyidea.models.authentication_log_reason.authentication_log_reason_column_length.
        op.create_table(
            TABLE,
            sa.Column('id', BigIntegerType, sa.Identity(always=False), nullable=False),
            sa.Column('auth_log_id', BigIntegerType, nullable=False),
            sa.Column('reason', _unicode_case_sensitive(40), nullable=False),
            sa.ForeignKeyConstraint(['auth_log_id'], [f'{PARENT}.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.Index('ix_authlog_reason_authlog', 'auth_log_id'),
            sa.Index('ix_authlog_reason_reason', 'reason', 'auth_log_id'),
        )
    except (OperationalError, ProgrammingError) as ex:
        if "already exists" in str(ex.orig).lower():
            print(f"Table '{TABLE}' already exists.")
        else:
            print(f"Could not add table '{TABLE}' to database.")
            raise

    try:
        # Carry the existing classifications over: each row's single reason becomes its first (and, for historic
        # entries, only) reason row. Done in the database rather than row by row, so a large log migrates in one
        # statement. Rows with no reason - every success - simply produce none.
        op.execute(sa.text(f"INSERT INTO {TABLE} (auth_log_id, reason) "
                           f"SELECT id, reason FROM {PARENT} WHERE reason IS NOT NULL"))
        op.drop_column(PARENT, 'reason')
    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such column" in msg or "unknown column" in msg or "does not exist" in msg:
            print(f"Column '{PARENT}.reason' already removed.")
        else:
            print(f"Could not move the reason column of '{PARENT}' into '{TABLE}'.")
            raise


def downgrade():
    # The column comes back with the highest-ranked reason of each entry, which is what it held before: the reason
    # rows ascend by precedence, so the lowest id of an entry is its top-ranked one.
    try:
        op.add_column(PARENT, sa.Column('reason', _unicode_case_sensitive(40), nullable=True))
        op.execute(sa.text(f"UPDATE {PARENT} SET reason = "
                           f"(SELECT r.reason FROM {TABLE} r WHERE r.auth_log_id = {PARENT}.id "
                           f" AND r.id = (SELECT MIN(r2.id) FROM {TABLE} r2 WHERE r2.auth_log_id = {PARENT}.id))"))
    except (OperationalError, ProgrammingError) as ex:
        if "duplicate column" in str(ex.orig).lower():
            print(f"Column '{PARENT}.reason' already exists.")
        else:
            print(f"Could not restore the column '{PARENT}.reason'.")
            raise
    # The indexes and the foreign key go with the table.
    try:
        op.drop_table(TABLE)
    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print(f"Table '{TABLE}' already removed.")
        else:
            print(f"Could not remove table '{TABLE}'.")
            raise
