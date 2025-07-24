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

__doc__ = """This module contains the REST API for doing authentication.
The methods are tested in the file tests/test_api_validate.py

Authentication is either done by providing a username and a password or a
serial number and a password.

**Authentication workflow**

Authentication workflow is like this:

In case of authenticating a user:

 * :func:`privacyidea.lib.token.check_user_pass`
 * :func:`privacyidea.lib.token.check_token_list`
 * :func:`privacyidea.lib.tokenclass.TokenClass.authenticate`
 * :func:`privacyidea.lib.tokenclass.TokenClass.check_pin`
 * :func:`privacyidea.lib.tokenclass.TokenClass.check_otp`

In case if authenticating a serial number:

 * :func:`privacyidea.lib.token.check_serial_pass`
 * :func:`privacyidea.lib.token.check_token_list`
 * :func:`privacyidea.lib.tokenclass.TokenClass.authenticate`
 * :func:`privacyidea.lib.tokenclass.TokenClass.check_pin`
 * :func:`privacyidea.lib.tokenclass.TokenClass.check_otp`

"""

import copy
import json
import logging
import threading

from flask import (Blueprint, request, g, current_app)
from flask_babel import gettext

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
                                            multichallenge_enroll_via_validate, preferred_client_mode)
from privacyidea.api.lib.prepolicy import (prepolicy, set_realm,
                                           api_key_required, mangle,
                                           save_client_application_type,
                                           check_base_action, pushtoken_validate, fido2_auth,
                                           webauthntoken_authz,
                                           webauthntoken_request, check_application_tokentype,
                                           increase_failcounter_on_challenge, get_first_policy_value, fido2_enroll,
                                           disabled_token_types)
from privacyidea.api.lib.utils import get_all_params, get_optional_one_of
from privacyidea.api.recover import recover_blueprint
from privacyidea.api.register import register_blueprint
from privacyidea.lib.applications.offline import MachineApplication
from privacyidea.lib.audit import getAudit
from privacyidea.lib.challenge import get_challenges, extract_answered_challenges
from privacyidea.lib.config import (return_saml_attributes, get_from_config,
                                    return_saml_attributes_on_fail,
                                    SYSCONF, ensure_no_config_object, get_privacyidea_node)
from privacyidea.lib.container import find_container_for_token, find_container_by_serial, check_container_challenge
from privacyidea.lib.error import ParameterError, PolicyError
from privacyidea.lib.event import EventConfiguration
from privacyidea.lib.event import event
from privacyidea.lib.machine import list_machine_tokens
from privacyidea.lib.policy import ACTION, Match
from privacyidea.lib.policy import PolicyClass, SCOPE
from privacyidea.lib.subscriptions import CheckSubscription
from privacyidea.lib.token import (check_user_pass, check_serial_pass,
                                   check_otp, create_challenges_from_tokens, get_one_token)
