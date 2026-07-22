"""v3.14: Add user_lockout_state live-state table

Create the user_lockout_state table that records the current locked status
of a user, keyed by the same (resolver, uid, realm) tuple used in
authentication_log. There is deliberately no failure-counter column: failure
counts are derived by querying authentication_log over the policy's time
window. The load-bearing field is lock_expires_at - a row whose
lock_expires_at lies in the future means the user is currently locked.

Revision ID: c1a9f7e2b840
Revises: 173d32328846
Create Date: 2026-06-08 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'c1a9f7e2b840'
down_revision = '173d32328846'
branch_labels = None
depends_on = None

TABLES = ['user_lockout_state']


def _unicode_case_sensitive(length):
    """
    A case-sensitive string column type (mirrors models.authentication_log._case_sensitive_unicode).

    The identity columns (resolver/uid/realm/username) are the user-lockout visibility boundary: a
    user-scoped read policy filters on them. On MySQL/MariaDB the server-default collation is typically
    case-insensitive (*_ci), which would make that boundary match case-insensitively -- a fail-open
    authorization risk. Pinning to utf8mb4_bin makes matching case-sensitive; SQLite, PostgreSQL and Oracle
    already compare case-sensitively by default. Kept self-contained here so the migration stays a stable
    snapshot.
    """
    return sa.Unicode(length).with_variant(mysql.VARCHAR(length, charset="utf8mb4", collation="utf8mb4_bin"),
                                           "mysql", "mariadb")


def _create_table(table_name, *columns):
    try:
        op.create_table(table_name, *columns)
    except (OperationalError, ProgrammingError) as ex:
        if "already exists" in str(ex.orig).lower():
            print(f"Table '{table_name}' already exists.")
        else:
            print(f"Could not add table '{table_name}' to database.")
            raise


def upgrade():
    _create_table(
        'user_lockout_state',
        sa.Column('resolver', _unicode_case_sensitive(120), nullable=False),
        sa.Column('uid', _unicode_case_sensitive(320), nullable=False),
        sa.Column('realm', _unicode_case_sensitive(255), nullable=False),
        sa.Column('username', _unicode_case_sensitive(255), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False),
        sa.Column('lock_expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_stage_triggered', sa.Integer(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['last_stage_triggered'], ['lockout_policy_stages.id'],
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('resolver', 'uid', 'realm'),
        sa.Index('ix_user_lockout_state_last_stage_triggered', 'last_stage_triggered'),
    )


def downgrade():
    for table_name in TABLES:
        try:
            op.drop_table(table_name)
        except (OperationalError, ProgrammingError) as ex:
            msg = str(ex.orig).lower()
            if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
                print(f"Table '{table_name}' already removed.")
            else:
                print(f"Could not remove table '{table_name}'.")
                raise
