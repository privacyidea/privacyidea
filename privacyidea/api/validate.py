# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2020-01-30 Jean-Pierre Höhmann <jean-pierre.hohemann@netknights.it>
#            Add WebAuthn token
# 2018-01-22 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add offline refill
# 2016-12-20 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add triggerchallenge endpoint
# 2016-10-23 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add subscription decorator
# 2016-09-05 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            SAML attributes on fail
# 2016-08-30 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            save client application type to database
# 2016-08-09 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add possibility to check OTP only
# 2015-11-19 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add support for transaction_id to saml_check
# 2015-06-17 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add policy decorator for API key requirement
# 2014-12-08 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Complete rewrite during flask migration
#            Try to provide REST API
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

__doc__ = """
The validate REST API verifies one-time passwords, drives challenge-
response flows, and supports out-of-band token polling. It is the
endpoint group that consumers (RADIUS plugins, SAML adapters, PAM
modules, web applications) call to actually authenticate a user.

This is distinct from :ref:`rest_auth`, which issues the JWT-based
admin/user session tokens for the management API.

The endpoints fall in five groups:

* :http:post:`/validate/check` — verify a user/serial + password and,
  for challenge-response tokens, trigger or complete the challenge.
  The ``/validate/radiuscheck`` URL alias shapes the response into
  RADIUS-friendly status codes (204 / 400) for protocol adapters.
* :http:post:`/validate/triggerchallenge` — admin-only, requires the
  ``triggerchallenge`` policy. Forces a challenge for every matching
  challenge-response token of a user.
* :http:get:`/validate/polltransaction` — anonymous. Out-of-band
  tokens (push, container) poll this to see whether a challenge has
  been answered.
* :http:post:`/validate/initialize` — anonymous. Bootstraps a
  FIDO2/passkey challenge before login.
* :http:post:`/validate/offlinerefill` — refills the OTP buffer of a
  token attached to a machine for offline use.

**Authentication workflow**

In case of authenticating a user:

 * :func:`privacyidea.lib.token.check_user_pass`
 * :func:`privacyidea.lib.token.check_token_list`
 * :func:`privacyidea.lib.tokenclass.TokenClass.authenticate`
 * :func:`privacyidea.lib.tokenclass.TokenClass.check_pin`
 * :func:`privacyidea.lib.tokenclass.TokenClass.check_otp`

In case of authenticating a serial number:

 * :func:`privacyidea.lib.token.check_serial_pass`
 * :func:`privacyidea.lib.token.check_token_list`
 * :func:`privacyidea.lib.tokenclass.TokenClass.authenticate`
 * :func:`privacyidea.lib.tokenclass.TokenClass.check_pin`
 * :func:`privacyidea.lib.tokenclass.TokenClass.check_otp`

See :ref:`client_modes` for the per-token-type interaction model that
clients consume from challenge responses.
"""

import copy
import json
import logging
import threading

from flask import (Blueprint, request, g, current_app, Response)
from flask_babel import _

from privacyidea.api.auth import admin_required
from privacyidea.api.lib.decorators import add_serial_from_response_to_g
from privacyidea.api.lib.postpolicy import (postpolicy,
                                            check_tokentype, check_serial,
                                            check_tokeninfo,
                                            no_detail_on_fail,
                                            no_detail_on_success, autoassign,
                                            offline_info,
                                            add_user_detail_to_response, construct_radius_response,
                                            mangle_challenge_response, is_authorized,
                                            multichallenge_enroll_via_validate, preferred_client_mode,
                                            hide_specific_error_message)
from privacyidea.api.lib.prepolicy import (prepolicy, set_realm,
                                           api_key_required, mangle,
                                           save_client_application_type,
                                           check_base_action, pushtoken_validate, fido2_auth,
                                           webauthntoken_authz,
                                           webauthntoken_request, check_application_tokentype,
                                           increase_failcounter_on_challenge, get_first_policy_value, fido2_enroll,
                                           disabled_token_types, load_challenge_text)
from privacyidea.api.lib.utils import get_all_params, get_optional_one_of, get_optional
from privacyidea.api.recover import recover_blueprint
from privacyidea.api.register import register_blueprint
from privacyidea.lib.applications.offline import MachineApplication
from privacyidea.lib.audit import getAudit
from privacyidea.lib.challenge import get_challenges, extract_answered_challenges, cancel_enrollment_via_multichallenge
from privacyidea.lib.config import (get_from_config,
                                    SYSCONF, ensure_no_config_object, get_privacyidea_node)
from privacyidea.lib.container import find_container_for_token, find_container_by_serial, check_container_challenge
from privacyidea.lib.error import ParameterError, PolicyError, ResourceNotFoundError, Error, AuthError, UserError
from privacyidea.lib.event import EventConfiguration
from privacyidea.lib.event import event
from privacyidea.lib.machine import list_machine_tokens, get_auth_items, attach_token
from privacyidea.lib.policy import Match
from privacyidea.lib.policy import PolicyClass, SCOPE
from privacyidea.lib.subscriptions import CheckSubscription
from privacyidea.lib.token import (check_user_pass, check_serial_pass,
                                   check_otp, create_challenges_from_tokens, get_one_token)
