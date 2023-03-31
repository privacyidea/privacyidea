# -*- coding: utf-8 -*-
"""
This testfile tests the basic app functionality of the privacyIDEA app
"""
import os
import unittest
import flask
import inspect
import logging
import mock
from testfixtures import Comparison, compare
from privacyidea.app import create_app, PiResponseClass
from privacyidea.config import config, TestingConfig

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
        self.assertEqual(app.env, 'production', app)
        self.assertTrue(app.debug, app)
        self.assertFalse(app.testing, app)
        self.assertEqual(app.import_name, 'privacyidea.app', app)
        self.assertEqual(app.name, 'privacyidea.app', app)
        self.assertTrue(app.response_class == PiResponseClass, app)
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
        members = inspect.getmembers(dc, lambda a: not(inspect.isroutine(a)))
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
                       level=logging.DEBUG,
                       partial=True)
        ], logger.handlers)

    def test_02_create_production_app(self):
        app = create_app(config_name='production')
        dc = config['production']()
        members = inspect.getmembers(dc, lambda a: not(inspect.isroutine(a)))
        conf = [m for m in members if not (m[0].startswith('__') and m[0].endswith('__'))]
        self.assertTrue(all(app.config[k] == v for k, v in conf), app)

    def test_03_logging_config_file(self):
        class Config(TestingConfig):
            PI_LOGCONFIG = "tests/testdata/logging.cfg"
        with mock.patch.dict("privacyidea.config.config", {"testing": Config}):
            app = create_app(config_name='testing')
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
            app = create_app(config_name='testing')
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
            app = create_app(config_name='testing')
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
                           level=logging.INFO,
                           partial=True)
            ], logger.handlers)
