"""v3.14: Add a composite (client_id, resolver, user_id, realm_id) index to remembered_devices

Revision ID: 2da1c3101430
Revises: 6296c0889f75
Create Date: 2026-08-27 00:00:00.000000

"""
from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = '2da1c3101430'
down_revision = '6296c0889f75'
branch_labels = None
depends_on = None


def upgrade():
    try:
        op.create_index('ix_remembered_devices_identity', 'remembered_devices',
                        ['client_id', 'resolver', 'user_id', 'realm_id'])
    except (OperationalError, ProgrammingError) as ex:
        if "already exists" in str(ex.orig).lower():
            print("Index 'ix_remembered_devices_identity' already exists.")
        else:
            print("Could not add index 'ix_remembered_devices_identity'.")
            raise


def downgrade():
    try:
        op.drop_index('ix_remembered_devices_identity', table_name='remembered_devices')
    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such index" in msg or "does not exist" in msg or "check that it exists" in msg:
            print("Index 'ix_remembered_devices_identity' already removed.")
        else:
            print("Could not remove index 'ix_remembered_devices_identity'.")
            raise
