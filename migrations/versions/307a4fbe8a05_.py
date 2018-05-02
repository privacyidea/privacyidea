"""alter table challenge

Revision ID: 307a4fbe8a05
Revises: 1edda52b619f
Create Date: 2017-04-19 14:39:20.255958

"""

# revision identifiers, used by Alembic.
revision = '307a4fbe8a05'
down_revision = '1edda52b619f'

from alembic import op


def upgrade():
    try:
        op.create_index(op.f('ix_challenge_serial'), 'challenge', ['serial'],
                        unique=False)
    except Exception as exx:
        print("Could not add index to 'challenge.serial'")
        print (exx)
    try:
        op.drop_index('ix_challenge_transaction_id', table_name='challenge')
        op.create_index(op.f('ix_challenge_transaction_id'), 'challenge',
                        ['transaction_id'], unique=False)
    except Exception as exx:
        print("Could not remove uniqueness from 'challenge.transaction_id'")
        print (exx)


def downgrade():
    op.drop_index(op.f('ix_challenge_transaction_id'), table_name='challenge')
    op.create_index('ix_challenge_transaction_id', 'challenge',
                    ['transaction_id'], unique=1)
    op.drop_index(op.f('ix_challenge_serial'), table_name='challenge')
