"""v3.14: Add enforced_since to conditional_access_policies

A policy leaving dry-run must not be judged against failures that accumulated during the trial - that transition is
what dry-run exists to make safe. enforced_since records the instant a policy started enforcing (NULL while
dry_run is set) so the count functions can floor their look-back window there instead of applying the full
configured window against the accumulated observation history.

Existing rows are backfilled: dry_run policies get NULL (unchanged), enforced policies get now(), which is a
reasonable approximation for policies that were already enforcing before this column existed.

Revision ID: f4a7c8e2b910
Revises: e0f1a2b3c4d5
Create Date: 2026-09-09 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'f4a7c8e2b910'
down_revision = 'e0f1a2b3c4d5'
branch_labels = None
depends_on = None


def upgrade():
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
            "UPDATE conditional_access_policies SET enforced_since = CURRENT_TIMESTAMP "
            "WHERE dry_run = :dry_run"
        ).bindparams(sa.bindparam("dry_run", False, type_=sa.Boolean())))
    except Exception as exx:
        print(f"Could not backfill 'enforced_since' for existing conditional-access policies: {exx}")
        raise


def downgrade():
    try:
        op.drop_column('conditional_access_policies', 'enforced_since')
    except (OperationalError, ProgrammingError) as exx:
        msg = str(exx.orig).lower()
        if "no such column" in msg or "does not exist" in msg or "check that it exists" in msg:
            print("Column 'enforced_since' already removed.")
        else:
            print("Could not remove column 'enforced_since' from table 'conditional_access_policies'.")
            raise
