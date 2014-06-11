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
This is the controller for the openid service
'''


ASSOC_EXPIRES_IN = 3600
COOKIE_NAME = "privacyidea_openid"


import logging

import webob
import traceback



from pylons import tmpl_context as c
from pylons import request, response
from pylons.controllers.util import redirect
from pylons import config
from pylons import url as url

from privacyidea.lib.base import BaseController

from privacyidea.lib.util import  getParam
from privacyidea.weblib.util import get_client
from privacyidea.lib.util import  is_valid_fqdn
from privacyidea.lib.user import  getUserFromParam
from privacyidea.lib.realm import  getDefaultRealm
from privacyidea.lib.realm import getRealms
from privacyidea.lib.user     import getRealmBox
from privacyidea.lib.util    import get_version
from privacyidea.lib.util    import get_copyright_info

from privacyidea.lib.policy import PolicyException
from pylons.templating import render_mako as render
from webob.exc import HTTPBadRequest


from privacyidea.lib.token import checkUserPass
from privacyidea.lib.reply import sendError
from privacyidea.model.meta import Session

from privacyidea.lib.openid import IdResMessage
from privacyidea.lib.openid import create_association, check_authentication

from privacyidea.lib.openid import OPENID_2_0_TYPE
from privacyidea.lib.openid import OPENID_1_0_TYPE
from privacyidea.lib.log import log_with

from urllib import urlencode


optional = True
required = False

log = logging.getLogger(__name__)

class OpenidController(BaseController):

    '''
    this is the controller for doing the openid stuff

        https://server/openid/<functionname>

    '''
    BASEURL = "https://privacyideaserver"
    COOKIE_EXPIRE = 3600

    @log_with(log)
    def __before__(self, action, **params):
        valid_request = False
        try:
            for key, value in params.items():
                log.debug("%r:%r]" % (key, value))

            c.audit['client'] = get_client()

            self.storage = config.get('openid_sql')

            getCookieExpire = int(config.get("privacyideaOpenID.CookieExpire", -1))

            self.COOKIE_EXPIRE = 3600
            if getCookieExpire >= 0:
                self.COOKIE_EXPIRE = getCookieExpire

            c.logged_in = False
            c.login = ""
            c.version = get_version()
            c.licenseinfo = get_copyright_info()

            http_host = request.environ.get("HTTP_HOST")
            log.debug("Doing openid request from host %s" % http_host)
            if not is_valid_fqdn(http_host, split_port=True):
                err = "Bad hostname: %s" % http_host
                self.audit.log(c.audit)
                c.audit["action_detail"] = err
                log.error(err)
                raise HTTPBadRequest(err)

            self.BASEURL = request.environ.get("wsgi.url_scheme") + "://" + http_host

            # check if the browser is logged in
            login = request.cookies.get(COOKIE_NAME)

            if login:
                c.logged_in = True

            ## default return for the __before__ and __after__
            valid_request = True
            return response

        except PolicyException as pex:
            log.error("%r policy exception %r" % (action, pex))
            log.error(traceback.format_exc())
            return sendError(response, pex, context='before')

        except webob.exc.HTTPUnauthorized as acc:
            ## the exception, when an abort() is called if forwarded
            log.error("%r webob.exception %r" % (action, acc))
            log.error(traceback.format_exc())
            raise acc

        except Exception as exx:
            log.error("%r exception %r" % (action, exx))
            log.error(traceback.format_exc())
            return sendError(response, exx, context='before')

        finally:
            if valid_request is False:
                self.storage.session.rollback()
                self.storage.session.close()


    @log_with(log)
    def __after__(self, action, **params):
        try:
            self.audit.log(c.audit)
            self.storage.session.commit()
            ## default return for the __before__ and __after__
            return response

        except Exception as exx:
            log.error("%r" % (exx))
            log.error(traceback.format_exc())
            self.storage.session.rollback()
            return sendError(response, exx, context='after')

        finally:
            self.storage.session.close()


    def id(self):
        '''
        This method is used by the consumer to authenticate like this:
        https://server/openid/id/<user>

        The URL has to return this one in the html head:
        <link rel="openid.server" href="http://localhost.localdomain:8011/openidserver">
        <meta http-equiv="x-xrds-location" content="http://localhost.localdomain:8011/yadis/corny">

        The request flow is:
            -> GET /openid/id
            -> GET /openid/yadis
            -> POST /openid/openidserver -> assocication
            -> POST /openid/openidserver -> checkid setup

        '''
        user = request.environ['pylons.routes_dict'].get('id')
        log.debug("requesting access for user %s" % user)

        baseurl = self.BASEURL
        baseyadis = baseurl + "/openid/yadis/"
        endpoint = baseurl + "/openid/openidserver"

        response.content_type = 'text/html'
        head = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
  <meta http-equiv="Content-type" content="text/html;charset=UTF-8" />
  <link rel="openid.server" href="%s" />
  <meta http-equiv="x-xrds-location" content="%s%s" />
</head>
<body>This is used to issue the user names</body>
</html>''' % (endpoint, baseyadis, user)
        return head


    def yadis(self):
        user = request.environ['pylons.routes_dict'].get('id')
        response.content_type = 'application/xrds+xml'

        endpoint_url = self.BASEURL + "/openid/openidserver"
        user_url = self.BASEURL + "/openid/id/%s" % user

        body = """\
<?xml version="1.0" encoding="UTF-8"?>
<xrds:XRDS xmlns:xrds="xri://$xrds" xmlns="xri://$xrd*($v*2.0)">
  <XRD>
    <Service priority="0">
      <Type>%s</Type>
      <Type>%s</Type>
      <URI>%s</URI>
      <LocalID>%s</LocalID>
    </Service>
  </XRD>
</xrds:XRDS>
""" % (OPENID_2_0_TYPE, OPENID_1_0_TYPE, endpoint_url, user_url)

        return body

    @log_with(log)
    def openidserver(self, action, **params):
        '''
        This is the so called server endpoint, that decides, if the user is authenticated or not.
        and returns to the given "openid." either directly or after authenticating the user
        openid.claimed_id.
        '''

        req_method = request.environ.get('REQUEST_METHOD')

        if "POST" == req_method:
            params = request.environ.get('webob._parsed_post_vars')
            params = params[0]
        else:
            # we got a GET request
            params = request.params

        # distpatching the request depending on the mode
        if 'openid.mode' not in params:
            raise HTTPBadRequest('Missing "openid.mode"')

        mode = params.get('openid.mode')
        log.debug("openid.mode=%s" % mode)

        if 'associate' == mode:
            return self.associate(params)

        # mandatory fields for other actions
        for field in ('openid.identity',):  #, 'openid.'):
            if field not in params:
                raise HTTPBadRequest('Missing "%s"' % field)

        if 'check_authentication' == mode:
            return self.check_authentication(params)

        elif mode in ('checkid_setup', 'checkid_immediate'):

            authenticated = False
            c.login, token = self._split_cookie()
            if "" != c.login:
                # what user wants to login?
                rest, claimed_user = params.get("openid.claimed_id").rsplit("/", 1)
                stored_token = self.storage.get_user_token(c.login)

                log.debug("checking authenticated? %s=%s, %s=%s" %
                            (stored_token, token, c.login, claimed_user))

                if stored_token == token and self._compare_users(c.login, claimed_user):
                    authenticated = True

            if not authenticated:
                # Not logged in!
                redirect_to = self.BASEURL + "/openid/openidserver"
                openid_params = urlencode(params)
                redirect("/openid/login?%s&%s" % (urlencode({ "redirect_to" : redirect_to }), openid_params))
            else:
                return self.checkid_setup(params)

        # other modes are ignored
        raise HTTPBadRequest('"%s" mode not supported' % mode)


    def checkid_setup(self, param):
        '''
        This function is called, when the user needs to verify that he is willing to
        authenticate for a relying party
        '''
        params = {}
        params.update(param)

        HOST = self.BASEURL + "/openid/openidserver"
        message = IdResMessage(self.storage, HOST, 3600, **params)
        # signing it
        message.sign()

        # for checking trusted roots
        user, token = self._split_cookie()
        redirect_token = message.store_redirect()
        _url, site, handle = self.storage.get_redirect(redirect_token)
        trusted_roots = self.storage.get_trusted_roots(user)

        # was it called by the identity plugin ?
        if 'X-Identity' in request.headers:
            # storing the site in allowed sites
            message.store_site()
            # redirecting
            redirect(message.get_url())

        elif site in trusted_roots:
            login, token = self._split_cookie()
            user = self.storage.get_user_by_token(token)
            c.audit['user'], c.audit['realm'] = user.split('@', 2)
            c.audit['success'] = True
            c.audit['action_detail'] = site
            c.audit['info'] = "site found in trusted root"
            # automatic validate, i.e.
            # the user gets redirected to the relying party
            redirect_to = message.get_url()
            redirect(redirect_to)

        else:
            # if not, we store the redirect url and display
            # a manual screen the user needs to validate
            c.identity = message.identity
            c.redirect_token = redirect_token
            c.rely_party = message.site
            return render('/openid/check_setup.mako')


    @log_with(log)
    def checkid_submit(self, action, **params):
        '''
        This is called when the user accepts - hit the submit button - that he will login to the consumer
        '''
        param = request.params
        redirect_token = getParam(param, "redirect_token", required)
        verify_always = getParam(param, "verify_always", optional)
        r_url, site, handle = self.storage.get_redirect(redirect_token)
        self.storage.add_site(site, handle)

        # The user checked the box, that he wants not be bothered again in the future
        # the relying party will be added to the trusted root
        login, token = self._split_cookie()
        user = self.storage.get_user_by_token(token)
        c.audit['user'], c.audit['realm'] = user.split('@', 2)
        c.audit['success'] = True
        c.audit['action_detail'] = site

        if "always" == verify_always:
            log.debug("putting into trusted root: %s, %s" % (site, handle))
            if "" != user:
                self.storage.add_trusted_root(user, site)

        log.debug("redirecting to %s" % r_url)
        redirect(r_url)

    def check_authentication(self, params):
        res = check_authentication(**params)
        response.status = 200
        response.content_type = "text/plain"
        return res


    def associate(self, params):
        '''
        This sets up a association (encryption key) bewtween the ID Provider and the consumer
        '''
        expires_in = ASSOC_EXPIRES_IN
        res = create_association(self.storage, expires_in, **params)
        response.status = 200
        response.content_type = "text/plain"
        return res


