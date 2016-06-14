"""Add smsgateway table

Revision ID: 5402fd96fbca
Revises: 50adc980d625
Create Date: 2016-06-19 17:25:05.152889

"""

# revision identifiers, used by Alembic.
revision = '5402fd96fbca'
down_revision = '50adc980d625'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError


def upgrade():
    try:
        op.create_table('smsgateway',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.Unicode(length=255), nullable=False),
        sa.Column('description', sa.Unicode(length=1024), nullable=True),
        sa.Column('providermodule', sa.Unicode(length=1024), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('identifier')
        )
        op.create_table('smsgatewayoption',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('Key', sa.Unicode(length=255), nullable=False),
        sa.Column('Value', sa.UnicodeText(), nullable=True),
        sa.Column('Type', sa.Unicode(length=100), nullable=True),
        sa.Column('gateway_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['gateway_id'], ['smsgateway.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gateway_id', 'Key', name='sgix_1')
        )
        op.create_index(op.f('ix_smsgatewayoption_gateway_id'), 'smsgatewayoption', ['gateway_id'], unique=False)
    except (OperationalError, ProgrammingError, InternalError) as exx:
        if exx.orig.message.lower().startswith("duplicate column name"):
            print("Good. Table smsgateway already exists.")
        else:
            print("Table already exists")
            print(exx)

    except Exception as exx:
        print("Could not add Table smsgateway")
        print (exx)
    ### end Alembic commands ###


def downgrade():
    op.drop_index(op.f('ix_smsgatewayoption_gateway_id'), table_name='smsgatewayoption')
    op.drop_table('smsgatewayoption')
    op.drop_table('smsgateway')

