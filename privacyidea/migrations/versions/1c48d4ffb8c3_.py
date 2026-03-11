"""v3.12: Add option column to radiusserver table

Revision ID: 1c48d4ffb8c3
Revises: 52c494a115a9
Create Date: 2025-08-19 19:20:32.427088

"""
from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.exc import DatabaseError


# revision identifiers, used by Alembic.
revision = '1c48d4ffb8c3'
down_revision = '52c494a115a9'
branch_labels = None
depends_on = None


def upgrade():
    if context.get_context().dialect.name == "oracle":
        # For Oracle: use CLOB with JSON constraint
        op.add_column("radiusserver", sa.Column("options", sa.Text(), nullable=True))
        # Add JSON validation constraint
        op.execute("""
                   ALTER TABLE radiusserver
                       ADD CONSTRAINT json_data_is_json
                           CHECK ("OPTIONS" IS JSON)
                    """)
    else:
        with op.batch_alter_table("radiusserver", schema=None) as batch_op:
            batch_op.add_column(sa.Column('options', sa.JSON(), nullable=True))


def downgrade():
    try:
        with op.batch_alter_table('radiusserver', schema=None) as batch_op:
            batch_op.drop_column('options')
    except DatabaseError as exx:
        msg = str(exx.orig).lower()
        if any(x in msg for x in ["no such column", "does not exist", "check that it exists"]):
            print("Column 'options' in 'radiusserver' already removed.")
        else:
            raise
