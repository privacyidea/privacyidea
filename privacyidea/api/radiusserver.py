# -*- coding: utf-8 -*-
#
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
from .lib.utils import (getParam,
                        required,
                        send_result)
from ..lib.log import log_with
from ..lib.policy import ACTION
from ..api.lib.prepolicy import prepolicy, check_base_action
from flask import g
import logging
from privacyidea.lib.radiusserver import (add_radius, RADIUSServer,
                                          delete_radius, get_radiusservers, test_radius)
from privacyidea.models import RADIUSServer as RADIUSServerDB
from privacyidea.api.auth import admin_required


log = logging.getLogger(__name__)

radiusserver_blueprint = Blueprint('radiusserver_blueprint', __name__)


@radiusserver_blueprint.route('/<identifier>', methods=['POST'])
@admin_required
@prepolicy(check_base_action, request, ACTION.RADIUSSERVERWRITE)
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
    server = getParam(param, "server", required)
    port = int(getParam(param, "port", default=1812))
    secret = getParam(param, "secret", required)
    retries = int(getParam(param, "retries", default=3))
    timeout = int(getParam(param, "timeout", default=5))
    description = getParam(param, "description", default="")
    dictionary = getParam(param, "dictionary",
                          default="/etc/privacyidea/dictionary")

    r = add_radius(identifier, server, secret, port=port,
                   description=description, dictionary=dictionary,
                   retries=retries, timeout=timeout)

    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)


@radiusserver_blueprint.route('/', methods=['GET'])
@log_with(log)
def list_radius():
    """
    This call gets the list of RADIUS server definitions
    """
    res = {}
    server_list = get_radiusservers()
    for server in server_list:
        # We do not add the secret!
        if g.logged_in_user.get("role") == "admin":
            res[server.config.identifier] = {"server": server.config.server,
                                             "port": server.config.port,
                                             "dictionary": server.config.dictionary,
                                             "description":
                                                 server.config.description,
                                             "timeout": server.config.timeout,
                                             "retries": server.config.retries}
        else:
            # We do not pass any information to a normal user!
            res[server.config.identifier] = {"server": "",
                                             "port": "",
                                             "dictionary": "",
                                             "description": "",
                                             "timeout": 0,
                                             "retries": 0}

    g.audit_object.log({'success': True})
    return send_result(res)


@radiusserver_blueprint.route('/<identifier>', methods=['DELETE'])
@admin_required
@prepolicy(check_base_action, request, ACTION.RADIUSSERVERWRITE)
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
@admin_required
@prepolicy(check_base_action, request, ACTION.RADIUSSERVERWRITE)
@log_with(log)
def test():
    """
    Test the RADIUS definition
    :return:
    """
    param = request.all_data
    identifier = getParam(param, "identifier", required)
    server = getParam(param, "server", required)
    port = int(getParam(param, "port", default=1812))
    secret = getParam(param, "secret", required)
    retries = int(getParam(param, "retries", default=3))
    timeout = int(getParam(param, "timeout", default=5))
    user = getParam(param, "username", required)
    password = getParam(param, "password", required)
    dictionary = getParam(param, "dictionary",
                          default="/etc/privacyidea/dictionary")

    r = test_radius(identifier, server, secret, user, password, port=port,
                    dictionary=dictionary, retries=retries, timeout=timeout)
    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)
