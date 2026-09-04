"""v3.14: Mark u2f tokens as deprecated

Flip rows with tokentype='u2f' to tokentype='deprecated', stash the
original type and active state in tokeninfo, and mark the tokens
inactive. See dev/token-deprecation-strategy.md for the full design.

upgrade() creates three tokeninfo marker rows per affected token:
    original_tokentype = 'u2f'
    original_active    = '1' or '0'   (so downgrade is lossless)
    deprecated_in      = '3.14'

Revision ID: a1e0ba6ad9dc
Revises: 06b105a4f941
Create Date: 2026-04-15 10:00:00.000000

"""
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Boolean, Integer, Unicode, UnicodeText, case, func, select
from sqlalchemy.sql import column, insert, table
from sqlalchemy.sql.elements import BinaryExpression


# revision identifiers, used by Alembic.
revision = 'a1e0ba6ad9dc'
down_revision = 'b1a2c3d4e5f6'
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")


# Lightweight reflections of the columns we touch. Using ``table`` /
# ``column`` constructs lets SQLAlchemy emit dialect-appropriate
# identifier quoting ("Key" on postgres, `Key` on mariadb, etc.).
_token = table(
    "token",
    column("id", Integer),
    column("tokentype", Unicode(30)),
    column("active", Boolean),
)

_tokeninfo = table(
    "tokeninfo",
    column("id", Integer),
    column("token_id", Integer),
    column("Key", Unicode(255)),
    column("Value", UnicodeText),
    column("Type", Unicode(100)),
    column("Description", Unicode(2000)),
)


def _marker_value_is(marker_value: str) -> BinaryExpression:
    """
    Return a predicate matching tokeninfo rows whose ``Value`` is
    ``marker_value``.

    ``Value`` is a ``UnicodeText`` column, which is a CLOB on Oracle, and Oracle
    rejects ``=`` between a CLOB and a string with "ORA-00932: inconsistent
    datatypes". LIKE is the comparison operator it does accept for LOBs, and the
    marker values this migration writes are fixed literals without LIKE
    wildcards ('u2f', '1', '0'), so the same rows match on every backend.
    """
    return _tokeninfo.c.Value.like(marker_value)


def _stash_marker(bind, marker_key: str, marker_value_expr) -> None:
    """
    Insert one marker tokeninfo row per u2f token.

    ``marker_value_expr`` may be a plain literal (for ``'u2f'``,
    ``'3.14'``) or a SQLAlchemy expression (for the ``CASE WHEN active``
    used by ``original_active``).
    """
    stmt = insert(_tokeninfo).from_select(
        ["token_id", "Key", "Value", "Type", "Description"],
        select(
            _token.c.id.label("token_id"),
            sa.literal(marker_key).label("Key"),
            sa.type_coerce(marker_value_expr, UnicodeText()).label("Value"),
            sa.literal("").label("Type"),
            sa.literal("").label("Description"),
        ).where(_token.c.tokentype == "u2f"),
    )
    bind.execute(stmt)


def upgrade():
    bind = op.get_bind()

    count = bind.execute(
        select(func.count()).select_from(_token).where(_token.c.tokentype == "u2f")
    ).scalar() or 0

    if count == 0:
        log.info("No u2f tokens found. Nothing to migrate.")
        return

    log.warning(
        "\n" + "=" * 70 + "\n"
        f"Found {count} u2f token(s). U2F is no longer supported as of v3.14.\n"
        "These tokens have been marked as 'deprecated' and disabled, and can\n"
        "no longer be used to authenticate. They are still visible in the\n"
        "token list and can be removed with:\n"
        "    pi-tokenjanitor deprecated delete u2f\n"
        + "=" * 70
    )

    _stash_marker(bind, "original_tokentype", sa.literal("u2f"))
    _stash_marker(
        bind,
        "original_active",
        # "= true()" rather than "is_(True)": Oracle has no boolean type, and the
        # IS operator only accepts NULL/TRUE/FALSE keywords there, so is_(True)
        # renders as "active IS 1" and fails with ORA-00908. Equality renders as
        # "active = 1" on Oracle and "active = true" everywhere else.
        case((_token.c.active == sa.true(), sa.literal("1")), else_=sa.literal("0")),
    )
    _stash_marker(bind, "deprecated_in", sa.literal("3.14"))

    bind.execute(
        _token.update()
        .where(_token.c.tokentype == "u2f")
        .values(tokentype="deprecated", active=False)
    )


def downgrade():
    bind = op.get_bind()

    # Restore active=True for rows whose stashed original_active was '1',
    # and active=False for rows whose stashed original_active was '0'. Two
    # passes avoids a correlated subquery.
    for stashed_value, restored in (("1", True), ("0", False)):
        token_ids_with_original_active = (
            select(_tokeninfo.c.token_id)
            .where(_tokeninfo.c.Key == "original_active")
            .where(_marker_value_is(stashed_value))
        )
        token_ids_with_original_type_u2f = (
            select(_tokeninfo.c.token_id)
            .where(_tokeninfo.c.Key == "original_tokentype")
            .where(_marker_value_is("u2f"))
        )
        bind.execute(
            _token.update()
            .where(_token.c.id.in_(token_ids_with_original_active))
            .where(_token.c.id.in_(token_ids_with_original_type_u2f))
            .values(active=restored)
        )

    # Restore tokentype to u2f for rows whose original_tokentype was u2f
    u2f_origin_ids = (
        select(_tokeninfo.c.token_id)
        .where(_tokeninfo.c.Key == "original_tokentype")
        .where(_marker_value_is("u2f"))
    )
    bind.execute(
        _token.update()
        .where(_token.c.id.in_(u2f_origin_ids))
        .values(tokentype="u2f")
    )

    # Drop the three marker rows — but only those belonging to u2f-origin
    # tokens, not any other deprecation that may also be present.
    u2f_restored_ids = select(_token.c.id).where(_token.c.tokentype == "u2f")
    bind.execute(
        _tokeninfo.delete()
        .where(_tokeninfo.c.Key.in_(["original_tokentype", "original_active", "deprecated_in"]))
        .where(_tokeninfo.c.token_id.in_(u2f_restored_ids))
    )
