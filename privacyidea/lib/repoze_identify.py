# -*- coding: utf-8 -*-
#
#  2010 - 2014 LSE Leading Security Experts GmbH
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
#
# based on repoze/who/plugins/form.py
#
# Author: Agendaless Consulting <repoze-dev@lists.repoze.org>
#
#
# Copyright: Copyright © 2007 Agendaless Consulting and Contributors
# License:
#   A copyright notice accompanies this license document that identifies
#   the copyright holders.
#  
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are
#   met:
#  
#   1.  Redistributions in source code must retain the accompanying
#       copyright notice, this list of conditions, and the following
#       disclaimer.
#  
#   2.  Redistributions in binary form must reproduce the accompanying
#       copyright notice, this list of conditions, and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#  
#   3.  Names of the copyright holders must not be used to endorse or
#       promote products derived from this software without prior
#       written permission from the copyright holders.
#  
#   4.  If any files are modified, you must cause the modified files to
#       carry prominent notices stating that you changed the files and
#       the date of any change.
#  
#   Disclaimer
#  
#     THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND
#     ANY EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
#     TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
#     PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#     HOLDERS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#     EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
#     TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#     DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#     ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
#     TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
#     THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
#     SUCH DAMAGE.

import urlparse
import urllib
import cgi

from paste.httpheaders import CONTENT_LENGTH
from paste.httpheaders import CONTENT_TYPE
from paste.httpheaders import LOCATION
from paste.httpexceptions import HTTPFound
from paste.httpexceptions import HTTPUnauthorized

from paste.request import parse_dict_querystring
from paste.request import parse_formvars
from paste.request import construct_url

from paste.response import header_value

from zope.interface import implements

from repoze.who.config import _resolve
from repoze.who.interfaces import IChallenger
from repoze.who.interfaces import IIdentifier

_DEFAULT_FORM = """
<html>
<head>
  <title>Log In</title>
</head>
<body>
  <div>
     <b>Log In</b>
  </div>
  <br/>
  <form method="POST" action="?__do_login=true">
    <table border="0">
    <tr>
      <td>User Name</td>
      <td><input type="text" name="login"></input></td>
    </tr>
    <tr>
      <td>Password</td>
      <td><input type="password" name="password"></input></td>
    </tr>
    <tr>
      <td></td>
      <td><input type="submit" name="submit" value="Log In"/></td>
    </tr>
    </table>
  </form>
  <pre>
  </pre>
</body>
</html>
"""

class FormPluginBase(object):
    def _get_rememberer(self, environ):
        rememberer = environ['repoze.who.plugins'][self.rememberer_name]
        return rememberer

    # IIdentifier
    def remember(self, environ, identity):
        rememberer = self._get_rememberer(environ)
        return rememberer.remember(environ, identity)

    # IIdentifier
    def forget(self, environ, identity):
        rememberer = self._get_rememberer(environ)
        return rememberer.forget(environ, identity)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__,
                            id(self))  #pragma NO COVERAGE

class FormPlugin(FormPluginBase):

    implements(IChallenger, IIdentifier)

    def __init__(self, login_form_qs, rememberer_name, formbody=None,
                 formcallable=None):
        self.login_form_qs = login_form_qs
        # rememberer_name is the name of another configured plugin which
        # implements IIdentifier, to handle remember and forget duties
        # (ala a cookie plugin or a session plugin)
        self.rememberer_name = rememberer_name
        self.formbody = formbody
        self.formcallable = formcallable

    # IIdentifier
    def identify(self, environ):
        query = parse_dict_querystring(environ)
        # If the extractor finds a special query string on any request,
        # it will attempt to find the values in the input body.
        if query.get(self.login_form_qs):
            form = parse_formvars(environ)
            from StringIO import StringIO
            # XXX we need to replace wsgi.input because we've read it
            # this smells funny
            environ['wsgi.input'] = StringIO()
            form.update(query)
            try:
                login = form['login']
                password = form['password']
                realm = form['realm']
            except KeyError:
                return None
            del query[self.login_form_qs]
            environ['QUERY_STRING'] = urllib.urlencode(query)
            environ['repoze.who.application'] = HTTPFound(
                                                    construct_url(environ))
            credentials = {'login':login, 'password':password, 'realm':realm}
            max_age = form.get('max_age', None)
            if max_age is not None:
                credentials['max_age'] = max_age
            return credentials

        return None

    # IChallenger
    def challenge(self, environ, status, app_headers, forget_headers):
        if app_headers:
            location = LOCATION(app_headers)
            if location:
                headers = list(app_headers) + list(forget_headers)
                return HTTPFound(headers=headers)

        form = self.formbody or _DEFAULT_FORM
        if self.formcallable is not None:
            form = self.formcallable(environ)
        def auth_form(environ, start_response):
            content_length = CONTENT_LENGTH.tuples(str(len(form)))
            content_type = CONTENT_TYPE.tuples('text/html')
            headers = content_length + content_type + forget_headers
            start_response('200 OK', headers)
            return [form]

        return auth_form

