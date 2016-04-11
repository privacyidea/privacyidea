# -*- coding: utf-8 -*-
#
#  2015-05-15 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial writup
#
# License:  AGPLv3
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
#
__doc__ = """This is the REST API for managing CA connector definitions.
The CA connectors are written to the database table "caconnector".

The code is tested in tests/test_api_caconnector.py.
"""
from flask import (Blueprint, request)
from lib.utils import (send_result)
from ..lib.log import log_with
from flask import g
import logging
from privacyidea.lib.caconnector import (save_caconnector,
                                         delete_caconnector,
                                         get_caconnector_list)
from ..api.lib.prepolicy import prepolicy, check_base_action
from privacyidea.lib.policy import ACTION
from .auth import admin_required

log = logging.getLogger(__name__)


caconnector_blueprint = Blueprint('caconnector_blueprint', __name__)


@caconnector_blueprint.route('/<name>', methods=['GET'])
@caconnector_blueprint.route('/', methods=['GET'])
@log_with(log)
#@prepolicy(check_base_action, request, ACTION.CACONNECTORREAD)
def get_caconnector_api(name=None):
    """
    returns a json list of the available applications
    """
    g.audit_object.log({"detail": "{0!s}".format(name)})
    role = g.logged_in_user.get("role")
    res = get_caconnector_list(filter_caconnector_name=name,
                               return_config=(role == "admin"))
    g.audit_object.log({"success": True})
    return send_result(res)


@caconnector_blueprint.route('/<name>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.CACONNECTORWRITE)
@admin_required
def save_caconnector_api(name=None):
    """
    returns a json list of the available applications
    """
    param = request.all_data
    param["caconnector"] = name
    g.audit_object.log({"detail": "{0!s}".format(name)})
    res = save_caconnector(param)
    g.audit_object.log({"success": True})
    return send_result(res)


@caconnector_blueprint.route('/<name>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.CACONNECTORDELETE)
@admin_required
def delete_caconnector_api(name=None):
    """
    returns a json list of the available applications
    """
    g.audit_object.log({"detail": "{0!s}".format(name)})
    res = delete_caconnector(name)
    g.audit_object.log({"success": True})
    return send_result(res)
