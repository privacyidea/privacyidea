"""v3.14: Add usersetting table for per-principal frontend settings

Revision ID: d4f5a6b7c8e9
Revises: 7d4e9b2c1a3f
Create Date: 2026-06-18 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text, Sequence
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.schema import CreateSequence

from privacyidea.models.db import build_restart_sequence_sql

# revision identifiers, used by Alembic.
revision = 'd4f5a6b7c8e9'
down_revision = '7d4e9b2c1a3f'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # The model declares Sequence('usersetting_seq'), so SQLAlchemy emits
    # SELECT nextval(...) on every ORM insert. Create the sequence on any
    # backend that supports CREATE SEQUENCE (Postgres + MariaDB 10.3+) via
    # SQLAlchemy's CreateSequence construct, which the increment_by_zero
    # @compiles hook rewrites to append INCREMENT BY 0 on MariaDB so a Galera
    # cluster accepts the cached sequence. A raw "CREATE SEQUENCE" string would
    # bypass that hook.
    if bind.dialect.supports_sequences:
        op.execute(CreateSequence(Sequence("usersetting_seq"), if_not_exists=True))

    try:
        if is_postgres:
            id_column = sa.Column(
                'id', sa.Integer(), nullable=False,
                server_default=sa.text("nextval('usersetting_seq')"),
            )
        else:
            id_column = sa.Column('id', sa.Integer(), nullable=False, autoincrement=True)
        op.create_table(
            'usersetting',
            id_column,
            sa.Column('subject_type', sa.Unicode(length=20), nullable=False),
            sa.Column('username', sa.Unicode(length=320), nullable=True),
            sa.Column('user_id', sa.Unicode(length=320), nullable=True),
            sa.Column('resolver', sa.Unicode(length=120), nullable=True),
            sa.Column('realm_id', sa.Integer(), nullable=True),
            sa.Column('settings', sa.JSON(), nullable=True),
            sa.Column('last_modified', sa.DateTime(), nullable=True),
            sa.Column('node', sa.Unicode(length=120), nullable=True),
            sa.ForeignKeyConstraint(['realm_id'], ['realm.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('subject_type', 'username', 'user_id', 'resolver', 'realm_id',
                                name='uq_usersetting_subject'),
        )
    except (OperationalError, ProgrammingError) as ex:
        if "already exists" in str(ex.orig).lower():
            print("Table 'usersetting' already exists.")
        else:
            print("Could not add table 'usersetting' to database.")
            raise

    # Advance the sequence past any existing rows (covers the
    # table-already-exists branch where the sequence would otherwise hand out a
    # value <= MAX(id)). build_restart_sequence_sql emits each dialect's syntax
    # and appends INCREMENT BY 0 on MariaDB for Galera.
    if bind.dialect.supports_sequences:
        max_id = bind.execute(
            text("SELECT COALESCE(MAX(id), 0) FROM usersetting")
        ).scalar() or 0
        op.execute(build_restart_sequence_sql("usersetting_seq", max_id + 1, bind.dialect.name))


def downgrade():
    try:
        op.drop_table('usersetting')
        if op.get_bind().dialect.supports_sequences:
            op.execute("DROP SEQUENCE IF EXISTS usersetting_seq")
    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print("Table 'usersetting' already removed.")
        else:
            print("Could not remove table 'usersetting'.")
            raise
