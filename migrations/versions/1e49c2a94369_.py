"""Add SAML IdP database table

Revision ID: 1e49c2a94369
Revises: 239995464c48
Create Date: 2016-03-08 10:20:54.398547

"""

# revision identifiers, used by Alembic.
revision = '1e49c2a94369'
down_revision = '239995464c48'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError


def upgrade():
    try:
        op.create_table('samlidp',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.Unicode(length=255), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('metadata_url', sa.Unicode(length=1024), nullable=False),
        sa.Column('acs_url', sa.Unicode(length=1024), nullable=False),
        sa.Column('https_acs_url', sa.Unicode(length=1024), nullable=False),
        sa.Column('allow_unsolicited', sa.Boolean(), nullable=True),
        sa.Column('authn_requests_signed', sa.Boolean(), nullable=True),
        sa.Column('logout_requests_signed', sa.Boolean(), nullable=True),
        sa.Column('want_assertions_signed', sa.Boolean(), nullable=True),
        sa.Column('want_response_signed', sa.Boolean(), nullable=True),
        sa.Column('metadata_cache', sa.UnicodeText(), nullable=True),
        sa.Column('entityid', sa.Unicode(length=1024), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
    except (OperationalError, ProgrammingError, InternalError) as exx:
        if exx.orig.message.lower().startswith("duplicate column name"):
            print("Good. Table 'samlidp' already exists.")
        else:
            print(exx)
    except Exception as exx:
        print ("Could not add table 'samlidp'")
        print (exx)


def downgrade():
    op.drop_table('samlidp')

