# SPDX-FileCopyrightText: (C) 2015 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2015 Cornelius Kölbel, <info@privacyidea.org>
# SPDX-FileCopyrightText: (C) 2025 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# 2014-11-15 Cornelius Kölbel, info@privacyidea.org
#            Initial creation
#
# (c) Cornelius Kölbel
# Info: http://www.privacyidea.org
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import atexit
import datetime
from importlib import metadata
from importlib.metadata import PackageNotFoundError
import json
import os
import os.path
import logging
import logging.config
import secrets
import sys
import uuid
from pathlib import Path

import yaml
from flask import Flask, render_template, jsonify, request
from flask_babel import Babel
from flask_migrate import Migrate
from flaskext.versioned import Versioned
import sqlalchemy as sa

# we need this import to add the before/after request function to the blueprints
# noinspection PyUnresolvedReferences
import privacyidea.api.before_after  # noqa: F401
from privacyidea.api.container import container_blueprint
from privacyidea.api.healthcheck import healthz_blueprint
from privacyidea.api.lib.utils import send_html
from privacyidea.api.validate import validate_blueprint
from privacyidea.api.token import token_blueprint
from privacyidea.api.system import system_blueprint
from privacyidea.api.resolver import resolver_blueprint
from privacyidea.api.realm import realm_blueprint
from privacyidea.api.realm import defaultrealm_blueprint
from privacyidea.api.policy import policy_blueprint
from privacyidea.api.user import user_blueprint
from privacyidea.api.audit import audit_blueprint
from privacyidea.api.application import application_blueprint
from privacyidea.api.caconnector import caconnector_blueprint
from privacyidea.api.register import register_blueprint
from privacyidea.api.auth import jwtauth
from privacyidea.webui.login import login_blueprint, get_accepted_language
from privacyidea.webui.certificate import cert_blueprint
from privacyidea.api.machineresolver import machineresolver_blueprint
from privacyidea.api.machine import machine_blueprint
from privacyidea.api.ttype import ttype_blueprint
from privacyidea.api.smtpserver import smtpserver_blueprint
from privacyidea.api.radiusserver import radiusserver_blueprint
from privacyidea.api.periodictask import periodictask_blueprint
from privacyidea.api.privacyideaserver import privacyideaserver_blueprint
from privacyidea.api.recover import recover_blueprint
from privacyidea.api.event import eventhandling_blueprint
from privacyidea.api.smsgateway import smsgateway_blueprint
from privacyidea.api.clienttype import client_blueprint
from privacyidea.api.subscriptions import subscriptions_blueprint
from privacyidea.api.monitoring import monitoring_blueprint
from privacyidea.api.tokengroup import tokengroup_blueprint
from privacyidea.api.serviceid import serviceid_blueprint
from privacyidea.api.info import info_blueprint
from privacyidea.lib import queue
from privacyidea.lib.log import DEFAULT_LOGGING_CONFIG, DOCKER_LOGGING_CONFIG
from privacyidea.config import config, DockerConfig, ConfigKey, DefaultConfigValues
from privacyidea.models import db, NodeName
from privacyidea.lib.crypto import init_hsm

ENV_KEY = "PRIVACYIDEA_CONFIGFILE"

migrate = Migrate()
babel = Babel()

# We need to define the logging here to use it in the helper functions.
# But since the logging system is not configured properly, the message might not
# end up in the place as defined in the logging configuration
log = logging.getLogger(__name__)


def _register_blueprints(app):
    """Register the available Flask blueprints"""
    app.register_blueprint(validate_blueprint, url_prefix='/validate')
    app.register_blueprint(token_blueprint, url_prefix='/token')
    app.register_blueprint(system_blueprint, url_prefix='/system')
    app.register_blueprint(resolver_blueprint, url_prefix='/resolver')
    app.register_blueprint(realm_blueprint, url_prefix='/realm')
    app.register_blueprint(defaultrealm_blueprint, url_prefix='/defaultrealm')
    app.register_blueprint(policy_blueprint, url_prefix='/policy')
    app.register_blueprint(login_blueprint, url_prefix='/')
    app.register_blueprint(jwtauth, url_prefix='/auth')
    app.register_blueprint(user_blueprint, url_prefix='/user')
    app.register_blueprint(audit_blueprint, url_prefix='/audit')
    app.register_blueprint(machineresolver_blueprint, url_prefix='/machineresolver')
    app.register_blueprint(machine_blueprint, url_prefix='/machine')
    app.register_blueprint(application_blueprint, url_prefix='/application')
    app.register_blueprint(caconnector_blueprint, url_prefix='/caconnector')
    app.register_blueprint(cert_blueprint, url_prefix='/certificate')
    app.register_blueprint(ttype_blueprint, url_prefix='/ttype')
    app.register_blueprint(register_blueprint, url_prefix='/register')
    app.register_blueprint(smtpserver_blueprint, url_prefix='/smtpserver')
    app.register_blueprint(recover_blueprint, url_prefix='/recover')
    app.register_blueprint(radiusserver_blueprint, url_prefix='/radiusserver')
    app.register_blueprint(periodictask_blueprint, url_prefix='/periodictask')
    app.register_blueprint(privacyideaserver_blueprint, url_prefix='/privacyideaserver')
    app.register_blueprint(eventhandling_blueprint, url_prefix='/event')
    app.register_blueprint(smsgateway_blueprint, url_prefix='/smsgateway')
    app.register_blueprint(client_blueprint, url_prefix='/client')
    app.register_blueprint(subscriptions_blueprint, url_prefix='/subscriptions')
    app.register_blueprint(monitoring_blueprint, url_prefix='/monitoring')
    app.register_blueprint(tokengroup_blueprint, url_prefix='/tokengroup')
    app.register_blueprint(serviceid_blueprint, url_prefix='/serviceid')
    app.register_blueprint(container_blueprint, url_prefix='/container')
    app.register_blueprint(healthz_blueprint, url_prefix='/healthz')
    app.register_blueprint(info_blueprint, url_prefix='/info')


