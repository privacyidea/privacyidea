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
"""
The auth REST API issues the JWT-based authentication tokens that
every other administrative or user-self endpoint expects. Four
authentication paths are supported:

* **Password** — username and password verified against the local
  admin database, then against the user store. Token authentication
  may be required on top by the WebUI ``login_mode`` policy.
* **FIDO2 / Passkey** — ``credential_id`` plus ``transaction_id``
  from a prior call to :http:post:`/validate/initialize`.
* **REMOTE_USER** — when an upstream web server (Apache, nginx) has
  already authenticated the request, ``REMOTE_USER`` is honored if
  the WebUI ``remote_user`` policy is active.
* **Trusted JWT** — JWTs signed by an external IdP are accepted on
  any authenticated endpoint when the IdP's public key, algorithm
  and a username regex are listed in ``PI_TRUSTED_JWT``.

A successful login returns a JWT carrying ``username``, ``realm``,
``role`` (``user`` or ``admin``), ``rights`` (the policy-derived list
of allowed actions), ``authtype`` (``password`` / ``pi`` /
``remote_user``) and an ``exp`` claim. The default validity is one
hour; the WebUI ``jwt_validity`` policy overrides it.

Subsequent requests carry the token in the ``PI-Authorization``
header (``Authorization`` is also accepted as a fallback). Calls
that require authentication return a 401 response if the token is
absent, malformed or expired.

This API is distinct from :ref:`rest_validate`, which checks OTP
values for end users.
"""
from flask_babel import _
import copy

from flask import (Blueprint, request, current_app, g)
import jwt
from functools import wraps
from datetime import (datetime, timezone)

from privacyidea.api.lib.policyhelper import check_last_auth_policy, get_realm_for_authentication
from privacyidea.lib.error import AuthError, Error
from privacyidea.lib.crypto import geturandom, init_hsm
from privacyidea.lib.audit import getAudit
from privacyidea.lib.auth import (check_webui_user, ROLE, verify_db_admin,
                                  db_admin_exists)
from privacyidea.lib.fido2.policy_action import FIDO2PolicyAction
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.fido2.challenge import verify_fido2_challenge
from privacyidea.lib.fido2.util import get_fido2_token_by_credential_id
from privacyidea.lib.policies.helper import get_jwt_validity
from privacyidea.lib.user import User, split_user, log_used_user
from privacyidea.lib.policy import PolicyClass, REMOTE_USER
from privacyidea.lib.policydecorators import reset_all_user_tokens_active, reset_token_failcounters
from privacyidea.lib.token import get_tokens
from privacyidea.lib.realm import get_default_realm, realm_is_defined
from privacyidea.api.lib.postpolicy import (postpolicy, add_user_detail_to_response, check_tokentype,
                                            check_tokeninfo, check_serial, no_detail_on_success,
                                            get_webui_settings, hide_specific_error_message)
from privacyidea.api.lib.prepolicy import (is_remote_user_allowed, prepolicy,
                                           pushtoken_disable_wait, webauthntoken_authz, webauthntoken_request,
                                           fido2_auth, increase_failcounter_on_challenge,
                                           disabled_token_types, auth_timelimit, load_challenge_text)
from privacyidea.api.lib.utils import (send_result, get_all_params, INTERNAL_OPTION_KEYS,
                                       verify_auth_token, getParam, get_optional, get_required)
from privacyidea.lib.utils import (get_client_ip, hexlify_and_unicode, to_unicode, get_plugin_info_from_useragent,
                                   AUTH_RESPONSE)
from privacyidea.lib.config import get_from_config, SYSCONF, ensure_no_config_object, get_privacyidea_node
from privacyidea.lib.event import event, EventConfiguration
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
    g.serial = get_optional(request.all_data, "serial")
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
    g.resolved_user = {"is_local_admin": False}

    request.User = User()
    username = request.all_data.get("username")
    credential_id = request.all_data.get("credential_id")
    if username:
        # We only fill request.User, if we really have a username.
        # On endpoints like /auth/rights, this is not available
        login_name, realm = split_user(username)
        # overwrite the split realm if we have a realm parameter. Default back to default_realm
        realm = get_optional(request.all_data, "realm") or realm
        # Prefill the request.User. This is used by some pre-event handlers
        if not realm and db_admin_exists(login_name):
            # TODO: create an own local admin user object
            g.resolved_user["is_local_admin"] = True
            request.User = User(login_name)
        else:
            realm = realm or get_default_realm()
            # Check if realm should be overwritten
            realm = get_realm_for_authentication(g, login_name, realm)
            request.all_data["realm"] = realm
            try:
                request.User = User(login_name, realm)
            except Exception as e:
                request.User = None
                log.warning(f"Problem resolving user {login_name} in realm {realm}: {e!s}.")
                log.debug(f"{traceback.format_exc()!s}")
    elif credential_id:
        # Get user for passkey and webauthn login
        token = get_fido2_token_by_credential_id(credential_id)
        if token:
            request.User = token.user


