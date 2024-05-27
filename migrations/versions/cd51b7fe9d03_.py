"""v3.10: Add new tables tokencontainerstates, tokencontainerinfo and new columns (states, info_list, last_seen and
last_updated) to tokencontainer

Revision ID: cd51b7fe9d03
Revises: db6b2ef8100f
Create Date: 2024-05-21 13:46:28.577683

"""
from datetime import datetime

from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.schema import Sequence

# revision identifiers, used by Alembic.
revision = 'cd51b7fe9d03'
down_revision = 'db6b2ef8100f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    try:
        op.create_table('tokencontainerstates',
                        sa.Column("id", sa.Integer, sa.Identity(), primary_key=True),
                        sa.Column(sa.Integer(), sa.ForeignKey("tokencontainer.id")),
                        sa.Column(sa.Unicode(100), default='active', nullable=False),
                        mysql_row_format='DYNAMIC'
                        )
    except Exception as exx:
        print("Could not add table 'tokencontainerstates' - probably already exists!")
        print(exx)

    try:
        op.create_table('tokencontainerinfo',
                        sa.Column(sa.Integer, Sequence("containerinfo_seq"), primary_key=True),
                        sa.Column(sa.Unicode(255), nullable=False),
                        sa.Column(sa.UnicodeText(), default=''),
                        sa.Column(sa.Unicode(100), default=''),
                        sa.Column(sa.Unicode(2000), default=''),
                        sa.Column(sa.Integer(),
                                  sa.ForeignKey('tokencontainer.id'), index=True),
                        mysql_row_format='DYNAMIC'
                        )
    except Exception as exx:
        print("Could not add table 'tokencontainerstates' - probably already exists!")
        print(exx)

    try:
        op.add_column('tokencontainer',
                      sa.relationship('TokenContainerStates', lazy='dynamic', backref='tokencontainer'))
    except (OperationalError, ProgrammingError) as exx:
        if "already exists" in str(exx.orig).lower():
            print("Ok, column 'states' already exists.")
        else:
            print(exx)
    except Exception as exx:
        print("Could not add column 'states' to table 'tokencontainer'")
        print(exx)

    try:
        op.add_column('tokencontainer', sa.relationship('TokenContainerInfo', lazy='select',
                                                        backref='tokencontainer'))
    except (OperationalError, ProgrammingError) as exx:
        if "already exists" in str(exx.orig).lower():
            print("Ok, column 'info_list' already exists.")
        else:
            print(exx)
    except Exception as exx:
        print("Could not add column 'info_list' to table 'tokencontainer'")
        print(exx)

    try:
        op.add_column('tokencontainer',
                      sa.Column('last_seen', sa.DateTime, default=datetime.now()))
    except (OperationalError, ProgrammingError) as exx:
        if "already exists" in str(exx.orig).lower():
            print("Ok, column 'last_seen' already exists.")
        else:
            print(exx)
    except Exception as exx:
        print("Could not add column 'last_seen' to table 'tokencontainer'")
        print(exx)

    try:
        op.add_column('tokencontainer',
                      sa.Column('last_updated', sa.DateTime, default=datetime.now()))
    except (OperationalError, ProgrammingError) as exx:
        if "already exists" in str(exx.orig).lower():
            print("Ok, column 'last_updated' already exists.")
        else:
            print(exx)
    except Exception as exx:
        print("Could not add column 'last_updated' to table 'tokencontainer'")
        print(exx)


def downgrade():
    op.drop_table('tokencontainerstates')
    op.drop_table('tokencontainerinfo')
    op.drop_column('tokencontainer', 'info_list')
    op.drop_column('tokencontainer', 'states')
    op.drop_column('tokencontainer', 'last_seen')
    op.drop_column('tokencontainer', 'last_updated')
