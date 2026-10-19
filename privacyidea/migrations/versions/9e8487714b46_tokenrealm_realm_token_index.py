"""v3.14.1: Add an index on tokenrealm (realm_id, token_id)

The token list of a realm, and every token list of an administrator whose policies are restricted to
realms, selects the tokens by tokenrealm.realm_id. PostgreSQL and Oracle do not index foreign key columns,
so they scan the whole tokenrealm table for it. MySQL and MariaDB index the foreign key column themselves;
there the index also contains the token ID, so the lookup does not need to read the table rows. They drop
their own index on realm_id once this one exists, so the downgrade puts an index on realm_id back there.

The index may already exist, created from the models or by hand, so the migration only adds it when no
index on these two columns exists.

Revision ID: 9e8487714b46
Revises: f8a498439814
Create Date: 2026-10-19 15:00:00.000000

"""
from alembic import op
from sqlalchemy import inspect

revision = '9e8487714b46'
down_revision = 'f8a498439814'
branch_labels = None
depends_on = None

INDEX_NAME = 'ix_tokenrealm_realm_token'


def upgrade() -> None:
    indexes = inspect(op.get_bind()).get_indexes('tokenrealm')
    if not any(index["column_names"] == ["realm_id", "token_id"] for index in indexes):
        op.create_index(INDEX_NAME, 'tokenrealm', ['realm_id', 'token_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    indexes = inspect(bind).get_indexes('tokenrealm')
    if not any(index["name"] == INDEX_NAME for index in indexes):
        return
    other_realm_id_indexes = [index for index in indexes
                              if index["name"] != INDEX_NAME and index["column_names"][:1] == ["realm_id"]]
    if bind.dialect.name in ("mysql", "mariadb") and not other_realm_id_indexes:
        # The foreign key on realm_id needs an index, and the one MySQL and MariaDB created for it was dropped by
        # them when the upgrade added this index
        op.create_index('ix_tokenrealm_realm_id', 'tokenrealm', ['realm_id'], unique=False)
    op.drop_index(INDEX_NAME, table_name='tokenrealm')
