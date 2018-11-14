# -*- coding: utf-8 -*-
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
import os
import os.path
import logging
import logging.config
import sys
from flask import Flask, request
from privacyidea.lib import queue

import privacyidea.api.before_after
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
from privacyidea.webui.login import login_blueprint
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
from privacyidea.lib.log import DEFAULT_LOGGING_CONFIG
from privacyidea.config import config
from privacyidea.models import db
from flask_migrate import Migrate
from flask_babel import Babel


ENV_KEY = "PRIVACYIDEA_CONFIGFILE"
MY_LOG_FORMAT = "[%(asctime)s][%(process)d][%(thread)d][%(levelname)s][%(" \
                "name)s:%(lineno)d] %(message)s"

PI_LOGGING_CONFIG = {
    "version": 1,
    "formatters": {"detail": {"class":
                                  "privacyidea.lib.log.SecureFormatter",
                              "format": "[%(asctime)s][%(process)d]"
                                        "[%(thread)d][%(levelname)s]"
                                        "[%(name)s:%(lineno)d] "
                                        "%(message)s"}
                   },
    "handlers": {"file": {"formatter": "detail",
                          "class":
                              "logging.handlers.RotatingFileHandler",
                          "backupCount": 5,
                          "maxBytes": 10000000,
                          "level": logging.DEBUG,
                          "filename": "/var/log/privacyidea/privacyidea.log"}
                 },
    "loggers": {"privacyidea": {"handlers": ["file"],
                                "qualname": "privacyidea",
                                "level": logging.DEBUG}
                }
}


def create_app(config_name="development",
               config_file='/etc/privacyidea/pi.cfg',
               silent=False):
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
    :return: The flask application
    :rtype: App object
    """
    if not silent:
        print("The configuration name is: {0!s}".format(config_name))
    if os.environ.get(ENV_KEY):
        config_file = os.environ[ENV_KEY]
    if not silent:
        print("Additional configuration can be read from the file {0!s}".format(
              config_file))
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
    db.init_app(app)
    migrate = Migrate(app, db)


    try:
        # Try to read logging config from file
        log_config_file = app.config.get("PI_LOGCONFIG",
                                         "/etc/privacyidea/logging.cfg")
        if os.path.isfile(log_config_file):
            logging.config.fileConfig(log_config_file)
            if not silent:
                print("Reading Logging settings from {0!s}".format(log_config_file))
        else:
            raise Exception("The config file specified in PI_LOGCONFIG does "
                            "not exist.")
    except Exception as exx:
        if not silent:
            sys.stderr.write("{0!s}\n".format(exx))
            sys.stderr.write("Could not use PI_LOGCONFIG. "
                             "Using PI_LOGLEVEL and PI_LOGFILE.\n")
        level = app.config.get("PI_LOGLEVEL", logging.DEBUG)
        # If there is another logfile in pi.cfg we use this.
        logfile = app.config.get("PI_LOGFILE")
        if logfile:
            if not silent:
                sys.stderr.write("Using PI_LOGLEVEL {0!s}.\n".format(level))
                sys.stderr.write("Using PI_LOGFILE {0!s}.\n".format(logfile))
            PI_LOGGING_CONFIG["handlers"]["file"]["filename"] = logfile
            PI_LOGGING_CONFIG["handlers"]["file"]["level"] = level
            PI_LOGGING_CONFIG["loggers"]["privacyidea"]["level"] = level
            logging.config.dictConfig(PI_LOGGING_CONFIG)
        else:
            if not silent:
                sys.stderr.write("No PI_LOGFILE found. Using default "
                                  "config.\n")
            logging.config.dictConfig(DEFAULT_LOGGING_CONFIG)

    babel = Babel(app)

    @babel.localeselector
    def get_locale():
        # if we are not in the request context, return None to use the default
        # locale
        if not request:
            return None
        # otherwise try to guess the language from the user accept
        # header the browser transmits.  We support de/fr/en in this
        # example.  The best match wins.
        return request.accept_languages.best_match(['de',
                                                    'fr', 'it', 'es', 'en'])

    queue.register_app(app)

    return app

