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
from flask_babel import _
import json
import logging
import re
import string
import threading
import time
from copy import copy
from urllib.parse import unquote

import jwt
from flask import (jsonify,
                   current_app, request, g, Response)

from privacyidea.lib.utils import (prepare_result, get_version, to_unicode,
                                   get_plugin_info_from_useragent)
# Re-exported from privacyidea.lib.params for backwards-compatibility with
# callers that import these names from privacyidea.api.lib.utils.
from privacyidea.lib.params import (  # noqa: F401
    _get_param,
    get_required,
    get_required_one_of,
    get_optional,
    get_optional_one_of,
    attestation_certificate_allowed,
)
# check_policy_name lives in lib/policy; re-exported here for backward compatibility
from privacyidea.lib.policy import check_policy_name  # noqa: F401
from privacyidea.lib.policy import Match, SCOPE
from privacyidea.lib.policies.actions import PolicyAction
from ...lib.error import (PolicyError, ResourceNotFoundError,
                          PrivacyIDEAError, AuthError, Error)
from ...lib.log import log_with

log = logging.getLogger(__name__)
ENCODING = "utf-8"
TRUSTED_JWT_ALGOS = ["ES256", "ES384", "ES512",
                     "RS256", "RS384", "RS512",
                     "PS256", "PS384", "PS512"]

INTERNAL_OPTION_KEYS = frozenset({
    "session",                   # stamps a challenge as enrollment -> enroll_via_validate
    "data",                      # email/SMS concurrent_challenges OTP cache
    "initTime",                  # overrides server time -> strips the TOTP time window
    "radius_result",             # short-circuits the real RADIUS Access-Request
    "radius_state",              # RADIUS intra-request state
    # NOTE: "challenge" is intentionally NOT stripped — it is a legitimate OCRA/DisplayTAN
    # client input (the transaction to sign, read by ocratoken.create_challenge); on the
    # transaction_id path check_challenge_response overwrites it from the stored challenge,
    # so it cannot be used to bypass authentication.
    "push_triggered",            # set by create_challenges_from_tokens
    "valid_token_num",           # server-set count of already-valid tokens (check_token_list -> pushtoken)
})

# The following user-agents (with versions) do not need extra unquoting
# TODO: we should probably switch this when we do not do the extra unquote anymore
NO_UNQUOTE_USER_AGENTS = {
    'privacyidea-cp': None,
    'privacyidea-ldap-proxy': None,
    'simplesamlphp': None
}

SESSION_KEY_LENGTH = 32



def send_result(obj, rid=1, details=None, **kwargs) -> Response:
    """
    sendResult - return a json result document

    :param obj: simple result object like dict, sting or list
    :type obj: dict or list or string/unicode
    :param rid: id value, for future versions
    :type rid: int
    :param details: optional parameter, which allows to provide more detail
    :type  details: None or simple type like dict, list or string/unicode

    :return: json rendered string result
    :rtype: string
    """
    return jsonify(prepare_result(obj, rid, details, **kwargs))


def send_error(errstring, rid=1, context=None, error_code=-311, details=None):
    """
    sendError - return a json error result document

    remark:
     the 'context' is especially required to catch errors from the _before_
     methods. The return of a _before_ must be of type response and
     must have the attribute response._exception set, to stop further
     processing, which otherwise will have ugly results!!

    :param errstring: An error message
    :type errstring: basestring
    :param rid: id value, for future versions
    :type rid: int
    :param context: default is None or 'before'
    :type context: string
    :param error_code: The error code in the JSON object along with the error
    message.
    :type error_code: int
    :param details: dict with additional details about the error (like
        challenges)
    :type details: dict

    :return: json rendered sting result
    :rtype: string

    """
    if details:
        details["threadid"] = threading.current_thread().ident
    res = {"jsonrpc": "2.0",
           "detail": details,
           "result": {"status": False,
                      "error": {"code": error_code,
                                "message": errstring}
                      },
           "version": get_version(),
           "id": rid,
           "time": time.time()
           }

    ret = jsonify(res)
    return ret


def send_html(output):
    """
    Send the output as HTML to the client with the correct mimetype.

    :param output: The HTML to send to the client
    :type output: str
    :return: The generated response
    :rtype: flask.Response
    """
    return current_app.response_class(output, mimetype='text/html')


