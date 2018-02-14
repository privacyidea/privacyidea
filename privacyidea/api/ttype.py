# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) Cornelius Kölbel, privacyidea.org
#
# 2015-09-01 Cornelius Kölbel, <cornelius@privacyidea.org>
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
This API endpoint is a generic endpoint that can be used by any token
type.

The tokentype needs to implement a classmethod *api_endpoint* and can then be
called by /ttype/<tokentype>.
This way, each tokentype can create its own API without the need to change
the core API.

The TiQR Token uses this API to implement its special functionalities. See
:ref:`code_tiqr_token`.
"""
from flask import (Blueprint,
                   request)
from .lib.utils import (getParam,
                        optional,
                        required,
                        send_result)
from ..lib.log import log_with
from flask import g, jsonify, current_app, Response
import logging
from privacyidea.api.lib.utils import get_all_params
from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.audit import getAudit
from privacyidea.lib.config import (get_token_class, get_from_config,
                                    SYSCONF, ConfigClass)
from privacyidea.lib.user import get_user_from_param
from privacyidea.api.lib.postpolicy import postrequest, sign_response
from privacyidea.lib.utils import get_client_ip
import json

log = logging.getLogger(__name__)

ttype_blueprint = Blueprint('ttype_blueprint', __name__)


@ttype_blueprint.before_request
def before_request():
    """
    This is executed before the request
    """
    g.config_object = ConfigClass()
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
    g.client_ip = get_client_ip(request,
                                get_from_config(SYSCONF.OVERRIDECLIENT))
    g.audit_object.log({"success": False,
                        "action_detail": "",
                        "client": g.client_ip,
                        "client_user_agent": request.user_agent.browser,
                        "privacyidea_server": privacyidea_server,
                        "action": "{0!s} {1!s}".format(request.method, request.url_rule),
                        "info": ""})


@ttype_blueprint.after_request
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


@ttype_blueprint.route('/<ttype>', methods=['POST', 'GET'])
@log_with(log)
def token(ttype=None):
    """
    This is a special token function. Each token type can define an
    additional API call, that does not need authentication on the REST API
    level.

    :return: Token Type dependent
    """
    tokenc = get_token_class(ttype)
    res = tokenc.api_endpoint(request, g)
    serial = getParam(request.all_data, "serial")
    user = get_user_from_param(request.all_data)
    g.audit_object.log({"success": 1,
                        "user": user.login,
                        "realm": user.realm,
                        "serial": serial,
                        "token_type": ttype})
    if res[0] == "json":
        return jsonify(res[1])
    elif res[0] in ["html", "plain"]:
        return Response(res[1], mimetype="text/{0!s}".format(res[0]))
    elif len(res) == 2:
        return Response(json.dumps(res[1]),
                        mimetype="application/{0!s}".format(res[0]))
    else:
        return Response(res[1], mimetype="application/octet-binary",
                        headers=res[2])
