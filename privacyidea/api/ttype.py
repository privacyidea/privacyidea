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
The ``/ttype/`` endpoint is a generic dispatcher for token-type-specific
API calls. A token class may declare a ``classmethod api_endpoint`` and
will then be reachable at ``/ttype/<tokentype>`` without having to register
its own routes.

Authentication is **not** enforced by this dispatcher — it is the
responsibility of each token class to validate the request, typically
through cryptographic means (signed challenges, registered public keys,
shared secrets). The dispatcher only sets up the audit, policy and event
context.

Token classes that currently use this endpoint include TiQR
(:ref:`code_tiqr_token`), push, U2F and Yubikey.
"""
import copy
import json
import logging
import threading

from flask import (Blueprint,
                   request)
from flask import g, jsonify, current_app

from privacyidea.api.lib.utils import (get_all_params, get_optional, map_error_to_code, send_error,
                                       log_authentication)
from privacyidea.lib.audit import getAudit
from privacyidea.lib.config import (get_token_class, get_from_config,
                                    SYSCONF, ensure_no_config_object, get_privacyidea_node)
from privacyidea.lib.error import ParameterError
from privacyidea.lib.event import EventConfiguration, event
from privacyidea.lib.policy import PolicyClass, PolicyAction, SCOPE, Match
from privacyidea.lib.tokens.pushtoken import PUSH_AUTH_EVENT, PUSH_AUTH_TRANSACTION_ID
from privacyidea.lib.user import get_user_from_param
from privacyidea.lib.utils import get_client_ip, get_plugin_info_from_useragent
from ..lib.framework import get_app_config_value
from ..lib.log import log_with
from ..lib.tokens.push_types import PushAction

log = logging.getLogger(__name__)

ttype_blueprint = Blueprint('ttype_blueprint', __name__)


@ttype_blueprint.before_request
def before_request():
    """
    This is executed before the request
    """
    ensure_no_config_object()
    # Save the request data
    g.request_data = get_all_params(request)
    request.all_data = copy.deepcopy(g.request_data)
    privacyidea_server = get_app_config_value("PI_AUDIT_SERVERNAME", get_privacyidea_node(request.host))
    # Create a policy_object, that reads the database audit settings
    # and contains the complete policy definition during the request.
    # This audit_object can be used in the postpolicy and prepolicy and it
    # can be passed to the inner policies.
    g.policy_object = PolicyClass()
    g.audit_object = getAudit(current_app.config)
    g.event_config = EventConfiguration()
    # access_route contains the ip addresses of all clients, hops and proxies.
    g.client_ip = get_client_ip(request,
                                get_from_config(SYSCONF.OVERRIDECLIENT))
    g.serial = get_optional(request.all_data, "serial", default=None)
    ua_name, ua_version, _ua_comment = get_plugin_info_from_useragent(request.user_agent.string)
    g.user_agent = ua_name
    g.audit_object.log({"success": False,
                        "action_detail": "",
                        "client": g.client_ip,
                        "user_agent": ua_name,
                        "user_agent_version": ua_version,
                        "privacyidea_server": privacyidea_server,
                        "action": f"{request.method!s} {request.url_rule!s}",
                        "thread_id": f"{threading.current_thread().ident!s}",
                        "info": ""})


@ttype_blueprint.route('/<ttype>', methods=['POST', 'GET'])
@log_with(log)
@event("ttype", request, g)
def token(ttype=None):
    """
    Dispatch a token-type-specific API call to the matching token class.
    The path component selects the token type; the request body / query
    string is forwarded verbatim to the token class' ``api_endpoint``
    classmethod, which is responsible for both validation and the response.

    Authentication is **not** enforced by the dispatcher — token classes
    authenticate the request themselves (signed payloads, registered keys,
    shared secrets). The response shape depends on what the token class
    returns: JSON, HTML, plain text, or arbitrary binary data with custom
    headers.

    If the policy action :ref:`policy_hide_specific_error_message_for_ttype`
    is active, exceptions raised by the token class are converted into a
    generic error response instead of propagating the underlying message.

    For the push token type, the dispatcher additionally evaluates the
    ``push_code_to_phone_message`` policy and forwards its value to the
    token class.

    :param ttype: path component naming the token type
        (e.g. ``tiqr``, ``push``, ``u2f``, ``yubikey``).
    :status 200: token-type-dependent response.
    :status 400: the ``ttype`` does not match any registered token class.
    """
    token_class = get_token_class(ttype)
    if token_class is None:
        log.error(f"Invalid tokentype provided. ttype: {ttype.lower()}")
        raise ParameterError(f"Invalid tokentype provided. ttype: {ttype.lower()}")

    if ttype == "push":
        # Code to phone message
        # TODO this is probably not perfect, but we can not evaluate policies in the token class itself
        code_to_phone_message = None
        policies = Match.user(g, scope=SCOPE.AUTH, action=PushAction.PUSH_CODE_TO_PHONE_MESSAGE,
                              user_object=None).action_values(unique=True, allow_white_space_in_action=True,
                                                              write_to_audit_log=False)
        if len(policies) >= 1:
            code_to_phone_message = list(policies)[0]
        request.all_data[PushAction.PUSH_CODE_TO_PHONE_MESSAGE] = code_to_phone_message

    try:
        res = token_class.api_endpoint(request, g)
    except Exception as e:
        if Match.action_only(
                g,
                scope=SCOPE.TOKEN,
                action=PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE_FOR_TTYPE
        ).any():
            return send_error("Failed special token function"), map_error_to_code(e)
        raise
    serial = get_optional(request.all_data, "serial")
    user = get_user_from_param(request.all_data)
    g.audit_object.log({"success": True,
                        "user": user.login,
                        "realm": user.realm,
                        "serial": serial,
                        "token_type": ttype})

    # Log push authentication
    push_auth_event = getattr(g, PUSH_AUTH_EVENT, None)
    if push_auth_event:
        log_authentication(push_auth_event, user=user, serial=serial,
                           transaction_id=getattr(g, PUSH_AUTH_TRANSACTION_ID, None))

    if res[0] == "json":
        return jsonify(res[1])
    elif res[0] in ["html", "plain"]:
        return current_app.response_class(res[1], mimetype=f"text/{res[0]!s}")
    elif len(res) == 2:
        return current_app.response_class(json.dumps(res[1]),
                                          mimetype=f"application/{res[0]!s}")
    else:
        return current_app.response_class(res[1], mimetype="application/octet-binary",
                                          headers=res[2])
