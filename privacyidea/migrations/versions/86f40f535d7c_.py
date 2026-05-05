"""v3.8: Add indices to datetime columns

Revision ID: 86f40f535d7c
Revises: ef29ba43e290
Create Date: 2022-05-10 16:55:28.541847

"""

# revision identifiers, used by Alembic.
revision = '86f40f535d7c'
down_revision = 'ef29ba43e290'

from alembic import op


def upgrade():
    index_data = [('challenge', 'timestamp'),
                  ('clientapplication', 'lastseen'),
                  ('pidea_audit', 'date'),
                  ('usercache', 'timestamp'),
                  ('authcache', 'first_auth'),
                  ('authcache', 'last_auth'),
                  ('monitoringstats', 'timestamp')]
    for k, v in index_data:
        try:
            op.create_index(op.f(f'ix_{k!s}_{v!s}'), k, [v])
        except Exception as exx:
            print(f"Could not add index for column {v!s} in table {k!s}.")
            print(exx)


def downgrade():
    # there should be no need to disable/remove the index when downgrading.
    pass
