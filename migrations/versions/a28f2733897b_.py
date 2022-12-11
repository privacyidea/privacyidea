"""v3.8: Sequence for cusstomuserattribute, tokengroup and tokentokengroup

Revision ID: a28f2733897b
Revises: 89e57ed16379
Create Date: 2022-11-24 11:05:42.572284

"""

# revision identifiers, used by Alembic.
revision = 'a28f2733897b'
down_revision = '89e57ed16379'

from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.schema import Sequence, CreateSequence

def dialect_supports_sequences():
    migration_context = context.get_context()
    return migration_context.dialect.supports_sequences


def create_seq(seq):
    if dialect_supports_sequences():
        op.execute(CreateSequence(seq))


def upgrade():
    try:
        seq = Sequence('customuserattribute_seq')
        create_seq(seq)
    except Exception as exx:
        print(exx)

    try:
        seq = Sequence('tokengroup_seq')
        create_seq(seq)
    except Exception as exx:
        print(exx)

    try:
        seq = Sequence('tokentokengroup_seq')
        create_seq(seq)
    except Exception as exx:
        print(exx)


def downgrade():
    pass
