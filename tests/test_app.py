"""
This testfile tests the basic app functionality of the privacyIDEA app
"""
import os
import importlib
import shutil
import tempfile
import unittest
import flask
import inspect
import logging
import mock
from testfixtures import Comparison, compare, OutputCapture
from privacyidea.app import create_app
from privacyidea.config import config, TestingConfig
import privacyidea.config as pi_config

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


class DockerConfigSecretKeyTestCase(unittest.TestCase):
    """
    DockerConfig reads the Flask SECRET_KEY from SECRET_KEY / SECRET_KEY_FILE and
    also accepts PI_SECRET_KEY / PI_SECRET_KEY_FILE as an alias (for consistency
    with the other PI_* secret variables), with the unprefixed name taking
    precedence. DockerConfig evaluates these at class-definition time, so each
    case sets the environment and reloads the config module.
    """
    _SECRET_ENV = ("SECRET_KEY", "SECRET_KEY_FILE", "PI_SECRET_KEY", "PI_SECRET_KEY_FILE")

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._saved_env = {key: os.environ.pop(key, None) for key in self._SECRET_ENV}

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        for key in self._SECRET_ENV:
            os.environ.pop(key, None)
        for key, value in self._saved_env.items():
            if value is not None:
                os.environ[key] = value
        # Restore the module to its original (test) environment.
        importlib.reload(pi_config)

    def _write_secret(self, name, value):
        path = os.path.join(self.tmpdir, name)
        with open(path, "w") as secret_file:
            secret_file.write(value + "\n")
        return path

    def _docker_secret_key(self):
        importlib.reload(pi_config)
        return getattr(pi_config.DockerConfig, "SECRET_KEY", None)

    def test_01_pi_secret_key_file_alias(self):
        os.environ["PI_SECRET_KEY_FILE"] = self._write_secret("pi_sk", "ALIAS-VALUE")
        self.assertEqual(self._docker_secret_key(), "ALIAS-VALUE")

    def test_02_plain_secret_key_file_still_works(self):
        os.environ["SECRET_KEY_FILE"] = self._write_secret("plain_sk", "PLAIN-VALUE")
        self.assertEqual(self._docker_secret_key(), "PLAIN-VALUE")

    def test_03_plain_takes_precedence_over_alias(self):
        os.environ["SECRET_KEY_FILE"] = self._write_secret("plain_sk", "PLAIN-VALUE")
        os.environ["PI_SECRET_KEY_FILE"] = self._write_secret("pi_sk", "ALIAS-VALUE")
        self.assertEqual(self._docker_secret_key(), "PLAIN-VALUE")
