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
from .lib.utils import (send_result)
from ..lib.log import log_with
from flask import g
import logging
import privacyidea.lib.config as cfg
from ..api.lib.prepolicy import prepolicy, check_base_action
from privacyidea.lib.policy import ACTION

log = logging.getLogger(__name__)


caconnectortypes_blueprint = Blueprint('caconnectortypes_blueprint', __name__)


@caconnectortypes_blueprint.route('/', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.CACONNECTORREAD)
def get_caconnectortypes_api():
    """
    returns a json list of the available CA connector types
    """
    g.audit_object.log({"detail": u"{0!s}".format(name)})
    res = cfg.get_caconnector_types()
    g.audit_object.log({"success": True})
    return send_result(res)