def send_file(output, filename, content_type='text/csv'):
    """
    Send the output to the client with the "Content-disposition" header to
    declare it as a downloadable file.

    :param output: The data that should be sent as a file
    :type output: str
    :param filename: The proposed filename
    :type filename: str
    :param content_type: The proposed content type of the data
    :type content_type: str (should be something from this list:
                             https://www.iana.org/assignments/media-types/media-types.xhtml)
    :return: The generated response
    :rtype: flask.Response
    """
    headers = {'Content-disposition': f'attachment; filename={filename!s}'}
    return current_app.response_class(output, headers=headers, mimetype=content_type)


def send_csv_result(obj, data_key="tokens",
                    filename="privacyidea-tokendata.csv"):
    """
    returns a CSV document of the input data (like in /token/list)

    It takes an obj as a dict like:
    { "tokens": [ { ...token1... }, { ...token2....}, ... ],
      "count": 100,
      "....": .... }

    :param obj: The data, that gets serialized as CSV
    :type obj: dict
    :param data_key: The key, from which the list should be returned as CSV.
    Usually this is "tokens".
    :type data_key: basestring
    :param filename: The filename to save the CSV to.
    :type filename: basestring
    :return: The result serialized as a CSV
    :rtype: Response object
    """
    delim = "'"
    output = ""
    # check if there is any data
    if data_key in obj and len(obj[data_key]) > 0:
        # Do the header
        for k, _v in obj.get(data_key)[0].items():
            output += f"{delim!s}{k!s}{delim!s}, "
        output += "\n"

        # Do the data
        for row in obj.get(data_key):
            for val in row.values():
                if isinstance(val, str):
                    value = val.replace("\n", " ")
                else:
                    value = val
                output += f"{delim!s}{value!s}{delim!s}, "
            output += "\n"

    return send_file(output, filename)


@log_with(log)
def getLowerParams(param):
    ret = {}
    for key in param:
        lkey = key.lower()
        # strip the session parameter!
        if "session" != lkey:
            lval = param[key]
            ret[lkey] = lval
    return ret


def check_unquote(request, data):
    """
    Check if we need to unquote the given data.
    Based on the user-agent header of the request we unquote the given values
    in `data`. The user-agent string parsing is based on
    https://httpwg.org/specs/rfc9110.html#field.user-agent

    :param request: The Flask request context
    :type request: Flask.Request
    :param data: The dictionary containing the requested data
    :type data: dict
    :return: New dictionary with the possibly unquoted values
    :rtype: dict
    """
    ua_name, ua_version, _ua_comment = get_plugin_info_from_useragent(request.user_agent.string)
    # if no user agent is available, we assume that we must unquote the data
    if not ua_name:
        return {key: unquote(value) for (key, value) in data.items()}

    if ua_name.lower() not in NO_UNQUOTE_USER_AGENTS:
        return {key: unquote(value) for (key, value) in data.items()}
    else:
        return copy(data)


def get_all_params(request):
    """
    Retrieve all parameters from a request, no matter if these are GET or POST requests
    or parameters are contained as viewargs like the serial in DELETE /token/<serial>

    :param request: The flask request object
    """
    param = request.values
    body = request.data
    return_param = {}
    if param:
        log.debug(f"Update params in request {request.method!s} {request.base_url!s} with values.")
        # Add the unquoted HTML and form parameters
        return_param = check_unquote(request, request.values)

    if request.is_json:
        log.debug(f"Update params in request {request.method!s} {request.base_url!s} with JSON data.")
        # Add the original JSON data
        return_param.update(request.json)
    elif body:
        # In case of serialized JSON data in the body, add these to the values.
        try:
            json_data = json.loads(to_unicode(body))
            for k, v in json_data.items():
                return_param[k] = v
        except Exception as exx:
            log.debug(f"Can not get param: {exx!s}")

    if request.view_args:
        log.debug(f"Update params in request {request.method!s} {request.base_url!s} with view_args.")
        # We add the unquoted view_args
        return_param.update(check_unquote(request, request.view_args))

    return return_param


def get_priority_from_param(param):
    """
    Return a dictionary of priorities as int from params like
    priority.key1=value1

    :param param: The params dictionary
    :type param: dict
    :return: dict
    """
    priority = {}
    for k, v in param.items():
        if k.startswith("priority.") and isinstance(v, int):
            priority[k[len("priority."):]] = int(v)
    return priority


