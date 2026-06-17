"""v3.14: Add internaluserattribute table and migrate internal entries out of customuserattribute

Revision ID: 7d4e9b2c1a3f
Revises: b1a2c3d4e5f6
Create Date: 2026-04-28 00:00:00.000000

"""
from collections import defaultdict
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text, Sequence
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.schema import CreateSequence

from privacyidea.models.db import build_restart_sequence_sql

# revision identifiers, used by Alembic.
revision = '7d4e9b2c1a3f'
down_revision = '3cafe2771cdd'
branch_labels = None
depends_on = None

FIDO2_USER_ID_KEY = 'fido2_user_id'
LAST_USED_TOKEN_KEY = 'last_used_token'
LAST_USED_TOKEN_PREFIX = 'last_used_token_'
# Marker that ``validate.py`` always set on rows it wrote for the
# ``last_used_token_<agent>`` keys. Used to distinguish them from any
# admin-created ``customuserattribute`` rows that happen to share the prefix.
INTERNAL_TYPE_MARKER = 'pi_internal'


def _old_table():
    return sa.table(
        'customuserattribute',
        sa.column('id', sa.Integer),
        sa.column('user_id', sa.Unicode(320)),
        sa.column('resolver', sa.Unicode(120)),
        sa.column('realm_id', sa.Integer),
        sa.column('Key', sa.Unicode(255)),
        sa.column('Value', sa.UnicodeText),
        sa.column('Type', sa.Unicode(100)),
    )


def _new_table():
    return sa.table(
        'internaluserattribute',
        sa.column('user_id', sa.Unicode(320)),
        sa.column('resolver', sa.Unicode(120)),
        sa.column('realm_id', sa.Integer),
        sa.column('Key', sa.Unicode(255)),
        sa.column('Value', sa.JSON),
        sa.column('last_modified', sa.DateTime),
        sa.column('node', sa.Unicode(120)),
    )


