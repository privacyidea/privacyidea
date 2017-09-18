# -*- coding: utf-8 -*-
#
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
__doc__="""This is the audit REST API that can be used to retrieve the
privacyIDDEA authentication clients, which used privacyIDEA to authenticate.

  GET /clients
"""
from flask import (Blueprint, request)
from .lib.utils import (send_result, getParam)
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..api.auth import admin_required
from ..lib.policy import ACTION
from flask import g
import logging
from ..lib.clientapplication import get_clientapplication

log = logging.getLogger(__name__)

client_blueprint = Blueprint('client_blueprint', __name__)


@client_blueprint.route('/', methods=['GET'])
@prepolicy(check_base_action, request, ACTION.CLIENTTYPE)
def get_clients():
    """
    return a list of authenticated clients grouped (dictionary) by the
    clienttype.

    **Example request**:

    .. sourcecode:: http

       GET /client
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
            "value": {"PAM": [],
                      "SAML": [],
          },
          "version": "privacyIDEA unknown"
        }
    """
    clients = get_clientapplication()
    g.audit_object.log({'success': True})
    
    return send_result(clients)
