"""
This testfile tests the basic app functionality of the privacyIDEA app
"""
import os
import subprocess
import sys
import tempfile
import unittest
import flask
import inspect
import logging
import mock
from testfixtures import Comparison, compare, OutputCapture
from privacyidea.app import create_app, _setup_database_engine_options
from privacyidea.config import config, ConfigKey, TestingConfig

dirname = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger()
        self.orig_handlers = self.logger.handlers
        self.logger.handlers = []
        self.level = self.logger.level

    def tearDown(self):
        self.logger.handlers = self.orig_handlers
        self.logger.level = self.level

    def test_01_create_default_app(self):
        # This will create the app with the 'development' configuration
        app = create_app()
        self.assertIsInstance(app, flask.app.Flask, app)
#        self.assertEqual(app.env, 'production', app)
        self.assertTrue(app.debug, app)
        self.assertFalse(app.testing, app)
        self.assertEqual(app.import_name, 'privacyidea.app', app)
        self.assertEqual(app.name, 'privacyidea.app', app)
#        self.assertTrue(app.response_class == PiResponseClass, app)
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
        self.assertTrue(all(k in app.before_request_funcs for k in blueprints), app)
        self.assertTrue(all(k in app.blueprints for k in blueprints), app)
        extensions = ['sqlalchemy', 'migrate', 'babel']
        self.assertTrue(all(k in extensions for k in app.extensions), app)
        self.assertEqual(app.secret_key, 't0p s3cr3t', app)
        # TODO: check url_map and view_functions
        # check that the configuration was loaded successfully
        # the default configuration is 'development'
        dc = config['development']()
        members = inspect.getmembers(dc, lambda a: not (inspect.isroutine(a)))
        conf = [m for m in members if not (m[0].startswith('__') and m[0].endswith('__'))]
        self.assertTrue(all(app.config[k] == v for k, v in conf), app)
        # check the correct initialization of the logging
        logger = logging.getLogger('privacyidea')
        self.assertEqual(logger.level, logging.DEBUG, logger)
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
        app = create_app(config_name='production')
        dc = config['production']()
        members = inspect.getmembers(dc, lambda a: not (inspect.isroutine(a)))
        conf = [m for m in members if not (m[0].startswith('__') and m[0].endswith('__'))]
        self.assertTrue(all(app.config[k] == v for k, v in conf), app)

    def test_03_logging_config_file(self):
        class Config(TestingConfig):
            PI_LOGCONFIG = "tests/testdata/logging.cfg"
        with mock.patch.dict("privacyidea.config.config", {"testing": Config}):
            create_app(config_name='testing')
            # check the correct initialization of the logging from config file
            logger = logging.getLogger('privacyidea')
            self.assertEqual(logger.level, logging.DEBUG, logger)
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
            self.assertEqual(logger.level, logging.INFO, logger)
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
            self.assertEqual(logger.level, logging.INFO, logger)
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
            self.assertEqual(logger.level, logging.INFO, logger)
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
            self.assertIn("Could not use PI_LOGCONFIG: Unable to configure handler 'file'",
                          output.captured, output.captured)
            # check the correct initialization of the logging with the default
            # values since the yaml file is broken
            logger = logging.getLogger('privacyidea')
            self.assertEqual(logger.level, logging.INFO, logger)
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


