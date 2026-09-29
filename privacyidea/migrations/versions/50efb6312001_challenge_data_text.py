"""v3.14: Remove the length limit of challenge.data

The challenge data is stored encrypted, which takes a little more than twice
the length of its JSON, and a1b2c3d4e5f6 widened the column to 2000 characters
for that. A challenge cached in Redis has no such limit, so a challenge whose
data fits into Redis could not be written to the database when a worker falls
back to it. The column becomes a Text column like challenge.challenge.

Oracle cannot change a VARCHAR2 column into a CLOB or back, so there the data
is copied into a new column that then takes the place of the old one.

A downgrade deletes the challenges whose data does not fit into 2000
characters instead of truncating it, since truncated ciphertext can no longer
be decrypted. Challenges are short-lived, so only the authentication such a
challenge belongs to fails.

Revision ID: 50efb6312001
Revises: b7c1e4d2a9f3
Create Date: 2026-09-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '50efb6312001'
down_revision = 'b7c1e4d2a9f3'
branch_labels = None
depends_on = None

LIMITED_DATA_TYPE = sa.Unicode(length=2000)


def _replace_oracle_data_column(new_type: sa.types.TypeEngine, copy_expression: str) -> None:
    """
    Replace challenge.data by a new column of the given type on Oracle, which cannot convert between VARCHAR2 and
    CLOB in place.

    :param new_type: the type of the new column
    :param copy_expression: the SQL expression that reads the value of the old column for the new one
    """
    op.add_column('challenge', sa.Column('data_new', new_type, nullable=True))
    op.execute(f"UPDATE challenge SET data_new = {copy_expression}")
    op.alter_column('challenge', 'data', new_column_name='data_old')
    op.alter_column('challenge', 'data_new', new_column_name='data')
    op.drop_column('challenge', 'data_old')


def upgrade():
    if op.get_bind().dialect.name == "oracle":
        _replace_oracle_data_column(sa.Text(), "data")
    else:
        with op.batch_alter_table('challenge', schema=None) as batch_op:
            batch_op.alter_column('data',
                                  existing_type=LIMITED_DATA_TYPE,
                                  type_=sa.Text(),
                                  existing_nullable=True)


def downgrade():
    challenge = sa.table('challenge', sa.column('data', sa.Text()))
    op.execute(challenge.delete().where(sa.func.length(challenge.c.data) > LIMITED_DATA_TYPE.length))
    if op.get_bind().dialect.name == "oracle":
        # Every value left fits into the column, DBMS_LOB.SUBSTR only turns the CLOB into a VARCHAR2
        _replace_oracle_data_column(LIMITED_DATA_TYPE, f"DBMS_LOB.SUBSTR(data, {LIMITED_DATA_TYPE.length}, 1)")
    else:
        with op.batch_alter_table('challenge', schema=None) as batch_op:
            batch_op.alter_column('data',
                                  existing_type=sa.Text(),
                                  type_=LIMITED_DATA_TYPE,
                                  existing_nullable=True)
