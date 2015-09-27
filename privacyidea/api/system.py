# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2015-09-25 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add HSM interface
# 2015-06-26 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add system config documentation API
# 2014-12-08 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Complete rewrite during flask migration
#            Try to provide REST API
#
# privacyIDEA is a fork of LinOTP. Some code is adapted from
# the system-controller from LinOTP, which is
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
__doc__ = """
This is the REST API for system calls to create and read system configuration.

The code of this module is tested in tests/test_api_system.py
"""

from flask import (Blueprint,
                   request)
from .lib.utils import (getParam,
                        getLowerParams,
                        optional,
                        required,
                        send_result,
                        send_error,
                        get_all_params)
from ..lib.log import log_with
from ..lib.config import (get_privacyidea_config,
                          set_privacyidea_config,
                          delete_privacyidea_config,
                          get_from_config)
from ..lib.policy import PolicyClass, ACTION
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.error import (ParameterError,
                         AuthError,
                         PolicyError)
from ..lib.audit import getAudit

from .auth import admin_required
from flask import (g, current_app, render_template)
import logging
import json
import datetime
import re
import socket
from privacyidea.lib.resolver import get_resolver_list
from privacyidea.lib.realm import get_realms
from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.auth import get_db_admins
from .resolver import resolver_blueprint
from .policy import policy_blueprint
from .realm import realm_blueprint
from .realm import defaultrealm_blueprint
from .user import user_blueprint
from .token import token_blueprint
from .audit import audit_blueprint
from .machineresolver import machineresolver_blueprint
from .machine import machine_blueprint
from .application import application_blueprint
from .caconnector import caconnector_blueprint
from privacyidea.api.lib.postpolicy import postrequest, sign_response
from privacyidea.lib.error import HSMException

log = logging.getLogger(__name__)


system_blueprint = Blueprint('system_blueprint', __name__)


@system_blueprint.before_request
@resolver_blueprint.before_request
@machineresolver_blueprint.before_request
@machine_blueprint.before_request
@realm_blueprint.before_request
@defaultrealm_blueprint.before_request
@policy_blueprint.before_request
@application_blueprint.before_request
@admin_required
def before_request():
    """
    This is executed before the request
    It is checked, if a user of role admin is logged in.

    Checks for either user OR admin are performed in api/token.py.
    """
    # remove session from param and gather all parameters, either
    # from the Form data or from JSON in the request body.
    request.all_data = get_all_params(request.values, request.data)
    # Already get some typical parameters to log
    serial = getParam(request.all_data, "serial")
    realm = getParam(request.all_data, "realm")

    g.policy_object = PolicyClass()
    g.audit_object = getAudit(current_app.config)
    g.audit_object.log({"success": False,
                        "serial": serial,
                        "realm": "%s" % realm,
                        "client": request.remote_addr,
                        "client_user_agent": request.user_agent.browser,
                        "privacyidea_server": request.host,
                        "action": "%s %s" % (request.method, request.url_rule),
                        "administrator": g.logged_in_user.get("username"),
                        "action_detail": "",
                        "info": ""})


@system_blueprint.after_request
@resolver_blueprint.after_request
@realm_blueprint.after_request
@defaultrealm_blueprint.after_request
@policy_blueprint.after_request
@user_blueprint.after_request
@token_blueprint.after_request
@audit_blueprint.after_request
@application_blueprint.after_request
@machine_blueprint.after_request
@machineresolver_blueprint.after_request
@caconnector_blueprint.after_request
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


@system_blueprint.errorhandler(AuthError)
@realm_blueprint.app_errorhandler(AuthError)
@defaultrealm_blueprint.app_errorhandler(AuthError)
@resolver_blueprint.app_errorhandler(AuthError)
@policy_blueprint.app_errorhandler(AuthError)
@user_blueprint.app_errorhandler(AuthError)
@token_blueprint.app_errorhandler(AuthError)
@audit_blueprint.app_errorhandler(AuthError)
@application_blueprint.app_errorhandler(AuthError)
@postrequest(sign_response, request=request)
def auth_error(error):
    if "audit_object" in g:
        g.audit_object.log({"info": error.description})
        g.audit_object.finalize_log()
    return send_error(error.description,
                      error_code=-401,
                      details=error.details), error.status_code


