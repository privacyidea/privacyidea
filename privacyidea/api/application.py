# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) Cornelius Kölbel, privacyidea.org
#
# 2015-02-26 Cornelius Kölbel, <cornelius@privacyidea.org>
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
This endpoint is used to get the information from the server,
which application types are known and which options these applications provide.

Applications are used to attach tokens to machines.

The code of this module is tested in tests/test_api_applications.py
"""
from flask import (Blueprint)
from .lib.utils import (send_result)
from ..lib.log import log_with
from flask import g
import logging
from privacyidea.lib.applications import get_application_types


log = logging.getLogger(__name__)


application_blueprint = Blueprint('application_blueprint', __name__)


@application_blueprint.route('/', methods=['GET'])
@log_with(log)
def get_applications():
    """
    returns a json dict of the available applications

    {"luks": {"options": {"slot": {"type": "int"},
                          "partition": {"type": "str"}},
     "ssh": {"options": {"user": {"type": "str"}},
     "otherapplication": {"options": {"optionA": {"type": "int",
                                                  "required": True}}
    }
    """
    res = get_application_types()
    g.audit_object.log({"success": True})
    return send_result(res)
