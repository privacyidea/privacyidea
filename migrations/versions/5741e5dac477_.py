"""v3.10: Add a table for policy descriptions

Revision ID: 5741e5dac477
Revises: e3a64b4ca634
Create Date: 2024-02-23 11:06:41.729152

"""
from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.schema import Sequence, CreateSequence, DropSequence

# revision identifiers, used by Alembic.
revision = '5741e5dac477'
down_revision = 'db6b2ef8100f'


def upgrade():
    try:
        seq = Sequence('description_seq')
        try:
            if context.get_context().dialect.supports_sequences:
                op.execute(CreateSequence(seq))
        except (OperationalError, ProgrammingError) as exx:
            if "already exists" in str(exx.orig).lower():
                print(f"Ok, sequence '{seq}' already exists.")
            else:
                raise
        except Exception as _exx:
            print(f"Could not create sequence '{seq}'!")
            raise

        op.create_table('description',
                        sa.Column('id', sa.Integer(), seq, nullable=False),
                        sa.Column('object_type', sa.Unicode(length=64), nullable=False),
                        sa.Column('last_update', sa.DateTime),
                        sa.Column('description', sa.UnicodeText()),
                        sa.Column('object_id', sa.Integer(), nullable=False),
                        sa.ForeignKeyConstraint(('object_id',), ['policy.id'], ),
                        sa.PrimaryKeyConstraint('id'),
                        mysql_row_format='DYNAMIC'
                        )
    except (OperationalError, ProgrammingError) as exx:
        if "already exists" in str(exx.orig).lower():
            print("Ok, table 'description' already exists.")
        else:
            raise
    except Exception as _exx:
        print("Could not add table 'description'!")
        raise


def downgrade():
    op.drop_table('description')
    seq = Sequence('description_seq')
    if context.get_context().dialect.supports_sequences:
        op.execute(DropSequence(seq))
