"""
Tests for migration e1f2a3b4c5d6, which creates the webhook tables and
converts inline WebHook event handler options to first-class webhook objects.

See https://github.com/privacyidea/privacyidea/issues/5751 (steps 1.1-1.3)
"""
import datetime
import json
import os
import tempfile

import pytest

from privacyidea.models import db
from privacyidea.models.event import EventHandler, EventHandlerOption
from privacyidea.lib.webhook import get_webhook, set_webhook
from privacyidea.models.webhook import Webhook
from tests.migration_test_utils import MigrationTestBase

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]


def _create_webhook_handler(name, url, content_type="application/json",
                            data='{"msg": "hello"}', replace="True"):
    """
    Create an EventHandler + EventHandlerOption rows that look like a
    pre-migration inline WebHook configuration.
    """
    eh = EventHandler(
        name=name,
        event="validate_check",
        handlermodule="WebHook",
        action="post_webhook",
    )
    db.session.add(eh)
    db.session.flush()  # need eh.id for the option FK

    if url is not None:
        db.session.add(EventHandlerOption(
            eventhandler_id=eh.id, Key="URL", Value=url))
    if content_type is not None:
        db.session.add(EventHandlerOption(
            eventhandler_id=eh.id, Key="content_type", Value=content_type))
    if data is not None:
        db.session.add(EventHandlerOption(
            eventhandler_id=eh.id, Key="data", Value=data))
    if replace is not None:
        db.session.add(EventHandlerOption(
            eventhandler_id=eh.id, Key="replace", Value=replace))

    db.session.commit()
    return eh


class WebhookMigrationTestBase(MigrationTestBase):
    """
    Shared setup: a database whose schema alembic built, standing at this revision.

    Like every other per-migration test the schema comes from the seed plus the migration
    chain, never from ``db.create_all()``. The two differ in ways this migration runs into:
    the seed gives ``eventhandleroption.id`` an AUTO_INCREMENT and a sequence starting past
    the seeded rows, the models give it a sequence alone - and on a Galera node the models'
    sequences cannot even be restarted, which is what the shared ``MyTestCase`` reset does.

    The tables exist before each test so that the migration's own helpers can be called
    directly, one step at a time; ``test_migrations.py`` covers running it through alembic.
    """

    REVISION = "e1f2a3b4c5d6"
    PARENT_REVISION = "56529818c956"

    @pytest.fixture(autouse=True)
    def schema_at_this_revision(self, clean_database):
        self.tmpdir = tempfile.mkdtemp(prefix="pi-snapshot-test-")
        os.environ["PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR"] = self.tmpdir
        os.environ.pop("PRIVACYIDEA_MIGRATION_NO_SNAPSHOT", None)
        engine = self._engine()
        try:
            self._load_seed_and_upgrade_to_parent(engine)
        finally:
            engine.dispose()
        self._upgrade()
        # The upgrade ran through the app's engine; drop the session so the ORM below starts
        # on a connection that sees the new tables.
        db.session.remove()
        yield
        os.environ.pop("PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR", None)
        os.environ.pop("PRIVACYIDEA_MIGRATION_NO_SNAPSHOT", None)
        db.session.remove()

    @staticmethod
    def _write_snapshot():
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            _write_snapshot
        )
        return _write_snapshot(db.session.connection())

    @staticmethod
    def _run_migration():
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            _run_data_migration
        )
        result = _run_data_migration(db.session.connection())
        db.session.commit()
        return result

    @staticmethod
    def _webhook_option(handler_id):
        return EventHandlerOption.query.filter_by(
            eventhandler_id=handler_id, Key="webhook").first()


