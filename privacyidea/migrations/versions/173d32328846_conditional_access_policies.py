"""v3.14: Add conditional-access policy tables

Create the five tables of the conditional-access policy framework:
conditional_access_policies (the policy container), conditional_access_policy_counter_types (the
failure counter types a policy tracks, normalized for an indexed per-request
lookup), conditional_access_policy_conditions (the restrictions on which requests a policy
applies to at all), conditional_access_policy_stages (the failure thresholds within a
policy) and conditional_access_stage_actions (the reactions when a stage is triggered).

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
TABLES = ['conditional_access_stage_actions', 'conditional_access_policy_stages',
          'conditional_access_policy_conditions', 'conditional_access_policy_counter_types',
          'conditional_access_policies']

INDEXES = {
    'conditional_access_policy_counter_types': [
        ('ix_ca_counter_type_lookup', ['counter_type', 'policy_id']),
    ],
    'conditional_access_policy_conditions': [
        ('ix_conditional_access_policy_conditions_policy_id', ['policy_id']),
    ],
    'conditional_access_stage_actions': [
        ('ix_conditional_access_stage_actions_stage_id', ['stage_id']),
    ],
}


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


def _existing_tables() -> set[str]:
    """
    The names of the tables that already exist, lower-cased.

    Reflected once per migration rather than once per table: on a normal run nothing exists yet, so this
    single catalog read is all the guard below costs. Lower-cased because Oracle folds unquoted identifiers
    to upper case and the inspector reflects them back lower-cased (mirrors models.db.sequence_exists).
    """
    return {name.lower() for name in sa.inspect(op.get_bind()).get_table_names()}


def _create_table(existing_tables: set[str], table_name: str, *columns) -> None:
    """
    Create the table unless it is already there, then add each of its INDEXES that is absent.

    Presence is established by reflection rather than by swallowing an "already exists" error, which Oracle
    never says: it reports an existing object as ORA-00955 ("name is already used by an existing object").
    models.db.sequence_exists reflects for the same reason.

    The indexes are created by statements of their own and are deliberately not declared inline in the
    CREATE TABLE: every statement here autocommits (see migrations/env.py), so a run that created the table
    and then failed would leave the table behind, and a guard that keyed the indexes off the table's absence
    would skip them for good once Alembic stamped the revision.
    """
    if table_name.lower() in existing_tables:
        print(f"Table '{table_name}' already exists.")
        existing_indexes = {(index["name"] or "").lower()
                            for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
    else:
        op.create_table(table_name, *columns)
        existing_indexes = set()

    for index_name, index_columns in INDEXES.get(table_name, ()):
        if index_name.lower() in existing_indexes:
            print(f"Index '{index_name}' already exists.")
        else:
            op.create_index(index_name, table_name, index_columns)


def upgrade():
    existing_tables = _existing_tables()
    _create_table(
        existing_tables,
        'conditional_access_policies',
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
        sa.UniqueConstraint('priority', name='uq_ca_policy_priority'),
    )
    _create_table(
        existing_tables,
        'conditional_access_policy_counter_types',
        _id_column(),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('counter_type', sa.Unicode(length=100), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['conditional_access_policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_id', 'counter_type', name='uq_ca_counter_type_policy'),
    )
    _create_table(
        existing_tables,
        'conditional_access_policy_conditions',
        _id_column(),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('condition_type', sa.Unicode(length=50), nullable=False),
        sa.Column('operator', sa.Unicode(length=20), nullable=False),
        sa.Column('value', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['policy_id'], ['conditional_access_policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        # A policy carries at most one condition of each type; they are ANDed, so a
        # second one on the same value could only narrow to a contradiction.
        sa.UniqueConstraint('policy_id', 'condition_type', name='uq_ca_condition_policy'),
    )
    _create_table(
        existing_tables,
        'conditional_access_policy_stages',
        _id_column(),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Unicode(length=255), nullable=True),
        sa.Column('error_message', sa.Unicode(length=500), nullable=True),
        sa.Column('failure_threshold', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['conditional_access_policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_id', 'failure_threshold',
                            name='uq_ca_stage_policy_threshold'),
    )
    _create_table(
        existing_tables,
        'conditional_access_stage_actions',
        _id_column(),
        sa.Column('stage_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.Unicode(length=100), nullable=False),
        sa.Column('action_value', sa.JSON(), nullable=True),
        sa.Column('retrigger_above_threshold', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['stage_id'], ['conditional_access_policy_stages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    # Drop children before parents because of the foreign keys.
    # The indexes, foreign keys and identities all go with their table.
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
