"""v3.13.4: Give the container and tokengroup primary keys a generator again

The models declare how these primary keys are filled: the container tables with
an Identity, so the database generates the id, and tokengroup/tokentokengroup
with a Sequence, so SQLAlchemy asks for the next value. Both declarations were
lost for a while, and a database created in the meantime has neither - on Oracle,
which has no autoincrement of its own, every insert into those tables then fails
with ORA-01400.

This repairs whichever part an installation is missing:

* tokengroup_seq / tokentokengroup_seq are created if absent and advanced past
  the largest id in their table. Installs that ran the earlier migration which
  introduced them already have them; installs created while the models carried
  no Sequence do not.
* On Oracle, a container table whose id column has neither an identity nor a
  default gets a sequence-backed default, which is how the column would have
  been created. Oracle cannot turn an existing column into an identity column
  (ORA-30673), so a default is the way to hand generation back to the database.
  MySQL, MariaDB and PostgreSQL create those columns as AUTO_INCREMENT or SERIAL
  and need nothing.

Revision ID: c7f1a2b3d4e5
Revises: b1a2c3d4e5f6
Create Date: 2026-09-16 12:00:00.000000

"""
from alembic import op
from sqlalchemy import column, func, inspect, select, table, text, Sequence
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.schema import CreateSequence, DropSequence
from privacyidea.models.db import build_restart_sequence_sql

revision = 'c7f1a2b3d4e5'
down_revision = 'b1a2c3d4e5f6'
branch_labels = None
depends_on = None

# The models ask SQLAlchemy for the next value from these, on every dialect that has
# sequences. An earlier migration created them; installs that never ran it, or that were
# created while the models carried no Sequence, are missing them.
MODEL_SEQUENCES = {
    "tokengroup": "tokengroup_seq",
    "tokentokengroup": "tokentokengroup_seq",
}

# The models let the database generate these. Only Oracle can end up without a generator,
# and only on a database created while the Identity was missing.
CONTAINER_TABLES = [
    "tokencontainer",
    "tokencontainerinfo",
    "tokencontainerowner",
    "tokencontainerstates",
    "tokencontainertemplate",
]


def _existing_sequences(bind) -> set:
    """Reflected names are upper-cased on Oracle, so compare in lower case."""
    return {name.lower() for name in inspect(bind).get_sequence_names()}


def _next_id(bind, table_name: str) -> int:
    """The value a generator must start at so that it cannot collide with existing rows."""
    max_id_stmt = select(func.coalesce(func.max(column("id")), 0)).select_from(table(table_name))
    return (bind.execute(max_id_stmt).scalar() or 0) + 1


def _oracle_id_is_generated(bind, table_name: str) -> bool:
    """Whether Oracle fills this table's id by itself, through an identity or a default."""
    row = bind.execute(text("SELECT identity_column, data_default FROM user_tab_columns "
                            "WHERE table_name = :name AND column_name = 'ID'"),
                       {"name": table_name.upper()}).first()
    if row is None:
        # No such table on this installation; there is nothing to repair.
        return True
    identity, default = row
    return identity == "YES" or default is not None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.supports_sequences:
        existing = _existing_sequences(bind)
        for table_name, sequence_name in MODEL_SEQUENCES.items():
            try:
                start = _next_id(bind, table_name)
                # Oracle before 23c supports neither "CREATE SEQUENCE IF NOT EXISTS" nor
                # "ALTER SEQUENCE ... RESTART WITH", so branch on what is already there and
                # let build_restart_sequence_sql emit the RESTART START WITH it accepts.
                if bind.dialect.name == "oracle":
                    if sequence_name.lower() not in existing:
                        op.execute(CreateSequence(Sequence(sequence_name, start=start)))
                    else:
                        op.execute(build_restart_sequence_sql(sequence_name, start, "oracle"))
                    continue
                # CreateSequence rather than a raw string, because the increment_by_zero
                # @compiles hook in privacyidea.models.db appends INCREMENT BY 0 on MariaDB,
                # which Galera requires for a cached sequence.
                op.execute(CreateSequence(Sequence(sequence_name, start=start), if_not_exists=True))
                # Covers installs where the sequence exists but lags MAX(id), which would
                # otherwise hand out an id that is already taken.
                op.execute(build_restart_sequence_sql(sequence_name, start, bind.dialect.name))
            except (OperationalError, ProgrammingError) as ex:
                print(f"Could not create sequence '{sequence_name}': {ex}")
                raise

    if bind.dialect.name != "oracle":
        return

    existing = _existing_sequences(bind)
    for table_name in CONTAINER_TABLES:
        if _oracle_id_is_generated(bind, table_name):
            continue
        sequence_name = f"{table_name}_seq"
        print(f"Giving {table_name}.id the generator this database is missing.")
        try:
            start = _next_id(bind, table_name)
            if sequence_name.lower() not in existing:
                op.execute(CreateSequence(Sequence(sequence_name, start=start)))
            else:
                op.execute(build_restart_sequence_sql(sequence_name, start, "oracle"))
            op.execute(f"ALTER TABLE {table_name} MODIFY (id DEFAULT {sequence_name}.nextval)")
        except (OperationalError, ProgrammingError) as ex:
            print(f"Could not give '{table_name}.id' a default: {ex}")
            raise


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "oracle":
        # Nothing else was changed that is this migration's to undo: the two sequences
        # belong to an earlier migration, and on PostgreSQL a column default depends on
        # them.
        return
    existing = _existing_sequences(bind)
    for table_name in CONTAINER_TABLES:
        sequence_name = f"{table_name}_seq"
        if sequence_name.lower() not in existing:
            continue
        try:
            op.execute(f"ALTER TABLE {table_name} MODIFY (id DEFAULT NULL)")
            op.execute(DropSequence(Sequence(sequence_name)))
        except (OperationalError, ProgrammingError) as ex:
            print(f"Could not drop the default of '{table_name}.id': {ex}")
            raise
