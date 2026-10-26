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
that a downgrade is trivially safe.

No deduplication: two handlers posting to the same URL produce two webhook
objects (safe, behaviour-preserving).

Safety net
----------
privacyIDEA runs migrations with ``isolation_level="AUTOCOMMIT"`` (see
``migrations/env.py``), so there is no enclosing transaction that could roll
back a half-finished data migration. Before touching any row, this migration
therefore writes a JSON snapshot of exactly the rows it is about to read and
modify (the ``eventhandleroption`` rows of every WebHook handler) to

    <snapshot dir>/privacyidea-e1f2a3b4c5d6-<timestamp>.json

The directory is chosen in this order:

1. ``$PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR``
2. privacyIDEA's backup directory (``/var/lib/privacyidea/backup``, the default
   of ``pi-manage backup create``) if it already exists and is writable, so
   snapshots land where administrators already look for recovery material
3. the system temp directory

If anything goes wrong the exact pre-migration state can be restored with
:func:`restore_snapshot` without having to downgrade or replay a full dump.

Which rows are ours
-------------------
Every ``webhook`` row this migration creates carries :data:`MIGRATION_MARKER` in its
``description``, and that marker is what :func:`restore_snapshot` and the resume check in
:func:`_run_data_migration` match on. The identifier naming (``from_<name>_<id>``) says what a
row is called, not who created it, so it cannot tell the row a crashed run committed from one
that was already there - and telling those apart is exactly what makes re-running after a
partial failure resume rather than collide on ``uq_webhook_identifier``.

:func:`downgrade` needs none of this: it drops the ``webhook`` table, which takes every row with
it, ours or not.

See https://github.com/privacyidea/privacyidea/issues/5751

Revision ID: e1f2a3b4c5d6
Revises: 56529818c956
Create Date: 2026-08-20 00:00:00.000000

"""
import datetime
import json
import logging
import os
import re
import tempfile

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError

log = logging.getLogger("alembic.runtime.migration")

#: Environment variable that overrides where the pre-migration snapshot is written.
SNAPSHOT_DIR_ENV = "PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR"

#: Set this to "1"/"true"/"yes" to skip writing the snapshot entirely.
SNAPSHOT_DISABLE_ENV = "PRIVACYIDEA_MIGRATION_NO_SNAPSHOT"

#: Default backup directory of ``pi-manage backup create`` (see
#: privacyidea/cli/pimanage/backup.py). Used as the snapshot location when it
#: already exists, so snapshots sit next to regular backups.
PI_BACKUP_DIR = "/var/lib/privacyidea/backup"

#: Columns of ``eventhandleroption`` captured in the snapshot.
_OPTION_COLUMNS = ("id", "eventhandler_id", "Key", "Value", "Type", "Description")

#: Written into the ``description`` of every ``webhook`` row this migration creates. It is what
#: makes such a row recognisably *ours* to :func:`restore_snapshot` and to the resume check in
#: :func:`_run_data_migration`, both of which act on a ``webhook`` table that stays standing.
#:
#: The alternative, matching the ``from_``/``webhook_from_handler_`` identifier prefix, cannot tell a
#: migration-created row from one an administrator happened to name that way - and, more to the
#: point, cannot tell the row a crashed run committed from one that was already there. The resume
#: depends on exactly that distinction: adopt our own leftover, leave anything else alone.
#:
#: Deliberately free of ``%`` and ``_``, so it can be matched with ``LIKE`` without escaping.
MIGRATION_MARKER = "pi-migration:e1f2a3b4c5d6"


def _webhook_description(handler_id):
    """The ``description`` of a webhook row created for the given handler."""
    return (f"{MIGRATION_MARKER} - created from the inline options of WebHook "
            f"event handler {handler_id} (#5751)")


def _option_description(handler_id):
    """
    The ``Description`` of the ``webhook`` option row linking a handler to its webhook.

    Provenance for whoever reads the row later, nothing more: no code matches on it. The column
    would otherwise be empty, and "why does this handler have an option I never added?" is a fair
    question to find an answer to in the row itself.
    """
    return (f"Added by the privacyIDEA 3.15 webhook migration: links WebHook event handler "
            f"{handler_id} to the webhook object created from its inline options (#5751)")


def _marked(column):
    """A filter selecting the ``webhook`` rows this migration created, by their marker."""
    return column.like(f"{MIGRATION_MARKER}%")


# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = '56529818c956'
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
    sa.column('description', sa.Unicode(2000)),
    sa.column('url', sa.Unicode(2000)),
    sa.column('http_method', sa.Unicode(10)),
    sa.column('content_type', sa.Unicode(100)),
    sa.column('auth_type', sa.Unicode(50)),
    sa.column('verify_tls', sa.Boolean),
    sa.column('timeout', sa.Integer),
)

#: Name of the sequence feeding ``eventhandleroption.id`` (see privacyidea/models/event.py).
_EVENTHANDLEROPTION_SEQUENCE = 'eventhandleropt_seq'


def _next_eventhandleroption_id(conn):
    """
    Return the id for a new ``eventhandleroption`` row, or None to let the column supply it.

    ``eventhandleroption.id`` is declared with a ``Sequence``, and a sequence is a thing the
    inserter draws from, not a default on the column. On a backend that has real sequences -
    MariaDB 10.3 and later, PostgreSQL - the column therefore has no default of its own and an
    INSERT that omits the id fails; the ORM gets away with it because it fetches the next value
    first. The Core INSERT in :func:`_run_data_migration` has to do the same. Everywhere else
    (MySQL, SQLite) the column is an ordinary auto-increment and omitting the id is correct.

    :param conn: the connection the migration runs on
    :return: the next sequence value, or None if the column fills itself
    """
    if conn.dialect.supports_sequences:
        return conn.scalar(sa.Sequence(_EVENTHANDLEROPTION_SEQUENCE))
    return None


def _sanitize_name(name):
    """Turn a handler name into a safe identifier fragment (ASCII, max 40 chars)."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)[:40]


