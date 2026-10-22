"""
Data transformation test for migration 4aec628f7ef2
v3.14.1: Store the digest of the series id of remembered devices

upgrade()   — replaces the series id of each remembered device with its SHA-256 hex digest, the value a presented
              cookie is looked up by. A value that is a digest already stays, so the upgrade can run again.
downgrade() — removes the remembered devices stored with a digest, the previous version looks a device up by its
              series id
"""
import datetime
import os
import secrets

import pytest
from alembic import command
from sqlalchemy import Engine, text

from privacyidea.lib.remembered_device import hash_series_id
from tests.migration_test_utils import MigrationTestBase, get_alembic_cfg

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]

CLIENT_ID = "6f1c2c1e-4aec-4628-8f7e-f2a1b2c3d4e5"


class TestMigration4aec628f7ef2(MigrationTestBase):
    REVISION = "4aec628f7ef2"
    PARENT_REVISION = "9e8487714b46"

    def _insert_client(self, engine: Engine) -> None:
        self._insert_rows(engine, "clients", [{
            "id": CLIENT_ID, "display_name": "migration client", "client_type": "privacyidea-cp",
            "key_id": "0123456789abcdef", "key_hash": "0" * 64, "status": "active",
            "created_at": datetime.datetime(2026, 10, 1), "config": "{}"
        }])

    def _insert_devices(self, engine: Engine, series_ids: dict[str, str]) -> None:
        """Insert a remembered device for each ``{device_id: series_id}``, its counter is the length of the device_id"""
        realm_id = self._fetch_scalar(engine, "SELECT MIN(id) FROM realm")
        self._insert_rows(engine, "remembered_devices", [
            {"series_id": series_id, "device_id": device_id, "counter": len(device_id), "client_id": CLIENT_ID,
             "resolver": "resolver1", "user_id": device_id, "realm_id": realm_id,
             "created_at": datetime.datetime(2026, 10, 1), "expires_at": datetime.datetime(2099, 1, 1)}
            for device_id, series_id in series_ids.items()
        ])

    def _fetch_devices(self, engine: Engine) -> dict[str, tuple[str, int]]:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT device_id, series_id, counter FROM remembered_devices")).fetchall()
        return {device_id: (series_id, counter) for device_id, series_id, counter in rows}

    def test_upgrade_stores_the_digest(self, flask_app):
        """upgrade() replaces each series id with the digest the application looks it up by."""
        plain = {"device-a": secrets.token_urlsafe(32), "device-bb": secrets.token_urlsafe(32)}
        digest = {"device-ccc": hash_series_id(secrets.token_urlsafe(32))}
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_client(engine)
        self._insert_devices(engine, plain | digest)
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        expected = {device_id: (hash_series_id(series_id), len(device_id)) for device_id, series_id in plain.items()}
        # A value that is a digest already stays
        expected["device-ccc"] = (digest["device-ccc"], len("device-ccc"))
        assert self._fetch_devices(engine) == expected
        engine.dispose()

    def test_upgrade_runs_again(self, flask_app):
        """Running upgrade() on its own result changes nothing."""
        plain = {"device-a": secrets.token_urlsafe(32)}
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_client(engine)
        self._insert_devices(engine, plain)
        engine.dispose()

        self._upgrade()
        command.stamp(get_alembic_cfg(), self.PARENT_REVISION)
        self._upgrade()

        engine = self._engine()
        assert self._fetch_devices(engine) == {"device-a": (hash_series_id(plain["device-a"]), len("device-a"))}
        engine.dispose()

    def test_upgrade_without_devices(self, flask_app):
        """upgrade() runs on a database without remembered devices."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        engine.dispose()

        self._upgrade()

        engine = self._engine()
        assert self._fetch_devices(engine) == {}
        engine.dispose()

    def test_downgrade_removes_the_devices_stored_with_a_digest(self, flask_app):
        """downgrade() removes the devices stored with a digest and keeps a device stored with its series id."""
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        self._insert_client(engine)
        self._insert_devices(engine, {"device-a": secrets.token_urlsafe(32)})
        engine.dispose()

        self._upgrade()
        engine = self._engine()
        plain = secrets.token_urlsafe(32)
        self._insert_devices(engine, {"device-bb": plain})
        engine.dispose()
        self._downgrade()

        engine = self._engine()
        assert self._fetch_devices(engine) == {"device-bb": (plain, len("device-bb"))}
        engine.dispose()
