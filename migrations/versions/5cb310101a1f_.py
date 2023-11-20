"""v3.9: Create sequences needed for SQLAlchemy 1.4

E.g. mariadb now needs sequences.

Revision ID: 5cb310101a1f
Revises: 4a0aec37e7cf
Create Date: 2023-09-08 15:59:01.374626

"""

# revision identifiers, used by Alembic.
revision = '5cb310101a1f'
down_revision = '4a0aec37e7cf'

from alembic import op, context
from sqlalchemy.schema import Sequence, CreateSequence, DropSequence
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import func
from sqlalchemy.exc import OperationalError, ProgrammingError
from privacyidea.models import db


Session = sessionmaker()


def upgrade():
    migration_context = context.get_context()
    if migration_context.dialect.supports_sequences:
        if migration_context.dialect.name in ['mariadb', 'mysql']:
            # setting "increment" to 0 works like auto-increment but also supports replication
            # See <https://mariadb.com/kb/en/sequence-overview/#replication>
            inc_value = 0
        else:
            inc_value = 1
        bind = op.get_bind()
        # We only need a read session, so we do not need a commit
        session = Session(bind=bind)
        # Loop over all tables defined in the current models.py
        for tbl in db.metadata.sorted_tables:
            # we act only on tables with an "id" column
            if 'id' in tbl.c:
                seq = tbl.c['id'].default
                if isinstance(seq, Sequence):
                    seq_name = seq.name
                else:
                    # do we have tables with "id" columns which isn't a sequence?
                    print(f"Table {tbl.name} has an 'id' column which isn't a sequence!")
                    continue

                # Create the sequence with the correct next_id!
                current_id = session.query(func.max(tbl.c.id)).one()[0] or 0
                print(f"CurrentID in Table {tbl.name}: {current_id}")
                try:
                    seq = Sequence(seq_name, start=(current_id + 1), increment=inc_value)
                    print(f" +++ Creating Sequence: {seq_name}")
                    op.execute(CreateSequence(seq, if_not_exists=True))
                except OperationalError as exx:
                    if exx.orig.args[0] == 1050 or "already exists" in exx.orig.args[1]:
                        pass
                    else:
                        print(exx)
                except ProgrammingError as exx:
                    if "already exists" in exx.orig.args[0]:
                        pass
                    else:
                        print(exx)
                except Exception as exx:
                    print(exx)


def downgrade():

    migration_context = context.get_context()
    if migration_context.dialect.supports_sequences and migration_context.dialect.name in ['mysql', 'mariadb']:
        # don't remove sequences unless the db is MariaDB
        for tbl in db.metadata.sorted_tables:
            if 'id' in tbl.c:
                seq = tbl.c.id.default
                if isinstance(seq, Sequence):
                    try:
                        op.execute(DropSequence(seq))
                    except Exception as exx:
                        print(exx)
