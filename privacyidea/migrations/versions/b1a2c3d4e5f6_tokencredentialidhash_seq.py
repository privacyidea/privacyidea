"""Create missing tokencredentialidhash_seq on existing installs

The TokenCredentialIdHash model declares Sequence('tokencredentialidhash_seq')
on its id column, so SQLAlchemy 2.0's MariaDB/Postgres dialect emits
SELECT nextval(tokencredentialidhash_seq) on every insert. Some installs
ended up with the table but without the sequence, causing every insert to
fail with "Unknown SEQUENCE". Create it here if missing and advance it past
any existing ids so the next insert gets a free PK.

Revision ID: b1a2c3d4e5f6
Revises: 06b105a4f941
Create Date: 2026-04-22 14:30:00.000000

"""
from alembic import op
from sqlalchemy import text, Sequence
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.schema import CreateSequence

revision = 'b1a2c3d4e5f6'
down_revision = '06b105a4f941'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not bind.dialect.supports_sequences:
        # MySQL itself has no CREATE SEQUENCE; only MariaDB 10.3+ and Postgres do.
        return
    try:
        max_id = bind.execute(
            text("SELECT COALESCE(MAX(id), 0) FROM tokencredentialidhash")
        ).scalar() or 0
        start = max_id + 1
        # Build the sequence through SQLAlchemy's CreateSequence construct rather
        # than a raw "CREATE SEQUENCE" string. CreateSequence is rewritten by the
        # increment_by_zero @compiles hook in privacyidea.models.db, which appends
        # INCREMENT BY 0 on MariaDB. A Galera cluster only accepts a cached
        # sequence when it is defined that way (so each node gets a distinct
        # offset); a plain string would bypass the hook and fail with "CACHE
        # without INCREMENT BY 0 in Galera cluster". if_not_exists handles the
        # already-present case; the explicit RESTART afterwards covers installs
        # where the sequence exists but lags MAX(id), which would otherwise still
        # produce duplicate-PK errors on the next insert.
        seq = Sequence("tokencredentialidhash_seq", start=start)
        op.execute(CreateSequence(seq, if_not_exists=True))
        op.execute(f"ALTER SEQUENCE tokencredentialidhash_seq RESTART WITH {start}")
    except (OperationalError, ProgrammingError) as ex:
        print(f"Could not create sequence 'tokencredentialidhash_seq': {ex}")
        raise


def downgrade():
    bind = op.get_bind()
    if not bind.dialect.supports_sequences:
        return
    try:
        op.execute("DROP SEQUENCE IF EXISTS tokencredentialidhash_seq")
    except (OperationalError, ProgrammingError) as ex:
        print(f"Could not drop sequence 'tokencredentialidhash_seq': {ex}")
        raise