@system_blueprint.errorhandler(PolicyError)
@realm_blueprint.app_errorhandler(PolicyError)
@defaultrealm_blueprint.app_errorhandler(PolicyError)
@resolver_blueprint.app_errorhandler(PolicyError)
@policy_blueprint.app_errorhandler(PolicyError)
@user_blueprint.app_errorhandler(PolicyError)
@token_blueprint.app_errorhandler(PolicyError)
@audit_blueprint.app_errorhandler(PolicyError)
@application_blueprint.app_errorhandler(PolicyError)
@postrequest(sign_response, request=request)
def policy_error(error):
    if "audit_object" in g:
        g.audit_object.log({"info": error.message})
        g.audit_object.finalize_log()
    return send_error(error.message), error.id


@system_blueprint.app_errorhandler(500)
@realm_blueprint.app_errorhandler(500)
@defaultrealm_blueprint.app_errorhandler(500)
@resolver_blueprint.app_errorhandler(500)
@policy_blueprint.app_errorhandler(500)
@user_blueprint.app_errorhandler(500)
@token_blueprint.app_errorhandler(500)
@audit_blueprint.app_errorhandler(500)
@application_blueprint.app_errorhandler(500)
@postrequest(sign_response, request=request)
def internal_error(error):
    """
    This function is called when an internal error (500) occurs.
    This is each time an exception is thrown.
    """
    if "audit_object" in g:
        g.audit_object.log({"info": unicode(error)})
        g.audit_object.finalize_log()
    return send_error(unicode(error), error_code=-500), 500


@system_blueprint.route('/documentation', methods=['GET'])
@prepolicy(check_base_action, request, ACTION.CONFIGDOCUMENTATION)
def get_config_documentation():
    """
    returns an restructured text document, that describes the complete
    configuration.
    """
    P = PolicyClass()

    config = get_from_config()
    resolvers = get_resolver_list()
    realms = get_realms()
    policies = P.get_policies()
    admins = get_db_admins()
    context = {"system": socket.getfqdn(socket.gethostname()),
               "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
               "systemconfig": config,
               "appconfig": current_app.config,
               "resolverconfig": resolvers,
               "realmconfig": realms,
               "policyconfig": policies,
               "admins": admins}

    g.audit_object.log({"success": True})
    # Three or more line breaks will be changed to two.
    return re.sub("\n{3,}", "\n\n", render_template("documentation.rst",
                                               context=context))


@system_blueprint.route('/<key>', methods=['GET'])
@system_blueprint.route('/', methods=['GET'])
def get_config(key=None):
    """
    This endpoint either returns all config entries or only the value of the
    one config key.

    :param key: The key to return.
    :return: A json response or a single value, when queried with a key.
    :rtype: json or scalar
    """
    if not key:
        result = get_from_config()
    else:
        result = get_from_config(key)

    g.audit_object.log({"success": True,
                        "info": key})
    return send_result(result)


