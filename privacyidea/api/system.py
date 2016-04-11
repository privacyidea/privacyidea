# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2015-12-18 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Remove the complete before and after logic
# 2015-10-12 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add a call for testing token config
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
                        send_result)
from ..lib.log import log_with
from ..lib.config import (get_token_class,
                          set_privacyidea_config,
                          delete_privacyidea_config,
                          get_from_config)
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.error import ParameterError

from .auth import admin_required
from flask import (g, current_app, render_template)
import logging
import json
import datetime
import re
import socket
from privacyidea.lib.resolver import get_resolver_list
from privacyidea.lib.realm import get_realms
from privacyidea.lib.policy import PolicyClass, ACTION
from privacyidea.lib.auth import get_db_admins
from privacyidea.lib.error import HSMException
from privacyidea.lib.crypto import geturandom
import base64
import binascii


log = logging.getLogger(__name__)


system_blueprint = Blueprint('system_blueprint', __name__)


@system_blueprint.route('/documentation', methods=['GET'])
@prepolicy(check_base_action, request, ACTION.CONFIGDOCUMENTATION)
@admin_required
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

    This endpoint can be called by the administrator but also by the normal
    user, so that the normal user gets necessary information about the system
    config

    :param key: The key to return.
    :return: A json response or a single value, when queried with a key.
    :rtype: json or scalar
    """
    if not key:
        result = get_from_config(role=g.logged_in_user.get("role"))
    else:
        result = get_from_config(key, role=g.logged_in_user.get("role"))

    g.audit_object.log({"success": True,
                        "info": key})
    return send_result(result)


@system_blueprint.route('/setConfig', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.SYSTEMWRITE)
@admin_required
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
            g.audit_object.add_to_log({"info": "{0!s}={1!s}, ".format(key, value)})
    g.audit_object.log({"success": True})
    return send_result(result)


@system_blueprint.route('/setDefault', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.SYSTEMWRITE)
@admin_required
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
    
    description = "parameters are: {0!s}".format(", ".join(keys))
    param = getLowerParams(request.all_data)
    result = {}
    for k in keys:
        if k.lower() in param:
            value = getParam(param, k.lower(), required)
            res = set_privacyidea_config(k, value)
            result[k] = res
            g.audit_object.log({"success": True})
            g.audit_object.add_to_log({"info": "{0!s}={1!s}, ".format(k, value)})

    if not result:
        log.warning("Failed saving config. Could not find any "
                    "known parameter. %s"
                    % description)
        raise ParameterError("Usage: {0!s}".format(description), id=77)
    
    return send_result(result)


@system_blueprint.route('/<key>', methods=['DELETE'])
@prepolicy(check_base_action, request, ACTION.SYSTEMDELETE)
@log_with(log)
@admin_required
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


@system_blueprint.route('/hsm', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.SETHSM)
@log_with(log)
@admin_required
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


@system_blueprint.route('/hsm', methods=['GET'])
@log_with(log)
@admin_required
def get_security_module():
    """
    Get the status of the security module.
    """
    HSM = current_app.config["pi_hsm"]
    is_ready = HSM.get("obj").is_ready
    res = {"is_ready": is_ready}
    g.audit_object.log({'success': res})
    return send_result(res)


@system_blueprint.route('/random', methods=['GET'])
@prepolicy(check_base_action, request, action=ACTION.GETRANDOM)
@log_with(log)
@admin_required
def rand():
    """
    This endpoint can be used to retrieve random keys from privacyIDEA.
    In certain cases the client might need random data to initialize tokens
    on the client side. E.g. the command line client when initializing the
    yubikey or the WebUI when creating Client API keys for the yubikey.

    In this case, privacyIDEA can created the random data/keys.

    :queryparam len: The length of a symmetric key (byte)
    :queryparam encode: The type of encoding. Can be "hex" or "b64".

    :return: key material
    """
    length = int(getParam(request.all_data, "len") or 20)
    encode = getParam(request.all_data, "encode")

    r = geturandom(length=length)
    if encode == "b64":
        res = base64.b64encode(r)
    else:
        res = binascii.hexlify(r)

    g.audit_object.log({'success': res})
    return send_result(res)


@system_blueprint.route('/test/<tokentype>', methods=['POST'])
@prepolicy(check_base_action, request, action=ACTION.SYSTEMWRITE)
@log_with(log)
@admin_required
def test(tokentype=None):
    """
    The call /system/test/email tests the configuration of the email token.
    """
    tokenc = get_token_class(tokentype)
    res, description = tokenc.test_config(request.all_data)
    g.audit_object.log({"success": 1,
                        "tokentype": tokentype})
    return send_result(res, details={"message": description})