def _setup_logging(app, logging_config=DEFAULT_LOGGING_CONFIG):
    # Setup logging
    log_read_func = {
        'yaml': lambda x: logging.config.dictConfig(yaml.safe_load(open(x, 'r').read())),
        'cfg': lambda x: logging.config.fileConfig(x)
    }
    have_config = False
    log_exception = None
    log_config_file = app.config.get(ConfigKey.LOGCONFIG, DefaultConfigValues.LOGGING_CFG)
    if os.path.isfile(log_config_file):
        for cnf_type in ['cfg', 'yaml']:
            if app.config[ConfigKey.VERBOSE]:
                sys.stderr.write(f"Read Logging settings from {log_config_file}\n")
            try:
                log_read_func[cnf_type](log_config_file)
                have_config = True
                break
            except Exception as e:
                log_exception = e
                pass
    if not have_config:
        if log_exception:
            # We tried to read the logging configuration from a given file but failed
            sys.stderr.write(f"Could not use {ConfigKey.LOGCONFIG}: {log_exception}\n")
        if app.config[ConfigKey.VERBOSE]:
            sys.stderr.write(f"Using logging configuration {logging_config}.\n")
        logging.config.dictConfig(logging_config)


def _check_config(app: Flask):
    if ConfigKey.ENCFILE in app.config and Path(app.config[ConfigKey.ENCFILE]).is_file():
        # We have a proper encryption file to work with
        pass
    else:
        raise RuntimeError(f"'{ConfigKey.ENCFILE}' must be set and point to "
                           f"a file with the database encryption key!")
    if ConfigKey.PEPPER not in app.config:
        raise RuntimeError(f"'{ConfigKey.PEPPER}' must be defined in the app configuration")
    if ConfigKey.SECRET_KEY not in app.config or not app.config[ConfigKey.SECRET_KEY]:
        sys.stderr.write(f"'{ConfigKey.SECRET_KEY}' not defined in the app "
                         f"configuration! Generating a random key.\n")
        app.config[ConfigKey.SECRET_KEY] = secrets.token_hex()
    if not all([x in app.config for x in [ConfigKey.AUDIT_KEY_PUBLIC, ConfigKey.AUDIT_KEY_PRIVATE]]):
        sys.stderr.write("No keypair for audit signing defined. Disabling audit signing "
                         "and response signing!\n")
        app.config[ConfigKey.AUDIT_NO_SIGN] = True
        app.config[ConfigKey.NO_RESPONSE_SIGN] = True