# ---------------------------------------------------------------------------
# Pre-migration snapshot ("automatic backup")
# ---------------------------------------------------------------------------

def _snapshot_enabled():
    return os.environ.get(SNAPSHOT_DISABLE_ENV, "").strip().lower() not in (
        "1", "true", "yes", "on")


def _snapshot_directory():
    """
    Where to put the snapshot.

    Prefers an explicit override, then privacyIDEA's regular backup directory
    (so snapshots sit next to ``pi-manage backup create`` output and are found
    by administrators looking for recovery material), then the temp dir.
    """
    override = os.environ.get(SNAPSHOT_DIR_ENV)
    if override:
        return override
    if os.path.isdir(PI_BACKUP_DIR) and os.access(PI_BACKUP_DIR, os.W_OK):
        return PI_BACKUP_DIR
    return tempfile.gettempdir()


def _collect_snapshot(conn):
    """
    Return a JSON-serialisable snapshot of every row this migration may modify.

    That is the complete set of ``eventhandleroption`` rows belonging to
    handlers with ``handlermodule == 'WebHook'``. The ``webhook`` /
    ``webhookheader`` tables are not captured: they are created by this very
    migration, so their pre-migration state is "empty" by definition.
    """
    handler_ids = [
        row[0] for row in conn.execute(
            sa.select(_eventhandler.c.id)
            .where(_eventhandler.c.handlermodule == 'WebHook')
        ).fetchall()
    ]

    options = []
    if handler_ids:
        rows = conn.execute(
            sa.select(*(_eventhandleroption.c[name] for name in _OPTION_COLUMNS))
            .where(_eventhandleroption.c.eventhandler_id.in_(handler_ids))
        ).fetchall()
        for row in rows:
            options.append(dict(zip(_OPTION_COLUMNS, row)))

    return {
        "revision": revision,
        "created": datetime.datetime.now(datetime.UTC).isoformat(),
        "handler_ids": handler_ids,
        "eventhandleroption": options,
    }


