# -*- coding: utf-8 -*-
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
import string

from ...lib.error import (ParameterError,
                          AuthError, ERROR)
from ...lib.log import log_with
from privacyidea.lib import _
from privacyidea.lib.utils import prepare_result, get_version, to_unicode
import time
import logging
import json
import jwt
import threading
import re
from copy import copy
from urllib.parse import unquote
from flask import (jsonify,
                   current_app)

log = logging.getLogger(__name__)
ENCODING = "utf-8"
TRUSTED_JWT_ALGOS = ["ES256", "ES384", "ES512",
                     "RS256", "RS384", "RS512",
                     "PS256", "PS384", "PS512"]

# The following user-agents (with versions) do not need extra unquoting
# TODO: we should probably switch this when we do not do the extra unquote anymore
NO_UNQUOTE_USER_AGENTS = {
    'privacyIDEA-LDAP-Proxy': None,
    'simpleSAMLphp': None,
    'privacyidea-cp': None
}

SESSION_KEY_LENGTH = 32

optional = True
required = False


def getParam(param, key, optional=True, default=None, allow_empty=True, allowed_values=None):
    """
    returns a parameter from the request parameters.

    :param param: the dictionary of parameters
    :type param: dict
    :param key: the name of the parameter
    :param optional: defines if this parameter is optional or not
                     an exception is thrown if the parameter is required
                     otherwise: nothing done!
    :type optional: bool
    :param default: The value to assign to the parameter, if it is not
                    contained in the param.
    :param allow_empty: Set to False is the parameter is a string and is
        not allowed to be empty
    :param allowed_values: A list of allowed values. If another value is given,
        then the default value is returned
    :type allow_empty: bool

    :return: the value (literal) of the parameter if exists or nothing
             in case the parameter is optional, otherwise throw an exception
    """
    ret = None

    if key in param:
        ret = param[key]
    elif default:
        ret = default
    elif not optional:
        raise ParameterError("Missing parameter: {0!r}".format(key), id=905)

    if not allow_empty and ret == "":
        raise ParameterError("Parameter {0!r} must not be empty".format(key), id=905)

    if allowed_values and ret not in allowed_values:
        ret = default

    return ret


