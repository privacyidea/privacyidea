# -*- coding: utf-8 -*-
#
# 2016-04-08 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Avoid "None" as redundant 2nd argument
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
                   g)
from .lib.utils import (send_result, get_all_params,
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
from privacyidea.lib.utils import get_client_ip
from privacyidea.lib.config import get_from_config, SYSCONF, ConfigClass
import logging

log = logging.getLogger(__name__)


jwtauth = Blueprint('jwtauth', __name__)


@jwtauth.before_request
def before_request():
    """
    This is executed before the request
    """
    g.config_object = ConfigClass()
    request.all_data = get_all_params(request.values, request.data)
    privacyidea_server = current_app.config.get("PI_AUDIT_SERVERNAME") or \
                         request.host
    g.policy_object = PolicyClass()
    g.audit_object = getAudit(current_app.config)
    # access_route contains the ip adresses of all clients, hops and proxies.
    g.client_ip = get_client_ip(request,
                                get_from_config(SYSCONF.OVERRIDECLIENT))
    g.audit_object.log({"success": False,
                        "client": g.client_ip,
                        "client_user_agent": request.user_agent.browser,
                        "privacyidea_server": privacyidea_server,
                        "action": "{0!s} {1!s}".format(request.method, request.url_rule),
                        "action_detail": "",
                        "info": ""})


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
    validity = timedelta(hours=1)
    username = request.all_data.get("username")
    password = request.all_data.get("password")
    realm = request.all_data.get("realm")
    details = {}
    if realm:
        username = username + "@" + realm

    g.audit_object.log({"user": username})

    secret = current_app.secret_key
    superuser_realms = current_app.config.get("SUPERUSER_REALM", [])
    # This is the default role for the logged in user.
    # The role privileges may be risen to "admin"
    role = ROLE.USER
    # The way the user authenticated. This could be
    # "password" = The admin user DB or the user store
    # "pi" = The admin or the user is authenticated against privacyIDEA
    # "remote_user" = authenticated by webserver
    authtype = "password"
    if username is None:
        raise AuthError("Authentication failure",
                        "missing Username",
                        status=401)
    # Verify the password
    admin_auth = False
    user_auth = False

    loginname, realm = split_user(username)
    realm = realm or get_default_realm()

    # Check if the remote user is allowed
    if (request.remote_user == username) and is_remote_user_allowed(request):
        # Authenticated by the Web Server
        # Check if the username exists
        # 1. in local admins
        # 2. in a realm
        # 2a. is an admin realm
        authtype = "remote_user "
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
                   "clientip": g.client_ip}
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
                                               g.client_ip)
        menus = g.policy_object.ui_get_main_menus({"username": loginname,
                                                   "role": role,
                                                   "realm": realm},
                                                  g.client_ip)
    else:
        import os
        import binascii
        nonce = binascii.hexlify(os.urandom(20))
        rights = []
        menus = []

    # What is the log level?
    log_level = current_app.config.get("PI_LOGLEVEL", 30)

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
                        "log_level": log_level,
                        "rights": rights,
                        "menus": menus},
                       details=details)


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
    auth_token = request.headers.get('PI-Authorization')
    if not auth_token:
        auth_token = request.headers.get('Authorization')
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
    enroll_types = g.policy_object.ui_get_enroll_tokentypes(g.client_ip,
                                                            g.logged_in_user)

    g.audit_object.log({"success": True})
    return send_result(enroll_types)
