# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) Cornelius Kölbel, privacyidea.org
#
# 2016-06-15 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Initial writeup
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
This endpoint is used to create, modify, list and delete SMS gateway
definitions.
These gateway definitions are written to the database table "smsgateway" and
"smsgatewayoption".

The code of this module is tested in tests/test_api_smsgateway.py
"""
from flask import (Blueprint,
                   request)
from .lib.utils import getParam, send_result
from ..lib.log import log_with
from flask import g
import logging
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.policy import ACTION
from privacyidea.lib.smsprovider.SMSProvider import (SMS_PROVIDERS,
                                                     get_smsgateway,
                                                     set_smsgateway,
                                                     delete_smsgateway_option,
                                                     delete_smsgateway,
                                                     get_sms_provider_class)

log = logging.getLogger(__name__)


smsgateway_blueprint = Blueprint('smsgateway_blueprint', __name__)


@smsgateway_blueprint.route('', methods=['GET'])
@smsgateway_blueprint.route('/<gwid>', methods=['GET'])
@log_with(log)
def get_gateway(gwid=None):
    """
    returns a json list of the gateway definitions

    Or

    returns a list of available sms providers with their configuration
    /smsgateway/providers

    """
    res = {}
    # TODO: if the gateway definitions contains a password normal users should
    #  not be allowed to read the configuration. Normal users should only be
    # allowed to read the identifier of the definitions!
    if gwid == "providers":
        for classname in SMS_PROVIDERS:
            smsclass = get_sms_provider_class(classname.rsplit(".", 1)[0],
                                              classname.rsplit(".", 1)[1])
            res[classname] = smsclass.parameters()
    else:
        res = [gw.as_dict() for gw in get_smsgateway(id=gwid)]

    g.audit_object.log({"success": True})
    return send_result(res)


@smsgateway_blueprint.route('', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.SMSGATEWAYWRITE)
def set_gateway():
    """
    This creates a new SMS gateway definition or updates an existing one.

    :jsonparam name: The unique identifier of the SMS gateway definition
    :jsonparam module: The providermodule name
    :jsonparam description: An optional description of the definition
    :jsonparam options.*: Additional options for the provider module (module
        specific)
    """
    param = request.all_data
    identifier = getParam(param, "name", optional=False)
    providermodule = getParam(param, "module", optional=False)
    description = getParam(param, "description", optional=True)
    options = {}
    for k, v in param.iteritems():
        if k.startswith("option."):
            options[k[7:]] = v

    res = set_smsgateway(identifier, providermodule, description,
                         options=options)
    g.audit_object.log({"success": True,
                        "info": res})
    return send_result(res)


@smsgateway_blueprint.route('/<identifier>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.SMSGATEWAYWRITE)
def delete_gateway(identifier=None):
    """
    this function deletes an existing smsgateway definition

    :param identifier: The name of the sms gateway definition
    :return: json with success or fail
    """
    res = delete_smsgateway(identifier=identifier)
    g.audit_object.log({"success": res,
                        "info": identifier})

    return send_result(res)


@smsgateway_blueprint.route('/option/<gwid>/<option>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.SMSGATEWAYWRITE)
def delete_gateway_option(gwid=None, option=None):
    """
    this function deletes an option of a gateway definition

    :param gwid: The id of the sms gateway definition
    :return: json with success or fail
    """
    if option.startswith("option."):
        option = option[7:]

    res = delete_smsgateway_option(gwid, option)
    g.audit_object.log({"success": res,
                        "info": u"{0!s}/{1!s}".format(gwid, option)})

    return send_result(res)