from privacyidea.lib.token import get_tokens
from privacyidea.lib.tokenclass import ChallengeSession
from privacyidea.lib.user import log_used_user, User, split_user
from privacyidea.lib.utils import get_client_ip, get_plugin_info_from_useragent, AUTH_RESPONSE
from privacyidea.lib.utils import is_true, get_computer_name_from_user_agent
from .lib.policyhelper import check_last_auth_policy, get_realm_for_authentication
from .lib.utils import get_required, map_error_to_code, send_error, send_result, log_authentication
from ..lib.conditional_access.authentication_error_codes import AuthEventType, AUTH_EVENT_TYPE_KEY
from ..lib.conditional_access.engine import is_user_locked, evaluate_lockout_policies
from ..lib.decorators import (check_user_serial_or_cred_id_in_request)
from ..models import db
from ..lib.fido2.challenge import create_fido2_challenge, verify_fido2_challenge
from ..lib.fido2.policy_action import FIDO2PolicyAction
from ..lib.fido2.util import get_fido2_token_by_credential_id, get_fido2_token_by_transaction_id
from ..lib.framework import get_app_config_value
from ..lib.policies.actions import PolicyAction
from ..lib.realm import get_default_realm
from ..lib.users.internal_user_attributes import InternalUserAttributes

log = logging.getLogger(__name__)

validate_blueprint = Blueprint('validate_blueprint', __name__)


@validate_blueprint.before_request
@register_blueprint.before_request
@recover_blueprint.before_request
def before_request():
    """
    This is executed before the request
    """
    ensure_no_config_object()
    # Save the request data
    g.request_data = get_all_params(request)
    request.all_data = copy.deepcopy(g.request_data)

    privacyidea_server = get_app_config_value("PI_AUDIT_SERVERNAME", get_privacyidea_node(request.host))
    # Create a policy_object, that reads the database audit settings
    # and contains the complete policy definition during the request.
    # This audit_object can be used in the postpolicy and prepolicy
    # It can be passed to the inner policies.

    g.policy_object = PolicyClass()

    g.audit_object = getAudit(current_app.config, g.startdate)
    g.event_config = EventConfiguration()
    # access_route contains the ip addresses of all clients, hops and proxies.
    g.client_ip = get_client_ip(request, get_from_config(SYSCONF.OVERRIDECLIENT))
    # Save the HTTP header in the localproxy object
    g.request_headers = request.headers
    g.serial = get_optional(request.all_data, "serial", default=None)
    ua_name, ua_version, _ua_comment = get_plugin_info_from_useragent(request.user_agent.string)
    g.user_agent = ua_name

    # Get user
    username = request.all_data.get("user", "")
    username, realm = split_user(username)
    realm = request.all_data.get("realm", realm)
    if username and not realm:
        realm = get_default_realm()
    # Check if a policy defines the realm
    realm = get_realm_for_authentication(g, username, realm)
    resolver = request.all_data.get("resolver")
    request.User = User(username, realm, resolver)
    request.all_data["realm"] = realm

    g.audit_object.log({"success": False,
                        "action_detail": "",
                        "client": g.client_ip,
                        "user_agent": ua_name,
                        "user_agent_version": ua_version,
                        "privacyidea_server": privacyidea_server,
                        "action": f"{request.method!s} {request.url_rule!s}",
                        "thread_id": f"{threading.current_thread().ident!s}",
                        "info": ""})
    # Add preliminary user to audit in case we fail with an error
    g.audit_object.log({
        "user": request.User.login,
        "resolver": request.User.resolver,
        "realm": request.User.realm})


@validate_blueprint.route('/offlinerefill', methods=['POST'])
@check_user_serial_or_cred_id_in_request(request)
@event("validate_offlinerefill", request, g)
def offlinerefill():
    """
    Replenish the OTP buffer of a token that is attached to a machine
    for offline use. Each successful refill rotates the
    ``refilltoken`` so that the previous one cannot be reused.

    For HOTP tokens, the response carries enough fresh OTP values to
    bring the offline buffer back up to the configured count. The
    caller must supply the last password (PIN+OTP) the end user
    entered so the server can advance the counter to the right
    position. For WebAuthn / Passkey tokens, the response carries
    only the new ``refilltoken`` and the WebAuthn/Passkey machine
    name is read from the user agent string; ``pass`` should be an
    empty string in that case.

    The response carries the new ``refilltoken``, the token serial,
    and the OTP material under
    ``response.auth_items.offline``. Failures may be masked into a
    generic error by the
    ``hide_specific_error_message_for_offline_refill`` user-scope
    policy.

    :jsonparam serial: token serial number (required).
    :jsonparam refilltoken: the refill authorization token issued on
        the previous refill or at offline attachment time (required).
    :jsonparam pass: the last PIN+OTP the user entered (required;
        empty string for WebAuthn / Passkey).
    :status 200: refill payload in the response body, with the new
        ``refilltoken`` and OTP material under
        ``auth_items.offline``.
    :status 400: the token does not exist, is not marked for offline
        use, the refilltoken is wrong, or the calling machine cannot
        be identified from the user agent (WebAuthn/Passkey).
    """
    serial = get_required(request.all_data, "serial")
    refilltoken_request = get_required(request.all_data, "refilltoken")
    password = get_required(request.all_data, "pass", allow_empty=True)
    try:
        tokens = get_tokens(serial=serial)
        if len(tokens) != 1:
            raise ParameterError(_("The token does not exist"))

        token = tokens[0]
        # check if token is disabled or otherwise not fit for auth
        message_list = []
        if not token.check_all(message_list):
            log.info(f"Failed to offline refill: {message_list}")
            raise ParameterError(_("The token is not valid."))
        token_attachments = list_machine_tokens(serial=serial, application="offline")
        if token_attachments:
            # TODO: Currently we do not distinguish, if a token had more than one offline attachment
            # check refill token depending on token type
            refilltoken_stored = None
            if token.type.lower() == "hotp":
                refilltoken_stored = token.get_tokeninfo("refilltoken")
            elif token.type.lower() in ["webauthn", "passkey"]:
                computer_name = get_computer_name_from_user_agent(request.user_agent.string)
                if not computer_name:
                    log.warning(f"Unable to refill because user agent does not contain a valid machine name: "
                                f"{request.user_agent.string}")
                    raise ParameterError(_("Machine can not be identified by user agent!"))
                refilltoken_stored = token.get_tokeninfo("refilltoken_" + computer_name)

            if refilltoken_stored and refilltoken_stored == refilltoken_request:
                # We need the options to pass the count and the rounds for the next offline OTP values,
                # which could have changed in the meantime.
                options = token_attachments[0].get("options")
                otps = MachineApplication.get_refill(token, password, options)
                refilltoken_new = MachineApplication.generate_new_refilltoken(token, request.user_agent.string)
                response = send_result(True)
                content = response.json
                content["auth_items"] = {"offline": [{"refilltoken": refilltoken_new,
                                                      "response": otps,
                                                      "serial": serial}]}
                response.set_data(json.dumps(content))
                return response
        raise ParameterError(_("Token is not an offline token or refill token is incorrect"))

    except Exception as e:
        if Match.user(
                g,
                scope=SCOPE.TOKEN,
                action=PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE_FOR_OFFLINE_REFILL,
                user_object=request.User if hasattr(request, "User") else None).any():
            return send_error("Failed offline token refill", error_code=Error.VALIDATE), map_error_to_code(e)
        raise


