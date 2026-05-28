"""
This testfile tests the basic app functionality of the privacyIDEA app
"""
import inspect
import logging
import os
import pathlib

import flask
import mock
import pytest
from testfixtures import Comparison, compare, OutputCapture

from privacyidea.app import create_app
from privacyidea.config import config, TestingConfig
from privacyidea.lib.crypto import ENCKEY_CHECK_PLAINTEXT
from privacyidea.lib.crypto import encryptPassword
from privacyidea.models import db
from privacyidea.models.pi_internal import PiInternal

dirname = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))


@pytest.fixture(autouse=True)
def reset_root_logger():
    """Save and restore root logger handlers/level around each test."""
    logger = logging.getLogger()
    orig_handlers = logger.handlers[:]
    orig_level = logger.level
    logger.handlers = []
    yield
    logger.handlers = orig_handlers
    logger.level = orig_level


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Remove PRIVACYIDEA_CONFIGFILE env var to avoid loading local config."""
    monkeypatch.delenv("PRIVACYIDEA_CONFIGFILE", raising=False)


class TestApp:
    def test_01_create_default_app(self):
        # This will create the app with the 'development' configuration
        app = create_app()
        assert isinstance(app, flask.app.Flask)
        assert app.debug
        assert not app.testing
        assert app.import_name == 'privacyidea.app'
        assert app.name == 'privacyidea.app'
        # TODO: additional blueprints will not be checked here
        blueprints = ['validate_blueprint', 'token_blueprint', 'system_blueprint',
                      'resolver_blueprint', 'realm_blueprint', 'defaultrealm_blueprint',
                      'policy_blueprint', 'login_blueprint', 'jwtauth', 'user_blueprint',
                      'audit_blueprint', 'machineresolver_blueprint', 'machine_blueprint',
                      'application_blueprint', 'caconnector_blueprint', 'cert_blueprint',
                      'ttype_blueprint', 'register_blueprint', 'smtpserver_blueprint',
                      'recover_blueprint', 'radiusserver_blueprint', 'periodictask_blueprint',
                      'privacyideaserver_blueprint', 'eventhandling_blueprint',
                      'smsgateway_blueprint', 'client_blueprint', 'subscriptions_blueprint',
                      'monitoring_blueprint']
        assert all(k in app.before_request_funcs for k in blueprints)
        assert all(k in app.blueprints for k in blueprints)
        extensions = ['sqlalchemy', 'migrate', 'babel']
        assert all(k in extensions for k in app.extensions)
        assert app.secret_key == 't0p s3cr3t'
        # TODO: check url_map and view_functions
        # check that the configuration was loaded successfully
        # the default configuration is 'development'
        dc = config['development']()
        members = inspect.getmembers(dc, lambda a: not (inspect.isroutine(a)))
        conf = [m for m in members if not (m[0].startswith('__') and m[0].endswith('__'))]
        assert all(app.config[k] == v for k, v in conf)
        # check the correct initialization of the logging
        logger = logging.getLogger('privacyidea')
        assert logger.level == logging.DEBUG
        compare([
            Comparison('logging.handlers.RotatingFileHandler',
                       baseFilename=os.path.join(dirname, 'privacyidea.log'),
                       formatter=Comparison('privacyidea.lib.log.SecureFormatter',
                                            _fmt="[%(asctime)s][%(process)d]"
                                                 "[%(thread)d][%(levelname)s]"
                                                 "[%(name)s:%(lineno)d] "
                                                 "%(message)s",
                                            partial=True),
                       level=logging.NOTSET,
                       partial=True)
        ], logger.handlers)

    def test_02_create_production_app(self):
        app = create_app(config_name='production', config_file=pathlib.Path.cwd() / "privacyida/config.py")
        dc = config['production']()
        members = inspect.getmembers(dc, lambda a: not (inspect.isroutine(a)))
        conf = [m for m in members if not (m[0].startswith('__') and m[0].endswith('__'))]
        assert all(app.config[k] == v for k, v in conf)

    def test_03_logging_config_file(self):
        class Config(TestingConfig):
            PI_LOGCONFIG = "tests/testdata/logging.cfg"

        with mock.patch.dict("privacyidea.config.config", {"testing": Config}):
            create_app(config_name='testing')
            # check the correct initialization of the logging from config file
            logger = logging.getLogger('privacyidea')
            assert logger.level == logging.DEBUG
            compare([
                Comparison('logging.handlers.RotatingFileHandler',
                           baseFilename=os.path.join(dirname, 'privacyidea.log'),
                           formatter=Comparison('privacyidea.lib.log.SecureFormatter',
                                                _fmt="[%(asctime)s][%(process)d]"
                                                     "[%(thread)d][%(levelname)s]"
                                                     "[%(name)s:%(lineno)d] "
                                                     "%(message)s",
                                                partial=True),
                           level=logging.DEBUG,
                           partial=True)
            ], logger.handlers)
            logger = logging.getLogger('privacyidea.lib.auditmodules.loggeraudit')
            assert logger.level == logging.INFO
            compare([
                Comparison('logging.handlers.RotatingFileHandler',
                           baseFilename=os.path.join(dirname, 'audit.log'),
                           formatter=Comparison('privacyidea.lib.log.SecureFormatter',
                                                _fmt="[%(asctime)s][%(process)d]"
                                                     "[%(thread)d][%(levelname)s]"
                                                     "[%(name)s:%(lineno)d] "
                                                     "%(message)s",
                                                partial=True),
                           level=logging.INFO,
                           partial=True)
            ], logger.handlers)

    def test_04_logging_config_yaml(self):
        class Config(TestingConfig):
            PI_LOGCONFIG = "tests/testdata/logging.yml"

        with mock.patch.dict("privacyidea.config.config", {"testing": Config}):
            create_app(config_name='testing')
            # check the correct initialization of the logging from config file
            logger = logging.getLogger('privacyidea')
            assert logger.level == logging.INFO
            compare([
                Comparison('logging.handlers.RotatingFileHandler',
                           baseFilename=os.path.join(dirname, 'privacyidea.log'),
                           formatter=Comparison('privacyidea.lib.log.SecureFormatter',
                                                _fmt="[%(asctime)s][%(process)d]"
                                                     "[%(thread)d][%(levelname)s]"
                                                     "[%(name)s:%(lineno)d] "
                                                     "%(message)s",
                                                partial=True),
                           backupCount=5,
                           level=logging.DEBUG,
                           partial=True)
            ], logger.handlers)
            logger = logging.getLogger('audit')
            assert logger.level == logging.INFO
            compare([
                Comparison('logging.handlers.RotatingFileHandler',
                           backupCount=14,
                           baseFilename=os.path.join(dirname, 'audit.log'),
                           level=logging.INFO,
                           formatter=None,
                           partial=True)
            ], logger.handlers)

    def test_05_logging_config_broken_yaml(self):
        class Config(TestingConfig):
            PI_LOGCONFIG = "tests/testdata/logging_broken.yaml"

        with mock.patch.dict("privacyidea.config.config", {"testing": Config}):
            with OutputCapture() as output:
                create_app(config_name='testing')
            assert "Could not use PI_LOGCONFIG: Unable to configure handler 'file'" in output.captured
            # check the correct initialization of the logging with the default
            # values since the yaml file is broken
            logger = logging.getLogger('privacyidea')
            assert logger.level == logging.INFO
            compare([
                Comparison('logging.handlers.RotatingFileHandler',
                           baseFilename=os.path.join(dirname, 'privacyidea.log'),
                           formatter=Comparison('privacyidea.lib.log.SecureFormatter',
                                                _fmt="[%(asctime)s][%(process)d]"
                                                     "[%(thread)d][%(levelname)s]"
                                                     "[%(name)s:%(lineno)d] "
                                                     "%(message)s",
                                                partial=True),
                           level=logging.NOTSET,
                           partial=True)
            ], logger.handlers)

    @staticmethod
    def _ensure_tables_exist():
        """Ensure the test DB has all tables created."""
        from sqlalchemy import create_engine
        from privacyidea.models import db as _db
        engine = create_engine(TestingConfig.SQLALCHEMY_DATABASE_URI)
        _db.metadata.create_all(engine)
        engine.dispose()

    @staticmethod
    def _clean_enckey_check():
        """Remove enckey_check from the test DB without triggering app verification."""
        from sqlalchemy import create_engine, text
        engine = create_engine(TestingConfig.SQLALCHEMY_DATABASE_URI)
        with engine.connect() as conn:
            try:
                conn.execute(text("DELETE FROM pi_internal WHERE name = 'enckey_check'"))
                conn.commit()
            except Exception:
                conn.rollback()
        engine.dispose()

    @staticmethod
    def _set_enckey_check(value):
        """Set enckey_check in the test DB without triggering app verification."""
        from sqlalchemy import create_engine, text
        engine = create_engine(TestingConfig.SQLALCHEMY_DATABASE_URI)
        with engine.connect() as conn:
            try:
                conn.execute(text("DELETE FROM pi_internal WHERE name = 'enckey_check'"))
                conn.execute(text("INSERT INTO pi_internal (name, check_value) VALUES ('enckey_check', :val)"),
                             {"val": value})
                conn.commit()
            except Exception:
                conn.rollback()
        engine.dispose()

    def test_06_enckey_verification_succeeds_with_correct_key(self):
        """App starts successfully when the enckey check value in DB matches the current key."""
        self._ensure_tables_exist()
        self._clean_enckey_check()

        # First app creation will init HSM and create the check value (table exists, no row)
        app = create_app(config_name='testing', config_file=pathlib.Path.cwd() / "tests/testdata/test_pi.cfg")
        with app.app_context():
            row = db.session.query(PiInternal).filter_by(name="enckey_check").first()
            assert row is not None

        # Creating the app again should not exit (key matches)
        app2 = create_app(config_name='testing', config_file=pathlib.Path.cwd() / "tests/testdata/test_pi.cfg")
        assert isinstance(app2, flask.app.Flask)

    def test_07_enckey_verification_fails_with_wrong_check_value(self):
        """App exits when the enckey check value in DB does not match the current key."""
        self._ensure_tables_exist()
        self._set_enckey_check("deadbeef:cafebabe")

        with pytest.raises(SystemExit) as exc_info:
            create_app(config_name='testing', config_file=pathlib.Path.cwd() / "tests/testdata/test_pi.cfg")
        assert exc_info.value.code == 1

        # Cleanup
        self._clean_enckey_check()

    def test_08_enckey_verification_skipped_when_no_check_value(self):
        """App starts normally and creates check value when none exists."""
        self._ensure_tables_exist()
        self._clean_enckey_check()

        # App should start fine and create a new check value
        app = create_app(config_name='testing', config_file=pathlib.Path.cwd() / "tests/testdata/test_pi.cfg")
        assert isinstance(app, flask.app.Flask)

        # Verify a check value was created
        with app.app_context():
            row = db.session.query(PiInternal).filter_by(name="enckey_check").first()
            assert row is not None
