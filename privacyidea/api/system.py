# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
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
"""
The code of this module is tested in tests/test_api_system.py
"""
from flask import (Blueprint,
                   request,
                   url_for)
from lib.utils import (getParam,
                       getLowerParams,
                       optional,
                       required,
                       send_result,
                       send_error,
                       remove_session_from_param)
from ..lib.log import log_with
from ..lib.realm import get_realms
from ..lib.resolver import (get_resolver_list,
                            save_resolver,
                            delete_resolver)
from ..lib.realm import (set_default_realm,
                         get_default_realm,
                         set_realm,
                         delete_realm)
from ..lib.config import (get_privacyidea_config,
                          set_privacyidea_config,
                          delete_privacyidea_config,
                          get_from_config)
from ..lib.policy import (set_policy,
                          get_policies, PolicyClass,
                          export_policies, import_policies,
                          delete_policy, get_static_policy_definitions)
from ..lib.error import (ParameterError,
                         AuthError,
                         PolicyError)
from ..lib.token import get_dynamic_policy_definitions
from ..lib.audit import getAudit

from .auth import (check_auth_token,
                   auth_required)
from flask import (g,
                    make_response,
                    current_app)
from gettext import gettext as _
from werkzeug.datastructures import FileStorage
from cgi import FieldStorage

import logging
import traceback
import re
import json


log = logging.getLogger(__name__)


system_blueprint = Blueprint('system_blueprint', __name__)
from .resolver import resolver_blueprint
from .policy import policy_blueprint
from .realm import realm_blueprint
from .realm import defaultrealm_blueprint
from .user import user_blueprint
from .token import token_blueprint
from .audit import audit_blueprint


@system_blueprint.before_request
@resolver_blueprint.before_request
@realm_blueprint.before_request
@defaultrealm_blueprint.before_request
@policy_blueprint.before_request
@user_blueprint.before_request
@token_blueprint.before_request
@audit_blueprint.before_request
@auth_required
def before_request():
    """
    This is executed before the request
    """
    # remove session from param and gather all parameters, either
    # from the Form data or from JSON in the request body.
    request.all_data = remove_session_from_param(request.values, request.data)
    # Already get some typical parameters to log
    serial = getParam(request.all_data, "serial")
    realm = getParam(request.all_data, "realm")

    g.audit_object = getAudit(current_app.config)
    g.audit_object.log({"success": False,
                        "serial": serial,
                        "realm": realm,
                        "action": "%s %s" % (request.method, request.url_rule),
                        "action_detail": "",
                        "info": ""})
    g.Policy = PolicyClass()


@system_blueprint.after_request
@resolver_blueprint.after_request
@realm_blueprint.after_request
@defaultrealm_blueprint.after_request
@policy_blueprint.after_request
@user_blueprint.after_request
@token_blueprint.after_request
@audit_blueprint.after_request
def after_request(response):
    """
    This function is called after a request
    :return: The response
    """
    # In certain error cases the before_request was not handled
    # completely so that we do not have an audit_object
    if "audit_object" in g:
        g.audit_object.finalize_log()
    return response


@system_blueprint.errorhandler(AuthError)
@realm_blueprint.app_errorhandler(AuthError)
@defaultrealm_blueprint.app_errorhandler(AuthError)
@resolver_blueprint.app_errorhandler(AuthError)
@policy_blueprint.app_errorhandler(AuthError)
@user_blueprint.app_errorhandler(AuthError)
@token_blueprint.app_errorhandler(AuthError)
@audit_blueprint.app_errorhandler(AuthError)
def auth_error(error):
    return send_error(error.description, error_code=-401), error.status_code


@system_blueprint.errorhandler(PolicyError)
@realm_blueprint.app_errorhandler(PolicyError)
@defaultrealm_blueprint.app_errorhandler(PolicyError)
@resolver_blueprint.app_errorhandler(PolicyError)
@policy_blueprint.app_errorhandler(PolicyError)
@user_blueprint.app_errorhandler(PolicyError)
@token_blueprint.app_errorhandler(PolicyError)
@audit_blueprint.app_errorhandler(PolicyError)
def policy_error(error):
    return send_error(error.description), error.status_code


@system_blueprint.app_errorhandler(500)
@realm_blueprint.app_errorhandler(500)
@defaultrealm_blueprint.app_errorhandler(500)
@resolver_blueprint.app_errorhandler(500)
@policy_blueprint.app_errorhandler(500)
@user_blueprint.app_errorhandler(500)
@token_blueprint.app_errorhandler(500)
@audit_blueprint.app_errorhandler(500)
def internal_error(e):
    """
    This function is called when an internal error (500) occurs.
    This is each time an exception is thrown.
    """
    response = send_error(unicode(e))
    response.status_code = 500
    return response


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
    return send_result(result)