@validate_blueprint.route('/check', methods=['POST', 'GET'])
@validate_blueprint.route('/radiuscheck', methods=['POST', 'GET'])
@postpolicy(hide_specific_error_message)
@postpolicy(construct_radius_response, request=request)
@postpolicy(is_authorized, request=request)
@postpolicy(multichallenge_enroll_via_validate, request=request)
@postpolicy(mangle_challenge_response, request=request)
@postpolicy(preferred_client_mode, request=request)
@postpolicy(no_detail_on_fail, request=request)
@postpolicy(no_detail_on_success, request=request)
@postpolicy(add_user_detail_to_response, request=request)
@postpolicy(offline_info, request=request)
@postpolicy(check_tokeninfo, request=request)
@postpolicy(check_tokentype, request=request)
@postpolicy(check_serial, request=request)
@postpolicy(autoassign, request=request)
@add_serial_from_response_to_g
@prepolicy(check_application_tokentype, request=request)
@prepolicy(pushtoken_validate, request=request)
@prepolicy(set_realm, request=request)
@prepolicy(mangle, request=request)
@prepolicy(increase_failcounter_on_challenge, request=request)
@prepolicy(save_client_application_type, request=request)
@prepolicy(webauthntoken_request, request=request)
@prepolicy(webauthntoken_authz, request=request)
@prepolicy(disabled_token_types, request=request)
@prepolicy(load_challenge_text, request=request)
@prepolicy(fido2_auth, request=request)
@check_user_serial_or_cred_id_in_request(request)
@CheckSubscription(request)
@prepolicy(api_key_required, request=request)
@event("validate_check", request, g)
def check():
    """
    Verify an authentication attempt.

    The endpoint is bound to two URL paths that share the same
    request shape but produce different response shapes for protocol
    adapters:

    * ``/validate/check`` — standard JSON response, ``result.value``
      is ``true`` / ``false``.
    * ``/validate/radiuscheck`` — RADIUS adapter shape: a successful
      authentication returns an empty ``204``, a failed
      authentication an empty ``400``. Error responses (server-side
      faults) are the same as for ``/validate/check``.

    To return user attributes alongside the authentication result
    (the former ``/validate/samlcheck`` use case), enable the AUTHZ
    policies :ref:`policy_add_user_in_response` and/or
    :ref:`policy_add_resolver_in_response` on ``/validate/check``;
    the user info is then included under ``detail.user``.

    Either ``user`` (with optional ``realm``) or ``serial`` is
    required. The PIN+OTP is sent in ``pass``. Subsequent legs of a
    challenge-response flow carry ``transaction_id`` (and any
    additional fields the token type needs). The authorization
    decision can be vetoed by the AUTHZ-scope ``authorized=deny_access``
    policy (see :ref:`authorization_policies`).

    :jsonparam serial: token serial. Either ``serial`` or ``user`` is
        required.
    :jsonparam user: login name of the user. Either ``serial`` or
        ``user`` is required.
    :jsonparam realm: realm of the user; defaults to the default
        realm if omitted.
    :jsonparam pass: PIN concatenated with OTP. For WebAuthn/Passkey
        endpoints it may be empty.
    :jsonparam type: restrict the authentication to tokens of this
        type. Requires the AUTHZ policy
        :ref:`application_tokentype_policy`. Ignored when a serial
        is supplied.
    :jsonparam otponly: ``1`` to skip the PIN check and only verify
        the OTP value. Used by the management UI; only meaningful
        with ``serial``.
    :jsonparam transaction_id: transaction id for the second leg of
        a challenge-response flow.
    :jsonparam state: alias of ``transaction_id`` for legacy callers.
    :jsonparam exception: ``1`` to surface delivery failures (SMS,
        email, push) as HTTP 500 instead of returning a generic
        challenge-creation error.
    :jsonparam credential_id: FIDO2 credential id for passkey /
        WebAuthn authentication.
    :jsonparam cancel_enrollment: ``1`` together with
        ``transaction_id`` cancels an in-progress
        ``enroll_via_multichallenge`` flow without authenticating.

    **Example Validation Request**:

        .. sourcecode:: http

            POST /validate/check HTTP/1.1
            Host: example.com
            Accept: application/json

            user=user
            realm=realm1
            pass=s3cret123456

    **Example response** for a successful authentication:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
              "detail": {
                "message": "matching 1 tokens",
                "serial": "PISP0000AB00",
                "type": "spass"
              },
              "id": 1,
              "jsonrpc": "2.0",
              "result": {
                "status": true,
                "value": true
              },
              "version": "privacyIDEA unknown"
            }

    **Example response** for this first part of a challenge response authentication:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
              "detail": {
                "serial": "PIEM0000AB00",
                "type": "email",
                "transaction_id": "12345678901234567890",
                "multi_challenge": [ {"serial": "PIEM0000AB00",
                                      "transaction_id":  "12345678901234567890",
                                      "message": "Please enter otp from your email",
                                      "client_mode": "interactive"},
                                     {"serial": "PISM12345678",
                                      "transaction_id": "12345678901234567890",
                                      "message": "Please enter otp from your SMS",
                                      "client_mode": "interactive"}
                ]
              },
              "id": 2,
              "jsonrpc": "2.0",
              "result": {
                "status": true,
                "value": false
              },
              "version": "privacyIDEA unknown"
            }

    In this example two challenges are triggered, one with an email and one
    with an SMS. The application and thus the user has to decide, which one
    to use. They can use either.

    The challenges also contain the information of the "client_mode". This
    tells the plugin, whether it should display an input field to ask for the
    OTP value or e.g. to poll for an answered authentication.
    Read more at :ref:`client_modes`.

    .. note:: All challenge response tokens have the same ``transaction_id`` in
       this case.


    """
    # Conditional-access pre-check (step 1): runs before any token logic and
    # before the existing failcounter / max_auth checks. A currently-locked user
    # is rejected immediately with a generic failure response that leaks no
    # reason (the real reason is recorded only in the audit log).
    if is_user_locked(request.User):
        log.info(f"Rejecting authentication for locked user {request.User!r}.")
        g.audit_object.log({"success": False,
                            "info": "Rejected: account is temporarily locked"})
        return send_result(False, rid=2, details={})

    # Handle Enrollment Cancellation (Immediate Return)
    if is_true(request.all_data.get("cancel_enrollment")):
        return _handle_enrollment_cancellation(request.all_data)

    # This dictionary carries state across the extracted helper functions
    # to avoid changing the functional signatures of the underlying libraries yet.
    context = {
        "user": request.User,
        "result": False,
        "details": {},
        "response_params": {},
        "serial_list": [],
        "is_container_challenge": False,
        AUTH_EVENT_TYPE_KEY: None,
        "options": request.all_data.copy()
    }
    # Add standard context to options and the user object again, because options is passed down to every function
    context["options"].update({"g": g, "clientip": g.client_ip})
    context["options"]["user"] = context["user"]

    # Dispatch to Logic Handlers
    credential_id = get_optional_one_of(request.all_data, ["credential_id", "credentialid"])
    serial = get_optional(request.all_data, "serial")

    try:
        if credential_id:
            _handle_fido2_auth(context, credential_id)
        elif serial:
            _handle_serial_auth(context, serial)
        else:
            _handle_standard_auth(context)
        response = _finalize_auth_response(context)
    finally:
        # Write the single authentication-log row for this request, then let the
        # conditional-access engine react to the classified outcome. Both run in
        # the finally so they cover early returns and handler errors alike.
        _log_authentication_event(context)
        _evaluate_lockout_policies(context)
    return response


