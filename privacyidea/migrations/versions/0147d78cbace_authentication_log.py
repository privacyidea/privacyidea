"""v3.14: Add authentication log table

Revision ID: 0147d78cbace
Revises: a1b2c3d4e5f6
Create Date: 2026-06-01 08:37:51.884173

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text, inspect, Sequence
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.schema import CreateSequence, DropSequence

from privacyidea.models.db import build_restart_sequence_sql
# Same type the model uses: BigInteger everywhere, but INTEGER on SQLite so the
# primary key becomes "INTEGER PRIMARY KEY" and SQLite auto-assigns it via rowid.
from privacyidea.models.utils import BigIntegerType

# revision identifiers, used by Alembic.
revision = '0147d78cbace'
down_revision = 'a1b2c3d4e5f6'
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
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # The model declares Sequence('authentication_log_seq'), so SQLAlchemy emits SELECT nextval(...) on every ORM
    # insert. Create the sequence on any backend that supports CREATE SEQUENCE (Postgres + MariaDB 10.3+).
    # Build it through SQLAlchemy's CreateSequence construct rather than a raw "CREATE SEQUENCE" string:
    # CreateSequence is rewritten by the increment_by_zero @compiles hook in privacyidea.models.db, which appends
    # INCREMENT BY 0 on MariaDB so a Galera cluster accepts the cached sequence. A raw string bypasses the hook and
    # fails with "CACHE without INCREMENT BY 0 in Galera cluster".
    if bind.dialect.supports_sequences:
        if bind.dialect.name == "oracle":
            # Oracle (19c+) has no "CREATE SEQUENCE IF NOT EXISTS" (23c-only), so reflect the
            # existing sequences (upper-cased on Oracle, compared lower-case) and create ours
            # only when absent.
            existing = {name.lower() for name in inspect(bind).get_sequence_names()}
            if "authentication_log_seq" not in existing:
                op.execute(CreateSequence(Sequence("authentication_log_seq")))
        else:
            op.execute(CreateSequence(Sequence("authentication_log_seq"), if_not_exists=True))

    try:
        if is_postgres:
            # Postgres needs the column default wired to the sequence so raw
            # INSERTs (e.g. our data-migration block below) get an id.
            id_column = sa.Column(
                'id', BigIntegerType, nullable=False,
                server_default=sa.text("nextval('authentication_log_seq')"),
            )
        else:
            id_column = sa.Column('id', BigIntegerType, nullable=False, autoincrement=True)

        # The column lengths must match privacyidea.models.authentication_log.authentication_log_column_length.
        # The columns in the composite index below (resolver, uid, realm, event_type) are kept small enough that the
        # index stays below the 3072-byte InnoDB key limit of MySQL/MariaDB with utf8mb4:
        # (120+320+255+40)*4 + 8 (timestamp) = 2948 bytes. The non-indexed columns (client_label, serial) are sized
        # generously to avoid truncation. transaction_id (indexed below) matches the challenge table's 64 chars.
        op.create_table(
            'authentication_log',
            id_column,
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
            sa.Column('previous_transaction_id', _unicode_case_sensitive(64), nullable=True),
            sa.Column('attempt_id', _unicode_case_sensitive(64), nullable=True),
            sa.Column('other_info', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_authlog_user_event_time', 'authentication_log',
                        ['resolver', 'uid', 'realm', 'event_type', 'timestamp'])
        op.create_index('ix_authlog_ip_event_time', 'authentication_log',
                        ['source_ip', 'event_type', 'timestamp'])
        # Serves the attempt_id recovery lookup by transaction_id (see get_attempt_id_for_transaction).
        op.create_index('ix_authlog_transaction', 'authentication_log',
                        ['transaction_id'])

    except (OperationalError, ProgrammingError) as ex:
        if "already exists" in str(ex.orig).lower():
            print("Table 'authentication_log' already exists.")
        else:
            print("Could not add table 'authentication_log' to database.")
            raise

    # Advance the sequence past any existing rows. Covers the table-already-exists branch above where rows may already
    # be present and the sequence (newly created or pre-existing) would otherwise hand out a value <= MAX(id),
    # causing duplicate-PK errors on the next insert.
    if bind.dialect.supports_sequences:
        max_id = bind.execute(text("SELECT COALESCE(MAX(id), 0) FROM authentication_log")).scalar() or 0
        # No SQLAlchemy DDL construct exists for ALTER SEQUENCE ... RESTART, so a
        # raw string would only be correct on one backend. build_restart_sequence_sql
        # emits each dialect's accepted syntax and, crucially, appends INCREMENT BY 0
        # on MariaDB — a Galera cluster otherwise rejects RESTART on a cached sequence
        # with "CACHE without INCREMENT BY 0 in Galera cluster".
        op.execute(build_restart_sequence_sql("authentication_log_seq", max_id + 1, bind.dialect.name))

def downgrade():
    try:
        with op.batch_alter_table('authentication_log', schema=None) as batch_op:
            batch_op.drop_index('ix_authlog_user_event_time')
            batch_op.drop_index('ix_authlog_ip_event_time')
            batch_op.drop_index('ix_authlog_transaction')

        op.drop_table('authentication_log')
        bind = op.get_bind()
        if bind.dialect.supports_sequences:
            if bind.dialect.name == "oracle":
                # Oracle (19c+) has no "DROP SEQUENCE IF EXISTS"; reflect and drop only if present.
                existing = {name.lower() for name in inspect(bind).get_sequence_names()}
                if "authentication_log_seq" in existing:
                    op.execute(DropSequence(Sequence("authentication_log_seq")))
            else:
                op.execute("DROP SEQUENCE IF EXISTS authentication_log_seq")

    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print("Table 'authentication_log' already removed.")
        else:
            print("Could not remove table 'authentication_log'.")
            raise
