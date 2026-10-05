"""v3.14.1: Key the lock of a local admin on a placeholder resolver and realm

A local database admin has no resolver and no realm, and their user_lock_state row stored the empty string in
both key columns. Oracle stores an empty string as NULL, which a primary key column refuses, so on Oracle a local
admin could never be locked. Their rows now carry '~internal', which no resolver or realm name can be.

Only the other databases can hold such rows, so only there is anything rewritten.

Revision ID: 670d90ff7113
Revises: b7c1e4d2a9f3
Create Date: 2026-10-02 15:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = '670d90ff7113'
down_revision = 'b7c1e4d2a9f3'
branch_labels = None
depends_on = None

PLACEHOLDER = '~internal'
ADMIN_INTERNAL = 'admin-internal'


def upgrade():
    try:
        result = op.get_bind().execute(
            sa.text("UPDATE user_lock_state SET resolver = :placeholder, realm = :placeholder "
                    "WHERE user_role = :role"),
            {"placeholder": PLACEHOLDER, "role": ADMIN_INTERNAL})
        if result.rowcount:
            print(f"Moved {result.rowcount} local admin lock(s) to the placeholder resolver and realm.")
    except Exception as exx:
        print(f"Could not rewrite the local admin locks in 'user_lock_state': {exx}")
        raise


def downgrade():
    connection = op.get_bind()
    try:
        if connection.dialect.name == 'oracle':
            # The empty key is what Oracle cannot store, so the locks it now holds cannot be moved back to it.
            result = connection.execute(sa.text("DELETE FROM user_lock_state WHERE user_role = :role"),
                                        {"role": ADMIN_INTERNAL})
            if result.rowcount:
                print(f"Removed {result.rowcount} local admin lock(s), which Oracle cannot key on an empty "
                      f"resolver and realm.")
        else:
            connection.execute(
                sa.text("UPDATE user_lock_state SET resolver = '', realm = '' WHERE user_role = :role"),
                {"role": ADMIN_INTERNAL})
    except Exception as exx:
        print(f"Could not restore the local admin locks in 'user_lock_state': {exx}")
        raise
