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
from sqlalchemy import and_


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    try:
        for row in session.query(EventHandlerOption).filter(EventHandlerOption.Key == 'reply_to'):
            evh_id = row.eventhandler_id
            check = session.query(EventHandlerOption).filter(and_(EventHandlerOption.Key.like('reply_to %'),
                                                                  EventHandlerOption.eventhandler_id == evh_id)).first()
            if not check:
                reply_email = row.Value
                row.Value = NOTIFY_TYPE.EMAIL
                row.save()
                EventHandlerOption(evh_id, 'reply_to email', reply_email).save()
            else:
                continue

    except Exception as e:
        session.rollback()
        print(e)

    finally:
        session.commit()


def downgrade():
    pass
