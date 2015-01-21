# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2015-01-20 Cornelius Kölbel, <cornelius@privacyidea.org>
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
__doc__="""This is the audit REST API that can be used to search the audit log.
It only provides the method

  GET /audit
"""
from flask import (Blueprint,
                   request, current_app)
from lib.utils import (getParam,
                       send_result)
from flask import g
import logging
from ..lib.audit import search
log = logging.getLogger(__name__)


audit_blueprint = Blueprint('audit_blueprint', __name__)


@audit_blueprint.route('/', methods=['GET'])
def search_audit():
    """
    return a list of audit entries.

    Params can be passed as key-value-pairs.

    :param outform: If set to "csv" the output is returned as a CSV file.

    **Example request**:

    .. sourcecode:: http

       GET /audit?realm=realm1 HTTP/1.1
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
                "action": "GET /system/",
                "action_detail": "",
                "administrator": null,
                "clearance_level": null,
                "client": "",
                "date": "2015-01-21T09:06:03.685705",
                "info": "",
                "log_level": null,
                "missing_line": "FAIL",
                "number": 66,
                "privacyidea_server": null,
                "realm": null,
                "serial": null,
                "sig_check": "OK",
                "success": 0,
                "token_type": null,
                "user": null
              },
              {
                "action": "GET /resolver/",
                "action_detail": "",
                "administrator": null,
                "clearance_level": null,
                "client": "",
                "date": "2015-01-21T09:06:03.394826",
                "info": "",
                "log_level": null,
                "missing_line": "OK",
                "number": 65,
                "privacyidea_server": null,
                "realm": null,
                "serial": null,
                "sig_check": "OK",
                "success": 1,
                "token_type": null,
                "user": null
              }
            ]
          },
          "version": "privacyIDEA unknown"
        }
    """
    output_format = getParam(request.all_data, "outform")

    audit_list = search(current_app.config, request.all_data)

    g.audit_object.log({'success': True})
    
    return send_result(audit_list)