def _setup_node_configuration(app: Flask):
    # check that we have a correct node_name -> UUID relation
    with app.app_context():
        # TODO: this is not multi-process-safe since every process runs its own `create_app()`
        # First check if we have a UUID in the config file which takes precedence
        try:
            pi_uuid = uuid.UUID(app.config.get(ConfigKey.NODE_UUID))
        except (ValueError, TypeError) as e:
            log.debug(f"Could not determine UUID from config: {e}")
            # check if we can get the UUID from an external file
            pi_uuid_file = app.config.get(ConfigKey.UUID_FILE, DefaultConfigValues.UUID_FILE)
            try:
                with open(pi_uuid_file) as f:
                    pi_uuid = uuid.UUID(f.read().strip())
            except Exception as e:  # pragma: no cover
                log.debug(f"Could not determine UUID from file '{pi_uuid_file}': {e}")

                # we try to get the unique installation id (See <https://0pointer.de/blog/projects/ids.html>)
                try:
                    with open("/etc/machine-id") as f:
                        pi_uuid = uuid.UUID(f.read().strip())
                except Exception as e:  # pragma: no cover
                    log.debug(f"Could not determine the machine id: {e}")
                    # we generate a random UUID which will change on every startup
                    # unless it is persisted to the pi_uuid_file
                    pi_uuid = uuid.uuid4()
                    log.warning(f"Generating a random UUID: {pi_uuid}! If "
                                f"persisting the UUID fails, it will change on every application start")
                    # only in case of a generated UUID we save it to the uuid file
                    try:
                        with open(pi_uuid_file, 'w') as f:  # pragma: no cover
                            f.write(f"{str(pi_uuid)}\n")
                            log.info(f"Successfully wrote current UUID to file '{pi_uuid_file}'")
                    except IOError as exx:
                        log.warning(f"Could not write UUID to file '{pi_uuid_file}': {exx}")

            app.config[ConfigKey.NODE_UUID] = str(pi_uuid)
            log.debug(f"Current UUID: '{pi_uuid}'")

        pi_node_name = app.config.get(ConfigKey.NODE) or app.config.get(ConfigKey.AUDIT_SERVERNAME,
                                                                        DefaultConfigValues.NODE_NAME)

        inspect = sa.inspect(db.get_engine())
        if inspect.has_table(NodeName.__tablename__):
            db.session.merge(NodeName(id=str(pi_uuid),
                                      name=pi_node_name,
                                      lastseen=datetime.datetime.now(datetime.timezone.utc)))
            db.session.commit()
        else:
            log.warning(f"Could not update node names in db. "
                        f"Check that table '{NodeName.__tablename__}' exists.")
        log.debug("Finished setting up node names.")


def create_app(config_name="development",
               config_file=DefaultConfigValues.CFG_PATH,
               silent=False, initialize_hsm=False) -> Flask:
    """
    First the configuration from the config.py is loaded depending on the
    config type like "production" or "development" or "testing".

    Then the environment variable PRIVACYIDEA_CONFIGFILE is checked for a
    config file, that contains additional settings, that will overwrite the
    default settings from config.py

    :param config_name: The config name like "production" or "testing"
    :type config_name: basestring
    :param config_file: The name of a config file to read configuration from
    :type config_file: basestring
    :param silent: If set to True the additional information are not printed
        to stdout
    :type silent: bool
    :param initialize_hsm: Whether the HSM should be initialized on app startup
    :type initialize_hsm: bool
    :return: The flask application
    :rtype: App object
    """
    app = Flask(__name__, static_folder=DefaultConfigValues.STATIC_FOLDER,
                template_folder=DefaultConfigValues.TEMPLATE_FOLDER)
    app.config[ConfigKey.APP_READY] = False
    app.config[ConfigKey.VERBOSE] = not silent

    # Routed apps must fall back to index.html
    @app.errorhandler(404)
    def fallback(error):
        if request.path.startswith("/app/v2/"):
            index_html = app.config.get("PI_INDEX_HTML") or "index.html"
            return send_html(
                render_template(
                    index_html))
        return jsonify(error="Not found"), 404

    # Overwrite default config with environment setting
    config_name = os.environ.get(ConfigKey.CONFIG_NAME, config_name)
    if app.config.get(ConfigKey.VERBOSE):
        print("The configuration name is: {0!s}".format(config_name))
    app.config.from_object(config[config_name])

    # Load configuration from environment variables prefixed with PRIVACYIDEA_
    app.config.from_prefixed_env("PRIVACYIDEA")

    if ENV_KEY in os.environ:
        config_file = os.environ[ENV_KEY]
    if app.config.get(ConfigKey.VERBOSE):
        print("Additional configuration will be read from the file {0!s}".format(config_file))

    try:
        # Try to load the given config_file.
        app.config.from_pyfile(config_file, silent=False)
    except IOError as e:
        if config_name != "docker" or ENV_KEY in os.environ:
            sys.stderr.write("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
            sys.stderr.write("  WARNING: Unable to load additional configuration\n")
            sys.stderr.write(f"  from {config_file}!\n")
            if app.config.get(ConfigKey.VERBOSE):
                sys.stderr.write(f"  ({e})\n")
            sys.stderr.write("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")

    # Setup logging
    if config_name == "docker":
        if ConfigKey.LOGLEVEL in app.config:
            DOCKER_LOGGING_CONFIG["loggers"]["privacyidea"]["level"] = app.config.get(ConfigKey.LOGLEVEL)
        _setup_logging(app, DOCKER_LOGGING_CONFIG)
    else:
        if ConfigKey.LOGLEVEL in app.config:
            DEFAULT_LOGGING_CONFIG["loggers"]["privacyidea"]["level"] = app.config.get(ConfigKey.LOGLEVEL)
        if ConfigKey.LOGFILE in app.config:
            DEFAULT_LOGGING_CONFIG["handlers"]["file"]["filename"] = app.config.get(ConfigKey.LOGFILE)
        _setup_logging(app, DEFAULT_LOGGING_CONFIG)

    # We allow to set different static folders
    app.static_folder = app.config.get(ConfigKey.STATIC_FOLDER, DefaultConfigValues.STATIC_FOLDER)
    app.template_folder = app.config.get(ConfigKey.TEMPLATE_FOLDER, DefaultConfigValues.TEMPLATE_FOLDER)

    _register_blueprints(app)

    # Set up Plug-Ins
    db.init_app(app)

    # TODO: This is not necessary except for the pi-manage command line util
    # Try to get the path of the migration directory from the installed package
    # TODO: This still does not work with an editable installation if it is not called from the source folder
    # By default, we assume we are in the source folder
    migration_dir = "privacyidea/migrations"
    try:
        migration_path = [f for f in metadata.files("privacyidea") if f.match("migrations/env.py")][0]
        migration_dir = str(migration_path.locate().parent.resolve())
    except (PackageNotFoundError, IndexError):
        pass
    migrate.init_app(app, db, directory=migration_dir)

    Versioned(app, format='%(path)s?v=%(version)s')

    babel.init_app(app, locale_selector=get_accepted_language)

    queue.register_app(app)

    if initialize_hsm:
        with app.app_context():
            init_hsm()

    _setup_node_configuration(app)

    # SQLAlchemy Oracle dialect does not (yet) support JSON serializers
    with app.app_context():
        engine = db.session.get_bind()
        if engine.name == "oracle":
            engine.dialect._json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False)
            engine.dialect._json_deserializer=lambda obj: json.loads(obj)

    log.debug(f"Reading application from the static folder {app.static_folder} "
              f"and the template folder {app.template_folder}")
    app.config[ConfigKey.APP_READY] = True

    def exit_func():
        # Destroy the engine pool and close all open database connections on exit
        with app.app_context():
            db.engine.dispose()

    atexit.register(exit_func)

    return app


