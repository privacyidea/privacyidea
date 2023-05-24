# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) Cornelius Kölbel, privacyidea.org
#
# 2015-09-01 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Initial writeup
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
"""
This API endpoint is a generic endpoint that can be used by any token
type.

The tokentype needs to implement a classmethod *api_endpoint* and can then be
called by /ttype/<tokentype>.
This way, each tokentype can create its own API without the need to change
the core API.

The TiQR Token uses this API to implement its special functionalities. See
:ref:`code_tiqr_token`.
"""
from flask import (Blueprint,
                   request)
from .lib.utils import getParam
from ..lib.log import log_with
from flask import g, jsonify, current_app
import logging
from privacyidea.lib.error import ParameterError
from privacyidea.lib.config import get_token_class
from privacyidea.lib.user import get_user_from_param
import json

log = logging.getLogger(__name__)

ttype_blueprint = Blueprint('ttype_blueprint', __name__)


@ttype_blueprint.route('/<ttype>', methods=['POST', 'GET'])
@log_with(log)
def token(ttype=None):
    """
    This is a special token function. Each token type can define an
    additional API call, that does not need authentication on the REST API
    level.

    :return: Token Type dependent
    """
    tokenc = get_token_class(ttype)
    if tokenc is None:
        log.error("Invalid tokentype provided. ttype: {}".format(ttype.lower()))
        raise ParameterError("Invalid tokentype provided. ttype: {}".format(ttype.lower()))
    res = tokenc.api_endpoint(request, g)
    serial = getParam(request.all_data, "serial")
    user = get_user_from_param(request.all_data)
    g.audit_object.log({"success": 1,
                        "user": user.login,
                        "realm": user.realm,
                        "serial": serial,
                        "token_type": ttype})
    if res[0] == "json":
        return jsonify(res[1])
    elif res[0] in ["html", "plain"]:
        return current_app.response_class(res[1], mimetype="text/{0!s}".format(res[0]))
    elif len(res) == 2:
        return current_app.response_class(json.dumps(res[1]),
                                          mimetype="application/{0!s}".format(res[0]))
    else:
        return current_app.response_class(res[1], mimetype="application/octet-binary",
                                          headers=res[2])
