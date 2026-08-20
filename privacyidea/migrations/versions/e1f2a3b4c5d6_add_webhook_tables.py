"""v3.15: Add webhook tables and migrate inline WebHook handlers

First-class webhook configuration objects, following the SMTPServer / RADIUSServer /
SMSGateway pattern.  A webhook object owns the endpoint (URL, method, auth, headers,
TLS, proxy, timeout); the call site (event handler or Conditional Access stage action)
owns the payload.

After creating the tables, this migration converts existing inline WebHook event
handler options to first-class webhook objects:
  1. Reads the inline URL and content_type from eventhandleroption
  2. Creates a webhook row with the extracted URL and content_type
  3. Adds a 'webhook' option to the handler pointing at the new identifier

The inline URL/content_type option rows are intentionally left in place so
that the tolerant legacy reader (Phase 5.1) can still fall back to them, and
downgrade is trivially safe.

No deduplication: two handlers posting to the same URL produce two webhook
objects (safe, behaviour-preserving).

See https://github.com/privacyidea/privacyidea/issues/5751

Revision ID: e1f2a3b4c5d6
Revises: d9e0f1a2b3c4
Create Date: 2026-08-20 00:00:00.000000

"""
import logging
import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError

log = logging.getLogger("alembic.runtime.migration")

# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'd9e0f1a2b3c4'
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# Data-migration helpers
# ---------------------------------------------------------------------------

# Maps legacy shorthand values to proper MIME types (mirrors DB_CONTENT_TYPE_MAP
# in webhookeventhandler.py).
_CONTENT_TYPE_MAP = {
    "json": "application/json",
    "urlencoded": "application/x-www-form-urlencoded",
    "application/json": "application/json",
    "application/x-www-form-urlencoded": "application/x-www-form-urlencoded",
}

# Lightweight table references for Core-style DML inside the migration.
_eventhandler = sa.table(
    'eventhandler',
    sa.column('id', sa.Integer),
    sa.column('name', sa.Unicode(64)),
    sa.column('handlermodule', sa.Unicode(255)),
)

_eventhandleroption = sa.table(
    'eventhandleroption',
    sa.column('id', sa.Integer),
    sa.column('eventhandler_id', sa.Integer),
    sa.column('Key', sa.Unicode(255)),
    sa.column('Value', sa.Unicode(2000)),
    sa.column('Type', sa.Unicode(2000)),
    sa.column('Description', sa.Unicode(2000)),
)

_webhook = sa.table(
    'webhook',
    sa.column('id', sa.Integer),
    sa.column('identifier', sa.Unicode(255)),
    sa.column('url', sa.Unicode(2000)),
    sa.column('http_method', sa.Unicode(10)),
    sa.column('content_type', sa.Unicode(100)),
    sa.column('auth_type', sa.Unicode(50)),
    sa.column('verify_tls', sa.Boolean),
    sa.column('timeout', sa.Integer),
)


