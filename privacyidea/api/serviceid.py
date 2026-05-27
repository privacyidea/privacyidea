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
__doc__ = """
The serviceid REST API manages service ID definitions. Service IDs are
used to scope SSH key assignments and application-specific passwords;
see :ref:`serviceids` for the conceptual chapter.

All endpoints require admin authentication. Listing is gated by the
admin policy action :ref:`policy_serviceid_list`, creation/update by
:ref:`policy_serviceid_add`, deletion by :ref:`policy_serviceid_delete`.
"""
from flask import (Blueprint, request)
from .lib.utils import (send_result)
from ..lib.params import get_optional
from ..lib.log import log_with
from privacyidea.lib.serviceid import get_serviceids, delete_serviceid, set_serviceid
from privacyidea.lib.event import event
from ..lib.policies.actions import PolicyAction
from privacyidea.api.lib.prepolicy import prepolicy, check_base_action

from flask import g
import logging


log = logging.getLogger(__name__)


serviceid_blueprint = Blueprint('serviceid_blueprint', __name__)


@serviceid_blueprint.route('/<name>', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.SERVICEID_ADD)
@event("serviceid_add", request, g)
@log_with(log)
def set_serviceid_api(name):
    """
    Create a new service ID definition or update the description of an
    existing one. The name must be unique.

    Requires admin authentication and the policy action
    :ref:`policy_serviceid_add`.

    :param name: path component, the unique name of the service ID.
    :jsonparam description: free-form description of the service ID.
    :status 200: database id of the service ID in ``result.value``.

    **Example request**:

    .. sourcecode:: http

       POST /serviceid/serviceA HTTP/1.1
       Host: example.com
       Accept: application/json
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
         },
         "version": "privacyIDEA unknown"
       }
    """
    param = request.all_data
    description = get_optional(param, "description")

    r = set_serviceid(name, description)

    g.audit_object.log({'success': r > 0, 'info':  name})
    return send_result(r)


@serviceid_blueprint.route('/<name>', methods=['GET'])
@serviceid_blueprint.route('/', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.SERVICEID_LIST)
@event("serviceid_list", request, g)
@log_with(log)
def get_serviceid_api(name=None):
    """
    Return service ID definitions. If ``name`` is given, only the matching
    service ID is returned; otherwise all service IDs are listed.

    The result is a dictionary keyed by service ID name; each value carries
    ``description`` and ``id``.

    Requires admin authentication and the policy action
    :ref:`policy_serviceid_list`.

    :param name: optional path component selecting a single service ID.
    :status 200: dict of service IDs in ``result.value``.

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
             "service1": {"description": "1st service", "id": 1},
             "service2": {"description": "2nd service", "id": 2}
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
@prepolicy(check_base_action, request, PolicyAction.SERVICEID_DELETE)
@event("serviceid_delete", request, g)
@log_with(log)
def delete_serviceid_api(name=None):
    """
    Delete the service ID with the given name.

    .. warning::
       This call does **not** check whether the service ID is still in use
       by SSH key assignments or application-specific passwords. Removing
       a service ID that is still referenced will leave those assignments
       pointing at a missing target.

    Requires admin authentication and the policy action
    :ref:`policy_serviceid_delete`.

    :param name: path component, the name of the service ID.
    :status 200: ``result.value`` is ``1`` on success.
    :status 404: no service ID with that name exists.

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
    delete_serviceid(name)
    g.audit_object.log({"success": True,
                        "info": name})

    return send_result(1)