def _handle_enrollment_cancellation(data: dict) -> Response:
    """
    Handles the specific case where a user cancels enroll_via_multichallenge (possible if policy is enabled).
    Returns the Flask response object directly.
    """
    transaction_id = get_required(data, "transaction_id")
    success = cancel_enrollment_via_multichallenge(transaction_id)

    details = {}
    if success:
        details["message"] = _("Cancelled enrollment via multichallenge")
        message = _("Cancelled enrollment via multichallenge for transaction_id ") + f"{transaction_id}"
    else:
        details["message"] = _("Failed to cancel enrollment via multichallenge")
        message = _("Failed to cancel enrollment via multichallenge for transaction_id ") + f"{transaction_id}"

    ret = send_result(success, rid=2, details=details)

    g.audit_object.log({
        "success": success,
        "authentication": ret.json.get("result", {}).get("authentication", ""),
        "action_detail": message,
    })
    return ret


def _handle_fido2_auth(context: dict, credential_id: str):
    """
    Handles FIDO2/Passkey authentication and enroll_via_multichallenge of passkeys.
    Updates the context with the result.
    """
    transaction_id = get_required(request.all_data, "transaction_id")
    serial = get_optional(request.all_data, "serial")

    # Resolve Token
    if serial:
        token = get_one_token(serial=serial)
    else:
        token = get_fido2_token_by_credential_id(credential_id)

    if not token:
        log.debug(f"No token found for credential id {credential_id}. Checking transaction id...")
        token = get_fido2_token_by_transaction_id(transaction_id, credential_id)
        if not token:
            log.debug(f"No token found for transaction id {transaction_id}.")
            context["details"]["message"] = "No token found for the given credential ID or transaction ID!"
            context[AUTH_EVENT_TYPE_KEY] = AuthEventType.NO_TOKEN
            return  # Result remains False

    # Policy Checks
    if (PolicyAction.DISABLED_TOKEN_TYPES in request.all_data and
            token.get_type() in request.all_data[PolicyAction.DISABLED_TOKEN_TYPES]):
        raise PolicyError(_("The authentication method is not available."))

    if not token.user:
        context["details"]["message"] = "No user found for the token with the given credential ID!"
        context[AUTH_EVENT_TYPE_KEY] = AuthEventType.USER_UNKNOWN
        return  # Result remains False

    # Update User in Context
    user = token.user
    request.User = user
    context["user"] = user
    context["options"]["user"] = user
    # Handle Enrollment vs Authentication
    attestation_object = get_optional_one_of(request.all_data, ["attestationObject", "attestationobject"])

    if attestation_object:
        # Enrollment
        request.all_data.update({"type": "passkey"})
        fido2_enroll(request, None)
        try:
            registration_details = token.update(request.all_data)
            evm = registration_details.pop(PolicyAction.ENROLL_VIA_MULTICHALLENGE, None)

            # Check if offline data should be appended here already (policy)
            if evm and Match.user(g, scope=SCOPE.AUTH,
                                  action=PolicyAction.ENROLL_VIA_MULTICHALLENGE_PASSKEY_OFFLINE,
                                  user_object=user).any():
                __ = attach_token(token.get_serial(), "offline")
                offline_data = get_auth_items(serial=token.get_serial(), application="offline",
                                              user_agent=request.user_agent.string)
                if offline_data:
                    context["response_params"]["auth_items"] = offline_data

            context["result"] = True
        except Exception as ex:
            log.error(f"Error updating token: {ex}")
            context["result"] = False
    else:
        # Actual Authentication
        if not check_last_auth_policy(g, token):
            log.debug(f"Last authentication policy check failed for token {token.get_serial()}.")
            context["details"]["message"] = _(
                "Last authentication policy check failed for token {serial}").format(
                serial=token.get_serial())
            return

        if not token.is_active():
            log.debug(f"Authentication attempted with disabled token {token.get_serial()}")
            context["details"]["message"] = "Token is disabled"
            # Explicit audit for disabled token
            g.audit_object.log({
                "info": log_used_user(user, "Token is disabled"),
                "success": False,
                "authentication": AUTH_RESPONSE.REJECT,
                "serial": token.get_serial(),
                "token_type": context["details"].get("type")
            })
            context[AUTH_EVENT_TYPE_KEY] = AuthEventType.NO_TOKEN
            return

        try:
            fido_verification_result = verify_fido2_challenge(transaction_id, token, request.all_data)
        except (ResourceNotFoundError, AuthError):
            # The challenge could not be verified (e.g. answered for the wrong serial or expired) and propagates as a
            # failure. Record the outcome on the context; check() logs it once in its finally.
            context[AUTH_EVENT_TYPE_KEY] = AuthEventType.MFA_FAIL
            context["serial_list"].append(token.get_serial())
            raise
        context["result"] = fido_verification_result.success > 0

    # Success Handling
    if context["result"]:
        context["details"].update({
            "username": token.user.login,
            "message": _("Found matching challenge"),
            "serial": token.get_serial()
        })
        context["serial_list"].append(token.get_serial())
    else:
        context["details"]["message"] = _("Authentication failed.")

    context[AUTH_EVENT_TYPE_KEY] = AuthEventType.LOGIN_SUCCESS if context["result"] else AuthEventType.MFA_FAIL