class TestMigrateInlineWebhooks(WebhookMigrationTestBase):
    """
    Test the _run_data_migration function from the e1f2a3b4c5d6 migration.
    """

    # ------------------------------------------------------------------
    # Core scenarios
    # ------------------------------------------------------------------

    def test_no_webhook_handlers(self):
        """Migration on a DB with 0 WebHook handlers is a no-op."""
        assert self._run_migration() == 0
        assert Webhook.query.count() == 0

    def test_one_handler(self):
        """A single WebHook handler produces one webhook object."""
        eh = _create_webhook_handler(
            name="Slack Notify",
            url="https://hooks.slack.com/services/T00/B00/xxx",
            content_type="application/json",
        )

        assert self._run_migration() == 1

        # Verify webhook row
        webhooks = Webhook.query.all()
        assert len(webhooks) == 1
        wh = webhooks[0]
        assert wh.url == "https://hooks.slack.com/services/T00/B00/xxx"
        assert wh.content_type == "application/json"
        assert wh.http_method == "POST"
        assert wh.timeout == 10  # preserved from old TIMEOUT constant
        assert wh.auth_type == "none"
        assert wh.verify_tls
        assert "Slack_Notify" in wh.identifier
        assert str(eh.id) in wh.identifier

        # Verify the "webhook" option was added to the handler
        webhook_opt = self._webhook_option(eh.id)
        assert webhook_opt is not None
        assert webhook_opt.Value == wh.identifier

        # Verify inline options are still present (not deleted)
        assert EventHandlerOption.query.filter_by(
            eventhandler_id=eh.id, Key="URL").first() is not None
        assert EventHandlerOption.query.filter_by(
            eventhandler_id=eh.id, Key="data").first() is not None

    def test_two_handlers_same_url_no_dedup(self):
        """Two handlers with the same URL produce two separate webhook objects."""
        shared_url = "https://siem.example.com/ingest"
        eh1 = _create_webhook_handler(name="Hook A", url=shared_url)
        eh2 = _create_webhook_handler(name="Hook B", url=shared_url)

        assert self._run_migration() == 2

        webhooks = Webhook.query.all()
        assert len(webhooks) == 2
        # distinct identifiers, both pointing at the same URL
        assert len({wh.identifier for wh in webhooks}) == 2
        assert {wh.url for wh in webhooks} == {shared_url}

        # Each handler got its own "webhook" option
        for eh in [eh1, eh2]:
            assert self._webhook_option(eh.id) is not None

    def test_handler_with_null_name(self):
        """A handler with NULL name gets a fallback identifier."""
        eh = _create_webhook_handler(
            name=None,
            url="https://null-name.example.com",
        )

        assert self._run_migration() == 1
        assert Webhook.query.one().identifier == f"webhook_from_handler_{eh.id}"

    def test_legacy_content_type_json(self):
        """Legacy content_type value 'json' is normalized to 'application/json'."""
        _create_webhook_handler(
            name="Legacy JSON",
            url="https://legacy.example.com",
            content_type="json",
        )

        self._run_migration()

        assert Webhook.query.one().content_type == "application/json"

    def test_legacy_content_type_urlencoded(self):
        """Legacy content_type value 'urlencoded' is normalized."""
        _create_webhook_handler(
            name="Legacy Form",
            url="https://legacy-form.example.com",
            content_type="urlencoded",
        )

        self._run_migration()

        assert Webhook.query.one().content_type == "application/x-www-form-urlencoded"

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_missing_url_skipped(self):
        """A handler with no URL option is silently skipped."""
        eh = _create_webhook_handler(
            name="No URL",
            url=None,  # no URL option will be inserted
        )

        assert self._run_migration() == 0
        assert Webhook.query.count() == 0
        # No "webhook" option should have been added
        assert self._webhook_option(eh.id) is None

    def test_idempotency(self):
        """Running the migration twice produces the same result."""
        _create_webhook_handler(
            name="Idempotent Hook",
            url="https://idempotent.example.com",
        )

        assert self._run_migration() == 1
        assert Webhook.query.count() == 1

        # Run again: nothing new, and still just the one webhook.
        assert self._run_migration() == 0
        assert Webhook.query.count() == 1

    def test_non_webhook_handlers_ignored(self):
        """Handlers with a different handlermodule are not touched."""
        # Create a non-WebHook handler
        eh_other = EventHandler(
            name="Email Notify",
            event="validate_check",
            handlermodule="UserNotification",
            action="sendmail",
        )
        db.session.add(eh_other)
        db.session.commit()

        # Also create one WebHook handler
        _create_webhook_handler(
            name="Real Webhook",
            url="https://real.example.com",
        )

        assert self._run_migration() == 1
        assert Webhook.query.count() == 1
        # The non-webhook handler did not get a "webhook" option
        assert self._webhook_option(eh_other.id) is None

    def test_special_chars_in_name_sanitized(self):
        """Handler names with special characters are sanitized in the identifier."""
        eh = _create_webhook_handler(
            name="My Hook / with <special> chars!",
            url="https://special.example.com",
        )

        self._run_migration()

        identifier = Webhook.query.one().identifier
        # Special chars replaced with underscores
        for char in "/<>!":
            assert char not in identifier
        assert str(eh.id) in identifier

    def test_an_unusable_content_type_is_skipped(self):
        """
        Such a handler is already inert: the inline WebHookHandler maps the value through
        DB_CONTENT_TYPE_MAP and refuses anything that is not JSON or urlencoded. Migrating it would
        either store an empty Content-Type or quietly start posting as JSON, so it is left on its
        inline configuration the way a handler without a URL is.
        """
        eh = _create_webhook_handler(name="Bad", url="https://bad.example.com",
                                     content_type="nonsense")

        assert self._run_migration() == 0

        assert Webhook.query.count() == 0
        assert self._webhook_option(eh.id) is None
        # Its inline configuration is untouched, so nothing was lost.
        assert EventHandlerOption.query.filter_by(
            eventhandler_id=eh.id, Key="URL").one().Value == "https://bad.example.com"

    def test_an_empty_content_type_gets_the_default_like_a_missing_one(self):
        # Absent and present-but-empty are the same thing - a setting nobody made - and the inline
        # handler refuses both, so filling in the default repairs the handler instead of changing
        # what it does. `opts.get(key, default)` only covers the absent half.
        _create_webhook_handler(name="Empty", url="https://empty.example.com", content_type="")

        assert self._run_migration() == 1

        assert Webhook.query.one().content_type == "application/json"

    def test_missing_content_type_defaults_to_json(self):
        """A handler without a content_type option defaults to application/json."""
        _create_webhook_handler(
            name="No CT",
            url="https://no-ct.example.com",
            content_type=None,  # no content_type option inserted
        )

        self._run_migration()

        assert Webhook.query.one().content_type == "application/json"


