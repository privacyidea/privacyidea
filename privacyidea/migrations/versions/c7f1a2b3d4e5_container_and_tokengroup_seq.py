"""v3.13.4: Create the container and tokengroup sequences on existing installs

The container and tokengroup models declare a Sequence on their id column, so
SQLAlchemy's MariaDB/Postgres/Oracle dialect asks the sequence for the next
primary key on every insert. Installs that were created while the models
carried no sequence do not have them, and Oracle - which has no autoincrement
of its own - then rejects every insert with ORA-01400. Create whichever of them
is missing and advance it past any existing ids so the next insert gets a free
primary key.

Revision ID: c7f1a2b3d4e5
Revises: b1a2c3d4e5f6
Create Date: 2026-09-16 12:00:00.000000

"""
from alembic import op
from sqlalchemy import text, inspect, Sequence
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.schema import CreateSequence, DropSequence
from privacyidea.models.db import build_restart_sequence_sql

revision = 'c7f1a2b3d4e5'
down_revision = 'b1a2c3d4e5f6'
branch_labels = None
depends_on = None

# table -> sequence the model expects. The container sequences are introduced here.
NEW_SEQUENCES = {
    "tokencontainer": "tokencontainer_seq",
    "tokencontainerinfo": "tokencontainerinfo_seq",
    "tokencontainerowner": "tokencontainerowner_seq",
    "tokencontainerstates": "tokencontainerstates_seq",
    "tokencontainertemplate": "tokencontainertemplate_seq",
}

# These two belong to an earlier migration and only need creating on installs that
# never got them. The downgrade leaves them alone: they are not this migration's to
# remove, and on PostgreSQL a column default may depend on them.
INHERITED_SEQUENCES = {
    "tokengroup": "tokengroup_seq",
    "tokentokengroup": "tokentokengroup_seq",
}


def _existing_sequences(bind) -> set:
    """Reflected names are upper-cased on Oracle, so compare in lower case."""
    return {name.lower() for name in inspect(bind).get_sequence_names()}


def upgrade():
    bind = op.get_bind()
    if not bind.dialect.supports_sequences:
        # MySQL itself has no CREATE SEQUENCE; only MariaDB 10.3+, Postgres and
        # Oracle do. There the column is AUTO_INCREMENT and fills itself.
        return
    existing = _existing_sequences(bind)
    for table, sequence_name in {**NEW_SEQUENCES, **INHERITED_SEQUENCES}.items():
        try:
            max_id = bind.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table}")).scalar() or 0
            start = max_id + 1
            # Oracle (19c+) supports neither "CREATE SEQUENCE IF NOT EXISTS" nor
            # "ALTER SEQUENCE ... RESTART WITH", so branch on what is already there
            # and let build_restart_sequence_sql emit its RESTART START WITH.
            if bind.dialect.name == "oracle":
                if sequence_name.lower() not in existing:
                    op.execute(CreateSequence(Sequence(sequence_name, start=start)))
                else:
                    op.execute(build_restart_sequence_sql(sequence_name, start, "oracle"))
                continue
            # MariaDB/Postgres: CreateSequence rather than a raw string, because the
            # increment_by_zero @compiles hook in privacyidea.models.db appends
            # INCREMENT BY 0 on MariaDB, which Galera requires for a cached sequence.
            op.execute(CreateSequence(Sequence(sequence_name, start=start), if_not_exists=True))
            # Covers installs where the sequence exists but lags MAX(id), which would
            # otherwise hand out an id that is already taken.
            op.execute(build_restart_sequence_sql(sequence_name, start, bind.dialect.name))
        except (OperationalError, ProgrammingError) as ex:
            print(f"Could not create sequence '{sequence_name}': {ex}")
            raise


def downgrade():
    bind = op.get_bind()
    if not bind.dialect.supports_sequences:
        return
    existing = _existing_sequences(bind)
    for sequence_name in NEW_SEQUENCES.values():
        try:
            # Oracle (19c+) has no "DROP SEQUENCE IF EXISTS", so drop only what is there.
            if bind.dialect.name == "oracle":
                if sequence_name.lower() in existing:
                    op.execute(DropSequence(Sequence(sequence_name)))
            else:
                op.execute(f"DROP SEQUENCE IF EXISTS {sequence_name}")
        except (OperationalError, ProgrammingError) as ex:
            print(f"Could not drop sequence '{sequence_name}': {ex}")
            raise
