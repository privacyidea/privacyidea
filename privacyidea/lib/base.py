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
'''The base Controller API

Provides the BaseController class for subclassing.
'''
import os

from pylons.i18n.translation import set_lang
from pylons.i18n import LanguageError

from pylons.controllers import WSGIController

from pylons import tmpl_context as c
from pylons import config
from pylons import request
from pylons import response

from privacyidea.lib.config import init_privacyIDEA_config
from privacyidea.lib.resolver import initResolvers
from privacyidea.lib.resolver import setupResolvers
from privacyidea.lib.resolver import closeResolvers

from privacyidea.model import meta
from privacyidea.lib.openid import SQLStorage
from privacyidea.model.meta import Session
from privacyidea import model

from privacyidea.lib.selftest import isSelfTest
from pylons.controllers.util import abort
from privacyidea.lib.util    import check_session
from privacyidea.lib.account    import is_admin_identity
from privacyidea.lib.user    import User
from privacyidea.lib.util    import getParam
from privacyidea.lib.log import log_with
from privacyidea.lib.audit import getAudit

ENCODING = "utf-8"

import logging
log = logging.getLogger(__name__)


@log_with(log)
def set_config(key, value, typ, description=None):
    '''
    create an intial config entry, if it does not exist

    :param key: the key
    :param value: the value
    :param description: the description of the key

    :return: nothing
    '''

    count = Session.query(model.Config).filter(
                        model.Config.Key == "privacyidea." + key).count()

    if count == 0:
        config_entry = model.Config(key, value, Type=typ, Description=description)
        Session.add(config_entry)

    return

@log_with(log)
def set_defaults():
    '''
    add privacyidea default config settings

    :return: - nothing -
    '''
    set_config(key=u"DefaultMaxFailCount",
        value=u"10", typ=u"int",
        description=u"The default maximum count for unsuccessful logins")

    set_config(key=u"DefaultCountWindow",
        value=u"10", typ=u"int",
        description=u"The default lookup window for tokens out of sync ")

    set_config(key=u"DefaultSyncWindow",
        value=u"1000", typ=u"int",
        description=u"The default lookup window for tokens out of sync ")

    set_config(key=u"DefaultChallengeValidityTime",
        value=u"120", typ=u"int",
        description=u"The default time, a challenge is regarded as valid.")

    set_config(key=u"DefaultResetFailCount",
        value=u"True", typ=u"bool",
        description=u"The default maximum count for unsucessful logins")

    set_config(key=u"DefaultOtpLen",
        value=u"6", typ=u"int",
        description=u"The default len of the otp values")

    set_config(key=u"PrependPin",
        value=u"True", typ=u"bool",
        description=u"is the pin prepended - most cases")

    set_config(key=u"FailCounterIncOnFalsePin",
        value=u"True", typ=u"bool",
        description=u"increment the FailCounter, if pin did not match")

    set_config(key=u"SMSProvider",
        value=u"smsprovider.HttpSMSProvider.HttpSMSProvider", typ=u"text",
        description=u"SMS Default Provider via HTTP")

    set_config(key=u"SMSProviderTimeout",
               value=u"300", typ=u"int",
               description=u"Timeout until registration must be done")

    set_config(key=u"SMSBlockingTimeout",
               value=u"30", typ=u"int",
               description=u"Delay until next challenge is created")

    set_config(key=u"DefaultBlockingTimeout",
               value=u"0", typ=u"int",
               description=u"Delay until next challenge is created")


    ## setup for totp defaults
    # "privacyidea.totp.timeStep";"60";"None";"None"
    # "privacyidea.totp.timeWindow";"600";"None";"None"
    # "privacyidea.totp.timeShift";"240";"None";"None"

    set_config(key=u"totp.timeStep",
        value=u"30", typ=u"int",
        description=u"Time stepping of the time based otp token ")

    set_config(key=u"totp.timeWindow",
        value=u"300", typ=u"int",
        description=u"Lookahead time window of the time based otp token ")

    set_config(key=u"totp.timeShift",
        value=u"0", typ=u"int",
        description=u"Shift between server and totp token")

    set_config(key=u"AutoResyncTimeout",
        value=u"240", typ=u"int",
        description=u"Autosync timeout for an totp token")

    ## setup for ocra defaults
    # OcraDefaultSuite
    # QrOcraDefaultSuite
    # OcraMaxChallenges
    # OcraChallengeTimeout

    set_config(key=u"OcraDefaultSuite",
        value=u"OCRA-1:HOTP-SHA256-8:C-QN08", typ=u"string",
        description=u"Default OCRA suite for an ocra token ")

    set_config(key=u"QrOcraDefaultSuite",
        value=u"OCRA-1:HOTP-SHA256-8:C-QA64", typ=u"int",
        description=u"Default OCRA suite for an ocra qr token ")

    set_config(key=u"OcraMaxChallenges",
        value=u"4", typ=u"int",
        description=u"Maximum open ocra challenges")

    set_config(key=u"OcraChallengeTimeout",
        value=u"300", typ=u"int",
        description=u"Timeout for an open ocra challenge")

    # emailtoken defaults
    set_config(key=u"EmailProvider",
               value="privacyidea.lib.emailprovider.SMTPEmailProvider", typ=u"string",
               description=u"Default EmailProvider class")
    set_config(key=u"EmailChallengeValidityTime",
               value="600", typ=u"int",
               description=u"Time that an e-mail token challenge stays valid (seconds)")
    set_config(key=u"EmailBlockingTimeout",
               value="120", typ=u"int",
               description=u"Time during which no new e-mail is sent out")


