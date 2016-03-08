# -*- coding: utf-8 -*-
#
# 2016-03-07 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add SAML Service Provider based on
#            https://github.com/jpf/okta-pysaml2-example
# 2015-11-04 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add REMOTE_USER check
# 2015-04-03 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add logout time to response
# 2014-12-15 Cornelius Kölbel, info@privacyidea.org
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
__doc__ = """This REST API is used to authenticate the users. A user needs to
authenticate when he wants to use the API for administrative tasks like
enrolling a token.

This API must not be confused with the validate API, which is used to check,
if a OTP value is valid. See :ref:`rest_validate`.

Authentication of users and admins is tested in tests/test_api_roles.py

You need to authenticate for all administrative tasks. If you are not
authenticated, the API returns a 401 response.

To authenticate you need to send a POST request to /auth containing username
and password.
"""
from flask import (Blueprint,
                   request,
                   current_app,
                   g,
                   redirect, url_for)
from lib.utils import (send_result, get_all_params,
                       verify_auth_token)
from ..lib.crypto import geturandom, init_hsm
from ..lib.error import AuthError
from ..lib.auth import verify_db_admin, db_admin_exist
import jwt
from functools import wraps
from datetime import (datetime,
                      timedelta)
from privacyidea.lib.audit import getAudit
from privacyidea.lib.auth import check_webui_user, ROLE
from privacyidea.lib.user import User
from privacyidea.lib.user import split_user
from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.realm import get_default_realm
from privacyidea.api.lib.postpolicy import postpolicy, get_webui_settings
from privacyidea.api.lib.prepolicy import is_remote_user_allowed
import logging
import requests
from saml2 import (
    BINDING_HTTP_POST,
    BINDING_HTTP_REDIRECT,
    entity,
)
from saml2.client import Saml2Client
from saml2.config import Config as Saml2Config


log = logging.getLogger(__name__)


jwtauth = Blueprint('jwtauth', __name__)


@jwtauth.before_request
def before_request():
    """
    This is executed before the request
    """
    privacyidea_server = current_app.config.get("PI_AUDIT_SERVERNAME") or \
                         request.host
    g.policy_object = PolicyClass()
    g.audit_object = getAudit(current_app.config)
    g.audit_object.log({"success": False,
                        "client": request.remote_addr,
                        "client_user_agent": request.user_agent.browser,
                        "privacyidea_server": privacyidea_server,
                        "action": "%s %s" % (request.method, request.url_rule),
                        "action_detail": "",
                        "info": ""})
    request.all_data = get_all_params(request.values, request.data)


