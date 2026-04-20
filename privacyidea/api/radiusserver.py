# http://www.privacyidea.org
# (c) Cornelius Kölbel
#
# 2016-02-20 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Implement REST API, create, update, delete, list
#            for RADIUS server definitions
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
__doc__ = """This endpoint is used to create, update, list and delete RADIUS
server definitions. RADIUS server definitions can be used for several purposes
like RADIUS-Token or RADIUS-passthru policies.

The code of this module is tested in tests/test_api_radiusserver.py
"""
from flask import (Blueprint, request)

from privacyidea.lib.resolver import CENSORED
from .lib.utils import (send_result)
from ..lib.params import get_optional, get_required
from ..lib.log import log_with
from ..lib.policies.actions import PolicyAction
from ..api.lib.prepolicy import prepolicy, check_base_action
from flask import g
import logging
from privacyidea.lib.radiusserver import (add_radius, list_radiusservers,
                                          delete_radius, test_radius)


log = logging.getLogger(__name__)

radiusserver_blueprint = Blueprint('radiusserver_blueprint', __name__)


@radiusserver_blueprint.route('/<identifier>', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.RADIUSSERVERWRITE)
@log_with(log)
def create(identifier=None):
    """
    This call creates or updates a RADIUS server definition.

    :param identifier: The unique name of the RADIUS server definition
    :param server: The FQDN or IP of the RADIUS server
    :param port: The port of the RADIUS server
    :param secret: The RADIUS secret of the RADIUS server
    :param description: A description for the definition
    """
    param = request.all_data
    identifier = identifier.replace(" ", "_")
    server = get_required(param, "server")
    port = int(get_optional(param, "port", default=1812))
    secret = get_required(param, "secret")
    retries = int(get_optional(param, "retries", default=3))
    timeout = int(get_optional(param, "timeout", default=5))
    description = get_optional(param, "description", default="")
    dictionary = get_optional(param, "dictionary", default="/etc/privacyidea/dictionary")
    options = get_optional(param, "options", default=None)

    r = add_radius(identifier, server, secret, port=port,
                   description=description, dictionary=dictionary,
                   retries=retries, timeout=timeout, options=options)

    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)


@radiusserver_blueprint.route('/', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.RADIUSSERVERREAD)
def list_radius():
    """
    This call gets the list of RADIUS server definitions
    """
    res = list_radiusservers()
    # We do not add the secret!
    for identifier, data in res.items():
        data["secret"] = CENSORED
    g.audit_object.log({'success': True})
    return send_result(res)


@radiusserver_blueprint.route('/<identifier>', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.RADIUSSERVERWRITE)
@log_with(log)
def delete_server(identifier=None):
    """
    This call deletes the specified RADIUS server configuration

    :param identifier: The unique name of the RADIUS server definition
    """
    r = delete_radius(identifier)

    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)


@radiusserver_blueprint.route('/test_request', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.RADIUSSERVERWRITE)
@log_with(log)
def test():
    """
    Test the RADIUS definition
    :return:
    """
    param = request.all_data
    identifier = get_required(param, "identifier")
    server = get_required(param, "server")
    port = int(get_optional(param, "port", default=1812))
    secret = get_required(param, "secret")
    retries = int(get_optional(param, "retries", default=3))
    timeout = int(get_optional(param, "timeout", default=5))
    user = get_required(param, "username")
    password = get_required(param, "password")
    dictionary = get_optional(param, "dictionary", default="/etc/privacyidea/dictionary")
    options = get_optional(param, "options", default=None)

    r = test_radius(identifier, server, secret, user, password, port=port,
                    dictionary=dictionary, retries=retries, timeout=timeout, options=options)
    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)
