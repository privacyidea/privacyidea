"""v3.14: Add user_lock_state live-state table

Create the user_lock_state table that records the current locked status
of a user, keyed by the same (resolver, uid, realm) tuple used in
authentication_log. There is deliberately no failure-counter column: failure
counts are derived by querying authentication_log over the policy's time
window. The load-bearing field is lock_expires_at - a row whose
lock_expires_at lies in the future means the user is currently locked.
lock_cause records whether the engine or an administrator imposed that lock.

A local database admin is locked here too and has none of those three values,
only a login name: their row carries it as the uid with an empty resolver and
realm, which cannot collide with a user's (a user row always has all three).
user_role says which of the two a row is, so nothing has to infer it from the
columns a row leaves empty.

Revision ID: c1a9f7e2b840
Revises: 173d32328846
Create Date: 2026-06-08 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'c1a9f7e2b840'
down_revision = '173d32328846'
branch_labels = None
depends_on = None

TABLES = ['user_lock_state']


def _unicode_case_sensitive(length):
    """
    A case-sensitive string column type (mirrors models.utils.case_sensitive_unicode).

    The identity columns (resolver/uid/realm/username) are the user-lock visibility boundary: a
    user-scoped read policy filters on them. On MySQL/MariaDB the server-default collation is typically
    case-insensitive (*_ci), which would make that boundary match case-insensitively -- a fail-open
    authorization risk. Pinning to utf8mb4_bin makes matching case-sensitive; SQLite, PostgreSQL and Oracle
    already compare case-sensitively by default. Kept self-contained here so the migration stays a stable
    snapshot.
    """
    return sa.Unicode(length).with_variant(mysql.VARCHAR(length, charset="utf8mb4", collation="utf8mb4_bin"),
                                           "mysql", "mariadb")


def _existing_tables() -> set[str]:
    """
    The names of the tables that already exist, lower-cased.

    Reflected once per migration rather than once per table: on a normal run nothing exists yet, so this
    single catalog read is all the guard below costs. Lower-cased because Oracle folds unquoted identifiers
    to upper case and the inspector reflects them back lower-cased (mirrors models.db.sequence_exists).
    """
    return {name.lower() for name in sa.inspect(op.get_bind()).get_table_names()}


def _create_table(existing_tables: set[str], table_name: str, *columns) -> None:
    """
    Create the table unless it is already there -- a schema bootstrapped from the models with create_all
    before this migration ran carries it -- then add each of its COLUMNS that is absent.

    Presence is established by reflection rather than by swallowing an "already exists" error, which Oracle
    never says: it reports an existing object as ORA-00955 ("name is already used by an existing object").
    models.db.sequence_exists reflects for the same reason.

    The columns are reconciled rather than left to the CREATE TABLE alone, because this revision is the only
    place they are declared: a database already carrying the table skips that statement, so a column added to
    this revision after it ran there would never arrive, and every read of it would fail. A column added to a
    populated table takes the value of the rows already in it from its server_default, so one declared NOT NULL
    needs one.
    """
    if table_name.lower() in existing_tables:
        print(f"Table '{table_name}' already exists.")
        existing_columns = {column["name"].lower()
                            for column in sa.inspect(op.get_bind()).get_columns(table_name)}
        for column in columns:
            if not isinstance(column, sa.Column) or column.name.lower() in existing_columns:
                continue
            print(f"Adding the missing column '{column.name}' to '{table_name}'.")
            op.add_column(table_name, column)
        return
    op.create_table(table_name, *columns)


def upgrade():
    existing_tables = _existing_tables()
    _create_table(
        existing_tables,
        'user_lock_state',
        sa.Column('resolver', _unicode_case_sensitive(120), nullable=False),
        sa.Column('uid', _unicode_case_sensitive(320), nullable=False),
        sa.Column('realm', _unicode_case_sensitive(255), nullable=False),
        sa.Column('username', _unicode_case_sensitive(255), nullable=True),
        sa.Column('user_role', sa.Unicode(length=20), nullable=False, server_default='user'),
        sa.Column('lock_expires_at', sa.DateTime(), nullable=True),
        sa.Column('lock_cause', sa.Unicode(length=20), nullable=False, server_default='POLICY'),
        sa.Column('error_message', sa.Unicode(length=500), nullable=True),
        sa.Column('locked_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('resolver', 'uid', 'realm'),
    )


def downgrade():
    for table_name in TABLES:
        try:
            op.drop_table(table_name)
        except (OperationalError, ProgrammingError) as ex:
            msg = str(ex.orig).lower()
            if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
                print(f"Table '{table_name}' already removed.")
            else:
                print(f"Could not remove table '{table_name}'.")
                raise
