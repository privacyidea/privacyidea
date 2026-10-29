"""v3.14.1: Restart the id sequences of internaluserattribute and tokeninfo after their highest id

privacyIDEA takes the id of a new internal user attribute or token info from the sequence of the table. A data
migration that inserts rows without an id leaves the id to the column default instead. On MariaDB that is
AUTO_INCREMENT, and on databases whose id column has a default of its own, it is not the sequence either. The sequence
then stays behind the ids of the inserted rows: it hands out ids that already exist, and every new row fails with a
duplicate primary key until the sequence has passed them.

7d4e9b2c1a3f inserts the internal user attributes it moves out of customuserattribute without an id. a1e0ba6ad9dc
takes the ids of its token info marker rows from tokeninfo_seq, but its version in 3.14.0 inserted them without an id.
An installation that ran that version can have the gap in tokeninfo.

The migration restarts a sequence at the id after the highest one of its table when the sequence is behind the table.
A sequence that is in step or ahead keeps its position, so the ids that a writer which still runs during the upgrade
took from it are not handed out again. Databases without sequences (MySQL, SQLite) are not changed, and neither is a
sequence that does not exist.

Revision ID: 4b810261d282
Revises: 9e8487714b46
Create Date: 2026-10-21 16:00:00.000000

"""
from alembic import op
from sqlalchemy import inspect

from privacyidea.models.db import restart_sequence_past_max

revision = '4b810261d282'
down_revision = '9e8487714b46'
branch_labels = None
depends_on = None

TABLE_SEQUENCES = {
    'internaluserattribute': 'internaluserattribute_seq',
    'tokeninfo': 'tokeninfo_seq',
}


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    for table_name, sequence_name in TABLE_SEQUENCES.items():
        if inspector.has_table(table_name):
            restart_sequence_past_max(op, table_name, sequence_name)


def downgrade() -> None:
    # The position of a sequence is not part of the schema of the previous revision
    pass