class TestWebhookMigrationSnapshot(WebhookMigrationTestBase):
    """
    Test the pre-migration snapshot ("automatic backup") and its restore path.

    privacyIDEA runs migrations under AUTOCOMMIT (see migrations/env.py), so a
    failed data migration cannot be rolled back by the database. The snapshot
    captures the exact pre-migration state of every eventhandleroption row the
    migration may touch.
    """

    # ------------------------------------------------------------------
    # Snapshot creation
    # ------------------------------------------------------------------

    def test_no_snapshot_when_nothing_to_migrate(self):
        """With no WebHook handlers there is nothing worth snapshotting."""
        assert self._write_snapshot() is None

    def test_snapshot_captures_handler_options(self):
        """The snapshot contains every option row of every WebHook handler."""
        eh = _create_webhook_handler(
            name="Slack", url="https://hooks.slack.com/x",
            content_type="application/json")

        path = self._write_snapshot()
        assert path is not None
        assert os.path.exists(path)

        with open(path, encoding="utf-8") as fh:
            snapshot = json.load(fh)

        assert snapshot["revision"] == "e1f2a3b4c5d6"
        assert snapshot["handler_ids"] == [eh.id]

        keys = {opt["Key"] for opt in snapshot["eventhandleroption"]}
        assert keys == {"URL", "content_type", "data", "replace"}
        # No "webhook" option yet - this is the pre-migration state.
        assert "webhook" not in keys

    def test_snapshot_file_is_owner_only(self):
        """The snapshot may contain endpoint URLs, so restrict its permissions."""
        _create_webhook_handler(name="Slack", url="https://hooks.slack.com/x")
        path = self._write_snapshot()
        assert os.stat(path).st_mode & 0o777 == 0o600

    def test_snapshot_refuses_to_write_through_a_symlink(self):
        """
        The snapshot directory falls back to the system temp directory whenever the backup
        directory is absent, which is the normal state of a pip or container install - and the file
        name is fully predictable. Another local user can therefore place a symlink under that name
        in advance, and `pi-manage db upgrade` usually runs as root. Following one would truncate
        whatever it points at.
        """
        _create_webhook_handler(name="Slack", url="https://hooks.slack.com/x")
        target = os.path.join(self.tmpdir, "precious")
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("do not clobber me")

        # Pre-place the symlink under the exact name the snapshot is about to use.
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import revision
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        link = os.path.join(self.tmpdir, f"privacyidea-{revision}-{timestamp}.json")
        os.symlink(target, link)

        # The write fails rather than following the link, and the failure is swallowed so the
        # upgrade itself still proceeds.
        assert self._write_snapshot() is None
        with open(target, encoding="utf-8") as fh:
            assert fh.read() == "do not clobber me"

    def test_snapshot_can_be_disabled(self):
        """PRIVACYIDEA_MIGRATION_NO_SNAPSHOT=1 skips snapshot creation."""
        _create_webhook_handler(name="Slack", url="https://hooks.slack.com/x")
        os.environ["PRIVACYIDEA_MIGRATION_NO_SNAPSHOT"] = "1"
        assert self._write_snapshot() is None

    def test_unwritable_directory_does_not_break_migration(self):
        """A snapshot failure must never abort an otherwise healthy upgrade."""
        _create_webhook_handler(name="Slack", url="https://hooks.slack.com/x")
        os.environ["PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR"] = "/proc/definitely/not/writable"

        assert self._write_snapshot() is None
        # The data migration itself still works.
        assert self._run_migration() == 1

    # ------------------------------------------------------------------
    # Restore
    # ------------------------------------------------------------------

    def test_restore_undoes_the_migration(self):
        """Restoring the snapshot returns the DB to its exact pre-migration state."""
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            restore_snapshot
        )
        eh = _create_webhook_handler(
            name="Slack", url="https://hooks.slack.com/x",
            content_type="application/json")

        before = {
            (o.Key, o.Value)
            for o in EventHandlerOption.query.filter_by(eventhandler_id=eh.id).all()
        }

        path = self._write_snapshot()
        assert self._run_migration() == 1
        assert Webhook.query.count() == 1

        restore_snapshot(db.session.connection(), path)
        db.session.commit()
        db.session.expire_all()

        after = {
            (o.Key, o.Value)
            for o in EventHandlerOption.query.filter_by(eventhandler_id=eh.id).all()
        }
        assert before == after
        # The migration-created webhook object is gone again.
        assert Webhook.query.count() == 0

    def test_migration_is_replayable_after_restore(self):
        """After a restore, re-running the migration produces the same result."""
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            restore_snapshot
        )
        _create_webhook_handler(name="Slack", url="https://hooks.slack.com/x")

        path = self._write_snapshot()
        self._run_migration()
        identifier_first = Webhook.query.one().identifier

        restore_snapshot(db.session.connection(), path)
        db.session.commit()
        db.session.expire_all()

        assert self._run_migration() == 1
        assert Webhook.query.one().identifier == identifier_first

    def test_restore_rejects_foreign_snapshot(self):
        """A snapshot from a different revision must not be applied."""
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            restore_snapshot
        )
        path = os.path.join(self.tmpdir, "foreign.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"revision": "deadbeef1234", "handler_ids": [],
                       "eventhandleroption": []}, fh)

        with pytest.raises(ValueError):
            restore_snapshot(db.session.connection(), path)