def create_docker_app():
    """
    Create a Flask-app for docker deployment.
    The app is configured exclusively through environment variables and secret
    files via docker-compose.
    """
    app = Flask(__name__)
    app.config[ConfigKey.APP_READY] = False
    app.config[ConfigKey.VERBOSE] = bool(app.debug)

    # Begin the app configuration
    # First we load a default configuration
    if app.debug:
        sys.stderr.write(f"Reading default config: {DockerConfig}\n")
    app.config.from_object(DockerConfig)
    # Then we check if a config file is present in /etc/privacyidea/pi.cfg
    # (either mounted or built into the container image)
    try:
        app.config.from_pyfile(DefaultConfigValues.CFG_PATH, silent=False)
        if app.debug:
            sys.stderr.write(f"Read configuration from file: '{DefaultConfigValues.CFG_PATH}'\n")
    except IOError as _e:
        pass
    # Then we update the configuration with stuff from the environment
    if app.debug:
        sys.stderr.write("Reading configuration from environment with prefix 'PRIVACYIDEA'\n")
    app.config.from_prefixed_env("PRIVACYIDEA")

    # And then we check if we have a minimal viable config
    _check_config(app)

    if app.debug:
        DOCKER_LOGGING_CONFIG["loggers"]["privacyidea"]["level"] = logging.DEBUG
    if ConfigKey.LOGLEVEL in app.config:
        DOCKER_LOGGING_CONFIG["loggers"]["privacyidea"]["level"] = app.config.get(ConfigKey.LOGLEVEL)
    _setup_logging(app, DOCKER_LOGGING_CONFIG)

    # We allow to set different static folders
    app.static_folder = app.config.get(ConfigKey.STATIC_FOLDER, DefaultConfigValues.STATIC_FOLDER)
    app.template_folder = app.config.get(ConfigKey.TEMPLATE_FOLDER, DefaultConfigValues.TEMPLATE_FOLDER)

    _register_blueprints(app)

    # Set up Plug-Ins
    db.init_app(app)

    Versioned(app, format='%(path)s?v=%(version)s')

    babel.init_app(app, locale_selector=get_accepted_language)

    queue.register_app(app)

    if app.config.get(ConfigKey.HSM_INITIALIZE, False):
        with app.app_context():
            init_hsm()

    # Check database connection
    with app.app_context():
        try:
            log.debug("Test Database using URL '%s'", app.config[ConfigKey.SQLALCHEMY_DATABASE_URI])
            db.session.execute(sa.text('SELECT 1'))
            log.debug("Database Connection successful!")
        except Exception as e:
            raise RuntimeError(f"Could not connect to database: {e}")

    _setup_node_configuration(app)

    app.config[ConfigKey.APP_READY] = True

    def exit_func():
        # Destroy the engine pool and close all open database connections on exit
        with app.app_context():
            db.engine.dispose()

    atexit.register(exit_func)

    return app