@system_blueprint.route('/setConfig', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.SYSTEMWRITE)
def set_config():
    """
    set a configuration key or a set of configuration entries

    parameter are generic keyname=value pairs.

    **remark** In case of key-value pairs the type information could be
        provided by an additional parameter with same keyname with the
        postfix ".type". Value could then be 'password' to trigger the
        storing of the value in an encrypted form

    :jsonparam key: configuration entry name
    :jsonparam value: configuration value
    :jsonparam type: type of the value: int or string/text or password.
             password will trigger to store the encrypted value
    :jsonparam description: additional information for this config entry

    **or**

    :jsonparam key-value pairs: pair of &keyname=value pairs
    :return: a json result with a boolean "result": true

    **Example request 1**:

    .. sourcecode:: http

       POST /system/setConfig
       key=splitAtSign
       value=true

       Host: example.com
       Accept: application/json

    **Example request 2**:

    .. sourcecode:: http

       POST /system/setConfig
       BINDDN=myName
       BINDPW=mySecretPassword
       BINDPW.type=password

       Host: example.com
       Accept: application/json


    """
    param = request.all_data
    result = {}
    for key in param:
        if key.split(".")[-1] not in ["type", "desc"]:
            # Only store base values, not type or desc
            value = getParam(param, key, optional)
            typ = getParam(param, key + ".type", optional)
            desc = getParam(param, key + ".desc", optional)
            res = set_privacyidea_config(key, value, typ, desc)
            result[key] = res
            g.audit_object.log({"success": True})
            g.audit_object.add_to_log({"info": "%s=%s, " % (key, value)})
    return send_result(result)


@system_blueprint.route('/setDefault', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.SYSTEMWRITE)
def set_default():
    """
    define default settings for tokens. These default settings
    are used when new tokens are generated. The default settings will
    not affect already enrolled tokens.

    :jsonparam DefaultMaxFailCount: Default value for the maximum allowed
        authentication failures
    :jsonparam DefaultSyncWindow: Default value for the synchronization window
    :jsonparam DefaultCountWindow: Default value for the counter window
    :jsonparam DefaultOtpLen: Default value for the OTP value length --
        usually 6 or 8
    :jsonparam DefaultResetFailCount: Default value, if the FailCounter should
        be reset on successful authentication [True|False]

    :return: a json result with a boolean "result": true

    """
    keys = ["DefaultMaxFailCount",
            "DefaultSyncWindow",
            "DefaultCountWindow",
            "DefaultOtpLen",
            "DefaultResetFailCount"]
    
    description = "parameters are: %s" % ", ".join(keys)
    param = getLowerParams(request.all_data)
    result = {}
    for k in keys:
        if k.lower() in param:
            value = getParam(param, k.lower(), required)
            res = set_privacyidea_config(k, value)
            result[k] = res
            g.audit_object.log({"success": True})
            g.audit_object.add_to_log({"info": "%s=%s, " % (k, value)})

    if len(result) == 0:
        log.warning("Failed saving config. Could not find any "
                    "known parameter. %s"
                    % description)
        raise ParameterError("Usage: %s" % description, id=77)
    
    return send_result(result)


@log_with(log)
@system_blueprint.route('/<key>', methods=['DELETE'])
@prepolicy(check_base_action, request, ACTION.SYSTEMDELETE)
def delete_config(key=None):
    """
    delete a configuration key

    :jsonparam key: configuration key name
    :returns: a json result with the deleted value

    """
    if not key:
        raise ParameterError("You need to provide the config key to delete.")
    res = delete_privacyidea_config(key)
    g.audit_object.log({'success': res,
                        'info': key})
    return send_result(res)


@log_with
@system_blueprint.route('/hsm', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.SETHSM)
def set_security_module():
    """
    Set the password for the security module
    """
    password = getParam(request.all_data, "password", required)
    HSM = current_app.config["pi_hsm"]
    hsm = HSM.get("obj")
    if hsm.is_ready:
        raise HSMException("HSM already set up.")

    is_ready = hsm.setup_module({"password": password})
    res = {"is_ready": is_ready}
    g.audit_object.log({'success': res})
    return send_result(res)


@log_with
@system_blueprint.route('/hsm', methods=['GET'])
def get_security_module():
    """
    Get the status of the security module.
    """
    HSM = current_app.config["pi_hsm"]
    is_ready = HSM.get("obj").is_ready
    res = {"is_ready": is_ready}
    g.audit_object.log({'success': res})
    return send_result(res)