######### Auth stuff #################################################
    def logout(self):
        '''
        This action deletes the cookie and redirects to the
        /openid/status to show the login status

        If the logout is called in the context of an openid authentication,
        the user is already logged in as a different user. In this case we
        forward to the /openid/login page after the logout was made.

        Another option for the openid authentication context would be to
        redirect to the return_to url by setting
            redirect_to = params["openid.return_to"]
            p["openid.mode"] = "setup_needed"
        which advises the openid relying party to restart the login process.
        '''

        response.delete_cookie(COOKIE_NAME)

        params = {}
        params.update(request.params)
        p = {}

        ## are we are called during an openid auth request?
        if "openid.return_to" in params:
            redirect_to = "/openid/login"
            p.update(params)
            do_redirect = url(str("%s?%s" % (redirect_to, urlencode(p))))

        else:
            redirect_to = "/openid/status"
            do_redirect = url(str("%s?%s" % (redirect_to, urlencode(p))))

        redirect(do_redirect)

    def login(self):
        '''
        This is the redirect of the first template
        '''
        param = request.params

        c.defaultRealm = getDefaultRealm()
        c.p = {}
        c.user = ""
        c.title = "privacyIDEA OpenID Service"

        for k in param:
            c.p[k] = param[k]
            if "openid.claimed_id" == k:
                c.user = param[k].rsplit("/", 1)[1]

        ## if we have already a cookie but
        ## a difference between login and cookie user
        ## we show (via  /status) that he is already logged in
        ## and that he first must log out
        cookie = request.cookies.get(COOKIE_NAME)
        if cookie is not None:
            cookie_user, token = cookie.split(":")

            if cookie_user != c.user:
                c.login = cookie_user
                c.message = ("Before logging in as >%s< you have to log out."
                             % (c.user))

                return render("/openid/status.mako")

        return render('/openid/login.mako')

    def status(self):
        '''
        This shows the login status.
        '''
        param = {}
        param.update(request.params)

        cookie = request.cookies.get(COOKIE_NAME)
        if cookie is not None:
            c.login, token = cookie.split(":")

        if "message" in param:
            c.message = param.get("message")

        return render("/openid/status.mako")


    @log_with(log)
    def check(self, action, **params):
        '''
        This function is used to login

        method:
            openid/check

        arguments:
            user     - user to login
            realm    - in which realm the user should login
            pass     - password

        returns:
            JSON response
        '''
        ok = False
        param = {}
        do_redirect = None
        message = None

        try:
            param.update(request.params)

            same_user = True
            passw = getParam(param, "pass", optional)

            ## getUserFromParam will return default realm if no realm is
            ## provided via @ append or extra parameter realm
            ## if the provided realm does not exist, the realm is left empty
            user = getUserFromParam(param, optional)

            ## if the requested user has a realm specified (via @realm append)
            ## and this is not the same as the user from getUserFromParam
            ## the requested user is not a valid one!
            p_user = param.get('user', '')
            if "@" in p_user:
                if p_user != "%s@%s" % (user.login, user.realm):
                    same_user = False

            c.audit['user'] = user.login
            c.audit['realm'] = user.realm or getDefaultRealm()

            if same_user is True:
                (ok, opt) = checkUserPass(user, passw)

            c.audit['success'] = ok

            if ok:
                ## if the user authenticated successfully we need to set the cookie aka
                ## the ticket and we need to remember this ticket.
                user = "%s@%s" % (user.login, c.audit['realm'])
                log.debug("user=%s" % user)
                token = self.storage.set_user_token(user, expire=self.COOKIE_EXPIRE)
                log.debug("token=%s" % token)
                cookie = "%s:%s" % (user, token)
                log.debug("cookie=%s" % cookie)
                response.set_cookie(COOKIE_NAME, cookie, max_age=self.COOKIE_EXPIRE)
            else:
                message = "Your login attempt was not successful!"

            Session.commit()
            # Only if we logged in successfully we redirect to the original
            # page (Servive Provider). Otherwise we will redirect to the
            # status page

            p = {}
            redirect_to = getParam(param, "redirect_to", optional)
            if redirect_to and ok:
                p = {}
                for k in  [ 'openid.return_to', "openid.realm", "openid.ns", "openid.claimed_id", "openid.mode",
                            "openid.identity" ]:
                    p[k] = param[k]
            else:
                if message is not None:
                    p["message"] = message
                redirect_to = "/openid/status"

            do_redirect = url(str("%s?%s" % (redirect_to, urlencode(p))))

        except Exception as exx:
            log.error("openid/check failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, "openid/check failed: %r" % exx, 0)

        finally:
            Session.close()

        if do_redirect:
            log.debug("now redirecting to %s" % do_redirect)
            redirect(do_redirect)

    def _compare_users(self, u1, u2):
        realm = getDefaultRealm()
        if len(u1.split('@')) == 1:
            u1 = "%s@%s" % (u1, realm)
        if len(u2.split('@')) == 1:
            u2 = "%s@%s" % (u2, realm)
        log.debug("%s == %s?" % (u1, u2))
        return u1 == u2


    def _split_cookie(self):
        login = ""
        token = ""
        cookie = request.cookies.get(COOKIE_NAME)
        if cookie is not None:
            login, token = cookie.split(":")
        return login, token

#eof###########################################################################
