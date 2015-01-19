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
from flask import Flask

from .api.validate import validate_blueprint
from .api.token import token_blueprint
from .api.system import system_blueprint
from .api.resolver import resolver_blueprint
from .api.realm import realm_blueprint
from .api.realm import defaultrealm_blueprint
from .api.policy import policy_blueprint
from .api.user import user_blueprint
from .api.auth import jwtauth
from .webui.login import login_blueprint
from config import config
from .models import db
from flask.ext.migrate import Migrate
from flask.ext.bootstrap import Bootstrap 


def create_app(config_name=None, var2=None):
    """
    First the configuration from the config.py is loaded depending on the
    config type like "Production" or "Development".

    Then the environment variable PRIVACYIDEA_CONFIGFILE is checked for a
    config file, that contains additional settings, that will overwrite the
    default settings from config.py

    :param config_name: The config name like "Production" or "Testing"
    :return: The flask application
    :rtype: App object
    """
    print "configname: %s" % config_name
    print "var2      : %s" % var2
    app = Flask(__name__, static_folder="static",
                template_folder="static/templates")
    if config_name:
        app.config.from_object(config[config_name])

    # Try to load the default config from /etc/privacyidea
    # If it does not exist, just ignore it.
    app.config.from_pyfile('/etc/privacyidea/pi.cfg', silent=True)
    # Try to load the file, that was specified in the environment variable
    # PRIVACYIDEA_CONFIG_FILE
    # If this file does not exist, we create an error!
    app.config.from_envvar('PRIVACYIDEA_CONFIGFILE', silent=True)

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
    
    db.init_app(app)
    migrate = Migrate(app, db)
    bootstrap = Bootstrap(app)
        
    return app

# We create this app to be used in the wsgi script
wsgi_app = create_app("production")
