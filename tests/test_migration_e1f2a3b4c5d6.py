"""
Tests for migration e1f2a3b4c5d6, which creates the webhook tables and
converts inline WebHook event handler options to first-class webhook objects.

See https://github.com/privacyidea/privacyidea/issues/5751 (steps 1.1-1.3)
"""
import json
import os
import tempfile

from privacyidea.models import db
from privacyidea.models.event import EventHandler, EventHandlerOption
from privacyidea.models.webhook import Webhook
from .base import MyTestCase


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


class MigrateInlineWebhooksTestCase(MyTestCase):
    """
    Test the _run_data_migration function from the e1f2a3b4c5d6 migration.
    """

    def _cleanup(self):
        """Remove all test data so each test starts clean."""
        for wh in Webhook.query.all():
            wh.delete()
        for eh in EventHandler.query.filter_by(handlermodule="WebHook").all():
            db.session.delete(eh)
        db.session.commit()

    def setUp(self):
        super().setUp()
        self._cleanup()
        self.tmpdir = tempfile.mkdtemp(prefix="pi-snapshot-test-")
        os.environ["PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR"] = self.tmpdir
        os.environ.pop("PRIVACYIDEA_MIGRATION_NO_SNAPSHOT", None)

    def tearDown(self):
        os.environ.pop("PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR", None)
        os.environ.pop("PRIVACYIDEA_MIGRATION_NO_SNAPSHOT", None)
        self._cleanup()
        super().tearDown()

    def _write_snapshot(self):
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            _write_snapshot
        )
        return _write_snapshot(db.session.connection())

    def _run_migration(self):
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            _run_data_migration
        )
        result = _run_data_migration(db.session.connection())
        db.session.commit()
        return result

    # ------------------------------------------------------------------
    # Core scenarios
    # ------------------------------------------------------------------

    def test_no_webhook_handlers(self):
        """Migration on a DB with 0 WebHook handlers is a no-op."""
        migrated = self._run_migration()
        self.assertEqual(migrated, 0)
        self.assertEqual(Webhook.query.count(), 0)

    def test_one_handler(self):
        """A single WebHook handler produces one webhook object."""
        eh = _create_webhook_handler(
            name="Slack Notify",
            url="https://hooks.slack.com/services/T00/B00/xxx",
            content_type="application/json",
        )

        migrated = self._run_migration()
        self.assertEqual(migrated, 1)

        # Verify webhook row
        webhooks = Webhook.query.all()
        self.assertEqual(len(webhooks), 1)
        wh = webhooks[0]
        self.assertEqual(wh.url, "https://hooks.slack.com/services/T00/B00/xxx")
        self.assertEqual(wh.content_type, "application/json")
        self.assertEqual(wh.http_method, "POST")
        self.assertEqual(wh.timeout, 10)  # preserved from old TIMEOUT constant
        self.assertEqual(wh.auth_type, "none")
        self.assertTrue(wh.verify_tls)
        self.assertIn("Slack_Notify", wh.identifier)
        self.assertIn(str(eh.id), wh.identifier)

        # Verify the "webhook" option was added to the handler
        webhook_opt = EventHandlerOption.query.filter_by(
            eventhandler_id=eh.id, Key="webhook"
        ).first()
        self.assertIsNotNone(webhook_opt)
        self.assertEqual(webhook_opt.Value, wh.identifier)

        # Verify inline options are still present (not deleted)
        url_opt = EventHandlerOption.query.filter_by(
            eventhandler_id=eh.id, Key="URL"
        ).first()
        self.assertIsNotNone(url_opt)
        data_opt = EventHandlerOption.query.filter_by(
            eventhandler_id=eh.id, Key="data"
        ).first()
        self.assertIsNotNone(data_opt)

    def test_two_handlers_same_url_no_dedup(self):
        """Two handlers with the same URL produce two separate webhook objects."""
        shared_url = "https://siem.example.com/ingest"
        eh1 = _create_webhook_handler(name="Hook A", url=shared_url)
        eh2 = _create_webhook_handler(name="Hook B", url=shared_url)

        migrated = self._run_migration()
        self.assertEqual(migrated, 2)

        webhooks = Webhook.query.all()
        self.assertEqual(len(webhooks), 2)

        identifiers = {wh.identifier for wh in webhooks}
        self.assertEqual(len(identifiers), 2)  # distinct identifiers

        # Both point to the same URL
        urls = {wh.url for wh in webhooks}
        self.assertEqual(urls, {shared_url})

        # Each handler got its own "webhook" option
        for eh in [eh1, eh2]:
            opt = EventHandlerOption.query.filter_by(
                eventhandler_id=eh.id, Key="webhook"
            ).first()
            self.assertIsNotNone(opt)

    def test_handler_with_null_name(self):
        """A handler with NULL name gets a fallback identifier."""
        eh = _create_webhook_handler(
            name=None,
            url="https://null-name.example.com",
        )

        migrated = self._run_migration()
        self.assertEqual(migrated, 1)

        wh = Webhook.query.first()
        self.assertEqual(wh.identifier, f"webhook_from_handler_{eh.id}")

    def test_legacy_content_type_json(self):
        """Legacy content_type value 'json' is normalized to 'application/json'."""
        _create_webhook_handler(
            name="Legacy JSON",
            url="https://legacy.example.com",
            content_type="json",
        )

        self._run_migration()

        wh = Webhook.query.first()
        self.assertEqual(wh.content_type, "application/json")

    def test_legacy_content_type_urlencoded(self):
        """Legacy content_type value 'urlencoded' is normalized."""
        _create_webhook_handler(
            name="Legacy Form",
            url="https://legacy-form.example.com",
            content_type="urlencoded",
        )

        self._run_migration()

        wh = Webhook.query.first()
        self.assertEqual(wh.content_type, "application/x-www-form-urlencoded")

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_missing_url_skipped(self):
        """A handler with no URL option is silently skipped."""
        eh = _create_webhook_handler(
            name="No URL",
            url=None,  # no URL option will be inserted
        )

        migrated = self._run_migration()
        self.assertEqual(migrated, 0)
        self.assertEqual(Webhook.query.count(), 0)

        # No "webhook" option should have been added
        opt = EventHandlerOption.query.filter_by(
            eventhandler_id=eh.id, Key="webhook"
        ).first()
        self.assertIsNone(opt)

    def test_idempotency(self):
        """Running the migration twice produces the same result."""
        _create_webhook_handler(
            name="Idempotent Hook",
            url="https://idempotent.example.com",
        )

        migrated_1 = self._run_migration()
        self.assertEqual(migrated_1, 1)
        count_after_first = Webhook.query.count()
        self.assertEqual(count_after_first, 1)

        # Run again
        migrated_2 = self._run_migration()
        self.assertEqual(migrated_2, 0)  # no new migrations
        count_after_second = Webhook.query.count()
        self.assertEqual(count_after_second, 1)  # still just 1

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

        migrated = self._run_migration()
        self.assertEqual(migrated, 1)
        self.assertEqual(Webhook.query.count(), 1)

        # The non-webhook handler should not have a "webhook" option
        opt = EventHandlerOption.query.filter_by(
            eventhandler_id=eh_other.id, Key="webhook"
        ).first()
        self.assertIsNone(opt)

        # Clean up the non-webhook handler
        db.session.delete(eh_other)
        db.session.commit()

    def test_special_chars_in_name_sanitized(self):
        """Handler names with special characters are sanitized in the identifier."""
        eh = _create_webhook_handler(
            name="My Hook / with <special> chars!",
            url="https://special.example.com",
        )

        self._run_migration()

        wh = Webhook.query.first()
        # Special chars replaced with underscores
        self.assertNotIn("/", wh.identifier)
        self.assertNotIn("<", wh.identifier)
        self.assertNotIn(">", wh.identifier)
        self.assertNotIn("!", wh.identifier)
        self.assertIn(str(eh.id), wh.identifier)

    def test_missing_content_type_defaults_to_json(self):
        """A handler without a content_type option defaults to application/json."""
        _create_webhook_handler(
            name="No CT",
            url="https://no-ct.example.com",
            content_type=None,  # no content_type option inserted
        )

        self._run_migration()

        wh = Webhook.query.first()
        self.assertEqual(wh.content_type, "application/json")