def verify_auth_token(auth_token, required_role=None):
    """
    Check if a given auth token is valid.

    Return a dictionary describing the authenticated user.

    :param auth_token: The Auth Token
    :param required_role: list of "user" and "admin"
    :return: dict with authtype, realm, rights, role, username, exp, nonce
    :rtype: dict
    """
    r = None
    if required_role is None:
        required_role = ["admin", "user"]
    if auth_token is None:
        raise AuthError(_("Authentication failure. Missing Authorization header."), id=Error.AUTHENTICATE_AUTH_HEADER)

    try:
        headers = jwt.get_unverified_header(auth_token)
    except jwt.DecodeError as err:
        raise AuthError(_("Authentication failure. Error decoding the Authorization token:") + f" {err!s}",
                        id=Error.AUTHENTICATE_DECODING_ERROR)
    algorithm = headers.get("alg")
    wrong_username = None
    if algorithm in TRUSTED_JWT_ALGOS:
        # The trusted JWTs are RSA, PSS or elliptic curve signed
        trusted_jwts = current_app.config.get("PI_TRUSTED_JWT", [])
        for trusted_jwt in trusted_jwts:
            try:
                if trusted_jwt.get("algorithm") in TRUSTED_JWT_ALGOS:
                    j = jwt.decode(auth_token, trusted_jwt.get("public_key"), algorithms=[trusted_jwt.get("algorithm")])
                    if (dict((k, j.get(k)) for k in ("role", "resolver", "realm")) ==
                            dict((k, trusted_jwt.get(k)) for k in ("role", "resolver", "realm"))):
                        if re.match(trusted_jwt.get("username") + "$", j.get("username")):
                            r = j
                            break
                        else:
                            r = wrong_username = j.get("username")
                else:
                    log.warning("Unsupported JWT algorithm in PI_TRUSTED_JWT.")
            except jwt.ExpiredSignatureError as err:
                # We have the correct token. It expired, so we raise an error
                raise AuthError(_("Authentication failure. Your token has expired:") + f" {err!s}",
                                id=Error.AUTHENTICATE_TOKEN_EXPIRED)
            except jwt.InvalidTokenError:
                # Wrong signature, wrong/disallowed algorithm, malformed, ... -> this
                # definition simply does not match; try the next one.
                log.info("A given JWT definition does not match.")

    if not r:
        try:
            r = jwt.decode(auth_token, current_app.secret_key, algorithms=['HS256'])
        except jwt.ExpiredSignatureError as err:
            raise AuthError(_("Authentication failure. Your token has expired:") + f" {err!s}",
                            id=Error.AUTHENTICATE_TOKEN_EXPIRED)
        except jwt.InvalidTokenError as err:
            # Covers DecodeError as well as InvalidAlgorithmError (a token whose alg is a
            # trusted-JWT algorithm but matches no PI_TRUSTED_JWT entry decodes here against
            # HS256 and would otherwise raise InvalidAlgorithmError). Normalising every
            # invalid token to an AuthError keeps callers from leaking an HTTP 500.
            raise AuthError(_("Authentication failure. Error decoding the Authorization token:") + f" {err!s}",
                            id=Error.AUTHENTICATE_DECODING_ERROR)
    if wrong_username:
        raise AuthError(_("Authentication failure. The username {wrong_username} "
                          "is not allowed to impersonate via JWT.").format(wrong_username=wrong_username))
    if required_role and r.get("role") not in required_role:
        # If we require a certain role like "admin", but the users role does
        # not match
        raise AuthError(_("Authentication failure. You do not have the necessary "
                          "role ({required_role}) to access this resource!").format(required_role=required_role),
                        id=Error.AUTHENTICATE_MISSING_RIGHT)
    return r


def get_auth_token_from_request():
    """
    Return the auth token presented on the current request, looking at the
    ``PI-Authorization`` header first and falling back to ``Authorization``.

    :return: the token string, or None if neither header is set
    """
    return request.headers.get("PI-Authorization") or request.headers.get("Authorization")


def logged_in_user_from_token(token_payload):
    """
    Build the standard ``g.logged_in_user`` dict from a verified/decoded auth
    token payload.

    :param token_payload: the dict returned by ``verify_auth_token`` (or a
        decoded JWT) carrying ``username``, ``realm`` and ``role``
    :return: dict with ``username``, ``realm`` and ``role``
    """
    return {"username": token_payload.get("username"),
            "realm": token_payload.get("realm"),
            "role": token_payload.get("role")}