class DatabaseEngineOptionsTestCase(unittest.TestCase):
    """
    The engine options for the main database are resolved before the engine is created.
    They are checked on the helper directly, since building a whole app for a
    non-SQLite URI would require a reachable database server.
    """

    @staticmethod
    def _resolve(database_uri, engine_options=None):
        app = flask.Flask(__name__)
        app.config[ConfigKey.VERBOSE] = False
        app.config[ConfigKey.SQLALCHEMY_DATABASE_URI] = database_uri
        if engine_options is not None:
            app.config[ConfigKey.SQLALCHEMY_ENGINE_OPTIONS] = engine_options
        _setup_database_engine_options(app)
        return app.config[ConfigKey.SQLALCHEMY_ENGINE_OPTIONS]

    def test_01_pre_ping_enabled_for_server_databases(self):
        self.assertTrue(self._resolve("mysql+pymysql://pi:pi@localhost/pi")["pool_pre_ping"])

    def test_02_pre_ping_skipped_for_sqlite(self):
        self.assertNotIn("pool_pre_ping", self._resolve("sqlite:////etc/privacyidea/data.sqlite"))

    def test_03_explicit_setting_is_kept(self):
        options = self._resolve("mysql+pymysql://pi:pi@localhost/pi", {"pool_pre_ping": False})
        self.assertFalse(options["pool_pre_ping"])

    def test_04_other_options_are_preserved(self):
        options = self._resolve("oracle://pi:pi@localhost/pi", {"max_identifier_length": 128})
        self.assertEqual(128, options["max_identifier_length"])
        self.assertTrue(options["pool_pre_ping"])

    def test_05_configured_options_are_not_modified(self):
        engine_options = {"max_identifier_length": 128}
        self._resolve("mysql+pymysql://pi:pi@localhost/pi", engine_options)
        self.assertEqual({"max_identifier_length": 128}, engine_options)

    def test_06_missing_database_uri(self):
        app = flask.Flask(__name__)
        app.config[ConfigKey.VERBOSE] = False
        _setup_database_engine_options(app)
        self.assertTrue(app.config[ConfigKey.SQLALCHEMY_ENGINE_OPTIONS]["pool_pre_ping"])


class DockerConfigSecretKeyTestCase(unittest.TestCase):
    """
    DockerConfig reads the Flask SECRET_KEY from SECRET_KEY / SECRET_KEY_FILE and
    also accepts PI_SECRET_KEY / PI_SECRET_KEY_FILE as an alias (for consistency
    with the other PI_* secret variables), with the unprefixed name taking
    precedence.

    DockerConfig evaluates these at import time, so each case is checked in a
    fresh subprocess with a controlled environment. Reloading the config module
    in-process must be avoided: it would rebind ``privacyidea.config.config`` away
    from the reference ``privacyidea.app`` holds and silently break config
    overrides for later tests on the same worker.
    """
    _SECRET_ENV = ("SECRET_KEY", "SECRET_KEY_FILE", "PI_SECRET_KEY", "PI_SECRET_KEY_FILE")
    _SCRIPT = ("import sys\n"
               "import privacyidea.config as c\n"
               "sys.stdout.write(getattr(c.DockerConfig, 'SECRET_KEY', '') or '<none>')\n")

    def _docker_secret_key(self, extra_env):
        env = {key: value for key, value in os.environ.items() if key not in self._SECRET_ENV}
        env.update(extra_env)
        result = subprocess.run([sys.executable, "-c", self._SCRIPT],
                                env=env, cwd=dirname, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def _write_secret(self, tmpdir, name, value):
        path = os.path.join(tmpdir, name)
        with open(path, "w") as secret_file:
            secret_file.write(value + "\n")
        return path

    def test_01_pi_secret_key_file_alias(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            alias = self._write_secret(tmpdir, "pi_sk", "ALIAS-VALUE")
            self.assertEqual(self._docker_secret_key({"PI_SECRET_KEY_FILE": alias}), "ALIAS-VALUE")

    def test_02_plain_secret_key_file_still_works(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plain = self._write_secret(tmpdir, "plain_sk", "PLAIN-VALUE")
            self.assertEqual(self._docker_secret_key({"SECRET_KEY_FILE": plain}), "PLAIN-VALUE")

    def test_03_plain_takes_precedence_over_alias(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plain = self._write_secret(tmpdir, "plain_sk", "PLAIN-VALUE")
            alias = self._write_secret(tmpdir, "pi_sk", "ALIAS-VALUE")
            self.assertEqual(
                self._docker_secret_key({"SECRET_KEY_FILE": plain, "PI_SECRET_KEY_FILE": alias}),
                "PLAIN-VALUE")