class TestMigrationOwnershipMarker(WebhookMigrationTestBase):
    """
    Which ``webhook`` rows belong to this migration is recorded on the rows themselves
    (``MIGRATION_MARKER`` in their description), not inferred from the
    ``from_``/``webhook_from_handler_`` naming. A name says what a row is called, not who
    created it, and the resume after a partial failure turns on exactly that distinction:
    adopt our own leftover, leave anything else alone.

    ``downgrade()`` needs none of it - it drops the table - and is covered here for the one
    thing it does have to get right: the ``eventhandleroption`` rows, which survive it.
    """

    @staticmethod
    def _drop_webhook_option(handler_id):
        """
        Leave the database in exactly the state a crash between the webhook insert and the
        handler-option insert produces: migrations run under AUTOCOMMIT, so the webhook row is
        durable the moment it is written and nothing rolls it back.
        """
        EventHandlerOption.query.filter_by(
            eventhandler_id=handler_id, Key="webhook").delete()
        db.session.commit()

    # ------------------------------------------------------------------
    # The marker itself
    # ------------------------------------------------------------------

    def test_created_webhook_rows_carry_the_marker(self):
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            MIGRATION_MARKER
        )
        eh = _create_webhook_handler(name="Siem", url="https://siem.example.com")
        assert self._run_migration() == 1

        webhook = Webhook.query.one()
        assert webhook.description.startswith(MIGRATION_MARKER), webhook.description
        # The link row carries provenance for whoever reads it later, but nothing matches on it.
        assert "webhook migration" in self._webhook_option(eh.id).Description

    # ------------------------------------------------------------------
    # Resume after a partial failure
    # ------------------------------------------------------------------

    def test_re_run_adopts_the_webhook_a_crashed_run_left_behind(self):
        # What upgrade() tells the admin to do when the data migration fails: "Re-run
        # 'pi-manage db upgrade'. This migration is idempotent and additive, so it resumes where
        # it stopped." Before the marker, this raised a UNIQUE violation on webhook.identifier
        # and every later upgrade attempt failed the same way.
        eh = _create_webhook_handler(name="Siem Hook", url="https://siem.example.com")
        assert self._run_migration() == 1
        identifier = Webhook.query.one().identifier
        self._drop_webhook_option(eh.id)

        assert self._run_migration() == 1

        # The leftover row was adopted rather than duplicated, and the handler is linked to it.
        assert Webhook.query.count() == 1
        assert Webhook.query.one().identifier == identifier
        assert self._webhook_option(eh.id).Value == identifier

    def test_re_run_after_a_resume_is_still_idempotent(self):
        eh = _create_webhook_handler(name="Siem Hook", url="https://siem.example.com")
        self._run_migration()
        self._drop_webhook_option(eh.id)
        self._run_migration()

        assert self._run_migration() == 0
        assert Webhook.query.count() == 1
        assert EventHandlerOption.query.filter_by(
            eventhandler_id=eh.id, Key="webhook").count() == 1

    def test_a_foreign_webhook_of_the_same_name_is_not_hijacked(self):
        # An unmarked row of that name belongs to someone else. Adopting it would point the
        # handler at an endpoint nobody chose for it. Leaving the handler on its inline
        # configuration is no answer either: that shape is being removed, so the handler would
        # keep working until the release that drops it and then silently send nothing. It gets
        # its own webhook under the next free name.
        eh = _create_webhook_handler(name="Siem Hook", url="https://siem.example.com")
        foreign = f"from_Siem_Hook_{eh.id}"
        set_webhook(foreign, url="https://somewhere.else.example/hook")
        db.session.commit()

        assert self._run_migration() == 1

        # The foreign webhook is untouched, and the handler points at a new one of its own.
        assert get_webhook(foreign)["url"] == "https://somewhere.else.example/hook"
        identifier = self._webhook_option(eh.id).Value
        assert identifier == f"{foreign}_2"
        assert get_webhook(identifier)["url"] == "https://siem.example.com"

    def test_several_foreign_webhooks_push_the_name_further_along(self):
        # The suffix search has to keep going, not give up on the first taken variant.
        eh = _create_webhook_handler(name="Siem Hook", url="https://siem.example.com")
        base = f"from_Siem_Hook_{eh.id}"
        set_webhook(base, url="https://one.example/hook")
        set_webhook(f"{base}_2", url="https://two.example/hook")
        db.session.commit()

        assert self._run_migration() == 1

        assert self._webhook_option(eh.id).Value == f"{base}_3"

    # ------------------------------------------------------------------
    # Downgrade
    # ------------------------------------------------------------------

    def test_downgrade_drops_the_handler_link_and_leaves_the_inline_config(self):
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            _remove_webhook_handler_options
        )
        eh = _create_webhook_handler(name="Siem Hook", url="https://siem.example.com")
        self._run_migration()

        _remove_webhook_handler_options(db.session.connection())
        db.session.commit()
        db.session.expire_all()

        assert self._webhook_option(eh.id) is None
        # The inline options are never deleted, so the handler simply works as it did before.
        assert EventHandlerOption.query.filter_by(
            eventhandler_id=eh.id, Key="URL").one().Value == "https://siem.example.com"

    def test_downgrade_drops_a_hand_made_link_too(self):
        # A link an administrator wrote by hand goes as well, and that is the kinder outcome: the
        # webhook it names is about to be dropped with the table, and a surviving option row would
        # both point at nothing and make the next upgrade skip this handler (the idempotency check
        # keys on exactly that row), so it would never be given a working webhook object either.
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            _remove_webhook_handler_options
        )
        eh = _create_webhook_handler(name="Manual", url="https://manual.example.com")
        set_webhook("from_manual", url="https://manual.example.com/hook")
        db.session.add(EventHandlerOption(
            eventhandler_id=eh.id, Key="webhook", Value="from_manual"))
        db.session.commit()

        _remove_webhook_handler_options(db.session.connection())
        db.session.commit()
        db.session.expire_all()
        assert self._webhook_option(eh.id) is None

        # DROP TABLE takes every webhook row; emptying the table stands in for it, since the test
        # database keeps its schema across the cycle.
        for webhook in Webhook.query.all():
            webhook.delete()
        db.session.commit()

        # Upgrading again migrates the handler cleanly instead of skipping it.
        assert self._run_migration() == 1
        db.session.expire_all()
        assert self._webhook_option(eh.id).Value == Webhook.query.one().identifier

    # ------------------------------------------------------------------
    # Restore after a partial failure
    # ------------------------------------------------------------------

    def test_restore_clears_the_orphan_a_crashed_run_left_behind(self):
        # restore_snapshot() is the recovery route for a run that failed partway through, so the
        # one state it must handle is a webhook row committed without the option row naming it.
        # Finding the rows through those options would leave exactly that one behind, and the
        # next upgrade would collide with it.
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            restore_snapshot
        )
        eh = _create_webhook_handler(name="Siem Hook", url="https://siem.example.com")
        path = self._write_snapshot()
        self._run_migration()
        self._drop_webhook_option(eh.id)

        restore_snapshot(db.session.connection(), path)
        db.session.commit()
        db.session.expire_all()

        assert Webhook.query.count() == 0
        # And the upgrade can now start over cleanly.
        assert self._run_migration() == 1
        assert Webhook.query.count() == 1