def is_fqdn(x):
    """
    Check whether a given string could plausibly be a FQDN.

    This checks, whether a string could be a FQDN. Please note, that this
    function will currently return true for plenty of strings, that are not
    actually valid FQDNs. This is expected. This function performs a simple
    plausibility check to ward against obvious mistakes, like a user
    accidentally putting in a full url with protocol. The caller should not
    rely on this function, if it is absolutely crucial, that the checked
    string is a valid FQDN. It is solely intended to be used to implement user
    convenience, by alerting the user early on, if they have misunderstood
    a particular fields purpose.

    :param x: String to check.
    :type x: basestring
    :return: Whether the given string may plausibly be a FQDN.
    :rtype: bool
    """
    return set(string.punctuation).intersection(x).issubset({'-', '.'})


def map_error_to_code(error: Exception, default: int = 500) -> int:
    error_mapping: dict[type[Exception], int] = {
        PrivacyIDEAError: 400,
        AuthError: 401,
        PolicyError: 403,
        ResourceNotFoundError: 404,
        NotImplementedError: 501,
    }
    # return the code for the closest ancestor that is in the map
    for cls in type(error).mro():
        if cls in error_mapping:
            return error_mapping[cls]
    return default


def hardening_action_active(g, request, action) -> bool:
    """
    Return whether the given HARDENING-scope policy action matches the current
    request.

    Hardening policies are evaluated without user/realm/resolver/time conditions
    (client IP and user agent matching still apply). The evaluation is
    defensive: an incomplete request context (for example an error raised early
    in before_request, before g.client_ip was set) or a failure of the policy
    backend results in ``False`` rather than an exception, so callers in error
    handlers cannot themselves fail with a 500.
    """
    try:
        # Ensure g.policy_object and g.client_ip/user_agent are available even
        # when before_request failed early (e.g. an AuthError before the policy
        # object was created).
        if not hasattr(g, "policy_object"):
            from privacyidea.lib.policy import PolicyClass
            g.policy_object = PolicyClass()
        # Skip the policy evaluation entirely when no hardening policy is
        # configured. This keeps high-volume endpoints fast while the feature is
        # disabled instead of running a full policy match on every request.
        if not g.policy_object.list_policies(scope=SCOPE.HARDENING, active=True):
            return False
        # Match.action_only matches the client IP and user agent implicitly.
        if not hasattr(g, "client_ip") or not g.client_ip:
            from privacyidea.lib.config import get_from_config, SYSCONF
            from privacyidea.lib.utils import get_client_ip
            try:
                override_client = get_from_config(SYSCONF.OVERRIDECLIENT)
            except Exception:
                override_client = None
            g.client_ip = get_client_ip(request, override_client)
        if not g.get("user_agent"):
            ua_name, _ua_version, _ua_comment = get_plugin_info_from_useragent(request.user_agent.string)
            g.user_agent = ua_name
        return Match.action_only(g, scope=SCOPE.HARDENING, action=action).any(write_to_audit_log=False)
    except Exception:
        return False


def _is_authentication_endpoint(request) -> bool:
    """
    True if the current request targets an authentication endpoint: any
    /validate route, or the /auth login (not other jwtauth routes such as
    /auth/rights).
    """
    # The blueprint names are stable string constants, so we compare against
    # them directly instead of importing the blueprints (which would import
    # from this module) on the error-handling path.
    if request.blueprint == "validate_blueprint":
        return True
    return request.blueprint == "jwtauth" and request.path.endswith("/auth")


def get_auth_error_status_code(error: Exception) -> int:
    """
    Determine the HTTP status code for an error raised during authentication.

    Normally this is the error's mapped status code (e.g. 401 for AuthError,
    403 for PolicyError, 404 for ResourceNotFoundError, 400 for other
    PrivacyIDEAErrors such as a denied authorization). If the
    hide_auth_error_status policy (HARDENING scope) is set, the distinct 4xx
    codes are collapsed into a uniform 401, so the status code cannot be used
    to distinguish why the authentication failed.

    Server faults (5xx) are never masked, so a real internal error is not
    disguised as an authentication failure. Only requests to the authentication
    endpoints (the /auth login and /validate) are affected, so the same error
    types raised on other endpoints keep their regular status code.
    """
    mapped_code = map_error_to_code(error)
    # Already 401 -> nothing to normalize (avoids a policy match on the
    # high-volume failed-login path). Never collapse server faults to 401.
    if mapped_code == 401 or mapped_code >= 500:
        return mapped_code
    if not _is_authentication_endpoint(request):
        return mapped_code
    return 401 if hardening_action_active(g, request, PolicyAction.HIDE_AUTH_ERROR_STATUS) else mapped_code