def _handle_serial_auth(context: dict, serial: str):
    """
    Handles authentication with serial provided
    """
    user = context["user"]
    password = get_optional(request.all_data, "pass")
    otp_only = get_optional(request.all_data, "otponly")

    # Validate ownership if user is present
    if user:
        try:
            tokens = get_tokens(user=user, serial=serial, count=True)
            if not tokens:
                raise ParameterError(_("Given serial does not belong to given user!"))
        except ResourceNotFoundError:
            raise ParameterError(_("Given serial does not belong to given user!"))

    # Resolve the token owner so the auth log, audit log and per-user policies see the
    # authenticating user even when the request only carries a serial.
    if not user or not user.exist():
        token = get_one_token(serial=serial, silent_fail=True)
        if token and token.user:
            user = token.user
            request.User = user
            context["user"] = user
            context["options"]["user"] = user

    # Perform Check
    if not otp_only:
        success, details = check_serial_pass(serial, password, options=context["options"])
        context[AUTH_EVENT_TYPE_KEY] = details.pop(AUTH_EVENT_TYPE_KEY, None)
    else:
        success, details = check_otp(serial, password)
        context[AUTH_EVENT_TYPE_KEY] = AuthEventType.LOGIN_SUCCESS if success else AuthEventType.OTP_FAIL

    context["result"] = success
    context["details"] = details

    if "serial" in details:
        context["serial_list"].append(details["serial"])