class TestSnapshotDirectory:
    """
    Where the snapshot is written. No database is involved, so these need no schema.
    """

    def test_env_var_wins_over_everything(self, monkeypatch, tmp_path):
        """An explicit PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR always takes priority."""
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            _snapshot_directory
        )
        monkeypatch.setenv("PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR", str(tmp_path))
        assert _snapshot_directory() == str(tmp_path)

    def test_falls_back_to_pi_backup_dir_when_available(self, monkeypatch, tmp_path):
        """Without an override, snapshots go next to 'pi-manage backup create' output."""
        import privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables as mig

        monkeypatch.delenv("PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR", raising=False)
        # Point the "pi-manage backup" dir at a real, writable directory.
        monkeypatch.setattr(mig, "PI_BACKUP_DIR", str(tmp_path))
        assert mig._snapshot_directory() == str(tmp_path)

    def test_falls_back_to_tempdir_when_backup_dir_missing(self, monkeypatch):
        """On a system without /var/lib/privacyidea/backup, use the temp dir."""
        import privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables as mig

        monkeypatch.delenv("PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR", raising=False)
        monkeypatch.setattr(mig, "PI_BACKUP_DIR", "/nonexistent/privacyidea/backup")
        assert mig._snapshot_directory() == tempfile.gettempdir()


