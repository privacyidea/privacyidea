"""v3.14: Add a (client_id, created_at) index to remembered_devices

Revision ID: 4b95044dc3e8
Revises: 2da1c3101430
Create Date: 2026-08-28 00:00:00.000000

"""
from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = '4b95044dc3e8'
down_revision = '2da1c3101430'
branch_labels = None
depends_on = None


def upgrade():
    try:
        op.create_index('ix_remembered_devices_client_created', 'remembered_devices',
                        ['client_id', 'created_at'])
    except (OperationalError, ProgrammingError) as ex:
        if "already exists" in str(ex.orig).lower():
            print("Index 'ix_remembered_devices_client_created' already exists.")
        else:
            print("Could not add index 'ix_remembered_devices_client_created'.")
            raise


def downgrade():
    try:
        op.drop_index('ix_remembered_devices_client_created', table_name='remembered_devices')
    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such index" in msg or "does not exist" in msg or "check that it exists" in msg:
            print("Index 'ix_remembered_devices_client_created' already removed.")
        else:
            print("Could not remove index 'ix_remembered_devices_client_created'.")
            raise