class WebhookMigrationSnapshotTestCase(MyTestCase):
    """
    Test the pre-migration snapshot ("automatic backup") and its restore path.

    privacyIDEA runs migrations under AUTOCOMMIT (see migrations/env.py), so a
    failed data migration cannot be rolled back by the database. The snapshot
    captures the exact pre-migration state of every eventhandleroption row the
    migration may touch.
    """

    def _cleanup(self):
        for wh in Webhook.query.all():
            wh.delete()
        for eh in EventHandler.query.filter_by(handlermodule="WebHook").all():
            db.session.delete(eh)
        db.session.commit()

    def setUp(self):
        super().setUp()
        self._cleanup()
        self.tmpdir = tempfile.mkdtemp(prefix="pi-snapshot-test-")
        os.environ["PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR"] = self.tmpdir
        os.environ.pop("PRIVACYIDEA_MIGRATION_NO_SNAPSHOT", None)

    def tearDown(self):
        os.environ.pop("PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR", None)
        os.environ.pop("PRIVACYIDEA_MIGRATION_NO_SNAPSHOT", None)
        self._cleanup()
        super().tearDown()

    def _write_snapshot(self):
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            _write_snapshot
        )
        return _write_snapshot(db.session.connection())

    def _run_migration(self):
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            _run_data_migration
        )
        result = _run_data_migration(db.session.connection())
        db.session.commit()
        return result

    # ------------------------------------------------------------------
    # Snapshot creation
    # ------------------------------------------------------------------

    def test_no_snapshot_when_nothing_to_migrate(self):
        """With no WebHook handlers there is nothing worth snapshotting."""
        self.assertIsNone(self._write_snapshot())

    def test_snapshot_captures_handler_options(self):
        """The snapshot contains every option row of every WebHook handler."""
        eh = _create_webhook_handler(
            name="Slack", url="https://hooks.slack.com/x",
            content_type="application/json")

        path = self._write_snapshot()
        self.assertIsNotNone(path)
        self.assertTrue(os.path.exists(path))

        with open(path, encoding="utf-8") as fh:
            snapshot = json.load(fh)

        self.assertEqual(snapshot["revision"], "e1f2a3b4c5d6")
        self.assertEqual(snapshot["handler_ids"], [eh.id])

        keys = {opt["Key"] for opt in snapshot["eventhandleroption"]}
        self.assertEqual(keys, {"URL", "content_type", "data", "replace"})
        # No "webhook" option yet - this is the pre-migration state.
        self.assertNotIn("webhook", keys)

    def test_snapshot_file_is_owner_only(self):
        """The snapshot may contain endpoint URLs, so restrict its permissions."""
        _create_webhook_handler(name="Slack", url="https://hooks.slack.com/x")
        path = self._write_snapshot()
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_snapshot_can_be_disabled(self):
        """PRIVACYIDEA_MIGRATION_NO_SNAPSHOT=1 skips snapshot creation."""
        _create_webhook_handler(name="Slack", url="https://hooks.slack.com/x")
        os.environ["PRIVACYIDEA_MIGRATION_NO_SNAPSHOT"] = "1"
        self.assertIsNone(self._write_snapshot())

    def test_unwritable_directory_does_not_break_migration(self):
        """A snapshot failure must never abort an otherwise healthy upgrade."""
        _create_webhook_handler(name="Slack", url="https://hooks.slack.com/x")
        os.environ["PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR"] = "/proc/definitely/not/writable"

        self.assertIsNone(self._write_snapshot())
        # The data migration itself still works.
        self.assertEqual(self._run_migration(), 1)

    # ------------------------------------------------------------------
    # Snapshot directory selection (alignment with pi-manage backup)
    # ------------------------------------------------------------------

    def test_env_var_wins_over_everything(self):
        """An explicit PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR always takes priority."""
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            _snapshot_directory
        )
        os.environ["PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR"] = self.tmpdir
        self.assertEqual(_snapshot_directory(), self.tmpdir)

    def test_falls_back_to_pi_backup_dir_when_available(self):
        """Without an override, snapshots go next to 'pi-manage backup create' output."""
        import privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables as mig

        os.environ.pop("PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR", None)
        original = mig.PI_BACKUP_DIR
        try:
            # Point the "pi-manage backup" dir at a real, writable directory.
            mig.PI_BACKUP_DIR = self.tmpdir
            self.assertEqual(mig._snapshot_directory(), self.tmpdir)
        finally:
            mig.PI_BACKUP_DIR = original

    def test_falls_back_to_tempdir_when_backup_dir_missing(self):
        """On a system without /var/lib/privacyidea/backup, use the temp dir."""
        import privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables as mig

        os.environ.pop("PRIVACYIDEA_MIGRATION_SNAPSHOT_DIR", None)
        original = mig.PI_BACKUP_DIR
        try:
            mig.PI_BACKUP_DIR = "/nonexistent/privacyidea/backup"
            self.assertEqual(mig._snapshot_directory(), tempfile.gettempdir())
        finally:
            mig.PI_BACKUP_DIR = original

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
        self.assertEqual(self._run_migration(), 1)
        self.assertEqual(Webhook.query.count(), 1)

        restore_snapshot(db.session.connection(), path)
        db.session.commit()
        db.session.expire_all()

        after = {
            (o.Key, o.Value)
            for o in EventHandlerOption.query.filter_by(eventhandler_id=eh.id).all()
        }
        self.assertEqual(before, after)
        # The migration-created webhook object is gone again.
        self.assertEqual(Webhook.query.count(), 0)

    def test_migration_is_replayable_after_restore(self):
        """After a restore, re-running the migration produces the same result."""
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            restore_snapshot
        )
        _create_webhook_handler(name="Slack", url="https://hooks.slack.com/x")

        path = self._write_snapshot()
        self._run_migration()
        identifier_first = Webhook.query.first().identifier

        restore_snapshot(db.session.connection(), path)
        db.session.commit()
        db.session.expire_all()

        self.assertEqual(self._run_migration(), 1)
        self.assertEqual(Webhook.query.first().identifier, identifier_first)

    def test_restore_rejects_foreign_snapshot(self):
        """A snapshot from a different revision must not be applied."""
        from privacyidea.migrations.versions.e1f2a3b4c5d6_add_webhook_tables import (
            restore_snapshot
        )
        path = os.path.join(self.tmpdir, "foreign.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"revision": "deadbeef1234", "handler_ids": [],
                       "eventhandleroption": []}, fh)

        with self.assertRaises(ValueError):
            restore_snapshot(db.session.connection(), path)
