"""v3.14: Abort on error for the event handlers whose result the request consumes

A request mangler changes the parameters the endpoint works with and a response mangler the response the client
receives, so continuing without them answers the client as if they had run. A script handler that is configured to
raise an error decides whether the request may go on. The existing bindings of these handlers are marked with
abort_on_error, like the Federation bindings already are.

Revision ID: ad07c259b5c1
Revises: b7c1e4d2a9f3
Create Date: 2026-10-06 18:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = 'ad07c259b5c1'
down_revision = 'b7c1e4d2a9f3'
branch_labels = None
depends_on = None

# Lightweight reflections of the columns this migration touches. The table and column constructs let SQLAlchemy quote
# the identifiers for the dialect, e.g. "Key" and "Value" on PostgreSQL and Oracle.
eventhandler = sa.table("eventhandler", sa.column("id", sa.Integer()), sa.column("handlermodule", sa.Unicode(255)),
                        sa.column("abort_on_error", sa.Boolean()))
eventhandleroption = sa.table("eventhandleroption", sa.column("eventhandler_id", sa.Integer()),
                              sa.column("Key", sa.Unicode(255)), sa.column("Value", sa.Unicode(2000)))

MANGLER_MODULES = ["RequestMangler", "ResponseMangler"]
# The values the script handler reads as true, see privacyidea.lib.utils.is_true
TRUE_VALUES = ["1", "True", "true", "TRUE"]


def upgrade() -> None:
    connection = op.get_bind()
    try:
        # The boolean value goes through the bind processor of sa.Boolean(): Oracle has no native boolean type, so
        # the value has to become the 1 the NUMBER(1) column expects.
        result = connection.execute(eventhandler.update()
                                    .where(eventhandler.c.handlermodule.in_(MANGLER_MODULES))
                                    .values(abort_on_error=True))
        changed = result.rowcount or 0
        raising_scripts = (sa.select(eventhandleroption.c.eventhandler_id)
                           .where(eventhandleroption.c.Key == "raise_error")
                           .where(eventhandleroption.c.Value.in_(TRUE_VALUES)))
        result = connection.execute(eventhandler.update()
                                    .where(eventhandler.c.handlermodule == "Script")
                                    .where(eventhandler.c.id.in_(raising_scripts))
                                    .values(abort_on_error=True))
        changed += result.rowcount or 0
    except Exception as exx:
        print(f"Could not set 'abort_on_error' for the request mangler, response mangler and script handlers: {exx}")
        raise
    if changed:
        print(f"Set 'abort_on_error' for {changed} RequestMangler, ResponseMangler or Script event handler(s). Review "
              f"them under Config -> Events if a failure of the handler should not fail the request.")


def downgrade() -> None:
    # The handlers keep the value. An administrator may have set it on purpose since the upgrade, which can not be
    # told apart from the value this migration set.
    pass
