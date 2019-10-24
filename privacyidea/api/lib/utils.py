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
import six
import re
from flask import (jsonify,
                   current_app)

log = logging.getLogger(__name__)
ENCODING = "utf-8"
TRUSTED_JWT_ALGOS = ["ES256", "ES384", "ES512",
                     "RS256", "RS384", "RS512",
                     "PS256", "PS384", "PS512"]

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
    '''
    sendResult - return an json result document

    :param obj: simple result object like dict, sting or list
    :type obj: dict or list or string/unicode
    :param rid: id value, for future versions
    :type rid: int
    :param details: optional parameter, which allows to provide more detail
    :type  details: None or simple type like dict, list or string/unicode

    :return: json rendered sting result
    :rtype: string
    '''
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
    Send the ouput as HTML to the client with the correct mimetype.

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
    :param output: The data that should be send as a file
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

    It takes a obj as a dict like:
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
    output = u""
    # check if there is any data
    if data_key in obj and len(obj[data_key]) > 0:
        # Do the header
        for k, _v in obj.get(data_key)[0].items():
            output += "{0!s}{1!s}{2!s}, ".format(delim, k, delim)
        output += "\n"

        # Do the data
        for row in obj.get(data_key):
            for val in row.values():
                if isinstance(val, six.string_types):
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


def get_all_params(param, body):
    """
    Combine parameters from GET and POST requests
    """
    return_param = {}
    for key in param.keys():
        return_param[key] = param[key]

    # In case of serialized JSON data in the body, add these to the values.
    try:
        json_data = json.loads(to_unicode(body))
        for k, v in json_data.items():
            return_param[k] = v
    except Exception as exx:
        log.debug("Can not get param: {0!s}".format(exx))

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
        if k.startswith("priority."):
            priority[k[len("priority."):]] = int(v)
    return priority


def verify_auth_token(auth_token, required_role=None):
    """
    Check if a given auth token is valid.

    Return a dictionary describing the authenticated user.

    :param auth_token: The Auth Token
    :param required_role: list of "user" and "admin"
    :return: dict with authtype, realm, rights, role, username, exp, nonce
    """
    r = None
    if required_role is None:
        required_role = ["admin", "user"]
    if auth_token is None:
        raise AuthError(_("Authentication failure. Missing Authorization header."),
                        id=ERROR.AUTHENTICATE_AUTH_HEADER)

    headers = jwt.get_unverified_header(auth_token)
    algorithm = headers.get("alg")
    if algorithm in TRUSTED_JWT_ALGOS:
        # The trusted JWTs are RSA, PSS or eliptic curve signed
        trusted_jwts = current_app.config.get("PI_TRUSTED_JWT", [])
        for trusted_jwt in trusted_jwts:
            try:
                if trusted_jwt.get("algorithm") in TRUSTED_JWT_ALGOS:
                    j = jwt.decode(auth_token,
                                   trusted_jwt.get("public_key"),
                                   algorithms=TRUSTED_JWT_ALGOS)
                    if dict((k, j.get(k)) for k in ("role", "user", "resolver", "realm")) == \
                            dict((k, trusted_jwt.get(k)) for k in ("role", "user", "resolver", "realm")):
                        r = j
                        break
                else:
                    log.warning(u"Unsupported JWT algorithm in PI_TRUSTED_JWT.")
            except jwt.DecodeError as err:
                log.info(u"A given JWT definition does not match.")
            except jwt.ExpiredSignature as err:
                # We have the correct token. It expired, so we raise an error
                raise AuthError(_("Authentication failure. Your token has expired: {0!s}").format(err),
                                id=ERROR.AUTHENTICATE_TOKEN_EXPIRED)

    if not r:
        try:
            r = jwt.decode(auth_token, current_app.secret_key, algorithms=['HS256'])
        except jwt.DecodeError as err:
            raise AuthError(_("Authentication failure. Error during decoding your token: {0!s}").format(err),
                            id=ERROR.AUTHENTICATE_DECODING_ERROR)
        except jwt.ExpiredSignature as err:
            raise AuthError(_("Authentication failure. Your token has expired: {0!s}").format(err),
                            id=ERROR.AUTHENTICATE_TOKEN_EXPIRED)
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
            raise ParameterError(_(u"'{0!s}' is an invalid policy name.").format(name))

    if not re.match('^[a-zA-Z0-9_.\- ]*$', name):
        raise ParameterError(_("The name of the policy may only contain "
                               "the characters a-zA-Z0-9_.- "))


