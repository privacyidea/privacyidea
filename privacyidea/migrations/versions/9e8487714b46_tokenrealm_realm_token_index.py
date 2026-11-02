"""v3.14.1: Add an index on tokenrealm (realm_id, token_id)

The token list of a realm, and every token list of an administrator whose policies are restricted to
realms, selects the tokens by tokenrealm.realm_id. PostgreSQL and Oracle do not index foreign key columns,
so they scan the whole tokenrealm table for it. MySQL and MariaDB index the foreign key column themselves;
there the index also contains the token ID, so the lookup does not need to read the table rows.

MySQL and MariaDB drop the index they created for the foreign key, named "realm_id", as soon as this index
exists, because it serves the foreign key as well. The downgrade puts that index back under its name, and
the upgrade removes an index of that name on realm_id alone again, so that both directions end with the
indexes the database had before.

The index may already exist, created from the models or by hand, so the migration only adds it when no
index on these two columns exists.

Revision ID: 9e8487714b46
Revises: f8a498439814
Create Date: 2026-10-19 15:00:00.000000

"""
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.engine import Connection

revision = '9e8487714b46'
down_revision = 'f8a498439814'
branch_labels = None
depends_on = None

INDEX_NAME = 'ix_tokenrealm_realm_token'
# The name MySQL and MariaDB give the index they create for the foreign key on realm_id
FOREIGN_KEY_INDEX_NAME = 'realm_id'


def _uses_foreign_key_index(bind: Connection) -> bool:
    return bind.dialect.name in ("mysql", "mariadb")


def upgrade() -> None:
    bind = op.get_bind()
    indexes = inspect(bind).get_indexes('tokenrealm')
    if not any(index["column_names"] == ["realm_id", "token_id"] for index in indexes):
        op.create_index(INDEX_NAME, 'tokenrealm', ['realm_id', 'token_id'], unique=False)
    if _uses_foreign_key_index(bind):
        indexes = inspect(bind).get_indexes('tokenrealm')
        if any(index["name"] == FOREIGN_KEY_INDEX_NAME and index["column_names"] == ["realm_id"] for index in indexes):
            op.drop_index(FOREIGN_KEY_INDEX_NAME, table_name='tokenrealm')


def downgrade() -> None:
    bind = op.get_bind()
    indexes = inspect(bind).get_indexes('tokenrealm')
    if not any(index["name"] == INDEX_NAME for index in indexes):
        return
    other_realm_id_indexes = [index for index in indexes
                              if index["name"] != INDEX_NAME and index["column_names"][:1] == ["realm_id"]]
    if _uses_foreign_key_index(bind) and not other_realm_id_indexes:
        # The foreign key on realm_id needs an index
        op.create_index(FOREIGN_KEY_INDEX_NAME, 'tokenrealm', ['realm_id'], unique=False)
    op.drop_index(INDEX_NAME, table_name='tokenrealm')