class TestEventHandlerOptionId:
    """
    The id the migration supplies for the ``eventhandleroption`` rows it writes.

    ``eventhandleroption.id`` is declared with a ``Sequence``, so on MariaDB 10.3 and later and
    on PostgreSQL the sequence - not the column - is what hands out ids, and a Core INSERT has
    to draw from it. Neither the sequence branch nor a wrong sequence name shows up on SQLite
    or MySQL, where the column is an ordinary auto-increment, hence these two checks.
    """

    def test_the_sequence_name_is_the_one_the_model_declares(self):
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            _EVENTHANDLEROPTION_SEQUENCE
        )
        assert EventHandlerOption.__table__.c.id.default.name == _EVENTHANDLEROPTION_SEQUENCE

    def test_the_id_comes_from_the_sequence_only_where_there_is_one(self):
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            _next_eventhandleroption_id, _EVENTHANDLEROPTION_SEQUENCE
        )

        class _Connection:
            def __init__(self, supports_sequences):
                self.dialect = type("_Dialect", (),
                                    {"supports_sequences": supports_sequences})()
                self.asked_for = []

            def scalar(self, statement):
                self.asked_for.append(statement)
                return 42

        with_sequences = _Connection(True)
        assert _next_eventhandleroption_id(with_sequences) == 42
        assert [s.name for s in with_sequences.asked_for] == [_EVENTHANDLEROPTION_SEQUENCE]

        without_sequences = _Connection(False)
        assert _next_eventhandleroption_id(without_sequences) is None
        assert without_sequences.asked_for == []