class RedirectingFormPlugin(FormPluginBase):

    implements(IChallenger, IIdentifier)

    def __init__(self, login_form_url, login_handler_path, logout_handler_path,
                 rememberer_name, reason_param='reason'):
        self.login_form_url = login_form_url
        self.login_handler_path = login_handler_path
        self.logout_handler_path = logout_handler_path
        # rememberer_name is the name of another configured plugin which
        # implements IIdentifier, to handle remember and forget duties
        # (ala a cookie plugin or a session plugin)
        self.rememberer_name = rememberer_name
        self.reason_param = reason_param

    # IIdentifier
    def identify(self, environ):
        path_info = environ['PATH_INFO']
        query = parse_dict_querystring(environ)

        if path_info == self.logout_handler_path:
            # we've been asked to perform a logout
            form = parse_formvars(environ)
            form.update(query)
            referer = environ.get('HTTP_REFERER', '/')
            environ['repoze.who.application'] = HTTPUnauthorized()
            return None

        elif path_info == self.login_handler_path:
            # we've been asked to perform a login
            form = parse_formvars(environ)
            form.update(query)
            try:
                max_age = form.get('max_age', None)
                credentials = {
                    'login':form['login'],
                    'password':form['password'],
                    'realm':form['realm'],
                    }
            except KeyError:
                credentials = None

            if credentials is not None:
                max_age = form.get('max_age', None)
                if max_age is not None:
                    credentials['max_age'] = max_age

            referer = environ.get('HTTP_REFERER', '/')
            environ['repoze.who.application'] = HTTPFound(referer)
            return credentials

    # IChallenger
    def challenge(self, environ, status, app_headers, forget_headers):
        reason = header_value(app_headers, 'X-Authorization-Failure-Reason')
        url_parts = list(urlparse.urlparse(self.login_form_url))
        query = url_parts[4]
        query_elements = cgi.parse_qs(query)
        if reason:
            query_elements[self.reason_param] = reason
        url_parts[4] = urllib.urlencode(query_elements, doseq=True)
        login_form_url = urlparse.urlunparse(url_parts)
        headers = [ ('Location', login_form_url) ]
        cookies = [(h, v) for (h, v) in app_headers if h.lower() == 'set-cookie']
        headers = headers + forget_headers + cookies
        return HTTPFound(headers=headers)

def make_plugin(login_form_qs='__do_login',
                rememberer_name=None,
                form=None,
                formcallable=None,
               ):
    if rememberer_name is None:
        raise ValueError(
            'must include rememberer key (name of another IIdentifier plugin)')
    if form is not None:
        form = open(form).read()
    if isinstance(formcallable, str):
        formcallable = _resolve(formcallable)
    plugin = FormPlugin(login_form_qs, rememberer_name, form, formcallable)
    return plugin

def make_redirecting_plugin(login_form_url=None,
                            login_handler_path='/login_handler',
                            logout_handler_path='/logout_handler',
                            rememberer_name=None):
    if login_form_url is None:
        raise ValueError(
            'must include login_form_url in configuration')
    if login_handler_path is None:
        raise ValueError(
            'login_handler_path must not be None')
    if logout_handler_path is None:
        raise ValueError(
            'logout_handler_path must not be None')
    if rememberer_name is None:
        raise ValueError(
            'must include rememberer key (name of another IIdentifier plugin)')
    plugin = RedirectingFormPlugin(login_form_url,
                                   login_handler_path,
                                   logout_handler_path,
                                   rememberer_name)
    return plugin

