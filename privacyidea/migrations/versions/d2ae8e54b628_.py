"""shorten columns used in UNIQUE constraints in periodictasklastrun, periodictaskoption

Revision ID: d2ae8e54b628
Revises: 1a0710df148b
Create Date: 2018-10-24 11:17:40.279312

"""

# revision identifiers, used by Alembic.
revision = 'd2ae8e54b628'
down_revision = '1a0710df148b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # First, try to create the table with the shorter field sizes.
    # This will fail if the tables already exist (which will be
    # the case in most installations)
    try:
        op.create_table('periodictasklastrun',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('periodictask_id', sa.Integer(), nullable=True),
        sa.Column('node', sa.Unicode(length=255), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['periodictask_id'], ['periodictask.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('periodictask_id', 'node', name='ptlrix_1'),
        mysql_row_format='DYNAMIC'
        )
        op.create_table('periodictaskoption',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('periodictask_id', sa.Integer(), nullable=True),
        sa.Column('key', sa.Unicode(length=255), nullable=False),
        sa.Column('value', sa.Unicode(length=2000), nullable=True),
        sa.ForeignKeyConstraint(['periodictask_id'], ['periodictask.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('periodictask_id', 'key', name='ptoix_1'),
        mysql_row_format='DYNAMIC'
        )
        print('Successfully created shortened periodictasklastrun and periodictaskoption.')
    except Exception as exx:
        print('Creation of periodictasklastrun and periodictaskoption with shortened columns failed: {!r}'.format(exx))
        print('This is expected behavior if they were already present.')
    try:
        op.alter_column('periodictasklastrun', 'node',
                   existing_type=sa.VARCHAR(length=256),
                   type_=sa.Unicode(length=255),
                   existing_nullable=False)
        op.alter_column('periodictaskoption', 'key',
                   existing_type=sa.VARCHAR(length=256),
                   type_=sa.Unicode(length=255),
                   existing_nullable=False)
        print('Successfully shortened columns of periodictasklastrun and periodictaskoption.')
    except Exception as exx:
        print('Shortening of periodictasklastrun and periodictaskoption columns failed: {!r}'.format(exx))
        print('This is expected behavior if the columns have already been shorted.')


def downgrade():
    op.alter_column('periodictaskoption', 'key',
               existing_type=sa.Unicode(length=255),
               type_=sa.VARCHAR(length=256),
               existing_nullable=False)
    op.alter_column('periodictasklastrun', 'node',
               existing_type=sa.Unicode(length=255),
               type_=sa.VARCHAR(length=256),
               existing_nullable=False)