@jwtauth.route('', methods=['POST'])
@postpolicy(get_webui_settings)
def get_auth_token():
    """
    This call verifies the credentials of the user and issues an
    authentication token, that is used for the later API calls. The
    authentication token has a validity, that is usually 1 hour.

    :jsonparam username: The username of the user who wants to authenticate to
        the API.
    :jsonparam password: The password/credentials of the user who wants to
        authenticate to the API.
    :jsonparam SAMLResponse: When acting as a SAML 2.0 SP and the user has
        authenticated to an IdP, this contains the SAML Response.

    :return: A json response with an authentication token, that needs to be
        used in any further request.

    :status 200: in case of success
    :status 401: if authentication fails

    **Example Authentication Request**:

    .. sourcecode:: http

       POST /auth HTTP/1.1
       Host: example.com
       Accept: application/json

       username=admin
       password=topsecret

    **Example Authentication Response**:

    .. sourcecode:: http

       HTTP/1.0 200 OK
       Content-Length: 354
       Content-Type: application/json

       {
            "id": 1,
            "jsonrpc": "2.0",
            "result": {
                "status": true,
                "value": {
                    "token": "eyJhbGciOiJIUz....jdpn9kIjuGRnGejmbFbM"
                }
            },
            "version": "privacyIDEA unknown"
       }

    **Response for failed authentication**:

    .. sourcecode:: http

       HTTP/1.1 401 UNAUTHORIZED
       Content-Type: application/json
       Content-Length: 203

       {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "error": {
              "code": -401,
              "message": "missing Authorization header"
            },
            "status": false
          },
          "version": "privacyIDEA unknown",
          "config": {
            "logout_time": 30
          }
       }

    """
    # The way the user authenticated. This could be
    # "password" = The admin user DB or the user store
    # "pi" = The admin or the user is authenticated against privacyIDEA
    # "remote_user" = authenticated by webserver
    authtype = "password"

    validity = timedelta(hours=1)
    username = request.all_data.get("username")
    password = request.all_data.get("password")
    saml_respone = request.all_data.get("SAMLResponse")

    if saml_respone:
        saml_client = saml_client_for("okta")
        authn_response = saml_client.parse_authn_request_response(
            saml_respone,
            entity.BINDING_HTTP_POST)
        authn_response.get_identity()
        user_info = authn_response.get_subject()
        username = user_info.text
        authtype = "saml"

    # Here we need to check, if the user exists and log the user in.
    loginname, realm = split_user(username)
    realm = realm or get_default_realm()
    g.audit_object.log({"user": username})
    secret = current_app.secret_key
    superuser_realms = current_app.config.get("SUPERUSER_REALM", [])
    # This is the default role for the logged in user.
    # The role privileges may be risen to "admin"
    role = ROLE.USER
    if username is None:
        raise AuthError("Authentication failure",
                        "missing Username",
                        status=401)
    # Verify the password
    admin_auth = False
    user_auth = False
    details = None

    if ((request.remote_user == username) and is_remote_user_allowed(
            request)) or saml_respone:
        # Now we only have to check, if the user exists and if he is a admin
        # or a normal user
        # Check if the remote user is allowed

        # Authenticated by the Web Server
        # Check if the username exists
        # 1. in local admins
        # 2. in a realm
        # 2a. is an admin realm
        authtype = "remote_user"
        if db_admin_exist(username):
            role = ROLE.ADMIN
            admin_auth = True
            g.audit_object.log({"success": True,
                                "user": "",
                                "administrator": username,
                                "info": "internal admin"})
        else:
            # check, if the user exists
            user_obj = User(loginname, realm)
            if user_obj.exist():
                user_auth = True
                if user_obj.realm in superuser_realms:
                    role = ROLE.ADMIN
                    admin_auth = True

    elif verify_db_admin(username, password):
        role = ROLE.ADMIN
        admin_auth = True
        # This admin is not in the default realm!
        realm = ""
        g.audit_object.log({"success": True,
                            "user": "",
                            "administrator": username,
                            "info": "internal admin"})

    else:
        # The user could not be identified against the admin database,
        # so we do the rest of the check
        options = {"g": g,
                   "clientip": request.remote_addr}
        for key, value in request.all_data.items():
            if value and key not in ["g", "clientip"]:
                options[key] = value
        user_obj = User(loginname, realm)
        user_auth, role, details = check_webui_user(user_obj,
                                                    password,
                                                    options=options,
                                                    superuser_realms=
                                                    superuser_realms)
        if role == ROLE.ADMIN:
            g.audit_object.log({"user": "",
                                "administrator": username})

    if not admin_auth and not user_auth:
        raise AuthError("Authentication failure",
                        "Wrong credentials", status=401,
                        details=details or {})
    else:
        g.audit_object.log({"success": True})

    # If the HSM is not ready, we need to create the nonce in another way!
    hsm = init_hsm()
    if hsm.is_ready:
        nonce = geturandom(hex=True)
        # Add the role to the JWT, so that we can verify it internally
        # Add the authtype to the JWT, so that we could use it for access
        # definitions
        rights = g.policy_object.ui_get_rights(role, realm, loginname,
                                               request.remote_addr)
    else:
        import os
        import binascii
        nonce = binascii.hexlify(os.urandom(20))
        rights = []

    token = jwt.encode({"username": loginname,
                        "realm": realm,
                        "nonce": nonce,
                        "role": role,
                        "authtype": authtype,
                        "exp": datetime.utcnow() + validity,
                        "rights": rights},
                       secret)

    # Add the role to the response, so that the WebUI can make decisions
    # based on this (only show selfservice, not the admin part)
    return send_result({"token": token,
                        "role": role,
                        "username": loginname,
                        "realm": realm,
                        "rights": rights})


def admin_required(f):
    """
    This is a decorator for routes, that require to be authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        check_auth_token(required_role=[ROLE.ADMIN])
        return f(*args, **kwargs)
    return decorated_function


def user_required(f):
    """
    This is a decorator for routes, that require to be authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        check_auth_token(required_role=["user", "admin"])
        return f(*args, **kwargs)
    return decorated_function


def check_auth_token(required_role=None):
    """
    This checks the authentication token
    
    You need to pass an authentication header:
    
        PI-Authorization: <token>
        
    You can do this using httpie like this:
    
        http -j POST http://localhost:5000/system/getConfig Authorization:ewrt
    """
    auth_token = request.headers.get('PI-Authorization', None)
    if not auth_token:
        auth_token = request.headers.get('Authorization', None)
    r = verify_auth_token(auth_token, required_role)
    g.logged_in_user = {"username": r.get("username"),
                        "realm": r.get("realm"),
                        "role": r.get("role")}


@jwtauth.route('/rights', methods=['GET'])
@user_required
def get_rights():
    """
    This returns the rights of the logged in user.

    :reqheader Authorization: The authorization token acquired by /auth request
    """
    enroll_types = g.policy_object.ui_get_enroll_tokentypes(request.remote_addr,
                                                            g.logged_in_user)
    return send_result(enroll_types)


saml_urls = {
    "okta": 'http://idp.oktadev.com/metadata',
}


