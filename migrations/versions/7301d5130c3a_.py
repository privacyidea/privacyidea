"""v3.11: Fix content type in EventHandlerOption table

Revision ID: 7301d5130c3a
Revises: 69e7817b9863
Create Date: 2024-11-29 12:03:46.090125

"""
from alembic import op
from sqlalchemy import orm, Unicode
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision = '7301d5130c3a'
down_revision = 'eac770c0bbed'

eventhandleroption = table("eventhandleroption", column("Key", Unicode(255)), column("Value", Unicode(2000)))


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    try:
        op.execute(eventhandleroption.update()
                   .where(eventhandleroption.c.Key == op.inline_literal("content_type"))
                   .where(eventhandleroption.c.Value == op.inline_literal("urlendcode"))
                   .values({"Value": op.inline_literal("urlencoded")}))
    except Exception as e:
        print("Failed to update urlendcode to urlencoded in eventhandleroption table.")
        print(e)
        session.rollback()
        raise

    finally:
        session.commit()


def downgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    try:
        op.execute(eventhandleroption.update()
                   .where(eventhandleroption.c.Key == op.inline_literal("content_type"))
                   .where(eventhandleroption.c.Value == op.inline_literal("urlencoded"))
                   .values({"Value": op.inline_literal("urlendcode")}))
    except Exception as e:
        print("Failed to revert urlencoded to urlendcode in eventhandleroption table.")
        print(e)
        session.rollback()
        raise

    finally:
        session.commit()
