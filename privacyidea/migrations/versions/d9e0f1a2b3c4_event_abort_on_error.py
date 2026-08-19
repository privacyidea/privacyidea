"""v3.14: Add abort_on_error to the eventhandler table

A failing event handler no longer aborts the request. Bindings that abort anyway can be marked with
abort_on_error, which is set for existing Federation bindings: a federation handler replaces the response with
the one of the remote privacyIDEA, so continuing without it answers the client with the local response as if it
came from the remote server.

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-08-12 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'd9e0f1a2b3c4'
down_revision = 'c8d9e0f1a2b3'
branch_labels = None
depends_on = None


def upgrade():
    try:
        op.add_column('eventhandler', sa.Column('abort_on_error', sa.Boolean(), nullable=True))
    except (OperationalError, ProgrammingError) as exx:
        if any(x in str(exx.orig).lower() for x in ["already exists", "duplicate column name"]):
            print("Ok, column 'abort_on_error' already exists.")
        else:
            print(exx)
            raise
    except Exception as exx:
        print(f"Could not add column 'abort_on_error' to database: {exx}")
        raise

    try:
        # Existing bindings are best-effort, which is the new default. Federation is the exception: its result
        # is the response the client receives, so a failure has to be reported instead of being downgraded to
        # an audit entry.
        # The boolean parameters are typed explicitly: Oracle has no native boolean type, so the value has to go
        # through the bind processor of sa.Boolean() to become the 1 / 0 the NUMBER(1) column expects.
        connection = op.get_bind()
        enable_federation = sa.text(
            "UPDATE eventhandler SET abort_on_error = :enabled WHERE handlermodule = 'Federation'"
        ).bindparams(sa.bindparam("enabled", True, type_=sa.Boolean()))
        result = connection.execute(enable_federation)
        disable_remaining = sa.text(
            "UPDATE eventhandler SET abort_on_error = :disabled WHERE abort_on_error IS NULL"
        ).bindparams(sa.bindparam("disabled", False, type_=sa.Boolean()))
        connection.execute(disable_remaining)
        if result.rowcount:
            print(f"Set 'abort_on_error' for {result.rowcount} Federation event handler(s). Review them under "
                  f"Config -> Events if a failed federation request should not fail the request.")
    except Exception as exx:
        print(f"Could not set 'abort_on_error' for the existing event handlers: {exx}")
        raise


def downgrade():
    try:
        op.drop_column('eventhandler', 'abort_on_error')
    except (OperationalError, ProgrammingError) as exx:
        msg = str(exx.orig).lower()
        if "no such column" in msg or "does not exist" in msg or "check that it exists" in msg:
            print("Column 'abort_on_error' already removed.")
        else:
            print("Could not remove column 'abort_on_error' from table 'eventhandler'.")
            raise
