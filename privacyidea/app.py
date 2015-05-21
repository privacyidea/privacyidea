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
import logging
from flask import Flask
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
from privacyidea.api.auth import jwtauth
from privacyidea.webui.login import login_blueprint
from privacyidea.webui.certificate import cert_blueprint
from privacyidea.api.machineresolver import machineresolver_blueprint
from privacyidea.api.machine import machine_blueprint
from privacyidea.lib.log import SecureFormatter
from privacyidea.config import config
from privacyidea.models import db
from flask.ext.migrate import Migrate

ENV_KEY="PRIVACYIDEA_CONFIGFILE"
MY_LOG_FORMAT = "[%(asctime)s][%(process)d][%(thread)d][%(levelname)s][%(" \
                "name)s:%(lineno)d] %(message)s"


def create_app(config_name="development",
               config_file='/etc/privacyidea/pi.cfg'):
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
    :return: The flask application
    :rtype: App object
    """
    print "The configuration name is: %s" % config_name
    print "Additional configuration can be read from the file %s" % config_file
    if os.environ.get(ENV_KEY):
        print("Additional configuration can be read from "
              "the file %s" % os.environ[ENV_KEY])
    app = Flask(__name__, static_folder="static",
                template_folder="static/templates")
    if config_name:
        app.config.from_object(config[config_name])

    try:
        # Try to load the given config_file.
        # If it does not exist, just ignore it.
        app.config.from_pyfile(config_file, silent=True)
    except IOError:
        print 50*"!"
        print "  WARNING: privacyidea create_app has no access"
        print "  to %s!" % config_file
        print 50*"!"

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
    db.init_app(app)
    migrate = Migrate(app, db)

    # Create the logger
    # Read log file from config
    from logging import handlers
    fhandler = handlers.RotatingFileHandler(app.config.get("PI_LOGFILE",
                                                           "privacyidea.log"),
                                            backupCount=4,
                                            maxBytes=10000000)


    formatter = SecureFormatter(MY_LOG_FORMAT)
    # Set the formatter
    fhandler.setFormatter(formatter)
    # read level from config
    fhandler.setLevel(app.config.get("PI_LOGLEVEL", logging.INFO))
    logging.getLogger("privacyidea").addHandler(fhandler)

    return app