def saml_client_for(idp_name=None):
    '''
    Given the name of an IdP, return a configuation.
    The configuration is a hash for use by saml2.config.Config
    '''

    if idp_name not in saml_urls:
        raise Exception("Settings for IDP '{}' not found".format(idp_name))
    #acs_url = url_for(
    #    ".saml_idp_return",
    #    idp_name=idp_name,
    #    _external=True)
    #https_acs_url = url_for(
    #    ".saml_idp_return",
    #    idp_name=idp_name,
    #    _external=True,
    #    _scheme='https')
    acs_url = "http://1b3369c8.ngrok.com/"
    https_acs_url = "http://1b3369c8.ngrok.com/"

    # NOTE:
    #   Ideally, this should fetch the metadata and pass it to
    #   PySAML2 via the "inline" metadata type.
    #   However, this method doesn't seem to work on PySAML2 v2.4.0
    #
    #   SAML metadata changes very rarely. On a production system,
    #   this data should be cached as approprate for your production system.
    rv = requests.get(saml_urls[idp_name])
    import tempfile
    tmp = tempfile.NamedTemporaryFile()
    f = open(tmp.name, 'w')
    f.write(rv.text)
    f.close()

    settings = {
        'metadata': {
            # 'inline': metadata,
            "local": [tmp.name]
            },
        'service': {
            'sp': {
                'endpoints': {
                    'assertion_consumer_service': [
                        (acs_url, BINDING_HTTP_REDIRECT),
                        (acs_url, BINDING_HTTP_POST),
                        (https_acs_url, BINDING_HTTP_REDIRECT),
                        (https_acs_url, BINDING_HTTP_POST)
                    ],
                },
                # Don't verify that the incoming requests originate from us via
                # the built-in cache for authn request ids in pysaml2
                'allow_unsolicited': True,
                # Don't sign authn requests, since signed requests only make
                # sense in a situation where you control both the SP and IdP
                'authn_requests_signed': False,
                'logout_requests_signed': True,
                'want_assertions_signed': True,
                'want_response_signed': False,
            },
        },
    }
    spConfig = Saml2Config()
    spConfig.load(settings)
    spConfig.allow_unknown_attributes = True
    saml_client = Saml2Client(config=spConfig)
    tmp.close()
    return saml_client


@jwtauth.route('/saml/acs/<idp_name>', methods=["POST"])
def saml_acs(idp_name):
    """
    This endpoint is called, after the login at the SAML IdP was successful.
    :param idp_name:
    :return:


    """
    # TODO: Put this logic into get_auth_token!!!!
    saml_client = saml_client_for(idp_name)
    authn_response = saml_client.parse_authn_request_response(
        request.all_data.get("SAMLResponse"),
        #request.form['SAMLResponse'],
        entity.BINDING_HTTP_POST)
    authn_response.get_identity()
    user_info = authn_response.get_subject()
    username = user_info.text

    # Here we need to check, if the user exists and log the user in.
    (loginname, realm) = split_user(username)
    realm = realm or get_default_realm()
    role = ROLE.USER
    admin_auth = False
    user_auth = False
    if db_admin_exist(username):
        role = ROLE.ADMIN
        admin_auth = True
        g.audit_object.log({"success": True,
                            "user": "",
                            "administrator": username,
                            "info": "internal admin"})
    else:
        # check, if the user exists
        user_obj = User(loginname, realm)
        if user_obj.exist():
            user_auth = True
            superuser_realms = current_app.config.get("SUPERUSER_REALM", [])
            if user_obj.realm in superuser_realms:
                role = ROLE.ADMIN
                admin_auth = True

    if not admin_auth and not user_auth:
        raise AuthError("Authentication failure",
                        "User does not exist", status=401)
    else:
        g.audit_object.log({"success": True})

    # If the HSM is not ready, we need to create the nonce in another way!
    hsm = init_hsm()
    if hsm.is_ready:
        nonce = geturandom(hex=True)
        # Add the role to the JWT, so that we can verify it internally
        # Add the authtype to the JWT, so that we could use it for access
        # definitions
        rights = g.policy_object.ui_get_rights(role, realm, loginname,
                                               request.remote_addr)
    else:
        import os
        import binascii
        nonce = binascii.hexlify(os.urandom(20))
        rights = []

    validity = timedelta(hours=1)
    secret = current_app.secret_key
    token = jwt.encode({"username": loginname,
                        "realm": realm,
                        "nonce": nonce,
                        "role": role,
                        "authtype": "saml",
                        "exp": datetime.utcnow() + validity,
                        "rights": rights}, secret)

    # Add the role to the response, so that the WebUI can make decisions
    # based on this (only show selfservice, not the admin part)
    return send_result({"token": token,
                        "role": role,
                        "username": loginname,
                        "realm": realm,
                        "rights": rights})


@jwtauth.route('/saml/login/<idp_name>', methods=['POST', 'GET'])
def saml_sp_login(idp_name):
    """
    This redirects to the SAML IdP Login page.
    :return:
    """
    saml_client = saml_client_for(idp_name)
    reqid, info = saml_client.prepare_for_authenticate()

    redirect_url = None
    # Select the IdP URL to send the AuthN request to
    for key, value in info['headers']:
        if key is 'Location':
            redirect_url = value
    response = redirect(redirect_url, code=302)
    response.headers['Cache-Control'] = 'no-cache, no-store'
    response.headers['Pragma'] = 'no-cache'
    return response
