"""v3.8: Increase key_enc column in token table

The key_enc column is too small to accommodate 1023 bit size WebAuthn
credential_ids. See https://github.com/privacyidea/privacyidea/issues/3137

Revision ID: fabcf24d9304
Revises: 00762b3f7a60
Create Date: 2022-10-06 12:13:09.044799

"""

# revision identifiers, used by Alembic.
revision = 'fabcf24d9304'
down_revision = '00762b3f7a60'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.alter_column(table_name='token', column_name='key_enc',
                        type_=sa.Unicode(2800), existing_type=sa.Unicode(1024))
    except Exception as exx:
        print("Could not increase key_enc column size in token table.")
        print(exx)


def downgrade():
    try:
        op.alter_column(table_name='token', column_name='key_enc',
                        type_=sa.Unicode(1024), existing_type=sa.Unicode(2800))
    except Exception as exx:
        print("Could not decrease key_enc column size in token table.")
        print(exx)
    pass
