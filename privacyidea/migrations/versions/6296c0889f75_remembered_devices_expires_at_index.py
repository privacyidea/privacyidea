"""v3.14: Add an index on remembered_devices.expires_at

Revision ID: 6296c0889f75
Revises: b8c9d0e1f2a3
Create Date: 2026-08-27 00:00:00.000000

"""
from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = '6296c0889f75'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade():
    try:
        op.create_index('ix_remembered_devices_expires_at', 'remembered_devices', ['expires_at'])
    except (OperationalError, ProgrammingError) as ex:
        if "already exists" in str(ex.orig).lower():
            print("Index 'ix_remembered_devices_expires_at' already exists.")
        else:
            print("Could not add index 'ix_remembered_devices_expires_at'.")
            raise


def downgrade():
    try:
        op.drop_index('ix_remembered_devices_expires_at', table_name='remembered_devices')
    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such index" in msg or "does not exist" in msg or "check that it exists" in msg:
            print("Index 'ix_remembered_devices_expires_at' already removed.")
        else:
            print("Could not remove index 'ix_remembered_devices_expires_at'.")
            raise
