# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2014-12-08 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Complete rewrite during flask migration
#            Try to provide REST API
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
__doc__ = """This REST API is used to list machines from Machine Resolvers.

The code is tested in tests/test_api_machines
"""
from flask import (Blueprint,
                   request)
from lib.utils import (getParam,
                       send_result)
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.policy import ACTION

from flask import (g)
from ..lib.machine import get_machines
import logging
import netaddr


log = logging.getLogger(__name__)


machine_blueprint = Blueprint('machine_blueprint', __name__)


@machine_blueprint.route('/', methods=['GET'])
@prepolicy(check_base_action, request, ACTION.MACHINELIST)
def list_machines():
    """
    List all machines that can be found in the machine resolvers.

    :param hostname: only show machines, that match this hostname as substring
    :param ip: only show machines, that exactly match this IP address
    :param id: filter for substring matching ids
    :param resolver: filter for substring matching resolvers
    
    :return: json result with "result": true and the machine list in "value".

    **Example request**:

    .. sourcecode:: http

       GET /hostname?hostname=on HTTP/1.1
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
            "value": [
              {
                "id": "908asljdas90ad0",
                "hostname": [ "flavon.example.com", "test.example.com" ],
                "ip": "1.2.3.4",
                "resolver_name": "machineresolver1"
              },
              {
                "id": "1908209x48x2183",
                "hostname": [ "london.example.com" ]
                "ip": "2.4.5.6",
                "resolver_name": "machineresolver1"
              }
            ]
          },
          "version": "privacyIDEA unknown"
        }
    """
    hostname = getParam(request.all_data, "hostname")
    ip = getParam(request.all_data, "ip")
    if ip:
        ip = netaddr.IPAddress(ip)
    id = getParam(request.all_data, "id")
    resolver = getParam(request.all_data, "resolver")

    machines = get_machines(hostname=hostname, ip=ip, id=id, resolver=resolver)
    # this returns a list of Machine Object. This is not JSON serialiable,
    # so we need to convert the Machine Object to dict
    machines = [mobject.get_dict() for mobject in machines]
    g.audit_object.log({'success': True,
                        'info': "hostname: %s, ip: %s" % (hostname, ip)})
    
    return send_result(machines)
