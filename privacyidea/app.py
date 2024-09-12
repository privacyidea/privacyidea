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
import datetime
import os
import os.path
import logging
import logging.config
import sys
import uuid

import yaml
from flask import Flask, request, Response
from flask_babel import Babel
from flask_migrate import Migrate
from flaskext.versioned import Versioned
import sqlalchemy as sa

# we need this import to add the before/after request function to the blueprints
# noinspection PyUnresolvedReferences
import privacyidea.api.before_after  # noqa: F401
from privacyidea.api.container import container_blueprint
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
from privacyidea.lib import queue
from privacyidea.lib.log import DEFAULT_LOGGING_CONFIG
from privacyidea.config import config
from privacyidea.models import db, NodeName
from privacyidea.lib.crypto import init_hsm


ENV_KEY = "PRIVACYIDEA_CONFIGFILE"

DEFAULT_UUID_FILE = "/etc/privacyidea/uuid.txt"

migrate = Migrate()


class PiResponseClass(Response):
    """Custom Response class overwriting the flask.Response.
    To avoid caching problems with the json property in the Response class,
    the property is overwritten using a non-caching approach.
    """
    @property
    def json(self):
        """This will contain the parsed JSON data if the mimetype indicates
        JSON (:mimetype:`application/json`, see :meth:`is_json`), otherwise it
        will be ``None``.
        Caching of the json data is disabled.
        """
        return self.get_json(cache=False)

    default_mimetype = 'application/json'


def create_app(config_name="development",
               config_file='/etc/privacyidea/pi.cfg',
               silent=False, initialize_hsm=False):
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
    if not silent:
        print("The configuration name is: {0!s}".format(config_name))
    if os.environ.get(ENV_KEY):
        config_file = os.environ[ENV_KEY]
    if not silent:
        print("Additional configuration will be read "
              "from the file {0!s}".format(config_file))
    app = Flask(__name__, static_folder="static",
                template_folder="static/templates")
    if config_name:
        app.config.from_object(config[config_name])

    try:
        # Try to load the given config_file.
        # If it does not exist, just ignore it.
        app.config.from_pyfile(config_file, silent=True)
    except IOError:
        sys.stderr.write("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        sys.stderr.write("  WARNING: privacyidea create_app has no access\n")
        sys.stderr.write("  to {0!s}!\n".format(config_file))
        sys.stderr.write("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")

    # Try to load the file, that was specified in the environment variable
    # PRIVACYIDEA_CONFIG_FILE
    # If this file does not exist, we create an error!
    app.config.from_envvar(ENV_KEY, silent=True)

    # We allow to set different static folders
    app.static_folder = app.config.get("PI_STATIC_FOLDER", "static/")
    app.template_folder = app.config.get("PI_TEMPLATE_FOLDER", "static/templates/")

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
    app.register_blueprint(machineresolver_blueprint,
                           url_prefix='/machineresolver')
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
    app.register_blueprint(privacyideaserver_blueprint,
                           url_prefix='/privacyideaserver')
    app.register_blueprint(eventhandling_blueprint, url_prefix='/event')
    app.register_blueprint(smsgateway_blueprint, url_prefix='/smsgateway')
    app.register_blueprint(client_blueprint, url_prefix='/client')
    app.register_blueprint(subscriptions_blueprint, url_prefix='/subscriptions')
    app.register_blueprint(monitoring_blueprint, url_prefix='/monitoring')
    app.register_blueprint(tokengroup_blueprint, url_prefix='/tokengroup')
    app.register_blueprint(serviceid_blueprint, url_prefix='/serviceid')
    app.register_blueprint(container_blueprint, url_prefix='/container')

    # Set up Plug-Ins
    db.init_app(app)
    migrate.init_app(app, db)

    Versioned(app, format='%(path)s?v=%(version)s')

    babel = Babel()
    babel.init_app(app)

    @babel.localeselector
    def get_locale():
        return get_accepted_language(request)

    app.response_class = PiResponseClass

    # Setup logging
    log_read_func = {
        'yaml': lambda x: logging.config.dictConfig(yaml.safe_load(open(x, 'r').read())),
        'cfg': lambda x: logging.config.fileConfig(x)
    }
    have_config = False
    log_exx = None
    log_config_file = app.config.get("PI_LOGCONFIG", "/etc/privacyidea/logging.cfg")
    if os.path.isfile(log_config_file):
        for cnf_type in ['cfg', 'yaml']:
            try:
                log_read_func[cnf_type](log_config_file)
                if not silent:
                    print('Read Logging settings from {0!s}'.format(log_config_file))
                have_config = True
                break
            except Exception as exx:
                log_exx = exx
                pass
    if not have_config:
        if log_exx:
            sys.stderr.write("Could not use PI_LOGCONFIG: " + str(log_exx) + "\n")
        if not silent:
            sys.stderr.write("Using PI_LOGLEVEL and PI_LOGFILE.\n")
        level = app.config.get("PI_LOGLEVEL", logging.INFO)
        # If there is another logfile in pi.cfg we use this.
        logfile = app.config.get("PI_LOGFILE", '/var/log/privacyidea/privacyidea.log')
        if not silent:
            sys.stderr.write("Using PI_LOGLEVEL {0!s}.\n".format(level))
            sys.stderr.write("Using PI_LOGFILE {0!s}.\n".format(logfile))
        DEFAULT_LOGGING_CONFIG["handlers"]["file"]["filename"] = logfile
        DEFAULT_LOGGING_CONFIG["handlers"]["file"]["level"] = level
        DEFAULT_LOGGING_CONFIG["loggers"]["privacyidea"]["level"] = level
        logging.config.dictConfig(DEFAULT_LOGGING_CONFIG)

    log = logging.getLogger(__name__)

    queue.register_app(app)

    if initialize_hsm:
        with app.app_context():
            init_hsm()

    # check that we have a correct node_name -> UUID relation
    with app.app_context():
        # first check if we have a UUID in the config file which takes precedence
        try:
            pi_uuid = uuid.UUID(app.config.get("PI_NODE_UUID", ""))
        except ValueError as e:
            log.debug(f"Could not determine UUID from config: {e}")
            # check if we can get the UUID from an external file
            pi_uuid_file = app.config.get('PI_UUID_FILE', DEFAULT_UUID_FILE)
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
                        with open(pi_uuid_file, 'a') as f:  # pragma: no cover
                            f.write(f"{str(pi_uuid)}\n")
                            log.info(f"Successfully wrote current UUID to file '{pi_uuid_file}'")
                    except IOError as exx:
                        log.warning(f"Could not write UUID to file '{pi_uuid_file}': {exx}")

            app.config["PI_NODE_UUID"] = str(pi_uuid)
            log.debug(f"Current UUID: '{pi_uuid}'")

        pi_node_name = app.config.get("PI_NODE") or app.config.get("PI_AUDIT_SERVERNAME", "localnode")

        insp = sa.inspect(db.get_engine())
        if insp.has_table(NodeName.__tablename__):
            db.session.merge(NodeName(id=str(pi_uuid), name=pi_node_name,
                                      lastseen=datetime.datetime.utcnow()))
            db.session.commit()
        else:
            log.warning(f"Could not update node names in db. "
                        f"Check that table '{NodeName.__tablename__}' exists.")

    log.debug(f"Reading application from the static folder {app.static_folder} "
              f"and the template folder {app.template_folder}")

    return app
