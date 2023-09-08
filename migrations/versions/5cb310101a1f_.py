"""v3.9: Create sequences needed for SQLAlchemy 1.4

E.g. mariadb now needs sequences.

Revision ID: 5cb310101a1f
Revises: 4a0aec37e7cf
Create Date: 2023-09-08 15:59:01.374626

"""

# revision identifiers, used by Alembic.
revision = '5cb310101a1f'
down_revision = '4a0aec37e7cf'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.schema import Sequence, CreateSequence


def upgrade():
    # TODO: Add all old tables
    for tab in ["token", "tokeninfo"]:
        try:
            # TODO: Create the sequence with the correct next_id!
            seq = Sequence('{0!s}_seq'.format(tab))
            op.execute(CreateSequence(seq))
        except Exception as exx:
            print(exx)


def downgrade():
    pass
