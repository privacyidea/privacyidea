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
                   current_app, Response)

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
from ...lib.error import (PolicyError, ResourceNotFoundError,
                          PrivacyIDEAError, AuthError, Error)
from ...lib.log import log_with

log = logging.getLogger(__name__)
ENCODING = "utf-8"
TRUSTED_JWT_ALGOS = ["ES256", "ES384", "ES512",
                     "RS256", "RS384", "RS512",
                     "PS256", "PS384", "PS512"]

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
            except jwt.DecodeError as _e:
                log.info("A given JWT definition does not match.")
            except jwt.ExpiredSignatureError as err:
                # We have the correct token. It expired, so we raise an error
                raise AuthError(_("Authentication failure. Your token has expired:") + f" {err!s}",
                                id=Error.AUTHENTICATE_TOKEN_EXPIRED)

    if not r:
        try:
            r = jwt.decode(auth_token, current_app.secret_key, algorithms=['HS256'])
        except jwt.DecodeError as err:
            raise AuthError(_("Authentication failure. Error decoding the Authorization token:") + f" {err!s}",
                            id=Error.AUTHENTICATE_DECODING_ERROR)
        except jwt.ExpiredSignatureError as err:
            raise AuthError(_("Authentication failure. Your token has expired:") + f" {err!s}",
                            id=Error.AUTHENTICATE_TOKEN_EXPIRED)
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
