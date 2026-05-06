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
__doc__ = """
The tokengroup REST API manages tokengroup definitions. See
:ref:`tokengroups` for the conceptual chapter.

All endpoints require admin authentication. Listing is gated by the
admin policy action :ref:`policy_tokengroup_list`, creation/update by
:ref:`policy_tokengroup_add`, deletion by :ref:`policy_tokengroup_delete`.
"""
from flask import (Blueprint, request)
from .lib.utils import (getParam, send_result)
from ..lib.log import log_with
from privacyidea.lib.tokengroup import get_tokengroups, set_tokengroup, delete_tokengroup
from privacyidea.lib.event import event
from ..lib.policies.actions import PolicyAction
from privacyidea.api.lib.prepolicy import prepolicy, check_base_action

from flask import g
import logging

log = logging.getLogger(__name__)

tokengroup_blueprint = Blueprint('tokengroup_blueprint', __name__)


@tokengroup_blueprint.route('/<groupname>', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.TOKENGROUP_ADD)
@event("tokengroup_add", request, g)
@log_with(log)
def set_tokengroup_api(groupname):
    """
    Create a new tokengroup or update the description of an existing one.
    The tokengroup name must be unique.

    Requires admin authentication and the policy action
    :ref:`policy_tokengroup_add`.

    :param groupname: path component, the unique name of the tokengroup.
    :jsonparam description: free-form description of the tokengroup.
    :status 200: database id of the tokengroup in ``result.value``.

    **Example request**:

    .. sourcecode:: http

       POST /tokengroup/groupA HTTP/1.1
       Host: example.com
       Accept: application/json
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
         },
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
@prepolicy(check_base_action, request, PolicyAction.TOKENGROUP_LIST)
@event("tokengroup_list", request, g)
@log_with(log)
def get_tokengroup_api(groupname=None):
    """
    Return tokengroup definitions. If ``groupname`` is given, only the
    matching tokengroup is returned; otherwise all tokengroups are listed.

    The result is a dictionary keyed by tokengroup name; each value carries
    ``description`` and ``id``.

    Requires admin authentication and the policy action
    :ref:`policy_tokengroup_list`.

    :param groupname: optional path component selecting a single tokengroup.
    :status 200: dict of tokengroups in ``result.value``.

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
             "gruppe1": {"description": "1st group", "id": 1},
             "gruppe2": {"description": "2nd group", "id": 2}
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
@prepolicy(check_base_action, request, PolicyAction.TOKENGROUP_DELETE)
@event("tokengroup_delete", request, g)
@log_with(log)
def delete_tokengroup_api(groupname=None):
    """
    Delete the tokengroup with the given name. The tokengroup must be empty
    — if any tokens are still assigned to it, the request fails.

    Requires admin authentication and the policy action
    :ref:`policy_tokengroup_delete`.

    :param groupname: path component, the name of the tokengroup.
    :status 200: ``result.value`` is ``1`` on success.
    :status 404: no tokengroup with that name exists.
    :status 400: the tokengroup still has tokens assigned and cannot be
        deleted.

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