def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # The model declares Sequence('internaluserattribute_seq'), so SQLAlchemy
    # emits SELECT nextval(...) on every ORM insert. Create the sequence on
    # any backend that supports CREATE SEQUENCE (Postgres + MariaDB 10.3+).
    # Build it through SQLAlchemy's CreateSequence construct rather than a raw
    # "CREATE SEQUENCE" string: CreateSequence is rewritten by the
    # increment_by_zero @compiles hook in privacyidea.models.db, which appends
    # INCREMENT BY 0 on MariaDB so a Galera cluster accepts the cached sequence.
    # A raw string bypasses the hook and fails with "CACHE without INCREMENT BY
    # 0 in Galera cluster".
    if bind.dialect.supports_sequences:
        op.execute(CreateSequence(Sequence("internaluserattribute_seq"), if_not_exists=True))

    try:
        if is_postgres:
            # Postgres needs the column default wired to the sequence so raw
            # INSERTs (e.g. our data-migration block below) get an id.
            id_column = sa.Column(
                'id', sa.Integer(), nullable=False,
                server_default=sa.text("nextval('internaluserattribute_seq')"),
            )
        else:
            id_column = sa.Column('id', sa.Integer(), nullable=False, autoincrement=True)
        op.create_table(
            'internaluserattribute',
            id_column,
            sa.Column('user_id', sa.Unicode(length=320), nullable=True),
            sa.Column('resolver', sa.Unicode(length=120), nullable=True),
            sa.Column('realm_id', sa.Integer(), nullable=True),
            sa.Column('Key', sa.Unicode(length=255), nullable=False),
            sa.Column('Value', sa.JSON(), nullable=True),
            sa.Column('last_modified', sa.DateTime(), nullable=True),
            sa.Column('node', sa.Unicode(length=120), nullable=True),
            sa.ForeignKeyConstraint(['realm_id'], ['realm.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'resolver', 'realm_id', 'Key',
                                name='uq_internaluserattribute_user_key'),
        )
    except (OperationalError, ProgrammingError) as ex:
        if "already exists" in str(ex.orig).lower():
            print("Table 'internaluserattribute' already exists.")
        else:
            print("Could not add table 'internaluserattribute' to database.")
            raise

    # Advance the sequence past any existing rows. Covers the
    # table-already-exists branch above where rows may already be present
    # and the sequence (newly created or pre-existing) would otherwise hand
    # out a value <= MAX(id), causing duplicate-PK errors on the next insert.
    if bind.dialect.supports_sequences:
        max_id = bind.execute(
            text("SELECT COALESCE(MAX(id), 0) FROM internaluserattribute")
        ).scalar() or 0
        # No SQLAlchemy DDL construct exists for ALTER SEQUENCE ... RESTART, so a
        # raw string would only be correct on one backend. build_restart_sequence_sql
        # emits each dialect's accepted syntax and, crucially, appends INCREMENT BY 0
        # on MariaDB — a Galera cluster otherwise rejects RESTART on a cached sequence
        # with "CACHE without INCREMENT BY 0 in Galera cluster".
        op.execute(build_restart_sequence_sql("internaluserattribute_seq", max_id + 1, bind.dialect.name))

    _run_data_migration(op.get_bind())


def _run_data_migration(conn) -> None:
    """
    Move internal-state rows from ``customuserattribute`` into
    ``internaluserattribute``. Safe to re-run: each insert checks for an
    existing target row first, so partial-failure recovery (re-running the
    migration after a crash between insert and delete) is supported.

    Scope:
    - ``fido2_user_id`` rows are matched by exact key. The Type column was
      never set for these (see ``passkeytoken.py`` history), so no Type
      filter is applied.
    - ``last_used_token_<agent>`` rows are matched by prefix AND require
      ``Type='pi_internal'`` so that an admin-created customuserattribute
      row that happens to share the prefix is left untouched.
    """
    old = _old_table()
    new = _new_table()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def _target_exists(user_id, resolver, realm_id, key) -> bool:
        return conn.execute(
            sa.select(new.c.user_id).where(
                new.c.user_id == user_id,
                new.c.resolver == resolver,
                new.c.realm_id == realm_id,
                new.c.Key == key,
            )
        ).first() is not None

    # 1. fido2_user_id: one row per user, copy Value as JSON string
    fido_rows = conn.execute(
        sa.select(old.c.user_id, old.c.resolver, old.c.realm_id, old.c.Value)
        .where(old.c.Key == FIDO2_USER_ID_KEY)
    ).fetchall()
    for row in fido_rows:
        if _target_exists(row.user_id, row.resolver, row.realm_id, FIDO2_USER_ID_KEY):
            continue
        conn.execute(
            new.insert().values(
                user_id=row.user_id,
                resolver=row.resolver,
                realm_id=row.realm_id,
                Key=FIDO2_USER_ID_KEY,
                Value=row.Value,
                last_modified=now,
                node=None,
            )
        )

    # 2. last_used_token_<user_agent>: consolidate per user into a single dict row.
    # Filter by Type='pi_internal' so we only consume rows privacyIDEA wrote itself.
    last_used_rows = conn.execute(
        sa.select(old.c.user_id, old.c.resolver, old.c.realm_id, old.c.Key, old.c.Value)
        .where(
            old.c.Key.like(f'{LAST_USED_TOKEN_PREFIX}%'),
            old.c.Type == INTERNAL_TYPE_MARKER,
        )
    ).fetchall()
    grouped = defaultdict(dict)
    for row in last_used_rows:
        user_agent = row.Key[len(LAST_USED_TOKEN_PREFIX):]
        if not user_agent:
            continue
        grouped[(row.user_id, row.resolver, row.realm_id)][user_agent] = row.Value
    for (user_id, resolver, realm_id), value_dict in grouped.items():
        if _target_exists(user_id, resolver, realm_id, LAST_USED_TOKEN_KEY):
            continue
        conn.execute(
            new.insert().values(
                user_id=user_id,
                resolver=resolver,
                realm_id=realm_id,
                Key=LAST_USED_TOKEN_KEY,
                Value=value_dict,
                last_modified=now,
                node=None,
            )
        )

    # 3. Remove migrated rows from the old table. The DELETE is naturally
    # idempotent; running it after a clean run is a no-op.
    conn.execute(old.delete().where(old.c.Key == FIDO2_USER_ID_KEY))
    conn.execute(old.delete().where(
        old.c.Key.like(f'{LAST_USED_TOKEN_PREFIX}%'),
        old.c.Type == INTERNAL_TYPE_MARKER,
    ))


def downgrade():
    # Best-effort rollback: copy the data back into customuserattribute and drop the new table.
    conn = op.get_bind()
    old = _old_table()
    new = _new_table()

    try:
        fido_rows = conn.execute(
            sa.select(new.c.user_id, new.c.resolver, new.c.realm_id, new.c.Value)
            .where(new.c.Key == FIDO2_USER_ID_KEY)
        ).fetchall()
        for row in fido_rows:
            conn.execute(
                old.insert().values(
                    user_id=row.user_id,
                    resolver=row.resolver,
                    realm_id=row.realm_id,
                    Key=FIDO2_USER_ID_KEY,
                    Value=row.Value,
                    Type=None,
                )
            )

        last_used_rows = conn.execute(
            sa.select(new.c.user_id, new.c.resolver, new.c.realm_id, new.c.Value)
            .where(new.c.Key == LAST_USED_TOKEN_KEY)
        ).fetchall()
        for row in last_used_rows:
            value_dict = row.Value or {}
            for user_agent, token_type in value_dict.items():
                conn.execute(
                    old.insert().values(
                        user_id=row.user_id,
                        resolver=row.resolver,
                        realm_id=row.realm_id,
                        Key=f'{LAST_USED_TOKEN_PREFIX}{user_agent}',
                        Value=token_type,
                        Type='pi_internal',
                    )
                )
    except (OperationalError, ProgrammingError) as ex:
        print(f"Could not copy data back to 'customuserattribute': {ex}")

    try:
        op.drop_table('internaluserattribute')
        if op.get_bind().dialect.supports_sequences:
            op.execute("DROP SEQUENCE IF EXISTS internaluserattribute_seq")
    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print("Table 'internaluserattribute' already removed.")
        else:
            print("Could not remove table 'internaluserattribute'.")
            raise
