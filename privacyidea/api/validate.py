# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2014-12-08 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Complete rewrite during flask migration
#            Try to provide REST API
#
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
"""
from flask import (Blueprint, request, g, current_app)
from privacyidea.lib.user import get_user_from_param
from lib.utils import send_result, getParam
from ..lib.decorators import (check_user_or_serial_in_request)
from lib.utils import required
from privacyidea.lib.token import (check_user_pass, check_serial_pass)
from privacyidea.api.lib.utils import remove_session_from_param
from privacyidea.lib.audit import getAudit

validate_blueprint = Blueprint('validate_blueprint', __name__)


@validate_blueprint.before_request
def before_request():
    """
    This is executed before the request
    """
    request.all_data = remove_session_from_param(request.values, request.data)
    # Already get some typical parameters to log
    serial = getParam(request.all_data, "serial")
    realm = getParam(request.all_data, "realm")

    g.audit_object = getAudit(current_app.config)
    g.audit_object.log({"success": False,
                        "serial": serial,
                        "realm": realm,
                        "action": "token/%s" % request.url_rule,
                        "action_detail": "",
                        "info": ""})


@validate_blueprint.route('/check', methods=['POST', 'GET'])
@check_user_or_serial_in_request
def check():
    """
    check the authentication for a user or a serial number.
    Either a ``serial`` or a ``user`` is required to authenticate.
    The PIN and OTP value is sent in the parameter ``pass``.

    :param serial: The serial number of the token, that tries to authenticate.
    :param user: The loginname/username of the user, who tries to authenticate.
    :param realm: The realm of the user, who tries to authenticate. If the
        realm is omitted, the user is looked up in the default realm.
    :param pass: The password, that consists of the OTP PIN and the OTP value.

    :return: a json result with a boolean "result": true

    **Example response** for a succesful authentication:

       .. sourcecode:: http

           HTTP/1.1 200 OK
           Content-Type: application/json

           {
              "id": 1,
              "jsonrpc": "2.0",
              "result": {
                "status": true,
                "value": true
              },
              "version": "privacyIDEA unknown"
            }
    """
    user = get_user_from_param(request.all_data)
    serial = getParam(request.all_data, "serial")
    password = getParam(request.all_data, "pass", required)
    if serial:
        result, details = check_serial_pass(serial, password)
    else:
        result, details = check_user_pass(user, password)

    return send_result(result, details=details)


@validate_blueprint.route('/simplecheck', methods=['POST', 'GET'])
@check_user_or_serial_in_request
def simplecheck():
    """
    check the authentication for a user or a serial number.
    Either a ``serial`` or a ``user`` is required to authenticate.
    The PIN and OTP value is sent in the parameter ``pass``.

    :param serial: The serial number of the token, that tries to authenticate.
    :param user: The loginname/username of the user, who tries to authenticate.
    :param realm: The realm of the user, who tries to authenticate. If the
        realm is omitted, the user is looked up in the default realm.
    :param pass: The password, that consists of the OTP PIN and the OTP value.

    :return: a json result with a boolean "result": true

    **Example response** for a succesful authentication:

       .. sourcecode:: http

           HTTP/1.1 200 OK
           Content-Type: application/text

           :-)
    """
    user = get_user_from_param(request.all_data)
    serial = getParam(request.all_data, "serial")
    password = getParam(request.all_data, "pass", required)
    if serial:
        result, details = check_serial_pass(serial, password)
    else:
        result, details = check_user_pass(user, password)

    if result is True:
        ret = ":-)"
    else:
        ret = ":-("
    return ret


@validate_blueprint.route('/samlcheck', methods=['POST', 'GET'])
def samlcheck():
    raise NotImplementedError("samlcheck is not implemented, yet")
