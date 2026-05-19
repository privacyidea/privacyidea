# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2016-08-30 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
#            Initial write
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
The client REST API lists the client applications (PAM, SAML, RADIUS,
Keycloak, ...) that have authenticated against privacyIDEA, grouped by
client type. Entries are populated automatically as clients hit the
:ref:`rest_validate` endpoints.

Access requires admin authentication and the admin policy action
:ref:`policy_clienttype`.
"""
from flask import (Blueprint, request)
from .lib.utils import send_result
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.policies.actions import PolicyAction
from flask import g
import logging
from ..lib.clientapplication import get_clientapplication

log = logging.getLogger(__name__)

client_blueprint = Blueprint('client_blueprint', __name__)


@client_blueprint.route('/', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.CLIENTTYPE)
def get_clients():
    """
    Return all client applications that have authenticated against
    privacyIDEA, grouped by client type. The result is a dictionary keyed
    by client type (``PAM``, ``SAML``, ``RADIUS``, ...) where each value
    is a list of records carrying the client's IP, hostname and the most
    recent ``lastseen`` timestamp across all nodes.

    Requires the admin policy action :ref:`policy_clienttype`.

    **Example request**:

    .. sourcecode:: http

      GET /client/ HTTP/1.1
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
            "PAM": [
              {"ip": "10.0.0.5", "hostname": "host1.example.com",
               "lastseen": "2026-05-01 12:34:56"}
            ],
            "SAML": []
          }
        },
        "version": "privacyIDEA unknown"
      }

    :status 200: clients returned in ``result.value``.
    """
    clients = get_clientapplication()
    g.audit_object.log({'success': True})

    return send_result(clients)