@log_with(log)
def setup_app(conf, conf_global=None, unitTest=False):
    '''
    setup_app is the hook, which is called, when the application is created

    :param conf: the application configuration

    :return: - nothing -
    '''
    if conf_global is not None:
        if conf_global.has_key("sqlalchemy.url"):
            log.info("sqlalchemy.url")
    else:
        conf.get("sqlalchemy.url", None)

    if unitTest is True:
        log.info("Deleting previous tables...")
        meta.metadata.drop_all(bind=meta.engine)

    ## Create the tables if they don't already exist
    log.info("Creating tables...")
    meta.metadata.create_all(bind=meta.engine)

    if conf.has_key("privacyideaSecretFile"):
        filename = conf.get("privacyideaSecretFile")
        try:
            with open(filename):
                pass
        except IOError:
            log.warning("The privacyIDEA Secret File could not be found " +
                        "-creating a new one: %s" % filename)
            f_handle = open(filename, 'ab+')
            secret = os.urandom(32 * 5)
            f_handle.write(secret)
            f_handle.close()
            os.chmod(filename, 0400)
        log.info("privacyideaSecretFile: %s" % filename)

    set_defaults()
    Session.commit()
    log.info("Successfully set up.")




class BaseController(WSGIController):
    """
    BaseController class - will be called with every request
    """

    def __init__(self, *args, **kw):
        """
        base controller constructor

        :param *args: generic argument array
        :param **kw: generic argument dict
        :return: None

        """
        self.parent = super(WSGIController, self)
        self.parent.__init__(*args, **kw)
        self.audit = getAudit()
        self.audit.initialize()

        # make the OpenID SQL Instance globally available
        openid_sql = config.get('openid_sql', None)
        if openid_sql is None:
            try:
                openid_storage = SQLStorage()
                config['openid_sql'] = openid_storage
            except Exception as exx:
                config['openid_sql'] = exx
                log.error("Failed to configure openid_sql: %r" % exx)

        app_setup_done = config.get('app_setup_done', False)
        if app_setup_done is False:
            try:
                setup_app(config)
                config['app_setup_done'] = True
            except Exception as exx:
                config['app_setup_done'] = False
                log.error("Failed to serve request: %r" % exx)
                raise exx

        l_config = init_privacyIDEA_config()

        resolver_setup_done = config.get('resolver_setup_done', False)
        if resolver_setup_done is False:
            try:
                cache_dir = config.get("app_conf", {}).get("cache_dir", None)
                setupResolvers(config=l_config, cache_dir=cache_dir)
                config['resolver_setup_done'] = True
            except Exception as exx:
                config['resolver_setup_done'] = False
                log.error("Failed to setup resolver: %r" % exx)
                raise exx

        initResolvers()
        
        # Add protection against click jacking
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        c.help_url = config.get('help_url')

        return

    def __call__(self, environ, start_response):
        '''Invoke the Controller'''
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']

        from privacyidea.lib.config      import getGlobalObject

        glo = getGlobalObject()
        sep = glo.security_provider

        try:
            hsm = sep.getSecurityModule()
            c.hsm = hsm
            ret = WSGIController.__call__(self, environ, start_response)
        finally:
            meta.Session.remove()
            ## free the lock on the scurityPovider if any
            sep.dropSecurityModule()
            closeResolvers()

        return ret

    @log_with(log)
    def before_identity_check(self, action="", check_admin=True):
        '''
        This is a function that can be called in the __before__ method to check the identity
        '''
        param = request.params
        if isSelfTest():
            log.debug("Doing selftest!")
            uuser = getParam(param, "selftest_user", True)
            if uuser is not None:
                (c.user, _foo, c.realm) = uuser.rpartition('@')
            else:
                c.realm = ""
                c.user = "--u--"
                env = request.environ
                uuser = env.get('REMOTE_USER')
                if uuser is not None:
                    (c.user, _foo, c.realm) = uuser.rpartition('@')

            self.authUser = User(c.user, c.realm, '')
            log.debug("authenticating as %s in realm %s!" % (c.user, c.realm))
        else:
            identity = request.environ.get('repoze.who.identity')
            if identity is None:
                abort(401, "You are not authenticated")

            log.debug("doing getAuthFromIdentity in action %s" % action)

            user_id = request.environ.get('repoze.who.identity').get('repoze.who.userid')
            if type(user_id) == unicode:
                user_id = user_id.encode(ENCODING)
            identity = user_id.decode(ENCODING)
            log.debug("getting identity from repoze.who: %r" % identity)

            (c.user, _foo, c.realm) = identity.rpartition('@')
            if check_admin:
                is_admin_identity(identity)
            self.authUser = User(c.user, c.realm, '')

            log.debug("set the self.authUser to: %s, %s " % (self.authUser.login, self.authUser.realm))
            log.debug('param for action %s: %s' % (action, param))

            # checking the session
            if (False == check_session(request)):
                c.audit['action'] = request.path[1:]
                c.audit['info'] = "session expired"
                self.audit.log(c.audit)
                abort(401, "No valid session")
            
    @log_with(log)
    def set_language(self):
        '''Invoke before everything else. And set the translation language'''
        languages = request.headers.get('Accept-Language', '').split(';')
        found_lang = False

        for language in languages:
            for lang in language.split(','):
                try:
                    if lang == "en":
                        found_lang = True
                        break
                    set_lang(lang)
                    found_lang = True
                    break
                except LanguageError as _exx:
                    pass

            if found_lang is True:
                break

        if found_lang is False:
            log.warning("Cannot set preferred language: %r" % languages)

        return

    def __enter__(self):
        pass
    def __exit__(self, typ, value, traceback):
        pass

###eof#########################################################################
