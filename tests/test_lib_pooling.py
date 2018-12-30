"""
This file contains the tests for the pooling module.

In particular, this tests
lib/pooling.py
"""
from sqlalchemy import create_engine

from privacyidea.app import create_app
from privacyidea.lib.auth import create_db_admin
from privacyidea.lib.pooling import get_engine, get_registry, SharedEngineRegistry, NullEngineRegistry
from privacyidea.models import db, save_config_timestamp
from .base import MyTestCase


class SharedPoolingTestCase(MyTestCase):
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
        create_db_admin(cls.app, "testadmin", "admin@test.tld", "testpw")

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


class NullPoolingTestCase(MyTestCase):
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


