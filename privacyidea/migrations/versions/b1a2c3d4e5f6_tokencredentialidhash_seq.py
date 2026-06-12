"""Create missing tokencredentialidhash_seq on existing installs

The TokenCredentialIdHash model declares Sequence('tokencredentialidhash_seq')
on its id column, so SQLAlchemy 2.0's MariaDB/Postgres/Oracle dialect emits
SELECT nextval(tokencredentialidhash_seq) on every insert. Some installs
ended up with the table but without the sequence, causing every insert to
fail with "Unknown SEQUENCE". Create it here if missing and advance it past
any existing ids so the next insert gets a free PK.

Revision ID: b1a2c3d4e5f6
Revises: 06b105a4f941
Create Date: 2026-04-22 14:30:00.000000

"""
from alembic import op
from sqlalchemy import text, inspect, Sequence
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.schema import CreateSequence, DropSequence
from privacyidea.models.db import build_restart_sequence_sql

revision = 'b1a2c3d4e5f6'
down_revision = '06b105a4f941'
branch_labels = None
depends_on = None

SEQ_NAME = "tokencredentialidhash_seq"


def _sequence_exists(bind) -> bool:
    """Return True if SEQ_NAME already exists. Reflected names are upper-cased on
    Oracle, so compare case-insensitively."""
    existing = {name.lower() for name in inspect(bind).get_sequence_names()}
    return SEQ_NAME.lower() in existing


def upgrade():
    bind = op.get_bind()
    if not bind.dialect.supports_sequences:
        # MySQL itself has no CREATE SEQUENCE; only MariaDB 10.3+, Postgres and
        # Oracle do.
        return
    try:
        max_id = bind.execute(
            text("SELECT COALESCE(MAX(id), 0) FROM tokencredentialidhash")
        ).scalar() or 0
        start = max_id + 1
        # Oracle (19c+) supports neither "CREATE SEQUENCE IF NOT EXISTS" nor
        # "ALTER SEQUENCE ... RESTART WITH" (both are 23c-only / wrong syntax), so
        # reflect first and branch: create only when absent, otherwise advance it
        # with build_restart_sequence_sql, which emits Oracle's RESTART START WITH.
        if bind.dialect.name == "oracle":
            if not _sequence_exists(bind):
                op.execute(CreateSequence(Sequence(SEQ_NAME, start=start)))
            else:
                op.execute(build_restart_sequence_sql(SEQ_NAME, start, "oracle"))
            return
        # MariaDB/Postgres: build the sequence through SQLAlchemy's CreateSequence
        # construct rather than a raw "CREATE SEQUENCE" string. CreateSequence is
        # rewritten by the increment_by_zero @compiles hook in privacyidea.models.db,
        # which appends INCREMENT BY 0 on MariaDB. A Galera cluster only accepts a
        # cached sequence when it is defined that way (so each node gets a distinct
        # offset); a plain string would bypass the hook and fail with "CACHE without
        # INCREMENT BY 0 in Galera cluster". if_not_exists handles the already-present
        # case; the explicit RESTART afterwards covers installs where the sequence
        # exists but lags MAX(id), which would otherwise still produce duplicate-PK
        # errors on the next insert.
        op.execute(CreateSequence(Sequence(SEQ_NAME, start=start), if_not_exists=True))
        # The RESTART needs the same INCREMENT BY 0 treatment as the CREATE above
        # for Galera; there is no SQLAlchemy DDL construct for ALTER SEQUENCE that
        # the hook could rewrite, so build_restart_sequence_sql appends it on MariaDB.
        op.execute(build_restart_sequence_sql(SEQ_NAME, start, bind.dialect.name))
    except (OperationalError, ProgrammingError) as ex:
        print(f"Could not create sequence '{SEQ_NAME}': {ex}")
        raise


def downgrade():
    bind = op.get_bind()
    if not bind.dialect.supports_sequences:
        return
    try:
        # Oracle (19c+) has no "DROP SEQUENCE IF EXISTS", so reflect and drop only
        # if present. MariaDB/Postgres accept the IF EXISTS guard directly.
        if bind.dialect.name == "oracle":
            if _sequence_exists(bind):
                op.execute(DropSequence(Sequence(SEQ_NAME)))
        else:
            op.execute(f"DROP SEQUENCE IF EXISTS {SEQ_NAME}")
    except (OperationalError, ProgrammingError) as ex:
        print(f"Could not drop sequence '{SEQ_NAME}': {ex}")
        raise
