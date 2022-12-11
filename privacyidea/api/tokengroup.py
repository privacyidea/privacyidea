# -*- coding: utf-8 -*-
#
# 2022-09-29 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
#            Add new API for tokengroups
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
__doc__ = """The tokengroup endpoint allows administrators to manage tokengroup definitions.
"""
from flask import (Blueprint, request)
from .lib.utils import (getParam, send_result)
from ..lib.log import log_with
from privacyidea.lib.tokengroup import get_tokengroups, set_tokengroup, delete_tokengroup
from privacyidea.lib.event import event
from privacyidea.lib.policy import ACTION
from privacyidea.api.lib.prepolicy import prepolicy, check_base_action

from flask import g
import logging

log = logging.getLogger(__name__)

tokengroup_blueprint = Blueprint('tokengroup_blueprint', __name__)


@tokengroup_blueprint.route('/<groupname>', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.TOKENGROUP_ADD)
@event("tokengroup_add", request, g)
@log_with(log)
def set_tokengroup_api(groupname):
    """
    This call creates a new tokengroup or updates the description
    of an existing tokengroup.

    Note, that the identifier (name) of the tokengroup needs to be unique.

    :param tokengroup: The unique name of the tokengroup
    :param description: The description of the tokengroup
    :return:

    **Example request**:

    To create a new tokengroup "groupA" with a description call:

    .. sourcecode:: http

       POST /tokengroup/groupA HTTP/1.1
       Host: example.com
       Accept: application/json
       Content-Length: 26
       Content-Type: application/x-www-form-urlencoded

       description=My cool first tokengroup

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

    r = set_tokengroup(groupname, description)

    g.audit_object.log({'success': r > 0, 'info':  groupname})
    return send_result(r)


@tokengroup_blueprint.route('/<groupname>', methods=['GET'])
@tokengroup_blueprint.route('/', methods=['GET'])
@prepolicy(check_base_action, request, ACTION.TOKENGROUP_LIST)
@event("tokengroup_list", request, g)
@log_with(log)
def get_tokengroup_api(groupname=None):
    """
    This call returns the information for the given tokengroup.
    If no groupname is specified, it returns a list of all defined tokengroups.

    :return: a json result with a list of tokengropups


    **Example request**:

    .. sourcecode:: http

       GET /tokengroup/ HTTP/1.1
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
              "gruppe1": {"description": "1st group"},
              "gruppe2": {"description": "2nd group"}
              }
            }
          },
          "version": "privacyIDEA unknown"
        }
    """
    tgs = get_tokengroups(name=groupname)
    g.audit_object.log({"success": True})
    r_tokengroups = {}
    for tg in tgs:
        r_tokengroups[tg.name] = {"description": tg.Description,
                                  "id": tg.id}

    return send_result(r_tokengroups)


@tokengroup_blueprint.route('/<groupname>', methods=['DELETE'])
@prepolicy(check_base_action, request, ACTION.TOKENGROUP_DELETE)
@event("tokengroup_delete", request, g)
@log_with(log)
def delete_tokengroup_api(groupname=None):
    """
    This call deletes the given tokengroup.

    :param groupname: The name of the token.

    :return: a json result with value=1 if deleting the realm was successful

    **Example request**:

    .. sourcecode:: http

       DELETE /tokengroup/gruppe1 HTTP/1.1
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
    ret = delete_tokengroup(groupname)
    g.audit_object.log({"success": True,
                        "info": groupname})

    return send_result(1)
