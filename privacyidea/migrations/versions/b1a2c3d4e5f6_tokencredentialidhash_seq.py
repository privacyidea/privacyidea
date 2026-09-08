"""v3.13: Create missing tokencredentialidhash_seq on existing installs

The TokenCredentialIdHash model declares Sequence('tokencredentialidhash_seq')
on its id column, so SQLAlchemy 2.0's MariaDB/Postgres/Oracle dialect emits
SELECT nextval(tokencredentialidhash_seq) on every insert. Some installs
ended up with the table but without the sequence, causing every insert to
fail with "Unknown SEQUENCE". Create it here if missing and advance it past
any existing ids so the next insert gets a free PK.

Revision ID: b1a2c3d4e5f6
Revises: 3cafe2771cdd
Create Date: 2026-04-22 14:30:00.000000

"""
from alembic import op
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from privacyidea.models.db import (build_restart_sequence_sql, create_sequence_if_supported,
                                   drop_sequence_if_supported, sequence_exists)

revision = 'b1a2c3d4e5f6'
down_revision = '06b105a4f941'
branch_labels = None
depends_on = None

SEQ_NAME = "tokencredentialidhash_seq"


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
        # Oracle (19c+) has no "CREATE SEQUENCE IF NOT EXISTS" to lean on, so
        # create_sequence_if_supported reflects instead — which means a sequence
        # that is already there keeps its old, possibly lagging value. Advance it
        # explicitly in that case, and skip the RESTART when the sequence was just
        # created with the right START WITH.
        if sequence_exists(bind, SEQ_NAME):
            op.execute(build_restart_sequence_sql(SEQ_NAME, start, bind.dialect.name))
        else:
            create_sequence_if_supported(op, SEQ_NAME, start=start)
    except (OperationalError, ProgrammingError) as ex:
        print(f"Could not create sequence '{SEQ_NAME}': {ex}")
        raise


def downgrade():
    try:
        drop_sequence_if_supported(op, SEQ_NAME)
    except (OperationalError, ProgrammingError) as ex:
        print(f"Could not drop sequence '{SEQ_NAME}': {ex}")
        raise