def _handle_standard_auth(context: dict):
    """
    Handles username+otp/password authentication, or container challenges.
    """
    transaction_id = request.all_data.get("transaction_id")
    container_result = check_container_challenge(transaction_id)

    success = container_result.get("success", False)
    details = container_result.get("details", {})
    context["is_container_challenge"] = success

    if not success:
        # Fallback to standard user check
        token_type = get_optional(request.all_data, "type")
        context["options"]["token_type"] = token_type

        try:
            success, details = check_user_pass(context["user"], get_optional(request.all_data, "pass"),
                                               options=context["options"])
        except (UserError, AuthError):
            # An unknown user is rejected by the auth_user_does_not_exist policy decorator before check_user_pass can
            # classify it. Record the outcome on the context; check() logs it once in its finally.
            if not context["user"] or not context["user"].exist():
                context[AUTH_EVENT_TYPE_KEY] = AuthEventType.USER_UNKNOWN
                context["login"] = context["user"].login if context["user"] else None
            raise

        # A policy decorator (passthru, passonnouser, authcache, accept-no-token) can
        # accept the login without the token layer classifying it -> LOGIN_SUCCESS.
        if success and details.get(AUTH_EVENT_TYPE_KEY) is None:
            details[AUTH_EVENT_TYPE_KEY] = AuthEventType.LOGIN_SUCCESS

    context["result"] = success
    context["details"] = details

    event_type = details.pop(AUTH_EVENT_TYPE_KEY, None)
    context[AUTH_EVENT_TYPE_KEY] = event_type

    # Extract serials for logging
    if 'multi_challenge' in details:
        context["serial_list"].extend([c["serial"] for c in details["multi_challenge"]])
    elif "serial" in details:
        context["serial_list"].append(details["serial"])


def _finalize_auth_response(context):
    """
    Handles final state updates (last_auth), audit logging, and response construction.
    """
    user = context["user"]
    details = context["details"]
    success = context["result"]

    # Update Last Authentication
    # FIDO2 tokens update this internally during verify, so we skip them here mostly,
    # but check if we have serials from standard flows.
    if success:
        for serial in context["serial_list"]:
            if not context["is_container_challenge"]:
                try:
                    container = find_container_for_token(serial)
                    if container:
                        container.update_last_authentication()
                except Exception as e:
                    log.debug(f"Could not find container for token {serial}: {e}")

            # Client Mode Per User Policy
            if Match.user(g, scope=SCOPE.AUTH, action=PolicyAction.CLIENT_MODE_PER_USER,
                          user_object=user).allowed():
                token = get_one_token(serial=serial, silent_fail=True)
                if token:
                    user_agent, __, __ = get_plugin_info_from_useragent(request.user_agent.string)
                    if user.exist():
                        # Read-modify-write on a per-user dict. Concurrent auths from
                        # different user-agents can race here and lose one update.
                        # Accepted: the value is a UX hint (preferred client mode) —
                        # at worst the user sees their second-most-recent choice.
                        last_used = dict(user.internal_attributes.get(
                            InternalUserAttributes.LAST_USED_TOKEN) or {})
                        last_used[user_agent] = token.get_tokentype()
                        user.set_internal_attribute(InternalUserAttributes.LAST_USED_TOKEN, last_used)

    # Audit Logging
    # Ensure user is logged even if we switched users (e.g. FIDO2)
    g.audit_object.log({"user": user.login, "resolver": user.resolver, "realm": user.realm})

    serials_str = ",".join(context["serial_list"])
    ret = send_result(context["result"], rid=2, details=details, **context["response_params"])

    g.audit_object.log({
        "info": log_used_user(user, details.get("message")),
        "success": success,
        "authentication": ret.json.get("result", {}).get("authentication", ""),
        "serial": serials_str,
        "token_type": details.get("type")
    })

    return ret


def _log_authentication_event(context):
    """
    Write the single authentication-log row for this /validate/check request.

    Called from check()'s finally, so it runs exactly once whether the request succeeded or a handler raised. The
    classified outcome is read from the explicit *context* dict (no framework global), and log_authentication is a
    no-op if nothing classified the request.
    """
    log_authentication(
        context[AUTH_EVENT_TYPE_KEY],
        user=context["user"],
        serial=",".join(context["serial_list"]) or None,
        transaction_id=(request.all_data.get("transaction_id") or request.all_data.get("state")
                        or context["details"].get("transaction_id")),
        login=context.get("login"),
    )


def _evaluate_lockout_policies(context):
    """
    Run the conditional-access policy engine (step 5) for this request's
    classified outcome.

    Called from check()'s finally, after the authentication-log row is written,
    so a failure count over the log includes the just-written event. This only
    produces side effects that the NEXT inbound request consults (it writes
    lockout state); it must never alter or break the response that already
    completed, so every error is swallowed. It deliberately returns nothing — a
    ``return`` inside the finally would mask an in-flight exception.
    """
    try:
        evaluate_lockout_policies(context["user"], context[AUTH_EVENT_TYPE_KEY], source_ip=g.client_ip)
    except Exception as ex:
        log.warning(f"Conditional-access policy evaluation failed: {ex!r}")
        # A prior handler error may have left the session in an aborted state;
        # clear it so request teardown can proceed cleanly.
        try:
            db.session.rollback()
        except Exception:
            pass