def _write_snapshot(conn):
    """
    Write a pre-migration snapshot and return its path (or None).

    Never raises: a failure to write the safety net must not abort an
    otherwise healthy upgrade.
    """
    if not _snapshot_enabled():
        log.info(f"Snapshot disabled via {SNAPSHOT_DISABLE_ENV} — skipping.")
        return None

    try:
        snapshot = _collect_snapshot(conn)
    except (OperationalError, ProgrammingError) as ex:
        log.warning(f"Could not collect pre-migration snapshot: {ex}")
        return None

    if not snapshot["handler_ids"]:
        # Nothing will be modified, so there is nothing worth snapshotting.
        return None

    directory = _snapshot_directory()
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(directory, f"privacyidea-{revision}-{timestamp}.json")

    try:
        os.makedirs(directory, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh, indent=2, ensure_ascii=False, default=str)
    except OSError as ex:
        log.warning(
            f"Could not write pre-migration snapshot to {path}: {ex}. "
            f"The migration continues; it is additive and idempotent, so a "
            f"failed run can simply be repeated with 'pi-manage db upgrade'."
        )
        return None

    print(f"Pre-migration snapshot written to {path}")
    log.info(
        f"Snapshot of {len(snapshot['eventhandleroption'])} eventhandleroption "
        f"row(s) for {len(snapshot['handler_ids'])} WebHook handler(s): {path}"
    )
    return path


def restore_snapshot(conn, path):
    """
    Restore the exact pre-migration state captured by :func:`_write_snapshot`.

    Use this instead of ``downgrade()`` when a migration run failed partway
    through and the database is in a mixed state::

        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables \\
            import restore_snapshot
        restore_snapshot(db.engine.connect(), "/tmp/privacyidea-e1f2a3b4c5d6-...json")

    The webhook tables themselves are left in place — they are empty of
    migration-created rows afterwards and harmless. Re-running
    ``pi-manage db upgrade`` after a restore is safe.

    :return: the number of ``eventhandleroption`` rows restored
    """
    with open(path, encoding="utf-8") as fh:
        snapshot = json.load(fh)

    if snapshot.get("revision") != revision:
        raise ValueError(
            f"Snapshot {path} belongs to revision {snapshot.get('revision')!r}, "
            f"not {revision!r}."
        )

    handler_ids = snapshot.get("handler_ids") or []
    options = snapshot.get("eventhandleroption") or []

    # 1. Drop the webhook objects this migration created.
    #
    #    Found by their own marker, not via the handlers' "webhook" option rows: the state this
    #    function exists for is a run that failed partway through, and the worst such state is a
    #    webhook row committed without the option row that names it. Looking the rows up through
    #    those options would leave exactly that one behind, and the next upgrade would collide
    #    with it.
    if sa.inspect(conn).has_table("webhook"):
        conn.execute(_webhook.delete().where(_marked(_webhook.c.description)))

    # 2. Reset eventhandleroption for the affected handlers to the snapshot state.
    if handler_ids:
        conn.execute(
            _eventhandleroption.delete().where(
                _eventhandleroption.c.eventhandler_id.in_(handler_ids)
            )
        )
    for opt in options:
        conn.execute(_eventhandleroption.insert().values(**opt))

    # Deliberately no conn.commit() here: migrations run under AUTOCOMMIT, where
    # every statement is already durable. Committing an ORM-owned connection
    # (as in the test suite) would break the surrounding session, so leave
    # transaction control to the caller.
    print(f"Restored {len(options)} eventhandleroption row(s) from {path}")
    return len(options)


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

