# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
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

 * lib/token/check_user_pass (user, passw, options)
 * lib/token/check_token_list(list, passw, user, options)
 * lib/tokenclass/authenticate(pass, user, options)
 * lib/tokenclass/check_pin(pin, user, options)
 * lib/tokenclass/check_otp(otpval, options)

IN case if authenitcating a serial number:

 * lib/token/check_serial_pass(serial, passw, options)
 * lib/token/check_token_list(list, passw, user, options)
 * lib/tokenclass/authenticate(pass, user, options)
 * lib/tokenclass/check_pin(pin, user, options)
 * lib/tokenclass/check_otp(otpval, options)
"""
from flask import (Blueprint, request, g, current_app)
from privacyidea.lib.user import get_user_from_param
from lib.utils import send_result, getParam
from ..lib.decorators import (check_user_or_serial_in_request)
from lib.utils import required
from privacyidea.lib.token import (check_user_pass, check_serial_pass)
from privacyidea.api.lib.utils import get_all_params
from privacyidea.lib.config import return_saml_attributes
from privacyidea.lib.audit import getAudit
from privacyidea.api.lib.prepolicy import (prepolicy, set_realm,
                                           api_key_required, mangle)
from privacyidea.api.lib.postpolicy import (postpolicy,
                                            check_tokentype, check_serial,
                                            no_detail_on_fail,
                                            no_detail_on_success, autoassign,
                                            offline_info)
from privacyidea.lib.policy import PolicyClass
import logging
from privacyidea.api.lib.postpolicy import postrequest, sign_response
from privacyidea.api.auth import jwtauth
from privacyidea.api.register import register_blueprint
from privacyidea.api.recover import recover_blueprint

log = logging.getLogger(__name__)

validate_blueprint = Blueprint('validate_blueprint', __name__)


@validate_blueprint.before_request
@register_blueprint.before_request
@recover_blueprint.before_request
def before_request():
    """
    This is executed before the request
    """
    request.all_data = get_all_params(request.values, request.data)
    privacyidea_server = current_app.config.get("PI_AUDIT_SERVERNAME") or \
                         request.host
    # Create a policy_object, that reads the database audit settings
    # and contains the complete policy definition during the request.
    # This audit_object can be used in the postpolicy and prepolicy and it
    # can be passed to the innerpolicies.
    g.policy_object = PolicyClass()
    g.audit_object = getAudit(current_app.config)
    # access_route contains the ip adresses of all clients, hops and proxies.
    g.client_ip = request.access_route[0] if request.access_route else \
        request.remote_addr
    g.audit_object.log({"success": False,
                        "action_detail": "",
                        "client": g.client_ip,
                        "client_user_agent": request.user_agent.browser,
                        "privacyidea_server": privacyidea_server,
                        "action": "{0!s} {1!s}".format(request.method, request.url_rule),
                        "info": ""})


@validate_blueprint.after_request
@register_blueprint.after_request
@recover_blueprint.after_request
@jwtauth.after_request
@postrequest(sign_response, request=request)
def after_request(response):
    """
    This function is called after a request
    :return: The response
    """
    # In certain error cases the before_request was not handled
    # completely so that we do not have an audit_object
    if "audit_object" in g:
        g.audit_object.finalize_log()

    # No caching!
    response.headers['Cache-Control'] = 'no-cache'
    return response


@validate_blueprint.route('/check', methods=['POST', 'GET'])
@postpolicy(no_detail_on_fail, request=request)
@postpolicy(no_detail_on_success, request=request)
@postpolicy(offline_info, request=request)
@postpolicy(check_tokentype, request=request)
@postpolicy(check_serial, request=request)
@postpolicy(autoassign, request=request)
@prepolicy(set_realm, request=request)
@prepolicy(mangle, request=request)
@check_user_or_serial_in_request
@prepolicy(api_key_required, request=request)
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
    :param transaction_id: The transaction ID for a response to a challenge
        request
    :param state: The state ID for a response to a challenge request

    :return: a json result with a boolean "result": true

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
    """
    user = get_user_from_param(request.all_data)
    serial = getParam(request.all_data, "serial")
    password = getParam(request.all_data, "pass", required)
    options = {"g": g,
               "clientip": g.client_ip}
    # Add all params to the options
    for key, value in request.all_data.items():
            if value and key not in ["g", "clientip"]:
                options[key] = value

    g.audit_object.log({"user": user.login,
                        "realm": user.realm})

    if serial:
        result, details = check_serial_pass(serial, password, options=options)
    else:
        result, details = check_user_pass(user, password, options=options)

    g.audit_object.log({"info": details.get("message"),
                        "success": result,
                        "serial": serial or details.get("serial"),
                        "tokentype": details.get("type")})
    return send_result(result, details=details)


@validate_blueprint.route('/samlcheck', methods=['POST', 'GET'])
@postpolicy(no_detail_on_fail, request=request)
@postpolicy(no_detail_on_success, request=request)
@postpolicy(check_tokentype, request=request)
@postpolicy(check_serial, request=request)
@postpolicy(autoassign, request=request)
@prepolicy(set_realm, request=request)
@prepolicy(mangle, request=request)
@check_user_or_serial_in_request
@prepolicy(api_key_required, request=request)
def samlcheck():
    """
    Authenticate the user and return the SAML user information.

    :param user: The loginname/username of the user, who tries to authenticate.
    :param realm: The realm of the user, who tries to authenticate. If the
        realm is omitted, the user is looked up in the default realm.
    :param pass: The password, that consists of the OTP PIN and the OTP value.

    :return: a json result with a boolean "result": true

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

    The response in value->attributes can contain additional attributes
    (like "myOwn") which you can define in the LDAP resolver in the attribute
    mapping.
    """
    user = get_user_from_param(request.all_data)
    password = getParam(request.all_data, "pass", required)
    options = {"g": g,
               "clientip": g.client_ip}
    # Add all params to the options
    for key, value in request.all_data.items():
            if value and key not in ["g", "clientip"]:
                options[key] = value

    auth, details = check_user_pass(user, password, options=options)
    ui = user.info
    result_obj = {"auth": auth,
                  "attributes": {}}
    if return_saml_attributes():
        # privacyIDEA's own attribute map
        result_obj["attributes"] = {"username": ui.get("username"),
                                    "realm": user.realm,
                                    "resolver": user.resolver,
                                    "email": ui.get("email"),
                                    "surname": ui.get("surname"),
                                    "givenname": ui.get("givenname"),
                                    "mobile": ui.get("mobile"),
                                    "phone": ui.get("phone")
                                    }
        # additional attributes
        for k, v in ui.iteritems():
            result_obj["attributes"][k] = v

    g.audit_object.log({"info": details.get("message"),
                        "success": auth,
                        "serial": details.get("serial"),
                        "tokentype": details.get("type"),
                        "user": user.login,
                        "realm": user.realm})
    return send_result(result_obj, details=details)

