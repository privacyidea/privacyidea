"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

# NOTE: If this migration changes data (UPDATE/INSERT/DELETE on existing rows,
# backfilling new columns, rewriting values, etc.) — not just schema — you are
# expected to add a dedicated test under tests/test_migration_<revision>.py
# using MigrationTestBase. Schema-only migrations are covered by the generic
# tests in tests/test_migrations.py and do not need their own test file.
# Delete this note once you have addressed it.


def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}
