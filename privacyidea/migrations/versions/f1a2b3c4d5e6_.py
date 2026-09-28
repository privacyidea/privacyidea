"""v3.14: Merging revisions

Joins the two Oracle fixes released in 3.13.4 back into this branch's lineage.
They keep the revision ids and the position they have on the release branch, so
that an installation which already applied them is recognised here, rather than
being told that its current revision does not exist.

Revision ID: f1a2b3c4d5e6
Revises: ('d3e8b1c47f92', 'd3a4b5c6e7f8')
Create Date: 2026-09-17 10:45:00.000000

"""

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = ('d3e8b1c47f92', 'd3a4b5c6e7f8')


def upgrade():
    pass


def downgrade():
    pass