def _create_webhook_table():
    if sa.inspect(op.get_bind()).has_table("webhook"):
        log.info("Table 'webhook' already exists, skipping creation.")
        return

    op.create_table(
        'webhook',
        # Identity rather than a Sequence plus autoincrement: it renders as IDENTITY on
        # PostgreSQL/Oracle, AUTO_INCREMENT on MySQL/MariaDB and the rowid on SQLite - one id
        # source per column, used by the ORM and by the raw INSERT of the data migration below
        # alike, with no sequence to create, advance or drop per dialect. A Sequence is known to
        # the ORM only, so on MariaDB the raw INSERT would find no default for the column. BY
        # DEFAULT rather than ALWAYS so an explicit id can still be inserted. Mirrors
        # conditional_access_policies and authentication_log, and the model.
        sa.Column('id', sa.Integer(), sa.Identity(always=False), primary_key=True),
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

    op.create_table(
        'webhookheader',
        sa.Column('id', sa.Integer(), sa.Identity(always=False), primary_key=True),
        sa.Column('webhook_id', sa.Integer(), nullable=False, index=True),
        sa.Column('key', sa.Unicode(length=255), nullable=False),
        # No server_default: MySQL rejects a DEFAULT on a TEXT column (error 1101), and the
        # model gives the column a Python-side default instead - as it does for the other
        # text column, webhook.default_payload.
        sa.Column('value', sa.UnicodeText(), nullable=True),
        sa.Column('encrypted', sa.Boolean(), nullable=True, server_default='0'),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhook.id'], ondelete='CASCADE'),
    )


# ---------------------------------------------------------------------------
# Data migration (inline WebHook handlers → webhook objects)
# ---------------------------------------------------------------------------

def _free_identifier(conn, base, handler_id):
    """
    Return the identifier to create this handler's webhook under, and whether it already exists.

    A name that is already taken belongs either to a previous, interrupted run of this migration
    or to somebody else. The first is adopted: migrations run under AUTOCOMMIT (see
    migrations/env.py), so a webhook row is durable the moment it is written and survives a run
    that fails before writing the option row that links it. The resume check in
    :func:`_run_data_migration` keys on that option row, so on a re-run this handler is not
    skipped and the identifier would collide - leaving the upgrade permanently stuck on a UNIQUE
    violation, which is the state the printed "just re-run" advice promises to resolve.

    Somebody else's webhook is not adopted; that would point the handler at an endpoint nobody
    chose for it. The handler is not left on its inline configuration either, which is what this
    used to do: that shape is being removed, so a working handler left behind this way keeps
    working until the release that drops it and then silently sends nothing. It gets a numeric
    suffix instead, which costs an ugly name and nothing else.

    :param conn: the connection the migration runs on
    :param base: the identifier the naming rule produces for this handler
    :param handler_id: the handler being migrated, for the log messages
    :return: a ``(identifier, reused)`` tuple; *reused* is True when the row already exists and
        belongs to this migration, so the caller must not insert it again
    """
    candidate = base
    suffix = 1
    while True:
        existing = conn.execute(
            sa.select(_webhook.c.description).where(_webhook.c.identifier == candidate)
        ).fetchone()
        if existing is None:
            if candidate != base:
                log.warning(
                    f"Webhook '{base}' already exists and was not created by this migration, so "
                    f"WebHook handler {handler_id} is migrated to '{candidate}' instead."
                )
            return candidate, False
        if str(existing.description or "").startswith(MIGRATION_MARKER):
            log.info(
                f"Webhook '{candidate}' already exists from an earlier, interrupted run of this "
                f"migration - reusing it."
            )
            return candidate, True
        suffix += 1
        candidate = f"{base}_{suffix}"


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
        #
        #    No content type at all - the option absent, or present with an empty value - is a
        #    setting that was never made, and it gets the same default a webhook created today
        #    gets. Such a handler sends nothing as it stands (the inline WebHookHandler maps the
        #    value through DB_CONTENT_TYPE_MAP, which has no default, and refuses anything that is
        #    not JSON or urlencoded), so filling it in repairs the handler rather than changing
        #    what it does. `opts.get(..., default)` alone would miss the empty case.
        #
        #    A value that *is* set but is not a MIME type is different: someone typed it. Storing
        #    it raw would put it past set_webhook()/_validate(), which this code writes around, and
        #    reading it as JSON would be a guess about what was meant. The handler is left on its
        #    inline configuration instead, the way one without a URL is - it sends nothing today
        #    either, and an admin can correct the value and run the upgrade again.
        raw_ct = opts.get('content_type') or 'application/json'
        content_type = _CONTENT_TYPE_MAP.get(raw_ct, raw_ct)
        if '/' not in content_type:
            log.warning(
                f"WebHook handler {handler_id} has an unusable content_type "
                f"({opts.get('content_type')!r}) — skipping migration. It sends nothing today "
                f"either; correct the option and run the upgrade again."
            )
            continue

        # 6. Insert the webhook row - unless a previous, interrupted run already did.
        #
        #    Migrations run under AUTOCOMMIT (see migrations/env.py), so the insert below is durable
        #    the moment it succeeds and nothing rolls it back if step 7 then fails. The check in
        #    step 2 keys on the option row step 7 writes, so on a re-run it would not skip this
        #    handler and the identifier would collide with the row already there - leaving the
        #    upgrade permanently stuck on a UNIQUE violation, which is precisely the state the
        #    printed advice to "just re-run" promises to resolve. So the leftover is adopted instead.
        identifier, reused = _free_identifier(conn, identifier, handler_id)
        if not reused:
            #    timeout=10 matches the handler's current TIMEOUT constant to preserve
            #    existing behaviour (the new default for manually created webhooks is 3).
            conn.execute(
                _webhook.insert().values(
                    identifier=identifier,
                    description=_webhook_description(handler_id),
                    url=url,
                    http_method='POST',
                    content_type=content_type,
                    auth_type='none',
                    verify_tls=True,
                    timeout=10,
                )
            )

        # 7. Add a "webhook" option to the handler pointing at the identifier.
        option_values = {
            'eventhandler_id': handler_id,
            'Key': 'webhook',
            'Value': identifier,
            'Type': '',
            'Description': _option_description(handler_id),
        }
        option_id = _next_eventhandleroption_id(conn)
        if option_id is not None:
            option_values['id'] = option_id
        conn.execute(_eventhandleroption.insert().values(**option_values))

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
    conn = op.get_bind()

    # Capture the rows the data migration will touch *before* creating any
    # table, so the snapshot reflects a pristine pre-migration state.
    snapshot_path = _write_snapshot(conn)

    _create_webhook_table()
    _create_webhookheader_table()

    try:
        _run_data_migration(conn)
    except Exception:
        print("\n" + "=" * 72)
        print("The webhook data migration FAILED.")
        if snapshot_path:
            print(
                f"\nThe pre-migration state of the affected eventhandleroption rows\n"
                f"was saved to:\n    {snapshot_path}\n"
                f"\nRecovery options, in order of preference:\n"
                f"  1. Re-run 'pi-manage db upgrade'. This migration is idempotent\n"
                f"     and additive, so it resumes where it stopped.\n"
                f"  2. Restore just this migration's changes:\n"
                f"       from privacyidea.migrations.versions."
                f"e1f2a3b4c5d6_add_webhook_tables \\\n"
                f"           import restore_snapshot\n"
                f"       restore_snapshot(conn, {snapshot_path!r})\n"
                f"  3. Only as a last resort, restore a full backup made with\n"
                f"     'pi-manage backup create' -- note this also reverts every\n"
                f"     other migration applied in this run.\n"
            )
        else:
            print(
                "\nNo pre-migration snapshot was written. Re-run\n"
                "'pi-manage db upgrade' -- this migration is idempotent and\n"
                "additive, so it resumes where it stopped.\n"
            )
        print("=" * 72 + "\n")
        raise


def _remove_webhook_handler_options(conn):
    """
    Delete every ``webhook`` option row of every event handler, as part of a downgrade.

    **Every** one, not only the ones this migration wrote. :func:`downgrade` drops the ``webhook``
    table a few statements later, so after it there is nothing left for such a row to name -
    including one an administrator wrote by hand to link a handler to a webhook of their own.

    Keeping theirs would not preserve it, it would break it twice over: the option would point at
    a webhook the downgrade destroyed, and on the next upgrade the data migration's idempotency
    check ("this handler already has a webhook option") would skip that handler, so it would never
    be given a working webhook object either. Removed, the handler falls straight back to its
    inline ``URL``/``content_type`` options - which are never deleted - and a later upgrade
    migrates it cleanly.

    This is why the webhook rows themselves are not deleted here: ``DROP TABLE`` takes them, and
    picking marked rows out first would only be a statement whose effect nothing can observe.
    :data:`MIGRATION_MARKER` earns its keep in the two places that leave the table standing - the
    resume check in :func:`_run_data_migration` and :func:`restore_snapshot`.

    Extracted from :func:`downgrade` so it can be called directly from tests without a full
    Alembic context, like :func:`_run_data_migration`.

    :return: the number of ``eventhandleroption`` rows deleted
    """
    deleted = conn.execute(
        _eventhandleroption.delete().where(_eventhandleroption.c.Key == 'webhook')
    ).rowcount
    log.info(f"Removed {deleted} 'webhook' handler option row(s); the handlers fall back to "
             f"their inline URL/content_type configuration.")
    return deleted


def downgrade():
    conn = op.get_bind()

    # 1. Remove every "webhook" handler option: the table they name is dropped below, and the
    #    handlers' inline URL/content_type options are still in place for them to fall back to.
    _remove_webhook_handler_options(conn)

    # 2. Drop child table first (FK dependency), then parent. This is what removes the webhook
    #    rows - there is no separate delete for them.
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
        op.drop_table('webhook')
    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex.orig).lower()
        if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
            print("Table 'webhook' already removed.")
        else:
            print("Could not remove table 'webhook'.")
            raise
