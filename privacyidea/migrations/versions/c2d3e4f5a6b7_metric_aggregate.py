"""Add metric_aggregate table

Used by the privacyidea.lib.metrics module to store rolling pre-aggregated
counter and histogram values, partitioned by 5-minute window and node.

Revision ID: c2d3e4f5a6b7
Revises: b1a2c3d4e5f6
Create Date: 2026-04-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError


revision = 'c2d3e4f5a6b7'
down_revision = 'b1a2c3d4e5f6'
branch_labels = None
depends_on = None


_BUCKET_COLUMNS = [
    "bucket_le_50ms", "bucket_le_100ms", "bucket_le_150ms", "bucket_le_200ms",
    "bucket_le_250ms", "bucket_le_500ms", "bucket_le_1s", "bucket_le_2s",
    "bucket_le_5s",
]


def upgrade():
    try:
        op.execute(sa.schema.CreateSequence(sa.Sequence("metric_aggregate_seq")))
    except (OperationalError, ProgrammingError, Exception):
        # Some dialects (sqlite, mysql) don't have sequences - SQLAlchemy
        # falls back to autoincrement, which is fine.
        pass

    columns = [
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("metric_name", sa.Unicode(length=128), nullable=False),
        sa.Column("labels_key", sa.Unicode(length=255), nullable=False, server_default=""),
        sa.Column("node", sa.Unicode(length=255), nullable=False, server_default=""),
        sa.Column("window_start", sa.DateTime(timezone=False), nullable=False),
        sa.Column("count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("sum_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("max_value", sa.Float(), nullable=False, server_default="0"),
    ]
    for bucket in _BUCKET_COLUMNS:
        columns.append(sa.Column(bucket, sa.BigInteger(), nullable=False, server_default="0"))
    columns.append(sa.UniqueConstraint("metric_name", "labels_key", "node",
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
    except (OperationalError, ProgrammingError, Exception):
        pass
