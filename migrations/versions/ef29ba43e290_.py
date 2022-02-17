"""v3.7: Allow empty machine_id and resolver_id in machinetoken

Revision ID: ef29ba43e290
Revises: ff26585932ec
Create Date: 2021-12-30 12:17:15.521336

"""

# revision identifiers, used by Alembic.
revision = 'ef29ba43e290'
down_revision = 'ff26585932ec'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.alter_column('machinetoken', 'machine_id',
                   existing_type=sa.VARCHAR(length=255),
                   nullable=True)
        op.alter_column('machinetoken', 'machineresolver_id',
                   existing_type=sa.INTEGER(),
                   nullable=True)
    except Exception as exx:
        print("Failed to make machine_id and resolver_id in machinetokens nullable.")
        print(exx)


def downgrade():
    try:
        op.alter_column('machinetoken', 'machineresolver_id',
                   existing_type=sa.INTEGER(),
                   nullable=False)
        op.alter_column('machinetoken', 'machine_id',
                   existing_type=sa.VARCHAR(length=255),
                   nullable=False)
    except Exception as exx:
        print("Failed to make machine_id and resolver_id in machinetokens non-nullable.")
        print(exx)
