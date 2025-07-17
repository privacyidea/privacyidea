# 2020-02-15 Jean-Pierre Höhmann <jean-pierre.hoehmann@netknights.it>
#            Add webAuthn token
# 2018-06-15 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add translation for authentication failure - since
#            this is a message that is displayed in the UI.
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
"""This REST API is used to authenticate the users. A user needs to
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
import copy

from flask import (Blueprint,
                   request,
                   current_app,
                   g)
import jwt
from functools import wraps
from datetime import (datetime,
                      timedelta, timezone)
from privacyidea.lib.error import AuthError, ERROR
from privacyidea.lib.crypto import geturandom, init_hsm
from privacyidea.lib.audit import getAudit
from privacyidea.lib.auth import (check_webui_user, ROLE, verify_db_admin,
                                  db_admin_exist)
from privacyidea.lib.fido2.policy_action import FIDO2PolicyAction
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.fido2.challenge import verify_fido2_challenge
from privacyidea.lib.fido2.util import get_fido2_token_by_credential_id
from privacyidea.lib.user import User, split_user, log_used_user
from privacyidea.lib.policy import PolicyClass, REMOTE_USER
from privacyidea.lib.realm import get_default_realm, realm_is_defined
from privacyidea.api.lib.postpolicy import (postpolicy, add_user_detail_to_response, check_tokentype,
                                            check_tokeninfo, check_serial, no_detail_on_success,
                                            get_webui_settings)
from privacyidea.api.lib.prepolicy import (is_remote_user_allowed, prepolicy,
                                           pushtoken_disable_wait, webauthntoken_authz, webauthntoken_request,
                                           fido2_auth, increase_failcounter_on_challenge,
                                           jwt_validity, disabled_token_types, auth_timelimit)
from privacyidea.api.lib.utils import (send_result, get_all_params,
                                       verify_auth_token, getParam, get_optional, get_required)
from privacyidea.lib.utils import get_client_ip, hexlify_and_unicode, to_unicode, get_plugin_info_from_useragent
from privacyidea.lib.config import get_from_config, SYSCONF, ensure_no_config_object, get_privacyidea_node
from privacyidea.lib.event import event, EventConfiguration
from privacyidea.lib import _
import logging
import traceback
import threading

log = logging.getLogger(__name__)

jwtauth = Blueprint('jwtauth', __name__)


@jwtauth.before_request
def before_request():
    """
    This is executed before the request
    """
    ensure_no_config_object()
    # Save the request data
    g.request_data = get_all_params(request)
    request.all_data = copy.deepcopy(g.request_data)
    privacyidea_server = get_app_config_value("PI_AUDIT_SERVERNAME", get_privacyidea_node(request.host))
    g.policy_object = PolicyClass()
    g.audit_object = getAudit(current_app.config)
    g.event_config = EventConfiguration()
    # access_route contains the ip addresses of all clients, hops and proxies.
    g.client_ip = get_client_ip(request,
                                get_from_config(SYSCONF.OVERRIDECLIENT))
    # Save the HTTP header in the localproxy object
    g.request_headers = request.headers
    g.serial = getParam(request.all_data, "serial", default=None)
    ua_name, ua_version, _ua_comment = get_plugin_info_from_useragent(request.user_agent.string)
    g.user_agent = ua_name
    g.audit_object.log({"success": False,
                        "client": g.client_ip,
                        "user_agent": ua_name,
                        "user_agent_version": ua_version,
                        "privacyidea_server": privacyidea_server,
                        "action": f"{request.method!s} {request.url_rule!s}",
                        "action_detail": "",
                        "thread_id": f"{threading.current_thread().ident!s}",
                        "info": ""})

    username = getParam(request.all_data, "username")
    if username:
        # We only fill request.User, if we really have a username.
        # On endpoints like /auth/rights, this is not available
        login_name, realm = split_user(username)
        # overwrite the split realm if we have a realm parameter. Default back to default_realm
        realm = getParam(request.all_data, "realm") or realm or get_default_realm()
        # Prefill the request.User. This is used by some pre-event handlers
        try:
            request.User = User(login_name, realm)
        except Exception as e:
            request.User = None
            log.warning(f"Problem resolving user {login_name} in realm {realm}: {e!s}.")
            log.debug(f"{traceback.format_exc()!s}")


@jwtauth.route('', methods=['POST'])
@prepolicy(auth_timelimit, request=request)
@prepolicy(increase_failcounter_on_challenge, request=request)
@prepolicy(pushtoken_disable_wait, request)
@prepolicy(webauthntoken_request, request=request)
@prepolicy(webauthntoken_authz, request=request)
@prepolicy(disabled_token_types, request=request)
@prepolicy(fido2_auth, request=request)
@prepolicy(jwt_validity, request)
@postpolicy(get_webui_settings, request=request)
@postpolicy(no_detail_on_success, request=request)
@postpolicy(add_user_detail_to_response, request=request)
@postpolicy(check_tokentype, request=request)
@postpolicy(check_tokeninfo, request=request)
@postpolicy(check_serial, request=request)
@event("auth", request, g)
def get_auth_token():
    """
    This call verifies the credentials of the user and issues an
    authentication token, that is used for the later API calls. The
    authentication token has a validity, that is usually 1 hour.

    :jsonparam username: The username of the user who wants to authenticate to
        the API.
    :jsonparam password: The password/credentials of the user who wants to
        authenticate to the API.
    :jsonparam realm: The realm where the user will be searched.

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
    jwt_validity_param = get_optional(request.all_data, "jwt_validity")
    validity = timedelta(seconds=int(jwt_validity_param))
    username = get_optional(request.all_data, "username")
    password = get_optional(request.all_data, "password")
    realm_param = get_optional(request.all_data, "realm")
    details = {}
    # Passkey login
    credential_id = get_optional(request.all_data, "credential_id")
    passkey_login_enabled = get_app_config_value("WEBUI_PASSKEY_LOGIN_ENABLED", True)
    passkey_login_success = False
    if not passkey_login_enabled and credential_id:
        log.debug("WebUI passkey login disabled in pi.cfg!")
        raise AuthError(_("Authentication with passkey disabled."), id=ERROR.AUTHENTICATE_ILLEGAL_METHOD)
    if credential_id and passkey_login_enabled:
        transaction_id: str = get_required(request.all_data, "transaction_id")
        token = get_fido2_token_by_credential_id(credential_id)
        if not token:
            raise AuthError(_("Authentication failure. The passkey is not registered."),
                            id=ERROR.AUTHENTICATE_WRONG_CREDENTIALS)
        if not token.user:
            raise AuthError(_("Authentication failure. Token has no user."),
                            id=ERROR.AUTHENTICATE_MISSING_USERNAME)
        # TODO For the WebUI login, always require user_verification so that it is a 2FA
        request.all_data.update({FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT: "required"})
        passkey_login_success = verify_fido2_challenge(transaction_id, token, request.all_data) > 0
        if passkey_login_success:
            user = token.user
            login_name = user.login
            realm = user.realm
            username = user.login
        else:
            raise AuthError(_("Authentication failure using passkey."), id=ERROR.AUTHENTICATE_WRONG_CREDENTIALS)
    # End passkey login
    else:
        # The realm parameter has precedence! Check if it exists
        if realm_param and not realm_is_defined(realm_param):
            raise AuthError(_("Authentication failure. Unknown realm:") + f" {realm_param}.",
                            id=ERROR.AUTHENTICATE_WRONG_CREDENTIALS)

        if username is None:
            raise AuthError(_("Authentication failure. Missing Username"), id=ERROR.AUTHENTICATE_MISSING_USERNAME)

        user = request.User
        if not user:
            # The user could not be resolved, but it could still be a local administrator
            login_name, realm = split_user(username)
            realm = (realm_param or realm or get_default_realm()).lower()
            user = User()
        else:
            realm = user.realm
            login_name = user.login

    # Failsafe to have the user attempt in the log, whatever happens
    # This can be overwritten later
    g.audit_object.log({"user": username, "realm": realm})

    secret = current_app.secret_key
    superuser_realms = [x.lower() for x in current_app.config.get("SUPERUSER_REALM", [])]
    # This is the default role for the logged-in user. The role privileges may be risen to "admin"
    role = ROLE.USER
    # The way the user authenticated. This could be:
    # "password" = The admin user DB or the user store
    # "pi" = The admin or the user is authenticated against privacyIDEA
    # "remote_user" = authenticated by webserver
    authtype = "password"
    # Verify the password
    admin_auth = False
    user_auth = False

    if passkey_login_success:
        authtype = "pi"
        # Login is already completed, get the role of the logged-in user
        if db_admin_exist(username):
            role = ROLE.ADMIN
            admin_auth = True
            g.audit_object.log({"success": True, "user": "", "administrator": username, "info": "internal admin"})
            user = User()
        elif user.realm in superuser_realms:
            role = ROLE.ADMIN
            admin_auth = True
            g.audit_object.log({"user": user.login, "realm": user.realm, "info": log_used_user(user)})
        else:
            user_auth = True
            g.audit_object.log({"user": user.login, "realm": user.realm, "info": log_used_user(user)})

    # Check if the remote user is allowed
    elif (request.remote_user == username) and is_remote_user_allowed(request) != REMOTE_USER.DISABLE:
        # Authenticated by the Web Server
        # Check if the username exists
        # 1. in local admins
        # 2. in a realm
        # 2a. is an admin realm
        authtype = "remote_user "
        if db_admin_exist(username):
            role = ROLE.ADMIN
            admin_auth = True
            g.audit_object.log({"success": True, "user": "", "administrator": username, "info": "internal admin"})
            user = User()
        else:
            # Check if the user exists
            g.audit_object.log({"user": user.login, "realm": user.realm, "info": log_used_user(user)})
            if user.exist():
                user_auth = True
                if user.realm in superuser_realms:
                    role = ROLE.ADMIN
                    admin_auth = True

    elif verify_db_admin(username, password):
        role = ROLE.ADMIN
        admin_auth = True
        log.info(f"Local admin '{username}' successfully logged in.")
        # This admin is not in the default realm!
        realm = ""
        user = User()
        g.audit_object.log({"success": True,
                            "user": "",
                            "realm": "",
                            "administrator": username,
                            "info": "internal admin"})

    else:
        # The user could not be identified against the admin database, so we do the rest of the check
        if password is None:
            g.audit_object.add_to_log({"info": 'Missing parameter "password"'}, add_with_comma=True)
        else:
            options = {"g": g, "clientip": g.client_ip}
            for key, value in request.all_data.items():
                if value and key not in ["g", "clientip"]:
                    options[key] = value
            user_auth, role, details = check_webui_user(user, password, options=options,
                                                        superuser_realms=superuser_realms)
            details = details or {}
            serials = (",".join([challenge_info["serial"] for challenge_info in details["multi_challenge"]])
                       if 'multi_challenge' in details else details.get('serial'))
            if db_admin_exist(user.login) and user_auth and realm == get_default_realm():
                # If there is a local admin with the same login name as the user
                # in the default realm, we inform about this in the log file.
                # This condition can only be checked if the user was authenticated as it
                # is the only way to verify if such a user exists.
                log.warning(f"A user '{user.login}' exists as local admin and as user in your default realm!")
            g.audit_object.log({
                "realm": user.realm,
                "resolver": user.resolver,
                "serial": serials,
                "info": log_used_user(user, f"loginmode={details.get('loginmode')}")})
            if role == ROLE.ADMIN:
                g.audit_object.log({"user": "", "administrator": user.login})
            else:
                g.audit_object.log({"user": user.login})

            if not user_auth and "multi_challenge" in details and len(details["multi_challenge"]) > 0:
                # Do not return user data in case of a challenge request.
                return send_result(False, rid=2, details=details)

    if not admin_auth and not user_auth:
        raise AuthError(_("Authentication failure. Wrong credentials"), id=ERROR.AUTHENTICATE_WRONG_CREDENTIALS,
                        details=details or {})
    else:
        g.audit_object.log({"success": True})
        request.User = user

    # If the HSM is not ready, we need to create the nonce in another way!
    hsm = init_hsm()
    if hsm.is_ready:
        nonce = geturandom(hex=True)
        # Add the role to the JWT, so that we can verify it internally and use the authtype for access definitions
        rights = g.policy_object.ui_get_rights(role, realm, login_name, g.client_ip, g.get("user_agent"))
        menus = g.policy_object.ui_get_main_menus({"username": login_name, "role": role, "realm": realm}, g.client_ip,
                                                  g.get("user_agent"))
    else:
        import os
        nonce = hexlify_and_unicode(os.urandom(20))
        rights = []
        menus = []

    # What is the log level?
    log_level = current_app.config.get("PI_LOGLEVEL", 30)

    token = jwt.encode({"username": login_name,
                        "realm": realm,
                        "nonce": nonce,
                        "role": role,
                        "authtype": authtype,
                        "exp": datetime.now(timezone.utc) + validity,
                        "rights": rights},
                       secret, algorithm='HS256')

    # set the logged-in user for post-policies and post-events
    g.logged_in_user = {"username": login_name, "realm": realm, "role": role}

    # Add the role to the response, so that the WebUI can make decisions
    # based on this (only show self-service, not the admin part)
    return send_result({"token": to_unicode(token),
                        "role": role,
                        "username": login_name,
                        "realm": realm,
                        "log_level": log_level,
                        "rights": rights,
                        "menus": menus,
                        "auth": True},
                       rid=2,
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
    g.logged_in_user = {"username": r.get("username"), "realm": r.get("realm"), "role": r.get("role")}


@jwtauth.route('/rights', methods=['GET'])
@user_required
def get_rights():
    """
    This returns the rights of the logged-in user.

    :reqheader Authorization: The authorization token acquired by /auth request
    """
    enroll_types = g.policy_object.ui_get_enroll_tokentypes(g.client_ip, g.logged_in_user, g.get("user_agent"))
    g.audit_object.log({"success": True})
    return send_result(enroll_types)
