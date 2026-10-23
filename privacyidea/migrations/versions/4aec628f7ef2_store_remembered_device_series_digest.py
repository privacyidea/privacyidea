"""v3.14.1: Store the digest of the series id of remembered devices

The cookie of a remembered device carries a series id and a counter. The remembered_devices table stores the SHA-256
digest of the series id as 64 hex characters instead of the series id itself, and a presented cookie is looked up by the
digest of its series id. The upgrade replaces each stored series id with its digest, so the cookies the clients hold
are recognized as before. A series id privacyIDEA creates is 43 characters long, so a value that is a digest already
stays as it is and the upgrade can run again.

The series ids cannot be computed from their digests, and the previous version looks a device up by its series id. The
downgrade therefore removes the remembered devices stored with a digest. Their users log in with the second factor once
and can have the device remembered again.

Revision ID: 4aec628f7ef2
Revises: 9e8487714b46
Create Date: 2026-10-22 12:53:31.000000

"""
import hashlib
import logging
import re

import sqlalchemy as sa
from alembic import op

log = logging.getLogger("alembic.env")

revision = '4aec628f7ef2'
down_revision = '9e8487714b46'
branch_labels = None
depends_on = None

# A SHA-256 digest as hex characters, the way privacyIDEA stores it
DIGEST = re.compile(r"[0-9a-f]{64}")

remembered_devices = sa.table("remembered_devices", sa.column("series_id", sa.Unicode(64)))


def upgrade() -> None:
    bind = op.get_bind()
    stored = bind.execute(sa.select(remembered_devices.c.series_id)).scalars()
    digests = [{"stored_series_id": series_id, "digest": hashlib.sha256(series_id.encode("utf-8")).hexdigest()}
               for series_id in stored if not DIGEST.fullmatch(series_id)]
    if not digests:
        return
    bind.execute(remembered_devices.update()
                 .where(remembered_devices.c.series_id == sa.bindparam("stored_series_id"))
                 .values(series_id=sa.bindparam("digest")), digests)
    log.info(f"Stored the digest of the series id of {len(digests)} remembered devices.")


def downgrade() -> None:
    # A digest has 64 characters, a series id privacyIDEA creates 43
    removed = op.get_bind().execute(
        remembered_devices.delete().where(sa.func.length(remembered_devices.c.series_id) == 64)).rowcount
    if removed:
        log.warning(f"Removed {removed} remembered devices. Their users log in with the second factor once and can "
                    f"have the device remembered again.")