@jwtauth.route('', methods=['POST'])
@prepolicy(auth_timelimit, request=request)
@prepolicy(increase_failcounter_on_challenge, request=request)
@prepolicy(pushtoken_disable_wait, request)
@prepolicy(webauthntoken_request, request=request)
@prepolicy(webauthntoken_authz, request=request)
@prepolicy(disabled_token_types, request=request)
@prepolicy(load_challenge_text, request=request)
@prepolicy(fido2_auth, request=request)
@postpolicy(hide_specific_error_message)
@postpolicy(get_webui_settings, request=request)
@postpolicy(no_detail_on_success, request=request)
@postpolicy(add_user_detail_to_response, request=request)
@postpolicy(check_tokentype, request=request)
@postpolicy(check_tokeninfo, request=request)
@postpolicy(check_serial, request=request)
@event("auth", request, g)
def get_auth_token():
    """
    Verify credentials and issue a JWT authentication token.

    Four credential shapes are accepted, see the module-level
    description for the full picture:

    * password (``username`` + ``password``);
    * passkey / FIDO2 (``credential_id`` + ``transaction_id``);
    * REMOTE_USER, when allowed by the WebUI ``remote_user`` policy;
    * a trusted external JWT, when configured via ``PI_TRUSTED_JWT``.

    The returned JWT carries ``username``, ``realm``, ``role`` (``user``
    or ``admin``), ``rights``, ``authtype`` and ``exp``. The default
    validity is one hour; this is overridable per user/realm via the
    WebUI :ref:`policy_jwt_validity` policy. The WebUI also reads
    ``log_level`` and ``menus`` from the response to render the right
    chrome.

    Several policy actions affect this endpoint, including
    :ref:`policy_login_mode` (whether token auth is required on top of
    password), :ref:`policy_remote_user` (whether REMOTE_USER is
    honored) and the FIDO2/passkey, push, WebAuthn and time-limit
    policies enforced by the registered prepolicies.

    Multi-step (challenge-response) login: when the user is configured
    with a challenge-response token type, the first call returns a
    200 with ``result.value=False`` and ``detail.multi_challenge``
    listing the active challenges. The caller submits the OTP via a
    second :http:post:`/auth` call carrying the same fields plus
    ``transaction_id``.

    :jsonparam username: login name (required for password / REMOTE_USER
        flows).
    :jsonparam password: password / credentials (required for password
        flow).
    :jsonparam realm: optional realm to scope the user lookup; defaults
        to the realm in ``username@realm`` syntax, otherwise the
        default realm.
    :jsonparam credential_id: FIDO2 credential id (required for passkey
        flow).
    :jsonparam transaction_id: transaction id from a prior
        :http:post:`/validate/initialize` (required for passkey and
        for the second leg of a challenge-response flow).

    :status 200: success — the JWT is in ``result.value.token``;
        or first leg of a challenge-response — ``result.value`` is
        ``False`` and ``detail.multi_challenge`` describes the next
        step.
    :status 401: authentication failed (wrong or missing credentials,
        unknown realm, expired token).

    **Example request**:

    .. sourcecode:: http

       POST /auth HTTP/1.1
       Host: example.com
       Content-Type: application/x-www-form-urlencoded

       username=admin&password=topsecret

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "id": 1,
         "jsonrpc": "2.0",
         "result": {
           "status": true,
           "value": {
             "token": "eyJhbGciOiJIUz....jdpn9kIjuGRnGejmbFbM",
             "role": "admin",
             "username": "admin",
             "realm": "",
             "log_level": 30,
             "rights": ["enrollHOTP", "enrollTOTP", ...],
             "menus": ["tokens", "users", ...],
             "auth": true
           }
         },
         "version": "privacyIDEA unknown"
       }
    """
    # TODO: Get rid of username / realm params and use a user object
    #  maybe a new user object that is not directly evaluated against the user store and where we can store some more
    #  information like the role (local / external admin) would be helpful
    user = request.User or User()
    g.audit_object.log({"user": user.login, "realm": user.realm})
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
        raise AuthError(_("Authentication with passkey disabled."), id=Error.AUTHENTICATE_ILLEGAL_METHOD)
    if credential_id and passkey_login_enabled:
        transaction_id: str = get_required(request.all_data, "transaction_id")
        token = get_fido2_token_by_credential_id(credential_id)
        if not token:
            raise AuthError(_("Authentication failure. The passkey is not registered."),
                            id=Error.AUTHENTICATE_WRONG_CREDENTIALS)
        if not token.is_active():
            log.debug(f"Authentication attempted with disabled token {token.get_serial()}")
            g.audit_object.log({"info": log_used_user(user, "Token is disabled"),
                                "success": False,
                                "authentication": AUTH_RESPONSE.REJECT,
                                "serial": token.get_serial(),
                                "token_type": token.get_type()})
            return send_result(False, rid=2, details={"message": "Token is disabled"})

        if not token.user:
            raise AuthError(_("Authentication failure. Token has no user."),
                            id=Error.AUTHENTICATE_MISSING_USERNAME)
        if token.get_type() in request.all_data.get("disabled_token_types", []):
            raise AuthError(
                _("Authentication failure. The token type {token_type} is disabled.").format(
                    token_type=token.get_type()),
                id=Error.AUTHENTICATE_WRONG_CREDENTIALS)
        if not check_last_auth_policy(g, token):
            log.debug(f"Last authentication policy check failed for token {token.get_serial()}.")
            raise AuthError(
                _("Authentication failure. Last authentication policy check failed for token {serial}").format(
                    serial=token.get_serial()), id=Error.AUTHENTICATE_MISSING_RIGHT)

        # TODO For the WebUI login, always require user_verification so that it is a 2FA
        request.all_data.update({FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT: "required"})
        passkey_login_result = verify_fido2_challenge(transaction_id, token, request.all_data)
        if passkey_login_result.success > 0:
            user = token.user
            login_name = user.login
            realm = user.realm
            username = user.login
            passkey_login_success = True
            # Passkey login bypasses check_token_list, so the reset_all_user_tokens
            # policy is applied explicitly here (mirrors the /validate FIDO2 path).
            if reset_all_user_tokens_active(g, user):
                reset_token_failcounters(get_tokens(user=user))
        else:
            raise AuthError(_("Authentication failure using passkey."), id=Error.AUTHENTICATE_WRONG_CREDENTIALS)
    # End passkey login
    else:
        # The realm parameter has precedence! Check if it exists
        if realm_param and not realm_is_defined(realm_param):
            raise AuthError(_("Authentication failure. Unknown realm:") + f" {realm_param}.",
                            id=Error.AUTHENTICATE_WRONG_CREDENTIALS)

        if username is None:
            raise AuthError(_("Authentication failure. Missing Username"), id=Error.AUTHENTICATE_MISSING_USERNAME)

        if not user or not user.realm:
            # The user could not be resolved, but it could still be a local administrator
            login_name, realm = split_user(username)
            realm = realm_param or realm or get_default_realm()
            realm = realm.lower() if realm else None
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
        if user.realm in superuser_realms:
            role = ROLE.ADMIN
            admin_auth = True
        else:
            user_auth = True
        g.audit_object.log({
            "user": user.login,
            "realm": user.realm,
            "resolver": user.resolver,
            "serial": token.get_serial(),
            "token_type": token.get_type(),
            "info": log_used_user(user)
        })
    # Check if the remote user is allowed
    elif (request.remote_user == username) and is_remote_user_allowed(request) != REMOTE_USER.DISABLE:
        # Authenticated by the Web Server
        # Check if the username exists
        # 1. in local admins
        # 2. in a realm
        # 2a. is an admin realm
        log.debug(f"Checking remote user: {username}")
        authtype = "remote_user"
        if db_admin_exists(username):
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
            local_admin_exist = g.get("resolved_user", {}).get("is_local_admin", False)
            if local_admin_exist:
                # The user is a local admin, but a user with the same username can still exist in the default realm
                try:
                    user = User(login_name, realm)
                    reload_policies = True
                except Exception:
                    # Either this is already logged in before_request (user is no local admin) or the user is a local
                    # admin that tries to authenticate with an invalid password (no need to log this)
                    reload_policies = False

                if reload_policies:
                    # We need to reload the pre-policies as they were not matched with the users realm since we
                    # expected a local admin
                    request.User = user
                    g.resolved_user["is_local_admin"] = False
                    auth_timelimit(request, None)
                    increase_failcounter_on_challenge(request, None)
                    disabled_token_types(request, None)

            options = {"g": g, "clientip": g.client_ip}
            for key, value in request.all_data.items():
                # Never copy internal keys
                if value and key not in ["g", "clientip"] and key not in INTERNAL_OPTION_KEYS:
                    options[key] = value
            user_auth, role, details = check_webui_user(user, password, options=options,
                                                        superuser_realms=superuser_realms)
            details = details or {}
            if 'multi_challenge' in details:
                serials = ",".join([challenge_info["serial"] for challenge_info in details["multi_challenge"]])
                token_types = ",".join([challenge_info["type"] for challenge_info in details["multi_challenge"]
                                        if challenge_info.get("type")])
            else:
                serials = details.get('serial')
                token_types = details.get('type')
            if local_admin_exist and user_auth and realm == get_default_realm():
                # If there is a local admin with the same login name as the user
                # in the default realm, we inform about this in the log file.
                # This condition can only be checked if the user was authenticated as it
                # is the only way to verify if such a user exists.
                log.warning(f"A user '{user.login}' exists as local admin and as user in your default realm!")
            g.audit_object.log({
                "realm": user.realm,
                "resolver": user.resolver,
                "serial": serials,
                "token_type": token_types,
                "info": log_used_user(user, f"loginmode={details.get('loginmode')}")})
            if role == ROLE.ADMIN:
                g.audit_object.log({"user": "", "administrator": user.login})
            else:
                g.audit_object.log({"user": user.login})

            if not user_auth and "multi_challenge" in details and len(details["multi_challenge"]) > 0:
                # Do not return user data in case of a challenge request.
                return send_result(False, rid=2, details=details)

    if not admin_auth and not user_auth:
        raise AuthError(_("Authentication failure. Wrong credentials"), id=Error.AUTHENTICATE_WRONG_CREDENTIALS,
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

    validity = get_jwt_validity(request.User)
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
    Route decorator that requires the request to carry a valid auth
    token belonging to a principal with the ``admin`` role. Raises
    ``AuthError`` (HTTP 401) otherwise.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        check_auth_token(required_role=[ROLE.ADMIN])
        return f(*args, **kwargs)

    return decorated_function


def user_required(f):
    """
    Route decorator that requires the request to carry a valid auth
    token belonging to either a ``user`` or an ``admin`` principal.
    Raises ``AuthError`` (HTTP 401) otherwise.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        check_auth_token(required_role=["user", "admin"])
        return f(*args, **kwargs)

    return decorated_function


def check_auth_token(required_role=None):
    """
    Verify the JWT auth token carried by the current request.

    The token is read from the ``PI-Authorization`` header; for
    backwards compatibility the standard ``Authorization`` header is
    accepted as a fallback. Raises ``AuthError`` (HTTP 401) if the
    token is missing, malformed, expired, or if its role does not
    match ``required_role``.

    On success ``g.logged_in_user`` is populated with ``username``,
    ``realm`` and ``role``.

    :param required_role: a list restricting which roles may pass —
        e.g. ``["admin"]`` or ``["user", "admin"]``. ``None`` means
        either role is acceptable.
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
    Return the token types the logged-in principal is allowed to
    enroll, computed from the active enrollment policies and the
    request's IP, user-agent and identity. The WebUI calls this
    immediately after login to render the enrollment UI.

    Requires authentication (any role).

    :reqheader PI-Authorization: JWT auth token returned by
        :http:post:`/auth`. ``Authorization`` is accepted as a
        fallback.
    :status 200: list of allowed enrollment token types in
        ``result.value``.
    """
    enroll_types = g.policy_object.ui_get_enroll_tokentypes(g.client_ip, g.logged_in_user, g.get("user_agent"))
    g.audit_object.log({"success": True})
    return send_result(enroll_types)
