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
                          AuthError)
from ...lib.log import log_with
import time
import threading
import pkg_resources
import logging
import json
import jwt
from flask import (jsonify,
                   current_app,
                   Response)

log = logging.getLogger(__name__)
ENCODING = "utf-8"

SESSION_KEY_LENGTH = 32

optional = True
required = False


def get_version_number():
    """
    returns the privacyidea version
    """
    version = "unknown"
    try:
        version = pkg_resources.get_distribution("privacyidea").version
    except:
        log.info("We are not able to determine the privacyidea version number.")
    return version


def get_version():
    """
    This returns the version, that is displayed in the WebUI and
    self service portal.
    """
    version = get_version_number()
    return "privacyIDEA {0!s}".format(version)


def getParam(param, key, optional=True, default=None):
    """
    returns a paramter from the request parameters.
    
    :param param: the dictionary of parameters
    :type param: dict
    :param key: the name of the parameter
    :param optional: defines if this parameter is optional or not
                     an exception is thrown if the parameter is required
                     otherwise: nothing done!
    :type optional: bool
    :param default: The value to assign to the parameter, if it is not
                    contained in the param.
    
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
    res = {"jsonrpc": "2.0",
           "result": {"status": True,
                      "value": obj},
           "version": get_version(),
           "versionnumber": get_version_number(),
           "id": rid,
           "time": time.time()}

    if details is not None and len(details) > 0:
        details["threadid"] = threading.current_thread().ident
        res["detail"] = details

    return jsonify(res)


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
    content_type = "application/force-download"
    headers = {'Content-disposition': 'attachment; filename={0!s}'.format(filename)}
    output = u""
    # Do the header
    for k, _v in obj.get(data_key, {})[0].items():
        output += "{0!s}{1!s}{2!s}, ".format(delim, k, delim)
    output += "\n"

    # Do the data
    for row in obj.get(data_key, {}):
        for val in row.values():
            if type(val) in [str, unicode]:
                value = val.replace("\n", " ")
            else:
                value = val
            output += "{0!s}{1!s}{2!s}, ".format(delim, value, delim)
        output += "\n"

    return Response(output, mimetype=content_type)


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
        json_data = json.loads(body)
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
    if required_role is None:
        required_role = ["admin", "user"]
    if auth_token is None:
        raise AuthError("Authentication failure",
                        "missing Authorization header",
                        status=401)
    try:
        r = jwt.decode(auth_token, current_app.secret_key)
    except jwt.DecodeError as err:
        raise AuthError("Authentication failure",
                        "error during decoding your token: {0!s}".format(err),
                        status=401)
    except jwt.ExpiredSignature as err:
        raise AuthError("Authentication failure",
                        "Your token has expired: {0!s}".format(err),
                        status=401)
    if required_role and r.get("role") not in required_role:
        # If we require a certain role like "admin", but the users role does
        # not match
        raise AuthError("Authentication failure",
                        "You do not have the necessary role (%s) to access "
                        "this resource!" % required_role,
                        status=401)
    return r
