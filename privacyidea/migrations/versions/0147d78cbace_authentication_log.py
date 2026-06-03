"""v3.14: Added authentication log table

Revision ID: 0147d78cbace
Revises: 7d4e9b2c1a3f
Create Date: 2026-06-01 08:37:51.884173

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

# Same type the model uses: BigInteger everywhere, but INTEGER on SQLite so the
# primary key becomes "INTEGER PRIMARY KEY" and SQLite auto-assigns it via rowid.
from privacyidea.models.utils import BigIntegerType

# revision identifiers, used by Alembic.
revision = '0147d78cbace'
down_revision = '7d4e9b2c1a3f'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # The model declares Sequence('authentication_log_seq'), so SQLAlchemy emits SELECT nextval(...) on every ORM
    # insert. Create the sequence on any backend that supports CREATE SEQUENCE (Postgres + MariaDB 10.3+).
    if bind.dialect.supports_sequences:
        op.execute("CREATE SEQUENCE IF NOT EXISTS authentication_log_seq")

    try:
        if is_postgres:
            # Postgres needs the column default wired to the sequence so raw
            # INSERTs (e.g. our data-migration block below) get an id.
            event_id_col = sa.Column(
                'event_id', BigIntegerType, nullable=False,
                server_default=sa.text("nextval('authentication_log_seq')"),
            )
        else:
            event_id_col = sa.Column('event_id', BigIntegerType, nullable=False, autoincrement=True)

        op.create_table(
            'authentication_log',
            event_id_col,
            sa.Column('resolver', sa.Unicode(length=1024), nullable=True),
            sa.Column('uid', sa.Unicode(length=1024), nullable=True),
            sa.Column('realm', sa.Unicode(length=1024), nullable=True),
            sa.Column('event_type', sa.Unicode(length=1024), nullable=False),
            sa.Column('timestamp', sa.DateTime(), nullable=False),
            sa.Column('source_ip', sa.Unicode(length=1024), nullable=True),
            sa.Column('client_label', sa.Unicode(length=1024), nullable=True),
            sa.Column('serial', sa.Unicode(length=1024), nullable=True),
            sa.Column('transaction_id', sa.Unicode(length=1024), nullable=True),
            sa.Column('other_info', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('event_id'),
        )
        op.create_index('ix_authlog_user_event_time', 'authentication_log',
                        ['resolver', 'uid', 'realm', 'event_type', 'timestamp'])
        op.create_index('ix_authlog_ip_event_time', 'authentication_log',
                        ['source_ip', 'event_type', 'timestamp'])

    except (OperationalError, ProgrammingError) as ex:
        if "already exists" in str(ex.orig).lower():
            print("Table 'authentication_log' already exists.")
        else:
            print("Could not add table 'authentication_log' to database.")
            raise

    # Advance the sequence past any existing rows. Covers the table-already-exists branch above where rows may already
    # be present and the sequence (newly created or pre-existing) would otherwise hand out a value <= MAX(event_id),
    # causing duplicate-PK errors on the next insert.
    if bind.dialect.supports_sequences:
        max_id = bind.execute(text("SELECT COALESCE(MAX(event_id), 0) FROM authentication_log")).scalar() or 0
        op.execute(f"ALTER SEQUENCE authentication_log_seq RESTART WITH {max_id + 1}")

def downgrade():
    try:
        with op.batch_alter_table('authentication_log', schema=None) as batch_op:
            batch_op.drop_index('ix_authlog_user_event_time')
            batch_op.drop_index('ix_authlog_ip_event_time')

        op.drop_table('authentication_log')
        if op.get_bind().dialect.supports_sequences:
            op.execute("DROP SEQUENCE IF EXISTS authentication_log_seq")

    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print("Table 'authentication_log' already removed.")
        else:
            print("Could not remove table 'authentication_log'.")
            raise
