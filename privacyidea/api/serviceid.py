# -*- coding: utf-8 -*-
#
# 2023-03-19 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
#            Add new API for service IDs
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
__doc__ = """The serviceid endpoint allows administrators to manage service ID definitions.
"""
from flask import (Blueprint, request)
from .lib.utils import (getParam, send_result)
from ..lib.log import log_with
from privacyidea.lib.serviceid import get_serviceids, delete_serviceid, set_serviceid
from privacyidea.lib.event import event
from privacyidea.lib.policy import ACTION
from privacyidea.api.lib.prepolicy import prepolicy, check_base_action

from flask import g
import logging


log = logging.getLogger(__name__)


serviceid_blueprint = Blueprint('serviceid_blueprint', __name__)


@serviceid_blueprint.route('/<name>', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.SERVICEID_ADD)
@event("serviceid_add", request, g)
@log_with(log)
def set_serviceid_api(name):
    """
    This call creates a new service ID definition or updates the description
    of an existing service ID.

    Note, that the identifier (name) of the service ID needs to be unique.

    :param name: The unique name of the service ID
    :param description: The description of the service ID definition
    :return:

    **Example request**:

    To create a new serviceid "serviceA" with a description call:

    .. sourcecode:: http

       POST /serviceid/serviceA HTTP/1.1
       Host: example.com
       Accept: application/json
       Content-Length: 26
       Content-Type: application/x-www-form-urlencoded

       description=My cool first service

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
                    "status": true,
                    "value": 1
          }
          "version": "privacyIDEA unknown"
       }

    """
    param = request.all_data
    description = getParam(param, "description", optional=True)

    r = set_serviceid(name, description)

    g.audit_object.log({'success': r > 0, 'info':  name})
    return send_result(r)


@serviceid_blueprint.route('/<name>', methods=['GET'])
@serviceid_blueprint.route('/', methods=['GET'])
@prepolicy(check_base_action, request, ACTION.SERVICEID_LIST)
@event("serviceid_list", request, g)
@log_with(log)
def get_serviceid_api(name=None):
    """
    This call returns the information for the given service ID.
    If no name is specified, it returns a list of all defined services.

    :return: a json result with a list of services


    **Example request**:

    .. sourcecode:: http

       GET /serviceid/ HTTP/1.1
       Host: example.com
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "value": {
              "service1": {"description": "1st service"},
              "service2": {"description": "2nd service"}
              }
            }
          },
          "version": "privacyIDEA unknown"
        }
    """
    sids = get_serviceids(name=name)
    g.audit_object.log({"success": True})
    r_serviceids = {}
    for si in sids:
        r_serviceids[si.name] = {"description": si.Description,
                                 "id": si.id}

    return send_result(r_serviceids)


@serviceid_blueprint.route('/<name>', methods=['DELETE'])
@prepolicy(check_base_action, request, ACTION.SERVICEID_DELETE)
@event("serviceid_delete", request, g)
@log_with(log)
def delete_serviceid_api(name=None):
    """
    This call deletes the given service ID definition.

    :param name: The name of the service.

    :return: a json result with value=1 if deleting the service ID was successful

    **Example request**:

    .. sourcecode:: http

       DELETE /serviceid/service1 HTTP/1.1
       Host: example.com
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "value": 1
          },
          "version": "privacyIDEA unknown"
        }

    """
    ret = delete_serviceid(name)
    g.audit_object.log({"success": True,
                        "info": name})

    return send_result(1)
