"""v3.14: Add metric_aggregate table

Used by the privacyidea.lib.metrics module to store rolling pre-aggregated
counter and histogram values, partitioned by 5-minute window and node.

Revision ID: c2d3e4f5a6b7
Revises: 7d4e9b2c1a3f
Create Date: 2026-04-29 00:00:00.000000

"""
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError

log = logging.getLogger("alembic.runtime.migration")

revision = 'c2d3e4f5a6b7'
down_revision = '7d4e9b2c1a3f'
branch_labels = None
depends_on = None


_BUCKET_COLUMNS = [
    "bucket_le_50ms", "bucket_le_100ms", "bucket_le_150ms", "bucket_le_200ms",
    "bucket_le_250ms", "bucket_le_500ms", "bucket_le_1s", "bucket_le_2s",
    "bucket_le_5s",
]


def upgrade():
    if sa.inspect(op.get_bind()).has_table("metric_aggregate"):
        # The table can already exist when the schema was bootstrapped from the
        # models (create_all) before this migration ran. The model defines the
        # same indexes and unique constraint, so there is nothing left to do.
        log.info("Table 'metric_aggregate' already exists, skipping creation.")
        return

    try:
        op.execute(sa.schema.CreateSequence(sa.Sequence("metric_aggregate_seq")))
    except (OperationalError, ProgrammingError):
        # Some dialects (sqlite, mysql) don't have sequences - SQLAlchemy
        # falls back to autoincrement, which is fine. Other failures
        # (permissions, connection issues) bubble up so the operator sees them.
        pass

    columns = [
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("metric_name", sa.Unicode(length=128), nullable=False),
        # Full label payload: JSON blob with sorted keys; can be arbitrarily
        # long (resolver names + types + ops + identifiers etc).
        sa.Column("labels_key", sa.Text(), nullable=False, server_default=""),
        # Fixed-size hex digest (SHA-256) of labels_key, used by the unique
        # constraint so the composite index stays under MySQL's 3072-byte
        # limit regardless of how long labels_key grows.
        sa.Column("labels_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("node", sa.Unicode(length=255), nullable=False, server_default=""),
        sa.Column("window_start", sa.DateTime(timezone=False), nullable=False),
        sa.Column("count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("sum_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("max_value", sa.Float(), nullable=False, server_default="0"),
    ]
    for bucket in _BUCKET_COLUMNS:
        columns.append(sa.Column(bucket, sa.BigInteger(), nullable=False, server_default="0"))
    columns.append(sa.UniqueConstraint("metric_name", "labels_hash", "node",
                                       "window_start", name="metricagg_uix"))

    op.create_table("metric_aggregate", *columns)
    op.create_index("ix_metric_aggregate_metric_name", "metric_aggregate", ["metric_name"])
    op.create_index("ix_metric_aggregate_window_start", "metric_aggregate", ["window_start"])


def downgrade():
    op.drop_index("ix_metric_aggregate_window_start", table_name="metric_aggregate")
    op.drop_index("ix_metric_aggregate_metric_name", table_name="metric_aggregate")
    op.drop_table("metric_aggregate")
    try:
        op.execute(sa.schema.DropSequence(sa.Sequence("metric_aggregate_seq")))
    except (OperationalError, ProgrammingError):
        # Same dialect-feature swallow as in upgrade(); real failures surface.
        pass
