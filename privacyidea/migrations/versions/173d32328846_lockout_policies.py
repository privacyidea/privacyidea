"""v3.14: Add conditional access lockout policy tables

Create the four tables of the lockout policy framework:
lockout_policies (the policy container), lockout_policy_counter_types (the
failure counter types a policy tracks, normalized for an indexed per-request
lookup), lockout_policy_stages (the failure thresholds within a policy) and
lockout_stage_actions (the reactions when a stage is triggered).

Revision ID: 173d32328846
Revises: 0147d78cbace
Create Date: 2026-06-03 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, Sequence
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.schema import CreateSequence, DropSequence

from privacyidea.models.db import build_restart_sequence_sql

# revision identifiers, used by Alembic.
revision = '173d32328846'
down_revision = '0147d78cbace'
branch_labels = None
depends_on = None

# The models declare Sequence('<name>_seq') on their id columns, so
# SQLAlchemy emits SELECT nextval(...) on every ORM insert on backends
# that support sequences (Postgres + MariaDB 10.3+).
SEQUENCES = ['lockoutpolicy_seq', 'lockoutpolicycountertype_seq',
             'lockoutpolicystage_seq', 'lockoutstageaction_seq']
# Drop order: children before parents (foreign keys).
TABLES = ['lockout_stage_actions', 'lockout_policy_stages',
          'lockout_policy_counter_types', 'lockout_policies']
# Each table's id column is backed by the sequence its model declares.
TABLE_SEQUENCES = {
    'lockout_policies': 'lockoutpolicy_seq',
    'lockout_policy_counter_types': 'lockoutpolicycountertype_seq',
    'lockout_policy_stages': 'lockoutpolicystage_seq',
    'lockout_stage_actions': 'lockoutstageaction_seq',
}


def _id_column(is_postgres, seq_name):
    """
    The primary-key ``id`` column. On PostgreSQL the column default is wired to
    the model-declared sequence (``nextval``) so that raw INSERTs draw the id
    from the *same* sequence the ORM uses. Without this, Postgres would create an
    implicit SERIAL sequence in addition to ``seq_name``, and the two could hand
    out colliding ids (duplicate-PK errors). Other backends use the regular
    autoincrement path (mirrors the authentication_log migration).
    """
    if is_postgres:
        return sa.Column('id', sa.Integer(), nullable=False,
                         server_default=sa.text(f"nextval('{seq_name}')"))
    return sa.Column('id', sa.Integer(), nullable=False, autoincrement=True)


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
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    # Build each sequence through SQLAlchemy's CreateSequence construct rather than a raw "CREATE SEQUENCE" string:
    # CreateSequence is rewritten by the increment_by_zero @compiles hook in privacyidea.models.db, which appends
    # INCREMENT BY 0 on MariaDB so a Galera cluster accepts the cached sequence. A raw string bypasses the hook and
    # fails with "CACHE without INCREMENT BY 0 in Galera cluster".
    if bind.dialect.supports_sequences:
        if bind.dialect.name == "oracle":
            # Oracle (19c+) has no "CREATE SEQUENCE IF NOT EXISTS" (23c-only), so reflect the
            # existing sequences (upper-cased on Oracle, compared lower-case) and create only
            # those that are absent.
            existing = {name.lower() for name in inspect(bind).get_sequence_names()}
            for seq in SEQUENCES:
                if seq.lower() not in existing:
                    op.execute(CreateSequence(Sequence(seq)))
        else:
            for seq in SEQUENCES:
                op.execute(CreateSequence(Sequence(seq), if_not_exists=True))

    _create_table(
        'lockout_policies',
        _id_column(is_postgres, 'lockoutpolicy_seq'),
        sa.Column('name', sa.Unicode(length=255), nullable=False),
        sa.Column('time_window_seconds', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('dry_run', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('target', sa.Unicode(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    _create_table(
        'lockout_policy_counter_types',
        _id_column(is_postgres, 'lockoutpolicycountertype_seq'),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('counter_type', sa.Unicode(length=100), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['lockout_policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_id', 'counter_type', name='uq_lockout_counter_type_policy'),
        sa.Index('ix_lockout_counter_type_lookup', 'counter_type', 'policy_id'),
    )
    _create_table(
        'lockout_policy_stages',
        _id_column(is_postgres, 'lockoutpolicystage_seq'),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Unicode(length=255), nullable=True),
        sa.Column('failure_threshold', sa.Integer(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['lockout_policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_id', 'failure_threshold',
                            name='uq_lockout_stage_policy_threshold'),
    )
    _create_table(
        'lockout_stage_actions',
        _id_column(is_postgres, 'lockoutstageaction_seq'),
        sa.Column('stage_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.Unicode(length=100), nullable=False),
        sa.Column('action_value', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['stage_id'], ['lockout_policy_stages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_lockout_stage_actions_stage_id', 'stage_id'),
    )

    # Advance each sequence past any rows already present. Covers the
    # table-already-exists branch in _create_table: a freshly created sequence
    # starts at 1 and would otherwise hand out a value <= MAX(id), causing
    # duplicate-PK errors on the next insert (mirrors the authentication_log
    # migration).
    if bind.dialect.supports_sequences:
        for table_name, seq in TABLE_SEQUENCES.items():
            max_id = bind.execute(
                sa.text(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}")).scalar() or 0
            # No SQLAlchemy DDL construct exists for ALTER SEQUENCE ... RESTART, so a
            # raw string would only be correct on one backend. build_restart_sequence_sql
            # emits each dialect's accepted syntax and, crucially, appends INCREMENT BY 0
            # on MariaDB — a Galera cluster otherwise rejects RESTART on a cached sequence
            # with "CACHE without INCREMENT BY 0 in Galera cluster".
            op.execute(build_restart_sequence_sql(seq, max_id + 1, bind.dialect.name))


def downgrade():
    # Drop children before parents because of the foreign keys.
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
    bind = op.get_bind()
    if bind.dialect.supports_sequences:
        if bind.dialect.name == "oracle":
            # Oracle (19c+) has no "DROP SEQUENCE IF EXISTS"; reflect and drop only those present.
            existing = {name.lower() for name in inspect(bind).get_sequence_names()}
            for seq in SEQUENCES:
                if seq.lower() in existing:
                    op.execute(DropSequence(Sequence(seq)))
        else:
            for seq in SEQUENCES:
                op.execute(f"DROP SEQUENCE IF EXISTS {seq}")
