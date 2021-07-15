"""v3.7: migrate old reply_to email

Revision ID: ff26585932ec
Revises: fa07bd604a75
Create Date: 2021-07-15 14:17:17.624748

"""

# revision identifiers, used by Alembic.
revision = 'ff26585932ec'
down_revision = 'fa07bd604a75'

from alembic import op
from sqlalchemy import orm
from privacyidea.models import EventHandlerOption
from privacyidea.lib.eventhandler.usernotification import NOTIFY_TYPE


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    try:
        for row in session.query(EventHandlerOption).filter(EventHandlerOption.Key == 'reply_to'):
            reply_email = row.Value
            evh_id = row.eventhandler_id
            row.Value = NOTIFY_TYPE.EMAIL
            row.save()
            EventHandlerOption(evh_id, 'reply_to email', reply_email).save()

    except Exception as e:
        session.rollback()
        print(e)

    finally:
        session.commit()


def downgrade():
    pass
