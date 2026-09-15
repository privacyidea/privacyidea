"""
This file contains the tests for the pooling module.

In particular, this tests
lib/pooling.py
"""
import shutil
import tempfile

from sqlalchemy import create_engine

from privacyidea.app import create_app
from privacyidea.lib.auditmodules.sqlaudit import Audit as SQLAudit
from privacyidea.lib.auth import create_db_admin
from privacyidea.lib.framework import get_request_local_store
from privacyidea.lib.monitoringmodules.sqlstats import Monitoring
from privacyidea.lib.pooling import (get_engine, get_registry, engines_are_shared,
                                     SharedEngineRegistry, NullEngineRegistry)
from privacyidea.lib.resolvers.SQLIdResolver import IdResolver as SQLResolver
from privacyidea.models import db, save_config_timestamp
from .base import MyTestCase


class EngineHolders:
    def _engine_holders(self):
        work_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, work_dir)
        shutil.copy("tests/testdata/testuser.sqlite", f"{work_dir}/testuser.sqlite")
        resolver = SQLResolver().loadConfig({"Driver": "sqlite",
                                             "Server": f"/{work_dir}",
                                             "Database": "testuser.sqlite",
                                             "Table": "users",
                                             "Map": '{"username": "username", "userid": "id"}'})
        return [SQLAudit(self.app.config), Monitoring(self.app.config), resolver]


class SharedPoolingTestCase(MyTestCase, EngineHolders):
    @classmethod
    def setUpClass(cls):
        # Modified setup method to use SharedEngineRegistry
        cls.app = create_app('testing', "")
        cls.app.config['PI_ENGINE_REGISTRY_CLASS'] = 'shared'
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.create_all()
        # save the current timestamp to the database to avoid hanging cached
        # data
        save_config_timestamp()
        db.session.commit()
        # Create an admin for tests.
        create_db_admin("testadmin", "admin@test.tld", "testpw")

    def _create_engine(self):
        return create_engine('sqlite://')

    def test_01_registry(self):
        # test that we have one registry per app
        registry1 = get_registry()
        registry2 = get_registry()
        self.assertIs(registry1, registry2)
        self.assertIsInstance(registry1, SharedEngineRegistry)

    def test_02_engine(self):
        # test that we get the same engine
        engine1 = get_engine('my engine', self._create_engine)
        engine2 = get_engine('my engine', self._create_engine)
        self.assertIs(engine1, engine2)
        engine3 = get_engine('my other engine', self._create_engine)
        self.assertIsNot(engine1, engine3)

    def test_03_engines_are_shared(self):
        self.assertTrue(engines_are_shared())

    def test_04_teardown_keeps_shared_engines(self):
        with self.app.test_request_context("/"):
            holders = self._engine_holders()
            pools = [holder.engine.pool for holder in holders]
        for holder, pool in zip(holders, pools):
            with self.subTest(holder=type(holder).__module__):
                self.assertFalse(holder._owns_engine)
                self.assertIs(pool, holder.engine.pool)


class NullPoolingTestCase(MyTestCase, EngineHolders):
    """ Test Null pooling. This is the default in the testing configuration. """
    def test_01_registry(self):
        # test that we still get one registry per app
        registry1 = get_registry()
        registry2 = get_registry()
        self.assertIs(registry1, registry2)
        self.assertIsInstance(registry1, NullEngineRegistry)

    def _create_engine(self):
        return create_engine('sqlite://')

    def test_02_engine(self):
        # test that we get different engines every time
        engine1 = get_engine('my engine', self._create_engine)
        engine2 = get_engine('my engine', self._create_engine)
        engine3 = get_engine('my other engine', self._create_engine)
        self.assertIsNot(engine1, engine2)
        self.assertIsNot(engine1, engine3)
        self.assertIsNot(engine2, engine3)

    def test_03_engines_are_not_shared(self):
        self.assertFalse(engines_are_shared())

    def test_04_teardown_disposes_owned_engines(self):
        with self.app.test_request_context("/"):
            holders = self._engine_holders()
            teardown = get_request_local_store()["call_on_teardown"]
            for holder in holders:
                self.assertIn(holder._finalize_session, teardown)
            pools = [holder.engine.pool for holder in holders]
        for holder, pool in zip(holders, pools):
            with self.subTest(holder=type(holder).__module__):
                self.assertTrue(holder._owns_engine)
                self.assertIsNot(pool, holder.engine.pool)

    def test_05_no_finalizer_outside_a_request(self):
        store = get_request_local_store()
        registered = list(store.get("call_on_teardown", []))
        self._engine_holders()
        self.assertEqual(registered, store.get("call_on_teardown", []))