@system_blueprint.route('/setConfig', methods=['POST'])
def set_config():
    """
    set a configuration key or a set of configuration entries

    parameter are generic keyname=value pairs.

    *remark: In case of key-value pairs the type information could be
             provided by an additional parameter with same keyname with the
             postfix ".type". Value could then be 'password' to trigger the
             storing of the value in an encrypted form

    :param key: configuration entry name
    :param value: configuration value
    :param type: type of the value: int or string/text or password
                 password will trigger to store the encrypted value
    :param description: additional information for this config entry

    * or
    :param key-value pairs: pair of &keyname=value pairs
    :return: a json result with a boolean "result": true
    """
    param = request.all_data
    result = {}
    for key in param:
        value = getParam(param, key, optional)
        res = set_privacyidea_config(key, value)
        result[key] = res
        g.audit_object.log({"success": True})
        g.audit_object.add_to_log({"info": "%s=%s, " % (key, value)})
    return send_result(result)


@system_blueprint.route('/setDefault', methods=['POST'])
def set_default():
    """
    method:
        system/set

    description:
        define default settings for tokens. These default settings
        are used when new tokens are generated. The default settings will
        not affect already enrolled tokens.

    arguments:
        DefaultMaxFailCount    - Default value for the maximum allowed
                                 authentication failures
        DefaultSyncWindow      - Default value for the synchronization
                                 window
        DefaultCountWindow     - Default value for the coutner window
        DefaultOtpLen          - Default value for the OTP value length --
                                 usually 6 or 8
        DefaultResetFailCount  - Default value, if the FailCounter should
                                 be reset on successful authentication
                                 [True|False]


    returns:
        a json result with a boolean
          "result": true

    exception:
        if an error occurs an exception is serialized and returned

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
def delete_config(key=None):
    """
    delete a configuration key
    * if an error occurs an exception is serializedsetConfig and returned

    :param key: configuration key name
    :returns: a json result with the deleted value

    """
    if not key:
        raise ParameterError("You need to provide the config key to delete.")
    res = delete_privacyidea_config(key)
    g.audit_object.log({'success': res,
                        'info': key})
    return send_result(res)



@log_with(log)
@system_blueprint.route('/policydefs', methods=['GET'])
@system_blueprint.route('/policydefs/<scope>', methods=['GET'])
def get_policy_defs(scope=None):
    """
    This is a helper function that returns the POSSIBLE policy
    definitions, that can
    be used to define your policies.

    :param scope: if given, the function will only return policy
                  definitions for the given scope.

    :return: The policy definitions of the allowed scope with the actions and
    action types. The top level key is the scope.
    :rtype: dict
    """
    pol = {}
    static_pol = get_static_policy_definitions()
    dynamic_pol = get_dynamic_policy_definitions()

    # combine static and dynamic policies
    keys = static_pol.keys() + dynamic_pol.keys()
    pol = {k: dict(static_pol.get(k, {}).items()
                   + dynamic_pol.get(k, {}).items()) for k in keys}

    if scope:
        pol = pol.get(scope)

    g.audit_object.log({"success": True,
                        'info': scope})
    return send_result(pol)

"""
@log_with(log)
@system_blueprint.route('/setupSecurityModule', methods=['POST'])
def setup_security_module_api():

    res = {}
    params = getLowerParams(request.values)
    hsm_id = params.get('hsm_id', None)

    # TODO: Migration
    #from privacyidea.lib.config import getGlobalObject
    #glo = getGlobalObject()
    #sep = glo.security_provider

    if hsm_id is None:
        hsm_id = sep.activeOne
        hsm = c.hsm.get('obj')
        error = c.hsm.get('error')
        if hsm is None or len(error) != 0:
            raise Exception('current activeSecurityModule >%r< '
                            'is not initialized::%s:: - Please '
                            'check your security module configuration'
                            ' and connection!' % (hsm_id, error))

        ready = hsm.is_ready()
        res['setupSecurityModule'] = {'activeSecurityModule': hsm_id,
                                      'connected': ready}
        ret = ready
    else:
        if hsm_id != sep.activeOne:
            raise Exception('current activeSecurityModule >%r< could '
                            'only be changed through the '
                            'configuration!' % sep.activeOne)

        ret = sep.setupModule(hsm_id, config=params)

        hsm = c.hsm.get('obj')
        ready = hsm.is_ready()
        res['setupSecurityModule'] = {'activeSecurityModule': hsm_id,
                                      'connected': ready,
                                      'result': ret}

    c.audit['success'] = ret
    return send_result(res)
"""
