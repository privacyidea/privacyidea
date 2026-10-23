"""v3.14: Set empty rollout_state to 'enrolled' in token table

The downgrade leaves the rollout_state as it is. 3.13 treats an empty rollout_state and 'enrolled' alike once a token
is enrolled, and sets 'enrolled' itself for several token types. The upgrade does not record which tokens it changed,
so setting 'enrolled' back to empty would also change the tokens that had it before.

Revision ID: 3cafe2771cdd
Revises: a1e0ba6ad9dc
Create Date: 2026-03-20 12:22:44.365016

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '3cafe2771cdd'
down_revision = 'a1e0ba6ad9dc'
branch_labels = None
depends_on = None


def upgrade():
    token = sa.table('token', sa.column('rollout_state', sa.Unicode(10)))
    op.execute(
        token.update()
        .where((token.c.rollout_state == '') | (token.c.rollout_state.is_(None)))
        .values(rollout_state='enrolled')
    )


def downgrade():
    pass
