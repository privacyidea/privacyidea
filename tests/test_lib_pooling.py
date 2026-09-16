"""
This file contains the tests for the pooling module.

In particular, this tests
lib/pooling.py

and the teardown contract its consumers depend on - the SQL audit module, the SQL monitoring
module and the SQL resolver, each of which disposes an engine of its own but leaves a shared
one alone.
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
    """
    Builds one of every object that takes an engine from the registry and defers the cleanup
    of its session to a finalizer.
    """

    def _engine_holders(self):
        """
        Return an audit module, a monitoring module and an SQL resolver, each of which has run
        a query, so that its session really holds a connection to hand back.
        """
        work_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, work_dir)
        shutil.copy("tests/testdata/testuser.sqlite", f"{work_dir}/testuser.sqlite")
        resolver = SQLResolver().loadConfig({"Driver": "sqlite",
                                             "Server": f"/{work_dir}",
                                             "Database": "testuser.sqlite",
                                             "Table": "users",
                                             "Map": '{"username": "username", "userid": "id"}'})
        audit = SQLAudit(self.app.config)
        monitoring = Monitoring(self.app.config)
        audit.get_total({})
        monitoring.get_keys()
        resolver.getUserList()
        # The resolver's session keeps the connection it queried with until someone closes it,
        # and that open connection is what a teardown has to give back. A holder that never ran
        # a query holds nothing, and then a teardown that releases nothing is indistinguishable
        # from one that works.
        self.assertTrue(resolver.session.in_transaction())
        return [audit, monitoring, resolver]


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
                # The engine goes on serving later requests, so its pool has to survive the
                # teardown of the request that happened to create it. Only the session is given
                # up, which returns the connection it held to that pool.
                self.assertIs(pool, holder.engine.pool)
                self.assertFalse(holder.session.in_transaction())


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
            teardown = get_request_local_store().get("call_on_teardown", [])
            for holder in holders:
                self.assertIn(holder._finalize_session, teardown)
            pools = [holder.engine.pool for holder in holders]
        for holder, pool in zip(holders, pools):
            with self.subTest(holder=type(holder).__module__):
                self.assertTrue(holder._owns_engine)
                # The session hands its connection back, and dispose() then installs a fresh
                # pool - which is what closes the connections the old one still held.
                self.assertFalse(holder.session.in_transaction())
                self.assertIsNot(pool, holder.engine.pool)

    def test_05_no_finalizer_outside_a_request(self):
        # Nothing tears a bare application context down - pi-manage, a cron job, a background
        # thread - so a finalizer registered there would never run. It would only keep the
        # holder, and with it an open connection, alive for the lifetime of the process.
        store = get_request_local_store()
        registered = list(store.get("call_on_teardown", []))
        self._engine_holders()
        self.assertEqual(registered, store.get("call_on_teardown", []))
