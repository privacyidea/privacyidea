"""Fixing type in EventHandlerOption table from urlendcode to urlencoded

Revision ID: 7301d5130c3a
Revises: 69e7817b9863
Create Date: 2024-11-29 12:03:46.090125

"""
from alembic import op
from sqlalchemy import orm

# revision identifiers, used by Alembic.
revision = '7301d5130c3a'
down_revision = '69e7817b9863'


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    try:
        op.execute("UPDATE eventhandleroption SET Value='urlencoded' WHERE Value='urlendcode'")
    except Exception as exx:
        print("Failed to update urlendcode to urlencoded in evanthandleroption table.")
        print(exx)
        session.rollback()

    finally:
        session.commit()


def downgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    try:
        op.execute("UPDATE eventhandleroption SET Value='urlendcode' WHERE Value='urlencoded'")
    except Exception as exx:
        print("Failed to revert urlencoded to urlendcode in evanthandleroption table.")
        print(exx)
        session.rollback()

    finally:
        session.commit()
