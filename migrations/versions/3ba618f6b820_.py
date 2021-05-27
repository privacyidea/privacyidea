"""v3.6: add fraction to MySQL DateTime type in audit table

Revision ID: 3ba618f6b820
Revises: 59ef3e03bc62
Create Date: 2021-05-05 11:27:13.705851

"""

# revision identifiers, used by Alembic.
revision = '3ba618f6b820'
down_revision = '59ef3e03bc62'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade():
    try:
        if op._proxy.migration_context.dialect.name == 'mysql':
            with op.batch_alter_table('pidea_audit') as batch_op:
                batch_op.alter_column('date', type_=mysql.DATETIME(fsp=6),
                                      existing_type=mysql.DATETIME)
                batch_op.alter_column('startdate', type_=mysql.DATETIME(fsp=6),
                                      existing_type=mysql.DATETIME)
                batch_op.alter_column('duration', type_=mysql.DATETIME(fsp=6),
                                      existing_type=mysql.DATETIME)
    except Exception as exx:
        print("Could not add fraction to MySQL DateTime Type in audit table.")
        print(exx)


def downgrade():
    try:
        if op._proxy.migration_context.dialect.name == 'mysql':
            with op.batch_alter_table('pidea_audit') as batch_op:
                batch_op.alter_column('date', type_=mysql.DATETIME,
                                      existing_type=mysql.DATETIME(fsp=6))
                batch_op.alter_column('startdate', type_=mysql.DATETIME,
                                      existing_type=mysql.DATETIME(fsp=6))
                batch_op.alter_column('duration', type_=mysql.DATETIME,
                                      existing_type=mysql.DATETIME(fsp=6))
    except Exception as exx:
        print("Could not remove fraction from MySQL DateTime Type in audit table.")
        print(exx)