@validate_blueprint.route('/triggerchallenge', methods=['POST', 'GET'])
@admin_required
@postpolicy(is_authorized, request=request)
@postpolicy(mangle_challenge_response, request=request)
@postpolicy(preferred_client_mode, request=request)
@add_serial_from_response_to_g
@check_user_serial_or_cred_id_in_request(request)
@prepolicy(check_application_tokentype, request=request)
@prepolicy(increase_failcounter_on_challenge, request=request)
@prepolicy(check_base_action, request, action=PolicyAction.TRIGGERCHALLENGE)
@prepolicy(webauthntoken_request, request=request)
@prepolicy(load_challenge_text, request=request)
@prepolicy(fido2_auth, request=request)
@event("validate_triggerchallenge", request, g)
def trigger_challenge():
    """
    Trigger a fresh challenge for every challenge-response token
    matching the given user and/or serial. Used by the WebUI and by
    automation that must initiate challenge-response flows on behalf
    of a user (for example pre-positioning a push prompt).

    Requires admin authentication and the policy action
    :ref:`policy_triggerchallenge`. The request must carry a valid
    ``PI-Authorization`` header.

    If the AUTHZ-scope ``increase_failcounter_on_challenge`` policy
    is active, the fail counter is incremented on every matching
    token before the challenges are created.

    :jsonparam user: user the challenges should be created for.
    :jsonparam realm: realm of the user; defaults to the default
        realm.
    :jsonparam serial: restrict to a specific token.
    :jsonparam type: restrict to tokens of this type. Requires the
        AUTHZ policy :ref:`application_tokentype_policy`. Ignored
        when ``serial`` is supplied.
    :reqheader PI-Authorization: admin auth token.
    :status 200: ``result.value`` is the number of created
        challenges; ``detail.multi_challenge`` lists them.

    **Example response** for a successful triggering of challenge:

       .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
               "detail": {
                    "client_mode": "interactive",
                    "message": "please enter otp: , please enter otp: ",
                    "messages":     [
                        "please enter otp: ",
                        "please enter otp: "
                    ],
                    "multi_challenge": [
                        {
                            "client_mode": "interactive",
                            "message": "please enter otp: ",
                            "serial": "TOTP000026CB",
                            "transaction_id": "11451135673179897001",
                            "type": "totp"
                        },
                        {
                            "client_mode": "interactive",
                            "message": "please enter otp: ",
                            "serial": "OATH0062752C",
                            "transaction_id": "11451135673179897001",
                            "type": "hotp"
                        }
                    ],
                    "serial": "OATH0062752C",
                    "threadid": 140329819764480,
                    "transaction_id": "11451135673179897001",
                    "transaction_ids": [
                        "11451135673179897001",
                        "11451135673179897001"
                    ],
                    "type": "hotp"
               },
               "id": 2,
               "jsonrpc": "2.0",
               "result": {
                   "status": true,
                   "value": 2
               }

    **Example response** for response, if the user has no challenge token:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
              "detail": {"messages": [],
                         "threadid": 140031212377856,
                         "transaction_ids": []},
              "id": 1,
              "jsonrpc": "2.0",
              "result": {"status": true,
                         "value": 0},
              "signature": "205530282...54508",
              "time": 1484303812.346576,
              "version": "privacyIDEA 2.17",
              "versionnumber": "2.17"
            }

    **Example response** for a failed triggering of a challenge. In this case
    the ``status`` will be ``false``.

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
              "detail": null,
              "id": 1,
              "jsonrpc": "2.0",
              "result": {"error": {"code": 905,
                                   "message": "ERR905: The user can not be
                                   found in any resolver in this realm!"},
                         "status": false},
              "signature": "14468...081555",
              "time": 1484303933.72481,
              "version": "privacyIDEA 2.17"
            }

    """
    user = request.User
    serial = get_optional(request.all_data, "serial")
    token_type = get_optional(request.all_data, "type")
    details = {"messages": [], "transaction_ids": []}

    # Add all params to the options
    options: dict = {}
    options.update(request.all_data)
    options.update({"g": g, "clientip": g.client_ip, "user": user})

    tokens = get_tokens(serial=serial, user=user, active=True, revoked=False, locked=False, tokentype=token_type)
    # Only use the tokens that are allowed to do challenge
    challenge_response_token = [token for token in tokens if "challenge" in token.mode]
    if is_true(options.get("increase_failcounter_on_challenge")):
        for token in challenge_response_token:
            token.inc_failcount()
    create_challenges_from_tokens(challenge_response_token, details, options)
    triggered_challenges = len(details.get("multi_challenge"))

    log_authentication(
        AuthEventType.CHALLENGE_TRIGGERED if triggered_challenges else AuthEventType.NO_TOKEN,
        user=user,
        serial=details.get("serial"),
        transaction_id=details.get("transaction_id"),
    )

    challenge_serials = [challenge_info["serial"] for challenge_info in details["multi_challenge"]]
    r = send_result(triggered_challenges, rid=2, details=details)
    g.audit_object.log({
        "user": user.login,
        "resolver": user.resolver,
        "realm": user.realm,
        "success": triggered_challenges > 0,
        "authentication": r.json.get("result").get("authentication"),
        "info": log_used_user(user, f"triggered {triggered_challenges!s} challenges"),
        "serial": ",".join(challenge_serials),
    })

    return r