from ..lib.fido2.util import get_fido2_token_by_credential_id, get_fido2_token_by_transaction_id
from ..lib.fido2.challenge import create_fido2_challenge, verify_fido2_challenge
from privacyidea.lib.token import get_tokens
from privacyidea.lib.tokenclass import CHALLENGE_SESSION
from privacyidea.lib.user import get_user_from_param, log_used_user, User
from privacyidea.lib.utils import get_client_ip, get_plugin_info_from_useragent
from privacyidea.lib.utils import is_true, get_computer_name_from_user_agent
from .lib.utils import required
from .lib.utils import send_result, getParam, get_required
from ..lib.decorators import (check_user_serial_or_cred_id_in_request)
from ..lib.fido2.policy_action import FIDO2PolicyAction
from ..lib.framework import get_app_config_value
from ..lib.users.custom_user_attributes import InternalCustomUserAttributes, INTERNAL_USAGE

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

    request.User = get_user_from_param(request.all_data)
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
    g.serial = getParam(request.all_data, "serial", default=None)
    ua_name, ua_version, _ua_comment = get_plugin_info_from_useragent(request.user_agent.string)
    g.user_agent = ua_name
    g.audit_object.log({"success": False,
                        "action_detail": "",
                        "client": g.client_ip,
                        "user_agent": ua_name,
                        "user_agent_version": ua_version,
                        "privacyidea_server": privacyidea_server,
                        "action": "{0!s} {1!s}".format(request.method, request.url_rule),
                        "thread_id": "{0!s}".format(threading.current_thread().ident),
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
    For HOTP token, this endpoint will return the amount of offline OTP values so that the client has the defined count,
    which is why the last pass is required.
    For WebAuthn/Passkey, this endpoint will return nothing specific.
    Every response contains the serial and a new refilltoken.
    Returns an error in case the token has been unmarked for offline use or if the refilltoken is incorrect.

    :param serial: The serial number of the token, that should be refilled.
    :param refilltoken: The authorization token, that allows refilling.
    :param pass: The last password (or password+OTP) entered by the user.
                 For WebAuthn/Passkey, the value should be empty ("").
    :return: Hashed OTP values (HOTP) or nothing (WebAuthn/Passkey). Returns an error in case the token has been
     unmarked for offline use or if the refilltoken is incorrect (out of sync).
    """
    serial = getParam(request.all_data, "serial", required)
    refilltoken_request = getParam(request.all_data, "refilltoken", required)
    password = getParam(request.all_data, "pass", required)
    tokens = get_tokens(serial=serial)
    if len(tokens) != 1:
        raise ParameterError("The token does not exist")
    else:
        token = tokens[0]
        # check if token is disabled or otherwise not fit for auth
        message_list = []
        if not token.check_all(message_list):
            log.info(f"Failed to offline refill: {message_list}")
            raise ParameterError("The token is not valid.")
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
                    raise ParameterError("Machine can not be identified by user agent!")
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
        raise ParameterError("Token is not an offline token or refill token is incorrect")


@validate_blueprint.route('/check', methods=['POST', 'GET'])
@validate_blueprint.route('/radiuscheck', methods=['POST', 'GET'])
@validate_blueprint.route('/samlcheck', methods=['POST', 'GET'])
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
@prepolicy(fido2_auth, request=request)
@check_user_serial_or_cred_id_in_request(request)
@CheckSubscription(request)
@prepolicy(api_key_required, request=request)
@event("validate_check", request, g)
def check():
    """
    .. important::
        The ``/validate/samlcheck`` endpoint will be deprecated in v3.12

    Check the authentication for a user or a serial number.
    Either a ``serial`` or a ``user`` is required to authenticate.
    The PIN and OTP value is sent in the parameter ``pass``.
    In case of successful authentication it returns ``result->value: true``.

    In case of a challenge response authentication a parameter ``exception=1``
    can be passed. This would result in an HTTP 500 Server Error response if
    an error occurred during sending of SMS or Email.

    In case ``/validate/radiuscheck`` is requested, the responses are
    modified as follows: A successful authentication returns an empty ``HTTP
    204`` response. An unsuccessful authentication returns an empty ``HTTP
    400`` response. Error responses are the same responses as for the
    ``/validate/check`` endpoint.

    :param serial: The serial number of the token, that tries to authenticate.
    :param user: The loginname/username of the user, who tries to authenticate.
    :param realm: The realm of the user, who tries to authenticate. If the
        realm is omitted, the user is looked up in the default realm.
    :param type: The tokentype of the tokens, that are taken into account during
        authentication. Requires the *authz* policy :ref:`application_tokentype_policy`.
        It is ignored when a distinct serial is given.
    :param pass: The password, that consists of the OTP PIN and the OTP value.
    :param otponly: If set to 1, only the OTP value is verified. This is used
        in the management UI. Only used with the parameter serial.
    :param transaction_id: The transaction ID for a response to a challenge
        request
    :param state: The state ID for a response to a challenge request

    :return: a json result with a boolean "result": true

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


    **Example response** for a successful authentication with ``/samlcheck``:

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
                "value": {"attributes": {
                            "username": "koelbel",
                            "realm": "themis",
                            "mobile": null,
                            "phone": null,
                            "myOwn": "/data/file/home/koelbel",
                            "resolver": "themis",
                            "surname": "Kölbel",
                            "givenname": "Cornelius",
                            "email": null},
                          "auth": true}
              },
              "version": "privacyIDEA unknown"
            }

    The response in ``value->attributes`` can contain additional attributes
    (like "myOwn") which you can define in the LDAP resolver in the attribute
    mapping.
    """
    user: User = request.User
    serial: str = getParam(request.all_data, "serial")
    password: str = getParam(request.all_data, "pass")
    otp_only: bool = getParam(request.all_data, "otponly")
    token_type: str = getParam(request.all_data, "type")

    # Add all params to the options
    options: dict = {}
    options.update(request.all_data)
    options.update({"g": g, "clientip": g.client_ip, "user": user})

    details: dict = {}
    # Passkey/FIDO2: Identify the user by the credential ID
    credential_id: str = get_optional_one_of(request.all_data, ["credential_id", "credentialid"])

    is_container_challenge = False

    # If only the credential ID is given, try to use it to identify the token
    if credential_id:
        # Find the token that responded to the challenge
        transaction_id: str = get_required(request.all_data, "transaction_id")
        if serial:
            token = get_one_token(serial=serial)
        else:
            token = get_fido2_token_by_credential_id(credential_id)
        if not token:
            log.debug(f"No token found for the given credential id {credential_id}. "
                      f"Trying to get the token by transaction id...")
            # For compatibility with the existing WebAuthn token, try to get the token via the transaction_id
            token = get_fido2_token_by_transaction_id(transaction_id, credential_id)
            if not token:
                log.debug(f"No token found for the given transaction id {transaction_id}.")
                return send_result(False, rid=2, details={
                    "message": "No token found for the given credential ID or transaction ID!"})

            if not token.user:
                return send_result(False, rid=2, details={
                    "message": "No user found for the token with the given credential ID!"})
        user = token.user

        # The request could also be an enrollment via validate. In that case, the param "attestationObject" is present
        # This does behave correctly but is obviously not a good solution in the long run
        attestation_object: str = get_optional_one_of(request.all_data, ["attestationObject", "attestationobject"])
        if attestation_object:
            request.all_data.update({"type": "passkey"})
            fido2_enroll(request, None)
            try:
                _ = token.update(request.all_data)
                r = 1
            except Exception as ex:
                log.error(f"Error updating token: {ex}")
                r = 0
        else:
            r: int = verify_fido2_challenge(transaction_id, token, request.all_data)
        result = r > 0
        success = result
        if r > 0:
            # If the authentication was successful, return the username of the token owner
            # TODO what is returned could be configurable, attribute mapping
            details = {"username": token.user.login,
                       "message": gettext("Found matching challenge"),
                       "serial": token.get_serial()}
    # End Passkey
    elif serial:
        if user:
            # Check if the given token belongs to the user
            if not get_tokens(user=user, serial=serial, count=True):
                raise ParameterError("Given serial does not belong to given user!")
        if not otp_only:
            success, details = check_serial_pass(serial, password, options=options)
        else:
            success, details = check_otp(serial, password)
        result = success

    else:
        # Check if the transaction_id belongs to a container challenge
        transaction_id = request.all_data.get("transaction_id")
        container_result = check_container_challenge(transaction_id)
        success = result = container_result.get("success", False)
        details = container_result.get("details", {})
        is_container_challenge = success

        if not success:
            # Challenge is for a token
            options["token_type"] = token_type
            success, details = check_user_pass(user, password, options=options)
            result = success
            if request.path.endswith("samlcheck"):
                result = {"auth": success, "attributes": {}}
                if return_saml_attributes():
                    if success or return_saml_attributes_on_fail():
                        # privacyIDEA's own attribute map
                        user_info = user.info
                        result["attributes"] = {"username": user_info.get("username"),
                                                "realm": user.realm,
                                                "resolver": user.resolver,
                                                "email": user_info.get("email"),
                                                "surname": user_info.get("surname"),
                                                "givenname": user_info.get("givenname"),
                                                "mobile": user_info.get("mobile"),
                                                "phone": user_info.get("phone")}
                        # Additional attributes
                        for k, v in user_info.items():
                            result["attributes"][k] = v
    # At this point there will be a user, even for FIDO2 credentials
    g.audit_object.log({"user": user.login, "resolver": user.resolver, "realm": user.realm})

    # update last authentication for all tokens
    if 'multi_challenge' in details:
        serial_list = [challenge_info["serial"] for challenge_info in details["multi_challenge"]]
    elif "serial" in details:
        serial_list = [details.get("serial")]
    else:
        serial_list = []

    if success:
        for serial in serial_list:
            # update container last_authentication
            if not is_container_challenge:
                try:
                    container = find_container_for_token(serial)
                    if container:
                        container.update_last_authentication()
                except Exception as e:
                    log.debug(f"Could not find container for token {serial}: {e}")

            # check policy if client mode per user shall be set
            client_mode_per_user_pol = Match.user(g, scope=SCOPE.AUTH, action=ACTION.CLIENT_MODE_PER_USER,
                                                  user_object=user).allowed()
            if client_mode_per_user_pol:
                # set the used token type as the preferred one for the user to indicate the preferred client mode for
                # the next authentication
                token = get_one_token(serial=serial, silent_fail=True)
                if token:
                    token_type = token.get_tokentype()
                    user_agent, _, _ = get_plugin_info_from_useragent(request.user_agent.string)
                    user.set_attribute(f"{InternalCustomUserAttributes.LAST_USED_TOKEN}_{user_agent}",
                                       token_type, INTERNAL_USAGE)

    serials = ",".join(serial_list)
    ret = send_result(result, rid=2, details=details)
    g.audit_object.log({"info": log_used_user(user, details.get("message")),
                        "success": success,
                        "authentication": ret.json.get("result").get("authentication") or "",
                        "serial": serials,
                        "token_type": details.get("type")})
    return ret


@validate_blueprint.route('/triggerchallenge', methods=['POST', 'GET'])
@admin_required
@postpolicy(is_authorized, request=request)
@postpolicy(mangle_challenge_response, request=request)
@postpolicy(preferred_client_mode, request=request)
@add_serial_from_response_to_g
@check_user_serial_or_cred_id_in_request(request)
@prepolicy(check_application_tokentype, request=request)
@prepolicy(increase_failcounter_on_challenge, request=request)
@prepolicy(check_base_action, request, action=ACTION.TRIGGERCHALLENGE)
@prepolicy(webauthntoken_request, request=request)
@prepolicy(fido2_auth, request=request)
@event("validate_triggerchallenge", request, g)
def trigger_challenge():
    """
    An administrator can call this endpoint if he has the right of
    ``triggerchallenge`` (scope: admin).
    He can pass a ``user`` name and or a ``serial`` number.
    privacyIDEA will trigger challenges for all native challenges response
    tokens, possessed by this user or only for the given serial number.

    The request needs to contain a valid PI-Authorization header.

    :param user: The loginname/username of the user, who tries to authenticate.
    :param realm: The realm of the user, who tries to authenticate. If the
        realm is omitted, the user is looked up in the default realm.
    :param serial: The serial number of the token.
    :param type: The tokentype of the tokens, that are taken into account during
        authentication. Requires authz policy application_tokentype.
        Is ignored when a distinct serial is given.

    :return: a json result with a "result" of the number of matching
        challenge response tokens

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
    serial = getParam(request.all_data, "serial")
    token_type = getParam(request.all_data, "type")
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
    result_obj = len(details.get("multi_challenge"))

    challenge_serials = [challenge_info["serial"] for challenge_info in details["multi_challenge"]]
    r = send_result(result_obj, rid=2, details=details)
    g.audit_object.log({
        "user": user.login,
        "resolver": user.resolver,
        "realm": user.realm,
        "success": result_obj > 0,
        "authentication": r.json.get("result").get("authentication"),
        "info": log_used_user(user, "triggered {0!s} challenges".format(result_obj)),
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
    Given a mandatory transaction ID, check if any non-expired challenge for this transaction ID
    has been answered. In this case, return true. If this is not the case, return false.
    This endpoint also returns false if no challenge with the given transaction ID exists.

    This is mostly useful for out-of-band tokens that should poll this endpoint
    to determine when to send an authentication request to ``/validate/check``.

    :jsonparam transaction_id: a transaction ID
    """

    if transaction_id is None:
        transaction_id = getParam(request.all_data, "transaction_id", required)
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
            if challenge.session == CHALLENGE_SESSION.DECLINED:
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
        if challenge_type == "token":
            user = get_one_token(serial=log_challenges[0].serial).user
        else:
            container = find_container_by_serial(log_challenges[0].serial)
            users = container.get_users()
            user = users[0] if users else User()
        if user:
            g.audit_object.log({
                "user": user.login,
                "resolver": user.resolver,
                "realm": user.realm,
            })

    # In any case, we log the transaction ID
    g.audit_object.log({
        "info": "status: {}".format(details.get("challenge_status")),
        "action_detail": "transaction_id: {}".format(transaction_id),
        "success": result
    })

    return send_result(result, rid=2, details=details)


@validate_blueprint.route('/initialize', methods=['POST', 'GET'])
@prepolicy(fido2_auth, request=request)
def initialize():
    """
    Start an authentication by requesting a challenge for a token type. Currently, supports only type passkey
    :jsonparam type: The type of the token, for which a challenge should be created.
    """
    token_type = get_required(request.all_data, "type")
    details = {}
    if token_type.lower() == "passkey":
        rp_id = get_first_policy_value(policy_action=FIDO2PolicyAction.RELYING_PARTY_ID, default="", scope=SCOPE.ENROLL)
        if not rp_id:
            raise PolicyError(f"Missing policy for {FIDO2PolicyAction.RELYING_PARTY_ID}, unable to create challenge!")

        user_verification = get_first_policy_value(policy_action=FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT,
                                                   default="preferred", scope=SCOPE.AUTH)
        challenge = create_fido2_challenge(rp_id, user_verification=user_verification)
        if f"passkey_{ACTION.CHALLENGETEXT}" in request.all_data:
            challenge["message"] = request.all_data[f"passkey_{ACTION.CHALLENGETEXT}"]
        details["passkey"] = challenge
        details["transaction_id"] = challenge["transaction_id"]
    else:
        raise ParameterError(f"Unsupported token type '{token_type}' for authentication initialization!")
    g.audit_object.log({"success": True})
    response = send_result(False, rid=2, details=details)
    return response
