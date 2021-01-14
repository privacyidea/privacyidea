"""Add constraint for smsoptions and set default type to "option"

Revision ID: e360c56bcf8c
Revises: a7e91b18a460
Create Date: 2020-06-15 09:18:43.855589

"""

# revision identifiers, used by Alembic.
revision = 'e360c56bcf8c'
down_revision = 'a7e91b18a460'

from alembic import op
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import orm
from privacyidea.models import SMSGatewayOption

Base = declarative_base()


def upgrade():
    try:
        with op.batch_alter_table("smsgatewayoption") as batch_op:
            batch_op.drop_constraint('sgix_1', type_='unique')
            batch_op.create_unique_constraint('sgix_1', ['gateway_id', 'Key', 'Type'])
    except Exception as exx:
        print("Cannot change constraint 'sgix_1' in table smsgatewayoption.")
        print(exx)

    bind = op.get_bind()
    session = orm.Session(bind=bind)
    try:
        # add default type 'option' for all rows
        for row in session.query(SMSGatewayOption):
            if not row.Type:
                row.Type = u"option"

    except Exception as exx:
        session.rollback()
        print("Failed to add option type for all existing entries in table smsgatewayoption!")
        print(exx)

    session.commit()


def downgrade():
    with op.batch_alter_table("smsgatewayoption") as batch_op:
        batch_op.drop_constraint('sgix_1', 'smsgatewayoption', type_='unique')
        batch_op.create_unique_constraint('sgix_1', 'smsgatewayoption', ['gateway_id', 'Key'])
