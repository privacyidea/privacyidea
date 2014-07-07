# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
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
'''
This file is part of the privacyidea service
'''

"""Pylons middleware initialization"""
from beaker.middleware import CacheMiddleware
from paste.cascade import Cascade
from paste.registry import RegistryManager
from paste.urlparser import StaticURLParser
from paste.deploy.converters import asbool
from pylons import config
from pylons.middleware import ErrorHandler, StatusCodeRedirect
from pylons.wsgiapp import PylonsApp
from routes.middleware import RoutesMiddleware
from privacyidea.config.environment import load_environment

from repoze.who.middleware import PluggableAuthenticationMiddleware
from repoze.who.interfaces import IIdentifier
from repoze.who.interfaces import IChallenger
from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
from privacyidea.lib.repoze_identify import make_redirecting_plugin
from privacyidea.lib.repoze_auth import UserModelPlugin as auth_privacy_plugin
from repoze.who.plugins.basicauth import BasicAuthPlugin
from privacyidea.lib.auth import request_classifier
from repoze.who.classifiers import default_challenge_decider
from privacyidea.lib.crypto import geturandom
import logging

profile_load = False
try:
    from repoze.profile.profiler import AccumulatingProfileMiddleware
    profile_load = True
except ImportError:
    pass

COOKIE_TIMEOUT = 600

_LEVELS = {'debug': logging.DEBUG,
           'info': logging.INFO,
           'warning': logging.WARNING,
           'error': logging.ERROR,
          }


def make_app(global_conf, full_stack=True, static_files=True, **app_conf):
    """
    Create a Pylons WSGI application and return it

    ``global_conf``
        The inherited configuration for this application. Normally from
        the [DEFAULT] section of the Paste ini file.

    ``full_stack``
        Whether this application provides a full WSGI stack (by default,
        meaning it handles its own exceptions and errors). Disable
        full_stack when this application is "managed" by another WSGI
        middleware.

    ``static_files``
        Whether this application serves its own static files; disable
        when another web server is responsible for serving them.

    ``app_conf``
        The application's local configuration. Normally specified in
        the [app:<name>] section of the Paste ini file (where <name>
        defaults to main).

    """
    # Configure the Pylons environment
    load_environment(global_conf, app_conf)

    # The Pylons WSGI app
    app = PylonsApp()

    # Profiling Middleware
    if profile_load:
        if asbool(config['profile']):
            app = AccumulatingProfileMiddleware(
                app,
                log_filename='/var/log/privacyidea/profiling.log',
                cachegrind_filename='/var/log/privacyidea/cachegrind.out',
                discard_first_request=True,
                flush_at_shutdown=True,
                path='/__profile__'
            )

    # Routing/Session/Cache Middleware
    app = RoutesMiddleware(app, config['routes.map'])
    # We do not use beaker sessions! Keep the environment smaller.
    #app = SessionMiddleware(app, config)
    app = CacheMiddleware(app, config)

    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)

    if asbool(full_stack):
        # Handle Python exceptions
        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])

        # Display error documents for 401, 403, 404 status codes (and
        # 500 when debug is disabled)
        if asbool(config['debug']):
            app = StatusCodeRedirect(app)
        else:
            app = StatusCodeRedirect(app, [400, 401, 403, 404, 500])

    # Establish the Registry for this application
    app = RegistryManager(app)

    if asbool(static_files):
        # Serve static files
        static_app = StaticURLParser(config['pylons.paths']['static_files'])
        app = Cascade([static_app, app])

    # Add the repoze.who middleware
    # with a cookie encryption key, that is generated at every server start!
    cookie_timeout = int(global_conf.get("privacyIDEASessionTimout",
                                         COOKIE_TIMEOUT))
    cookie_reissue_time = int(cookie_timeout / 2)
    cookie_key = geturandom(32)
    privacyidea_auth = auth_privacy_plugin()
    basicauth = BasicAuthPlugin('repoze.who')
    privacyidea_md = auth_privacy_plugin()
    auth_tkt = AuthTktCookiePlugin(cookie_key,
                                   cookie_name='privacyidea_session',
                                   secure=True,
                                   include_ip=False,
                                   timeout=cookie_timeout,
                                   reissue_time=cookie_reissue_time)
    form = make_redirecting_plugin(login_form_url="/account/login",
                            login_handler_path='/account/dologin',
                            logout_handler_path='/account/logout',
                            rememberer_name="auth_tkt")
    # For authentication for browsers
    form.classifications = {IIdentifier: ['browser'],
                            IChallenger: ['browser']}
    # basic authentication only for API calls
    basicauth.classifications = {IIdentifier: ['basic'],
                                 IChallenger: ['basic']}
    identifiers = [('form', form),
                   ('auth_tkt', auth_tkt),
                   ('basicauth', basicauth)]
    authenticators = [('privacyidea.lib.repoze_auth:UserModelPlugin',
                       privacyidea_auth)]
    challengers = [('form', form),
                   ('basicauth', basicauth)]

    mdproviders = [('privacyidea.lib.repoze_auth:UserModelPlugin',
                    privacyidea_md)]

    #app = make_who_with_config(app, global_conf, app_conf['who.config_file'],
    #                     app_conf['who.log_file'], app_conf['who.log_level'])

    log_file = app_conf.get("who.log_file")
    if log_file is not None:
        if log_file.lower() == 'stdout':
            log_stream = None
        else:
            log_stream = open(log_file, 'wb')

    log_level = app_conf.get("who.log_level")
    if log_level is None:
        log_level = logging.INFO
    else:
        log_level = _LEVELS[log_level.lower()]

    app = PluggableAuthenticationMiddleware(
        app,
        identifiers,
        authenticators,
        challengers,
        mdproviders,
        request_classifier,
        default_challenge_decider,
        log_stream,
        log_level
        )

    return app
