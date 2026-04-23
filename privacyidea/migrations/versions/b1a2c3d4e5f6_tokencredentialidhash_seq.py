"""Create missing tokencredentialidhash_seq on existing installs

Migration 903a6ed6f6c4 created the table with sa.Identity() instead of
sa.Sequence(), so the sequence declared by the model was never created.
SQLAlchemy 2.0's MariaDB dialect honors Sequence() and emits
SELECT nextval(tokencredentialidhash_seq) on insert, which fails with
"Unknown SEQUENCE" on already-upgraded installs. Create it here if missing
and advance it past any existing ids.

Revision ID: b1a2c3d4e5f6
Revises: 06b105a4f941
Create Date: 2026-04-22 14:30:00.000000

"""
from alembic import op
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

revision = 'b1a2c3d4e5f6'
down_revision = '06b105a4f941'


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect not in ('mysql', 'mariadb', 'postgresql'):
        return
    try:
        max_id = bind.execute(
            text("SELECT COALESCE(MAX(id), 0) FROM tokencredentialidhash")
        ).scalar() or 0
        start = max_id + 1
        if dialect == 'postgresql':
            op.execute(f"CREATE SEQUENCE IF NOT EXISTS tokencredentialidhash_seq START WITH {start}")
            op.execute(f"SELECT setval('tokencredentialidhash_seq', {start}, false)")
        else:
            op.execute(f"CREATE SEQUENCE IF NOT EXISTS tokencredentialidhash_seq START WITH {start}")
    except (OperationalError, ProgrammingError) as ex:
        print(f"Could not create sequence 'tokencredentialidhash_seq': {ex}")
        raise


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect not in ('mysql', 'mariadb', 'postgresql'):
        return
    try:
        op.execute("DROP SEQUENCE IF EXISTS tokencredentialidhash_seq")
    except (OperationalError, ProgrammingError) as ex:
        print(f"Could not drop sequence 'tokencredentialidhash_seq': {ex}")
