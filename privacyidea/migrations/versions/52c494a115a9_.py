"""v3.12: Increase challenge column size in challenge table

Revision ID: 52c494a115a9
Revises: 41ad6c9ada8b
Create Date: 2025-07-31 10:38:11.151300

"""
from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = '52c494a115a9'
down_revision = '41ad6c9ada8b'
branch_labels = None
depends_on = None


def upgrade():
    try:
        with op.batch_alter_table('challenge', schema=None) as batch_op:
            # Oracle does not support altering column type VARCHAR to TEXT (CLOB)
            if context.get_context().dialect.name == "oracle":
                batch_op.execute(
                    """
                    begin
                    execute immediate 'alter table challenge add (challenge_large clob)';
                    execute immediate 'update challenge set challenge_large = challenge';
                    execute immediate 'alter table challenge rename column challenge to challenge_old';
                    execute immediate 'alter table challenge rename column challenge_large to challenge';
                    execute immediate 'alter table challenge drop column challenge_old';
                    end;
                    """)
            else:
                batch_op.alter_column('challenge',
                                      existing_type=sa.VARCHAR(length=512),
                                      type_=sa.Text(),
                                      existing_nullable=True)
    except (OperationalError, ProgrammingError) as exx:
        print("Could not increase 'challenge' column size in 'challenge' table.")
        print(exx)


def downgrade():
    with op.batch_alter_table('challenge', schema=None) as batch_op:
        # Oracle cannot alter a CLOB column back to VARCHAR2 (ORA-22859), so
        # reverse the upgrade the same way: add a VARCHAR2 column, copy the data
        # across, then swap the columns by renaming. The copy uses
        # DBMS_LOB.SUBSTR to explicitly truncate to 512 chars — a direct
        # CLOB->VARCHAR2 assignment errors (ORA-12899/ORA-22835) instead of
        # truncating when a value exceeds the column width, which would make the
        # downgrade fail on real data.
        if context.get_context().dialect.name == "oracle":
            batch_op.execute(
                """
                begin
                execute immediate 'alter table challenge add (challenge_small varchar2(512))';
                execute immediate 'update challenge set challenge_small = dbms_lob.substr(challenge, 512, 1)';
                execute immediate 'alter table challenge rename column challenge to challenge_old';
                execute immediate 'alter table challenge rename column challenge_small to challenge';
                execute immediate 'alter table challenge drop column challenge_old';
                end;
                """)
        else:
            batch_op.alter_column('challenge',
                                  existing_type=sa.Text(),
                                  type_=sa.VARCHAR(length=512),
                                  existing_nullable=True)
