"""
This testfile tests the basic app functionality of the privacyIDEA app
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
import flask
import flask_migrate.cli
import inspect
import logging
import mock
import sqlalchemy as sa
from click.testing import Result
from sqlalchemy.dialects import mysql, oracle, postgresql, sqlite
from testfixtures import Comparison, compare, OutputCapture
from collections.abc import Iterator
from contextlib import contextmanager

from privacyidea.app import (ENV_KEY, PrivacyIDEARequest, create_app, create_docker_app,
                             _setup_database_engine_options)
from privacyidea.config import config, ConfigKey, DefaultConfigValues, TestingConfig
from privacyidea.lib.log import DEFAULT_LOGGING_CONFIG, DOCKER_LOGGING_CONFIG
from privacyidea.models import db
from .base import MyApiTestCase

dirname = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))


@contextmanager
def isolated_config_file():
    # A pi.cfg installed on the machine running the tests overwrites the values of the config
    # class, so the tests read an empty config file instead.
    with tempfile.NamedTemporaryFile(suffix=".cfg") as config_file:
        with mock.patch.dict(os.environ, {ENV_KEY: config_file.name}):
            yield


class FactoryStopped(Exception):
    """Raised by a patched step of an app factory, so that a test stops the factory at that step."""


@contextmanager
def docker_app_environment(extra_environment: dict[str, str] | None = None) -> Iterator[None]:
    """
    The environment variables that create_docker_app() needs to get past its config check, plus the given ones.
    The Docker factory also reads the pi.cfg of the machine the test runs on, so it reads a missing file instead.
    """
    environment = {"PRIVACYIDEA_PI_ENCFILE": os.path.join(dirname, "tests/testdata/enckey"),
                   "PRIVACYIDEA_PI_PEPPER": "pepper",
                   "PRIVACYIDEA_SQLALCHEMY_DATABASE_URI": "sqlite://",
                   **(extra_environment or {})}
    with (mock.patch.object(DefaultConfigValues, "CFG_PATH", os.path.join(dirname, "no-such-pi.cfg")),
          mock.patch.dict(os.environ, environment)):
        yield


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
        with isolated_config_file():
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
        with isolated_config_file():
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

    def test_06_logging_keeps_existing_loggers(self):
        # Loggers of other packages exist before the app is created, e.g. those of the WSGI server
        # or of Sphinx when it builds the API documentation. Configuring the logging must not mute them.
        existing_logger = logging.getLogger("other_package.module")
        existing_logger.disabled = False
        with isolated_config_file():
            create_app(config_name="testing", silent=True)
        self.assertFalse(existing_logger.disabled)

        class Config(TestingConfig):
            PI_LOGCONFIG = "tests/testdata/logging.cfg"
        with mock.patch.dict("privacyidea.config.config", {"testing": Config}):
            create_app(config_name="testing", silent=True)
        self.assertFalse(existing_logger.disabled)


class HashConfigTestCase(unittest.TestCase):
    """
    Both factories refuse to start with an unusable PI_HASH_ALGO_LIST or PI_HASH_ALGO_PARAMS.
    What counts as unusable is tested against build_pass_context() in test_lib_crypto.py, so
    only a failing configuration runs a factory here: it stops before the factory registers its
    atexit handler.
    """

    def setUp(self):
        self.logger = logging.getLogger()
        self.orig_handlers = self.logger.handlers
        self.logger.handlers = []
        self.level = self.logger.level
        self.pi_logger = logging.getLogger("privacyidea")
        self.pi_state = (self.pi_logger.handlers[:], self.pi_logger.level, self.pi_logger.propagate)
        self.logging_configs = (copy.deepcopy(DEFAULT_LOGGING_CONFIG), copy.deepcopy(DOCKER_LOGGING_CONFIG))

    def tearDown(self):
        self.logger.handlers = self.orig_handlers
        self.logger.level = self.level
        self.pi_logger.handlers, self.pi_logger.level, self.pi_logger.propagate = self.pi_state
        for logging_config, saved in zip((DEFAULT_LOGGING_CONFIG, DOCKER_LOGGING_CONFIG), self.logging_configs):
            logging_config.clear()
            logging_config.update(saved)

    def test_01_create_app_refuses_to_start(self):
        config_class = type("Config", (TestingConfig,), {"PI_HASH_ALGO_LIST": ["argon2", "nosuchscheme"]})
        with mock.patch.dict("privacyidea.config.config", {"testing": config_class}), isolated_config_file():
            with self.assertRaisesRegex(RuntimeError, "PI_HASH_ALGO_LIST.*nosuchscheme"):
                create_app(config_name="testing", silent=True)

    def test_02_create_docker_app_refuses_to_start(self):
        with docker_app_environment({"PRIVACYIDEA_PI_HASH_ALGO_LIST": json.dumps(["nosuchscheme"])}):
            with self.assertRaisesRegex(RuntimeError, "PI_HASH_ALGO_LIST.*nosuchscheme"):
                create_docker_app()


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


class DockerConfigDatabaseUriTestCase(unittest.TestCase):
    """
    DockerConfig builds the database URI from the PI_DB_* variables, with user and
    password percent-encoded, so that SQLAlchemy reads them back unchanged whatever
    characters they contain.

    Evaluated at import time, so each case runs in a fresh subprocess, as in
    DockerConfigSecretKeyTestCase.
    """
    _DB_ENV = ("PI_DB_USER", "PI_DB_PASSWORD", "PI_DB_PASSWORD_FILE", "PI_DB_HOST", "PI_DB_PORT", "PI_DB_NAME",
               "PI_DB_DRIVER", "PI_DB_EXTRA_PARAMS", "SQLALCHEMY_DATABASE_URI", "SQLALCHEMY_DATABASE_URI_FILE")
    _SCRIPT = ("import sys\n"
               "import privacyidea.config as c\n"
               "sys.stdout.write(c.DockerConfig.SQLALCHEMY_DATABASE_URI)\n")

    def _docker_database_uri(self, extra_env: dict[str, str]) -> str:
        env = {key: value for key, value in os.environ.items() if key not in self._DB_ENV}
        env.update({"PI_DB_HOST": "db.example.org", "PI_DB_NAME": "pi"}, **extra_env)
        result = subprocess.run([sys.executable, "-c", self._SCRIPT],
                                env=env, cwd=dirname, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        return result.stdout

    def test_01_special_characters_in_user_and_password(self):
        from sqlalchemy.engine import make_url
        uri = make_url(self._docker_database_uri({"PI_DB_USER": "pi@site", "PI_DB_PASSWORD": "p@ss:w/rd%?#"}))
        self.assertEqual("pi@site", uri.username)
        self.assertEqual("p@ss:w/rd%?#", uri.password)
        self.assertEqual("db.example.org", uri.host)
        self.assertEqual("pi", uri.database)

    def test_02_url_safe_password_is_kept_as_is(self):
        uri = self._docker_database_uri({"PI_DB_USER": "pi", "PI_DB_PASSWORD": "Ab0-_x", "PI_DB_PORT": "3307"})
        self.assertEqual("mysql+pymysql://pi:Ab0-_x@db.example.org:3307/pi", uri)


class DockerConfigEngineRegistryTestCase(unittest.TestCase):

    def test_01_shared_engine_registry(self):
        # The Docker image keeps one database engine with a connection pool per process for the audit log and the
        # SQL resolvers
        self.assertEqual("shared", config["docker"].PI_ENGINE_REGISTRY_CLASS)


class DbUpgradeCommandTestCase(unittest.TestCase):
    """
    "pi-manage db upgrade" stops on a database without schema revision stamp. Otherwise it passes its parameters on
    to the upgrade command of Flask-Migrate, which a mock replaces here. Each test has its own SQLite database.
    """

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = os.path.join(directory.name, "pi.sqlite")
        config_class = type("Config", (TestingConfig,), {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database}"})
        with mock.patch.dict("privacyidea.config.config", {"testing": config_class}), isolated_config_file():
            self.app = create_app(config_name="testing", silent=True)
        self.addCleanup(self.dispose_engine)
        upgrade_patcher = mock.patch.object(flask_migrate.cli.upgrade, "callback")
        self.flask_migrate_upgrade = upgrade_patcher.start()
        self.addCleanup(upgrade_patcher.stop)

    def dispose_engine(self) -> None:
        with self.app.app_context():
            db.engine.dispose()

    def run_sql(self, *statements: str) -> None:
        with self.app.app_context(), db.engine.begin() as connection:
            for statement in statements:
                connection.execute(sa.text(statement))

    def invoke(self, *arguments: str) -> Result:
        # The command runs in the active app context. Without the context of this app, it would use an app that an
        # earlier test left active.
        with self.app.app_context():
            return self.app.test_cli_runner().invoke(args=["db", *arguments])

    def test_01_stamped_database(self):
        self.run_sql("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)",
                     "INSERT INTO alembic_version (version_num) VALUES ('d3a4b5c6e7f8')")
        result = self.invoke("upgrade")
        self.assertEqual(0, result.exit_code, result.output)
        self.flask_migrate_upgrade.assert_called_once_with(directory=None, sql=False, tag=None, x_arg=(),
                                                           revision="head")

    def test_02_tables_without_stamp(self):
        with self.app.app_context():
            db.create_all()
        result = self.invoke("upgrade")
        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn(f"The database sqlite:///{self.database} has no schema revision stamp", result.output)
        self.assertIn("stamp the database with 'pi-manage db stamp head'", result.output)
        self.assertIn("If an older version created the tables, stamp the database with the newest revision of that "
                      "version.", result.output)
        self.flask_migrate_upgrade.assert_not_called()

    def test_03_empty_database(self):
        result = self.invoke("upgrade")
        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn("create the tables with 'pi-manage setup create_tables'", result.output)
        self.assertNotIn("stamp the database", result.output)
        self.flask_migrate_upgrade.assert_not_called()

    def test_04_sql_output_of_a_database_without_stamp(self):
        """With --sql the command only prints the SQL, so it does not read the stamp."""
        result = self.invoke("upgrade", "--sql", "base:head")
        self.assertEqual(0, result.exit_code, result.output)
        self.flask_migrate_upgrade.assert_called_once_with(directory=None, sql=True, tag=None, x_arg=(),
                                                           revision="base:head")


class UrlencodedBodySizeTestCase(MyApiTestCase):
    """
    The app answers a urlencoded body that is larger than MAX_FORM_MEMORY_SIZE with 413 when it parses the form.
    """

    def setUp(self) -> None:
        super().setUp()
        self.setUp_user_realms()

    def post_urlencoded(self, path: str, size: int, headers: dict[str, str] | None = None) -> flask.Response:
        prefix = "user=cornelius&pass="
        body = prefix + "x" * (size - len(prefix))
        with self.app.test_request_context(path, method="POST", data=body, headers=headers,
                                           content_type="application/x-www-form-urlencoded"):
            return self.app.full_dispatch_request()

    def test_01_request_class(self) -> None:
        self.assertIs(self.app.request_class, PrivacyIDEARequest)

    def test_02_configured_limit(self) -> None:
        limit = self.app.config["MAX_FORM_MEMORY_SIZE"]
        self.assertEqual(200, self.post_urlencoded("/validate/check", limit).status_code)
        self.assertEqual(413, self.post_urlencoded("/validate/check", limit + 1).status_code)

    def test_03_changed_limit(self) -> None:
        with mock.patch.dict(self.app.config, {"MAX_FORM_MEMORY_SIZE": 1000}):
            self.assertEqual(200, self.post_urlencoded("/validate/check", 1000).status_code)
            self.assertEqual(413, self.post_urlencoded("/validate/check", 1001).status_code)

    def test_04_no_limit(self) -> None:
        size = self.app.config["MAX_FORM_MEMORY_SIZE"] + 1
        with mock.patch.dict(self.app.config, {"MAX_FORM_MEMORY_SIZE": None}):
            self.assertEqual(200, self.post_urlencoded("/validate/check", size).status_code)

    def test_05_other_content_types(self) -> None:
        body = json.dumps({"user": "cornelius", "pass": "x" * 1000})
        with mock.patch.dict(self.app.config, {"MAX_FORM_MEMORY_SIZE": 1000}):
            with self.app.test_request_context("/validate/check", method="POST", data=body,
                                               content_type="application/json"):
                self.assertEqual(200, self.app.full_dispatch_request().status_code)

    def test_06_limit_after_authentication(self) -> None:
        # The endpoints that require a login check the auth token before they parse the form.
        with mock.patch.dict(self.app.config, {"MAX_FORM_MEMORY_SIZE": 1000}):
            self.assertEqual(401, self.post_urlencoded("/token/init", 1001).status_code)
            self.assertEqual(413, self.post_urlencoded("/token/init", 1001, {"Authorization": self.at}).status_code)


class DockerAppFactoryTestCase(unittest.TestCase):

    def test_01_request_class(self) -> None:
        with (docker_app_environment(),
              mock.patch("privacyidea.app._check_config", side_effect=FactoryStopped) as check_config):
            with self.assertRaises(FactoryStopped):
                create_docker_app()
        self.assertIs(check_config.call_args.args[0].request_class, PrivacyIDEARequest)

    def test_02_connection_check_compiles_for_oracle(self) -> None:
        # The Docker factory checks the database connection before it starts. Oracle 19c and 21c refuse a SELECT
        # without FROM, so the check is a statement that SQLAlchemy compiles for the dialect of the database.
        with (docker_app_environment(),
              mock.patch("privacyidea.app._setup_logging"),
              mock.patch.object(db.session, "execute", side_effect=FactoryStopped) as execute):
            with self.assertRaisesRegex(RuntimeError, "Could not connect to database"):
                create_docker_app()
        statement = execute.call_args.args[0]
        self.assertEqual("SELECT 1 FROM DUAL", str(statement.compile(dialect=oracle.dialect())))
        for dialect in (mysql.dialect(), postgresql.dialect(), sqlite.dialect()):
            self.assertEqual("SELECT 1", str(statement.compile(dialect=dialect)), dialect.name)
