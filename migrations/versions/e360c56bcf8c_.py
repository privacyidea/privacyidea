"""Add constraint for smsoptions and set default type to "option"

Revision ID: e360c56bcf8c
Revises: a7e91b18a460
Create Date: 2020-06-15 09:18:43.855589

"""

# revision identifiers, used by Alembic.
revision = 'e360c56bcf8c'
down_revision = 'a7e91b18a460'

from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Sequence, CreateSequence
from sqlalchemy import orm

Base = declarative_base()


class SMSGateway(Base):
    __tablename__ = 'smsgateway'
    __table_args__ = {'mysql_row_format': 'DYNAMIC'}
    id = sa.Column(sa.Integer, Sequence("smsgateway_seq"), primary_key=True)
    identifier = sa.Column(sa.Unicode(255), nullable=False, unique=True)
    description = sa.Column(sa.Unicode(1024), default=u"")
    providermodule = sa.Column(sa.Unicode(1024), nullable=False)
    options = orm.relationship('SMSGatewayOption',
                              lazy='dynamic',
                              backref='smsgw')


class SMSGatewayOption(Base):
    __tablename__ = 'smsgatewayoption'
    id = sa.Column(sa.Integer, Sequence("smsgwoption_seq"), primary_key=True)
    Key = sa.Column(sa.Unicode(255), nullable=False)
    Value = sa.Column(sa.UnicodeText(), default=u'')
    Type = sa.Column(sa.Unicode(100), default=u'option')
    gateway_id = sa.Column(sa.Integer(),
                           sa.ForeignKey('smsgateway.id'), index=True)
    __table_args__ = (sa.UniqueConstraint('gateway_id',
                                          'Key', 'Type',
                                          name='sgix_1'),
                      {'mysql_row_format': 'DYNAMIC'})


# Check if the SQL dialect uses sequences
# (from https://stackoverflow.com/a/17196812/7036742)
def dialect_supports_sequences():
    migration_context = context.get_context()
    return migration_context.dialect.supports_sequences


def create_seq(seq):
    if dialect_supports_sequences():
        op.execute(CreateSequence(seq))


def upgrade():
    try:
        with op.batch_alter_table("smsgatewayoption") as batch_op:
            batch_op.drop_constraint('sgix_1', type_='unique')
            batch_op.create_unique_constraint('sgix_1', ['gateway_id', 'Key', 'Type'])
    except Exception as exx:
        print("Cannot change constraint 'sgix_1' in table smsgatewayoption.")
        print(exx)

    try:
        bind = op.get_bind()
        session = orm.Session(bind=bind)
        # add default type 'option' for all rows
        for row in session.query(SMSGatewayOption):
            if not row.Type:
                row.Type = "option"

    except Exception as exx:
        session.rollback()
        print("Failed to add option type for all existing entries in table smsgatewayoption!")
        print(exx)

    session.commit()


def downgrade():
    with op.batch_alter_table("smsgatewayoption") as batch_op:
        batch_op.drop_constraint('sgix_1', 'smsgatewayoption', type_='unique')
        batch_op.create_unique_constraint('sgix_1', 'smsgatewayoption', ['gateway_id', 'Key'])