@validate_blueprint.route('/polltransaction', methods=['GET'])
@validate_blueprint.route('/polltransaction/<transaction_id>', methods=['GET'])
@prepolicy(mangle, request=request)
@CheckSubscription(request)
@prepolicy(api_key_required, request=request)
@event("validate_poll_transaction", request, g)
def poll_transaction(transaction_id=None):
    """
    Report whether a challenge has been answered. Out-of-band tokens
    (push, container) poll this endpoint to learn when the user has
    interacted with the challenge so that the calling client can
    follow up with :http:post:`/validate/check`.

    This endpoint is anonymous — no authentication header is
    required.

    :param transaction_id: optional path component, the transaction
        id to check. May also be supplied as a query parameter.
    :query transaction_id: alternative to the path component.
    :status 200: ``result.value`` is ``true`` if at least one
        non-expired challenge with this transaction id has been
        answered, ``false`` otherwise. ``detail.challenge_status`` is
        one of ``accept`` (an answered challenge exists),
        ``declined`` (the user declined a challenge), or ``pending``
        (the challenges are still open or no matching challenge
        exists at all).
    """

    if transaction_id is None:
        transaction_id = get_required(request.all_data, "transaction_id")
    # Fetch a list of challenges that are not expired with the given transaction ID
    # and determine whether it contains at least one non-expired answered challenge.
    matching_challenges = [challenge for challenge in get_challenges(transaction_id=transaction_id)
                           if challenge.is_valid()]
    answered_challenges = extract_answered_challenges(matching_challenges)
    declined_challenges = []
    if answered_challenges:
        result = True
        log_challenges = answered_challenges
        details = {"challenge_status": "accept"}
    else:
        result = False
        for challenge in matching_challenges:
            if challenge.session == ChallengeSession.DECLINED:
                declined_challenges.append(challenge)
        if declined_challenges:
            log_challenges = declined_challenges
            details = {"challenge_status": "declined"}
        else:
            log_challenges = matching_challenges
            details = {"challenge_status": "pending"}

    # We now determine the information that should be written to the audit log:
    # * If there are no answered valid challenges, we log all token serials of challenges matching
    #   the transaction ID and the corresponding token owner
    # * If there are any answered valid challenges, we log their token serials and the corresponding user
    if log_challenges:
        g.audit_object.log({
            "serial": ",".join(challenge.serial for challenge in log_challenges),
        })
        # check if the challenge is from a token or container
        challenge = log_challenges[0]
        challenge_type = "token"
        if challenge.data:
            try:
                challenge_data = json.loads(challenge.data)
                if isinstance(challenge_data, dict):
                    challenge_type = challenge_data.get("type", "token")
            except json.JSONDecodeError:
                pass
        if challenge_type == "container":
            container = find_container_by_serial(log_challenges[0].serial)
            users = container.get_users()
            user = users[0] if users else User()
        else:
            user = get_one_token(serial=log_challenges[0].serial).user

        if user:
            g.audit_object.log({
                "user": user.login,
                "resolver": user.resolver,
                "realm": user.realm,
            })

    # In any case, we log the transaction ID
    g.audit_object.log({
        "info": f"status: {details.get('challenge_status')}",
        "action_detail": f"transaction_id: {transaction_id}",
        "success": result
    })

    return send_result(result, rid=2, details=details)


@validate_blueprint.route('/initialize', methods=['POST', 'GET'])
@prepolicy(fido2_auth, request=request)
@prepolicy(disabled_token_types, request=request)
def initialize():
    """
    Initialize an authentication by requesting a fresh challenge for
    a token type. Currently only the ``passkey`` type is supported;
    the WebUI calls this to obtain the FIDO2 challenge it then
    forwards to the browser's ``navigator.credentials.get`` call.

    For ``passkey``, the ``webauthn_relying_party_id`` policy must
    be set (the FIDO2 prepolicy reads it from the AUTH scope); the
    user-verification requirement is taken from the
    ``user_verification_requirement`` policy and defaults to
    ``preferred``.

    This endpoint is anonymous — no authentication header is
    required.

    :jsonparam type: the token type to initialize a challenge for
        (``passkey``; required).
    :status 200: ``result.value`` is ``false`` (no authentication
        decision yet); ``detail.transaction_id`` carries the
        transaction id and ``detail.passkey`` carries the FIDO2
        challenge payload that the client must pass to the
        authenticator.
    :status 400: the requested ``type`` is unsupported, the token
        type is disabled by policy, or the relying-party id policy
        is missing.
    """
    token_type = get_required(request.all_data, "type")
    details = {}
    if PolicyAction.DISABLED_TOKEN_TYPES in request.all_data:
        if token_type in request.all_data[PolicyAction.DISABLED_TOKEN_TYPES]:
            raise PolicyError(_("The authentication method is not available."))

    if token_type.lower() == "passkey":
        rp_id = request.all_data[FIDO2PolicyAction.RELYING_PARTY_ID]
        if not rp_id:
            raise PolicyError(
                f"Missing policy for {FIDO2PolicyAction.RELYING_PARTY_ID}, unable to create challenge!")

        user_verification = get_first_policy_value(policy_action=FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT,
                                                   default="preferred", scope=SCOPE.AUTH)
        challenge = create_fido2_challenge(rp_id, user_verification=user_verification)
        if f"passkey_{PolicyAction.CHALLENGETEXT}" in request.all_data:
            challenge["message"] = request.all_data[f"passkey_{PolicyAction.CHALLENGETEXT}"]
        details["passkey"] = challenge
        details["transaction_id"] = challenge["transaction_id"]
    else:
        raise ParameterError(
            _("Unsupported token type '{token_type}' for authentication initialization!").format(
                token_type=token_type
            )
        )

    log_authentication(AuthEventType.CHALLENGE_TRIGGERED, transaction_id=details.get("transaction_id"))

    g.audit_object.log({"success": True})
    response = send_result(False, rid=2, details=details)
    return response
