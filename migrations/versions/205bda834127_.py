"""Add authcache table

Revision ID: 205bda834127
Revises: 4238eac8ccab
Create Date: 2017-08-11 16:33:31.164408

"""

# revision identifiers, used by Alembic.
revision = '205bda834127'
down_revision = '4238eac8ccab'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.create_table('authcache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_auth', sa.DateTime(), nullable=True),
        sa.Column('last_auth', sa.DateTime(), nullable=True),
        sa.Column('username', sa.Unicode(length=64), nullable=True),
        sa.Column('resolver', sa.Unicode(length=120), nullable=True),
        sa.Column('realm', sa.Unicode(length=120), nullable=True),
        sa.Column('client_ip', sa.Unicode(length=40), nullable=True),
        sa.Column('user_agent', sa.Unicode(length=120), nullable=True),
        sa.Column('authentication', sa.Unicode(length=64), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_authcache_realm'), 'authcache', ['realm'], unique=False)
        op.create_index(op.f('ix_authcache_resolver'), 'authcache', ['resolver'], unique=False)
        op.create_index(op.f('ix_authcache_username'), 'authcache', ['username'], unique=False)
    except Exception as exx:
        print ("Could not add table 'authcache' - probably already exists!")
        print (exx)


def downgrade():
    op.drop_index(op.f('ix_authcache_username'), table_name='authcache')
    op.drop_index(op.f('ix_authcache_resolver'), table_name='authcache')
    op.drop_index(op.f('ix_authcache_realm'), table_name='authcache')
    op.drop_table('authcache')