def send_result(obj, rid=1, details=None):
    """
    sendResult - return a json result document

    :param obj: simple result object like dict, sting or list
    :type obj: dict or list or string/unicode
    :param rid: id value, for future versions
    :type rid: int
    :param details: optional parameter, which allows to provide more detail
    :type  details: None or simple type like dict, list or string/unicode

    :return: json rendered sting result
    :rtype: string
    """
    return jsonify(prepare_result(obj, rid, details))


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
    headers = {'Content-disposition': 'attachment; filename={0!s}'.format(filename)}
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
            output += "{0!s}{1!s}{2!s}, ".format(delim, k, delim)
        output += "\n"

        # Do the data
        for row in obj.get(data_key):
            for val in row.values():
                if isinstance(val, str):
                    value = val.replace("\n", " ")
                else:
                    value = val
                output += "{0!s}{1!s}{2!s}, ".format(delim, value, delim)
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
    # if no user agent is available, we assume that we must unquote the data
    if not request.user_agent.string:
        return {key: unquote(value) for (key, value) in data.items()}

    ua_match = re.match(r'^(?P<agent>[a-zA-Z0-9_-]+)(/(?P<version>\d+[\d.]*)(\s.*)?)?',
                        request.user_agent.string)
    if ua_match and not ua_match.group('agent') in NO_UNQUOTE_USER_AGENTS:
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
        log.debug("Update params in request {0!s} {1!s} with values.".format(request.method,
                                                                             request.base_url))
        # Add the unquoted HTML and form parameters
        return_param = check_unquote(request, request.values)

    if request.is_json:
        log.debug("Update params in request {0!s} {1!s} with JSON data.".format(request.method,
                                                                                request.base_url))
        # Add the original JSON data
        return_param.update(request.json)
    elif body:
        # In case of serialized JSON data in the body, add these to the values.
        try:
            json_data = json.loads(to_unicode(body))
            for k, v in json_data.items():
                return_param[k] = v
        except Exception as exx:
            log.debug("Can not get param: {0!s}".format(exx))

    if request.view_args:
        log.debug("Update params in request {0!s} {1!s} with view_args.".format(request.method,
                                                                                request.base_url))
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
        raise AuthError(_("Authentication failure. Missing Authorization header."),
                        id=ERROR.AUTHENTICATE_AUTH_HEADER)

    try:
        headers = jwt.get_unverified_header(auth_token)
    except jwt.DecodeError as err:
        raise AuthError(_("Authentication failure. Error during decoding your token: {0!s}").format(err),
                        id=ERROR.AUTHENTICATE_DECODING_ERROR)
    algorithm = headers.get("alg")
    wrong_username = None
    if algorithm in TRUSTED_JWT_ALGOS:
        # The trusted JWTs are RSA, PSS or elliptic curve signed
        trusted_jwts = current_app.config.get("PI_TRUSTED_JWT", [])
        for trusted_jwt in trusted_jwts:
            try:
                if trusted_jwt.get("algorithm") in TRUSTED_JWT_ALGOS:
                    j = jwt.decode(auth_token,
                                   trusted_jwt.get("public_key"),
                                   algorithms=[trusted_jwt.get("algorithm")])
                    if dict((k, j.get(k)) for k in ("role", "resolver", "realm")) == \
                            dict((k, trusted_jwt.get(k)) for k in ("role", "resolver", "realm")):
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
                raise AuthError(_("Authentication failure. Your token has expired: {0!s}").format(err),
                                id=ERROR.AUTHENTICATE_TOKEN_EXPIRED)

    if not r:
        try:
            r = jwt.decode(auth_token, current_app.secret_key, algorithms=['HS256'])
        except jwt.DecodeError as err:
            raise AuthError(_("Authentication failure. Error during decoding your token: {0!s}").format(err),
                            id=ERROR.AUTHENTICATE_DECODING_ERROR)
        except jwt.ExpiredSignatureError as err:
            raise AuthError(_("Authentication failure. Your token has expired: {0!s}").format(err),
                            id=ERROR.AUTHENTICATE_TOKEN_EXPIRED)
    if wrong_username:
        raise AuthError(_("Authentication failure. The username {0!s} is not allowed to "
                          "impersonate via JWT.".format(wrong_username)))
    if required_role and r.get("role") not in required_role:
        # If we require a certain role like "admin", but the users role does
        # not match
        raise AuthError(_("Authentication failure. "
                          "You do not have the necessary role ({0!s}) to access "
                          "this resource!").format(required_role),
                        id=ERROR.AUTHENTICATE_MISSING_RIGHT)
    return r


def check_policy_name(name):
    """
    This function checks, if the given name is a valid policy name.

    :param name: The name of the policy
    :return: Raises a ParameterError in case of an invalid name
    """
    disallowed_patterns = [("^check$", re.IGNORECASE),
                           ("^pi-update-policy-", re.IGNORECASE)]
    for disallowed_pattern in disallowed_patterns:
        if re.search(disallowed_pattern[0], name, flags=disallowed_pattern[1]):
            raise ParameterError(_("'{0!s}' is an invalid policy name.").format(name))

    if not re.match(r'^[a-zA-Z0-9_.\- ]*$', name):
        raise ParameterError(_("The name of the policy may only contain "
                               "the characters a-zA-Z0-9_. -"))


def attestation_certificate_allowed(cert_info, allowed_certs_pols):
    """
    Check a certificate against a set of policies.

    This will check an attestation certificate of a U2F-, or WebAuthn-Token,
    against a list of policies. It is used to verify, whether a token with the
    given attestation may be enrolled, or authorized, respectively.

    The certificate info may be None, in which case, true will be returned if
    the policies are also empty.

    :param cert_info: The `attestation_issuer`, `attestation_serial`, and `attestation_subject` of the cert.
    :type cert_info: dict or None
    :param allowed_certs_pols: The policies restricting enrollment, or authorization.
    :type allowed_certs_pols: dict or None
    :return: Whether the token should be allowed to complete enrollment, or authorization, based on its attestation.
    :rtype: bool
    """

    if not cert_info:
        return not allowed_certs_pols

    if allowed_certs_pols:
        for allowed_cert in allowed_certs_pols:
            tag, matching, _rest = allowed_cert.split("/", 3)
            tag_value = cert_info.get("attestation_{0!s}".format(tag))
            # if we do not get a match, we bail out
            m = re.search(matching, tag_value) if matching and tag_value else None
            if matching and not m:
                return False

    return True


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
