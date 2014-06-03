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

