"""Make schema oracle compatible, Remove unnecessary columns from table usercache

Revision ID: 4238eac8ccab
Revises: 3429d523e51f
Create Date: 2017-08-10 11:53:30.426989

"""

# revision identifiers, used by Alembic.
revision = '4238eac8ccab'
down_revision = '3429d523e51f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        # Adapt schema definition to work with oracle
        op.create_unique_constraint(None, 'caconnector', ['name'])
        op.drop_index('ix_clientapplication_id', table_name='clientapplication')
        op.create_unique_constraint(None, 'machineresolver', ['name'])
        op.drop_index('ix_pidea_audit_id', table_name='pidea_audit')
        op.create_unique_constraint(None, 'policy', ['name'])
        op.create_unique_constraint(None, 'radiusserver', ['identifier'])
        op.create_unique_constraint(None, 'realm', ['name'])
        op.create_unique_constraint(None, 'resolver', ['name'])
        op.create_unique_constraint(None, 'smsgateway', ['identifier'])
        op.create_index(op.f('ix_subscription_application'), 'subscription', ['application'], unique=False)
        op.alter_column('token', 'active',
                   existing_type=sa.BOOLEAN(),
                   nullable=False)
        op.create_index(op.f('ix_token_resolver'), 'token', ['resolver'], unique=False)
        op.create_index(op.f('ix_token_serial'), 'token', ['serial'], unique=True)
        op.create_index(op.f('ix_token_tokentype'), 'token', ['tokentype'], unique=False)
        op.create_index(op.f('ix_token_user_id'), 'token', ['user_id'], unique=False)
        op.alter_column('tokenrealm', 'id',
                   existing_type=sa.INTEGER(),
                   nullable=True)
    except Exception as exx:
        print ("## Schema seems already to be oracle compatible.")
        print (exx)

    try:
        # Remove unused columns in the Table usercache.
        op.drop_column('usercache', 'realm')
        op.drop_column('usercache', 'expiration')
        op.drop_index('ix_usercache_expiration', table_name='usercache')
    except Exception as exx:
        print ("## Unnecessary columns in table usercache obviously do not "
               "exist anymore.")
        print (exx)


def downgrade():

    # Add old columns with usercache
    op.create_index('ix_usercache_expiration', 'usercache', ['expiration'], unique=False)
    op.add_column('usercache', sa.Column('expiration', sa.DATETIME(), nullable=True))
    op.add_column('usercache', sa.Column('realm', sa.VARCHAR(length=256), nullable=True))

    # Remove Oracle Schema definition
    op.alter_column('tokenrealm', 'id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_index(op.f('ix_token_user_id'), table_name='token')
    op.drop_index(op.f('ix_token_tokentype'), table_name='token')
    op.drop_index(op.f('ix_token_serial'), table_name='token')
    op.drop_index(op.f('ix_token_resolver'), table_name='token')
    op.alter_column('token', 'active',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    op.drop_index(op.f('ix_subscription_application'), table_name='subscription')
    op.drop_constraint(None, 'smsgateway')
    op.drop_constraint(None, 'resolver')
    op.drop_constraint(None, 'realm')
    op.drop_constraint(None, 'radiusserver')
    op.drop_constraint(None, 'policy')
    op.create_index('ix_pidea_audit_id', 'pidea_audit', ['id'], unique=False)
    op.drop_constraint(None, 'machineresolver')
    op.create_index('ix_clientapplication_id', 'clientapplication', ['id'], unique=False)
    op.drop_constraint(None, 'caconnector')

