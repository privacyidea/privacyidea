"""v3.14: Add conditional access lockout policy tables

Create the five tables of the lockout policy framework:
lockout_policies (the policy container), lockout_policy_counter_types (the
failure counter types a policy tracks, normalized for an indexed per-request
lookup), lockout_policy_conditions (the restrictions on which requests a policy
applies to at all), lockout_policy_stages (the failure thresholds within a
policy) and lockout_stage_actions (the reactions when a stage is triggered).

Revision ID: 173d32328846
Revises: 0147d78cbace
Create Date: 2026-06-03 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = '173d32328846'
down_revision = '0147d78cbace'
branch_labels = None
depends_on = None

# Drop order: children before parents (foreign keys).
TABLES = ['lockout_stage_actions', 'lockout_policy_stages',
          'lockout_policy_conditions', 'lockout_policy_counter_types',
          'lockout_policies']


def _id_column():
    """
    The primary-key ``id`` column, assigned by the server. The models declare
    ``Identity(always=False)``, which PostgreSQL and Oracle render as GENERATED
    BY DEFAULT AS IDENTITY, MySQL/MariaDB as AUTO_INCREMENT and SQLite as its
    rowid -- one id source per column, used by the ORM and by any raw INSERT
    alike, with no sequence to create, advance or drop per dialect. BY DEFAULT
    rather than ALWAYS so an explicit id can still be inserted (mirrors the
    authentication_log migration).
    """
    return sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False)


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
        'lockout_policies',
        _id_column(),
        sa.Column('name', sa.Unicode(length=255), nullable=False),
        sa.Column('time_window_seconds', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('dry_run', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('count_mode', sa.Unicode(length=20), nullable=False),
        sa.Column('reset_on_success', sa.Boolean(), nullable=False),
        sa.Column('target', sa.Unicode(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('priority', name='uq_lockout_policy_priority'),
    )
    _create_table(
        'lockout_policy_counter_types',
        _id_column(),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('counter_type', sa.Unicode(length=100), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['lockout_policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_id', 'counter_type', name='uq_lockout_counter_type_policy'),
        sa.Index('ix_lockout_counter_type_lookup', 'counter_type', 'policy_id'),
    )
    _create_table(
        'lockout_policy_conditions',
        _id_column(),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('condition_type', sa.Unicode(length=50), nullable=False),
        sa.Column('operator', sa.Unicode(length=20), nullable=False),
        sa.Column('value', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['policy_id'], ['lockout_policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        # A policy carries at most one condition of each type; they are ANDed, so a
        # second one on the same value could only narrow to a contradiction.
        sa.UniqueConstraint('policy_id', 'condition_type', name='uq_lockout_condition_policy'),
        sa.Index('ix_lockout_policy_conditions_policy_id', 'policy_id'),
    )
    _create_table(
        'lockout_policy_stages',
        _id_column(),
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
        _id_column(),
        sa.Column('stage_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.Unicode(length=100), nullable=False),
        sa.Column('action_value', sa.JSON(), nullable=True),
        sa.Column('retrigger_above_threshold', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['stage_id'], ['lockout_policy_stages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_lockout_stage_actions_stage_id', 'stage_id'),
    )


def downgrade():
    # Drop children before parents because of the foreign keys. The indexes, the
    # foreign keys and the identities all go with their table.
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
