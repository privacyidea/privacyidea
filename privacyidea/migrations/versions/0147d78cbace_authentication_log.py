"""v3.14: Add authentication log table

Revision ID: 0147d78cbace
Revises: b8c9d0e1f2a3
Create Date: 2026-06-01 08:37:51.884173

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import OperationalError, ProgrammingError

# Same type the model uses: BigInteger everywhere, but INTEGER on SQLite so the
# primary key becomes "INTEGER PRIMARY KEY" and SQLite auto-assigns it via rowid.
from privacyidea.models.utils import BigIntegerType

# revision identifiers, used by Alembic.
revision = '0147d78cbace'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def _unicode_case_sensitive(length):
    """
    A case-sensitive string column type (mirrors models.authentication_log._case_sensitive_unicode).

    On MySQL/MariaDB the server-default collation is typically case-insensitive (*_ci), which would make the
    authentication-log visibility boundary (realm/resolver/username) match case-insensitively -- a fail-open
    authorization risk. Pinning to utf8mb4_bin makes matching case-sensitive; SQLite, PostgreSQL and Oracle already
    compare case-sensitively by default.
    Kept self-contained here (not imported from the model) so the migration stays a stable snapshot.
    """
    return sa.Unicode(length).with_variant(mysql.VARCHAR(length, charset="utf8mb4", collation="utf8mb4_bin"),
                                           "mysql", "mariadb")


def upgrade():
    try:
        # Column lengths must match privacyidea.models.authentication_log.authentication_log_column_length. The
        # composite-index columns (resolver, uid, realm, event_type) stay under MySQL/MariaDB's 3072-byte utf8mb4
        # InnoDB key limit: (120+320+255+40)*4 + 8 (timestamp) = 2948 bytes.
        op.create_table(
            'authentication_log',
            sa.Column('id', BigIntegerType, sa.Identity(always=False), nullable=False),
            sa.Column('resolver', _unicode_case_sensitive(120), nullable=True),
            sa.Column('uid', _unicode_case_sensitive(320), nullable=True),
            sa.Column('realm', _unicode_case_sensitive(255), nullable=True),
            sa.Column('username', _unicode_case_sensitive(255), nullable=True),
            sa.Column('user_role', _unicode_case_sensitive(30), nullable=True),
            sa.Column('event_type', _unicode_case_sensitive(40), nullable=False),
            sa.Column('timestamp', sa.DateTime(), nullable=False),
            sa.Column('source_ip', _unicode_case_sensitive(50), nullable=True),
            sa.Column('client_label', _unicode_case_sensitive(1024), nullable=True),
            sa.Column('serial', _unicode_case_sensitive(1024), nullable=True),
            sa.Column('transaction_id', _unicode_case_sensitive(64), nullable=True),
            sa.Column('attempt_id', _unicode_case_sensitive(64), nullable=True),
            sa.Column('other_info', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_authlog_user_event_time', 'authentication_log',
                        ['resolver', 'uid', 'realm', 'event_type', 'timestamp'])
        op.create_index('ix_authlog_ip_event_time', 'authentication_log',
                        ['source_ip', 'event_type', 'timestamp'])
        # Serves PER_ATTEMPT counting (count_user_attempts / count_ip_attempts): a subject's rows range-scanned by
        # time, no event_type predicate.
        op.create_index('ix_authlog_user_time', 'authentication_log',
                        ['resolver', 'uid', 'realm', 'timestamp'])
        op.create_index('ix_authlog_ip_time', 'authentication_log',
                        ['source_ip', 'timestamp'])
        # Serves the deployment-wide reads that carry no subject predicate: the authentication-log statistics query
        # behind the dashboard's activity widget, and the retention delete in `pi-manage authlog cleanup`. The four
        # indexes above cannot, since each leads with a subject column that such a query leaves unconstrained.
        op.create_index('ix_authlog_time', 'authentication_log', ['timestamp'])

    except (OperationalError, ProgrammingError) as ex:
        if "already exists" in str(ex.orig).lower():
            print("Table 'authentication_log' already exists.")
        else:
            print("Could not add table 'authentication_log' to database.")
            raise


def downgrade():
    try:
        with op.batch_alter_table('authentication_log', schema=None) as batch_op:
            batch_op.drop_index('ix_authlog_user_event_time')
            batch_op.drop_index('ix_authlog_ip_event_time')
            batch_op.drop_index('ix_authlog_user_time')
            batch_op.drop_index('ix_authlog_ip_time')
            batch_op.drop_index('ix_authlog_time')

        op.drop_table('authentication_log')

    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print("Table 'authentication_log' already removed.")
        else:
            print("Could not remove table 'authentication_log'.")
            raise