def _sanitize_name(name):
    """Turn a handler name into a safe identifier fragment (ASCII, max 40 chars)."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)[:40]


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

def _create_webhook_table():
    if sa.inspect(op.get_bind()).has_table("webhook"):
        log.info("Table 'webhook' already exists, skipping creation.")
        return

    try:
        op.execute(sa.schema.CreateSequence(sa.Sequence("webhook_seq")))
    except (OperationalError, ProgrammingError):
        # Some dialects (sqlite, mysql) don't have sequences — SQLAlchemy
        # falls back to autoincrement, which is fine.
        pass

    op.create_table(
        'webhook',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('identifier', sa.Unicode(length=255), nullable=False),
        sa.Column('description', sa.Unicode(length=2000), nullable=True, server_default=''),
        sa.Column('url', sa.Unicode(length=2000), nullable=False),
        sa.Column('http_method', sa.Unicode(length=10), nullable=True, server_default='POST'),
        sa.Column('content_type', sa.Unicode(length=100), nullable=True,
                  server_default='application/json'),
        sa.Column('default_payload', sa.UnicodeText(), nullable=True),
        # Authentication
        sa.Column('auth_type', sa.Unicode(length=50), nullable=True, server_default='none'),
        sa.Column('username', sa.Unicode(length=255), nullable=True, server_default=''),
        sa.Column('password', sa.Unicode(length=1024), nullable=True, server_default=''),
        # TLS
        sa.Column('verify_tls', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('tls_ca_bundle', sa.Unicode(length=1024), nullable=True, server_default=''),
        # mTLS
        sa.Column('client_certificate', sa.Unicode(length=1024), nullable=True,
                  server_default=''),
        sa.Column('client_key', sa.Unicode(length=1024), nullable=True, server_default=''),
        sa.Column('client_key_password', sa.Unicode(length=1024), nullable=True,
                  server_default=''),
        # Proxy
        sa.Column('http_proxy', sa.Unicode(length=1024), nullable=True, server_default=''),
        sa.Column('https_proxy', sa.Unicode(length=1024), nullable=True, server_default=''),
        # Timeout
        sa.Column('timeout', sa.Integer(), nullable=True, server_default='3'),
        # Constraints
        sa.UniqueConstraint('identifier', name='uq_webhook_identifier'),
    )


def _create_webhookheader_table():
    if sa.inspect(op.get_bind()).has_table("webhookheader"):
        log.info("Table 'webhookheader' already exists, skipping creation.")
        return

    try:
        op.execute(sa.schema.CreateSequence(sa.Sequence("webhookheader_seq")))
    except (OperationalError, ProgrammingError):
        pass

    op.create_table(
        'webhookheader',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('webhook_id', sa.Integer(), nullable=False, index=True),
        sa.Column('key', sa.Unicode(length=255), nullable=False),
        sa.Column('value', sa.UnicodeText(), nullable=True, server_default=''),
        sa.Column('encrypted', sa.Boolean(), nullable=True, server_default='0'),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhook.id'], ondelete='CASCADE'),
    )


# ---------------------------------------------------------------------------
# Data migration (inline WebHook handlers → webhook objects)
# ---------------------------------------------------------------------------

def _run_data_migration(conn):
    """
    Convert inline WebHook handler options to first-class webhook objects.

    Extracted so it can be called directly from tests without a full Alembic
    context.
    """
    # 1. Find all WebHook event handlers.
    handlers = conn.execute(
        sa.select(_eventhandler.c.id, _eventhandler.c.name)
        .where(_eventhandler.c.handlermodule == 'WebHook')
    ).fetchall()

    if not handlers:
        log.info("No WebHook event handlers found — nothing to migrate.")
        return 0

    migrated = 0
    for handler_id, handler_name in handlers:
        # 2. Idempotency: skip if this handler already has a "webhook" option.
        existing_webhook_opt = conn.execute(
            sa.select(_eventhandleroption.c.Value)
            .where(
                _eventhandleroption.c.eventhandler_id == handler_id,
                _eventhandleroption.c.Key == 'webhook',
            )
        ).fetchone()
        if existing_webhook_opt:
            continue

        # 3. Read inline options (URL, content_type).
        opts = {}
        rows = conn.execute(
            sa.select(_eventhandleroption.c.Key, _eventhandleroption.c.Value)
            .where(
                _eventhandleroption.c.eventhandler_id == handler_id,
                _eventhandleroption.c.Key.in_(['URL', 'content_type']),
            )
        ).fetchall()
        for key, value in rows:
            opts[key] = value

        url = opts.get('URL')
        if not url:
            log.warning(
                f"WebHook handler {handler_id} has no URL option — skipping migration."
            )
            continue

        # 4. Build a unique identifier for the new webhook object.
        if handler_name:
            safe_name = _sanitize_name(handler_name)
            identifier = f"from_{safe_name}_{handler_id}"
        else:
            identifier = f"webhook_from_handler_{handler_id}"

        # 5. Normalize content_type (handle legacy "json"/"urlencoded" shorthand).
        raw_ct = opts.get('content_type', 'application/json')
        content_type = _CONTENT_TYPE_MAP.get(raw_ct, raw_ct)

        # 6. Insert the webhook row.
        #    timeout=10 matches the handler's current TIMEOUT constant to preserve
        #    existing behaviour (the new default for manually created webhooks is 3).
        conn.execute(
            _webhook.insert().values(
                identifier=identifier,
                url=url,
                http_method='POST',
                content_type=content_type,
                auth_type='none',
                verify_tls=True,
                timeout=10,
            )
        )

        # 7. Add a "webhook" option to the handler pointing at the new identifier.
        conn.execute(
            _eventhandleroption.insert().values(
                eventhandler_id=handler_id,
                Key='webhook',
                Value=identifier,
                Type='',
                Description='',
            )
        )

        migrated += 1
        log.info(
            f"Migrated WebHook handler {handler_id} "
            f"({handler_name or '<unnamed>'}) → webhook '{identifier}'"
        )

    if migrated:
        print(f"Migrated {migrated} inline WebHook handler(s) to first-class webhook objects.")
    else:
        log.info("All WebHook handlers were already migrated — nothing to do.")

    return migrated


# ---------------------------------------------------------------------------
# Alembic entry points
# ---------------------------------------------------------------------------

def upgrade():
    _create_webhook_table()
    _create_webhookheader_table()
    _run_data_migration(op.get_bind())


def downgrade():
    conn = op.get_bind()

    # 1. Remove the "webhook" option rows that point to migration-created identifiers.
    conn.execute(
        _eventhandleroption.delete().where(
            _eventhandleroption.c.Key == 'webhook',
            sa.or_(
                _eventhandleroption.c.Value.like('from_%'),
                _eventhandleroption.c.Value.like('webhook_from_handler_%'),
            ),
        )
    )

    # 2. Remove the webhook objects created by this migration.
    #    (The original URL/content_type options are still in eventhandleroption,
    #    so the handler falls back to inline mode — no data loss.)
    conn.execute(
        _webhook.delete().where(
            sa.or_(
                _webhook.c.identifier.like('from_%'),
                _webhook.c.identifier.like('webhook_from_handler_%'),
            )
        )
    )

    # 3. Drop child table first (FK dependency), then parent.
    try:
        op.drop_table('webhookheader')
    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print("Table 'webhookheader' already removed.")
        else:
            print("Could not remove table 'webhookheader'.")
            raise
    try:
        op.execute(sa.schema.DropSequence(sa.Sequence("webhookheader_seq")))
    except (OperationalError, ProgrammingError):
        pass

    try:
        op.drop_table('webhook')
    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print("Table 'webhook' already removed.")
        else:
            print("Could not remove table 'webhook'.")
            raise
    try:
        op.execute(sa.schema.DropSequence(sa.Sequence("webhook_seq")))
    except (OperationalError, ProgrammingError):
        pass
