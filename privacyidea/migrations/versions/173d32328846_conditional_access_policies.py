"""v3.14: Add conditional-access policy tables

Create the five tables of the conditional-access policy framework:
conditional_access_policies (the policy container), conditional_access_policy_counter_types (the
failure counter types a policy tracks, normalized for an indexed per-request
lookup), conditional_access_policy_conditions (the restrictions on which requests a policy
applies to at all), conditional_access_policy_stages (the failure thresholds within a
policy) and conditional_access_stage_actions (the reactions when a stage is triggered).

conditional_access_policies.enforced_since records the instant a policy started enforcing (NULL while
dry_run is set), so a policy leaving dry-run is not judged against failures accumulated during the trial - see
privacyidea.lib.conditional_access.engine._effective_window_seconds. Folded into this still-unreleased
revision rather than added as a new one; a dev/test DB that already ran the create_table form of this
revision gets the column added and backfilled by _add_enforced_since_column below.

Revision ID: 173d32328846
Revises: 0147d78cbace
Create Date: 2026-06-03 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError

from privacyidea.models.utils import utc_now

# revision identifiers, used by Alembic.
revision = '173d32328846'
down_revision = '0147d78cbace'
branch_labels = None
depends_on = None

# Drop order: children before parents (foreign keys).
TABLES = ['conditional_access_stage_actions', 'conditional_access_policy_stages',
          'conditional_access_policy_conditions', 'conditional_access_policy_counter_types',
          'conditional_access_policies']


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


def _add_enforced_since_column():
    """
    Add ``enforced_since`` to ``conditional_access_policies`` and backfill it for existing rows, for a
    database that already ran an earlier form of this revision without the column (create_table above then
    printed "already exists" and returned without it).

    Backfilled from Python's ``utc_now()``, not the SQL ``CURRENT_TIMESTAMP``: the column is compared against
    ``utc_now()`` everywhere else (see ``engine._effective_window_seconds``), and ``CURRENT_TIMESTAMP`` is the
    DB server's own clock/timezone, which need not be UTC. dry_run policies are left ``NULL`` (unchanged);
    already-enforced policies get ``now()``, a reasonable approximation for policies that were enforcing
    before this column existed.
    """
    try:
        op.add_column('conditional_access_policies', sa.Column('enforced_since', sa.DateTime(), nullable=True))
    except (OperationalError, ProgrammingError) as exx:
        if any(x in str(exx.orig).lower() for x in ["already exists", "duplicate column name"]):
            print("Ok, column 'enforced_since' already exists.")
            return
        else:
            print(exx)
            raise
    except Exception as exx:
        print(f"Could not add column 'enforced_since' to database: {exx}")
        raise

    try:
        connection = op.get_bind()
        connection.execute(sa.text(
            "UPDATE conditional_access_policies SET enforced_since = :enforced_since "
            "WHERE dry_run = :dry_run"
        ).bindparams(sa.bindparam("enforced_since", utc_now(), type_=sa.DateTime()),
                     sa.bindparam("dry_run", False, type_=sa.Boolean())))
    except Exception as exx:
        print(f"Could not backfill 'enforced_since' for existing conditional-access policies: {exx}")
        raise


def upgrade():
    _create_table(
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
        sa.Column('enforced_since', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('priority', name='uq_ca_policy_priority'),
    )
    _add_enforced_since_column()
    _create_table(
        'conditional_access_policy_counter_types',
        _id_column(),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('counter_type', sa.Unicode(length=100), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['conditional_access_policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_id', 'counter_type', name='uq_ca_counter_type_policy'),
        sa.Index('ix_ca_counter_type_lookup', 'counter_type', 'policy_id'),
    )
    _create_table(
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
        sa.Index('ix_conditional_access_policy_conditions_policy_id', 'policy_id'),
    )
    _create_table(
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
        'conditional_access_stage_actions',
        _id_column(),
        sa.Column('stage_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.Unicode(length=100), nullable=False),
        sa.Column('action_value', sa.JSON(), nullable=True),
        sa.Column('retrigger_above_threshold', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['stage_id'], ['conditional_access_policy_stages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_conditional_access_stage_actions_stage_id', 'stage_id'),
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
