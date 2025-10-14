"""v3.9: Create sequences needed for SQLAlchemy 1.4

E.g. mariadb now needs sequences.

Revision ID: 5cb310101a1f
Revises: 4a0aec37e7cf
Create Date: 2023-09-08 15:59:01.374626

"""
from alembic import op, context
from sqlalchemy import inspect
from sqlalchemy.schema import Sequence, CreateSequence, DropSequence
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import func
from sqlalchemy.exc import DatabaseError
from privacyidea.models import db

# revision identifiers, used by Alembic.
revision = '5cb310101a1f'
down_revision = '4a0aec37e7cf'


Session = sessionmaker()


def upgrade():
    migration_context = context.get_context()
    if migration_context.dialect.supports_sequences:
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
                    # do we have tables with "id" columns, which isn't a sequence?
                    print(f"Table {tbl.name} has an 'id' column which isn't a sequence. Skipping...")
                    continue

                # check if the table exists in the database (newer tables might not exist yet)
                insp = inspect(bind.engine)
                if not insp.has_table(tbl.name):
                    print(f"Table {tbl.name} does not exist in the database yet.")
                    continue
                # Create the sequence with the correct next_id!
                current_id = session.query(func.max(tbl.c.id)).one()[0] or 0
                try:
                    seq = Sequence(seq_name, start=(current_id + 1))
                    op.execute(CreateSequence(seq, if_not_exists=True))
                    print(f" +++ Created Sequence '{seq_name}' for table '{tbl.name}' "
                          f"with current id={current_id + 1}")
                except DatabaseError as e:
                    if any([x in str(e.orig) for x in ["already exists", "ORA-00955: name is already used"]]):
                        print(f"Sequence {seq_name} already exists. Skipping...")
                    else:
                        raise
                except Exception as e:
                    print(f"(Rev. {revision}) ERROR: Unable to create Sequences: {e}")
                    raise


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
