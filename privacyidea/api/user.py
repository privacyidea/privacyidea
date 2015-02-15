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

from flask import (Blueprint,
                   request)
from lib.utils import (getParam,
                       send_result)
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.policy import ACTION

from flask import (g)
from ..lib.user import get_user_list
import logging


log = logging.getLogger(__name__)


user_blueprint = Blueprint('user_blueprint', __name__)


@user_blueprint.route('/', methods=['GET'])
@prepolicy(check_base_action, request, ACTION.USERLIST)
def get_users():
    """
    list the users in a realm

    :param realm: a realm that contains several resolvers. Only show users
                  from this realm
    :param resolver: a distinct resolvername
    :param <searchexpr>: a search expression, that depends on the ResolverClass
    
    :return: json result with "result": true and the userlist in "value".

    **Example request**:

    .. sourcecode:: http

       GET /user?realm=realm1 HTTP/1.1
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
                "description": "Cornelius K\u00f6lbel,,+49 151 2960 1417,+49 561 3166797,cornelius.koelbel@netknights.it",
                "email": "cornelius.koelbel@netknights.it",
                "givenname": "Cornelius",
                "mobile": "+49 151 2960 1417",
                "phone": "+49 561 3166797",
                "surname": "K\u00f6lbel",
                "userid": "1009",
                "username": "cornelius"
              }
            ]
          },
          "version": "privacyIDEA unknown"
        }
    """
    realm = getParam(request.all_data, "realm")
    users = get_user_list(request.all_data)

    g.audit_object.log({'success': True,
                        'info': "realm: %s" % realm})
    
    return send_result(users)
