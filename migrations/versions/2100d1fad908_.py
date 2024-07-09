"""v3.10: Add index to expiration in challenge table

Revision ID: 2100d1fad908
Revises: 250931d82e51
Create Date: 2024-05-06 13:36:45.910206

"""

# revision identifiers, used by Alembic.
revision = '2100d1fad908'
down_revision = '250931d82e51'

from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError


def upgrade():
    try:
        op.create_index(op.f('ix_challenge_expiration'), 'challenge', ['expiration'], unique=False)
    except (OperationalError, ProgrammingError) as exx:
        if "Index already exists" in str(exx.orig).lower():
            print("Ok, Index 'expiration' in table 'challenge' already exists.")
        else:
            print(exx)
    except Exception as exx:
        print("Could not create index 'expiration' on table 'challenge'")
        print(exx)


def downgrade():
    op.drop_index(op.f('ix_challenge_expiration'), table_name='challenge')
