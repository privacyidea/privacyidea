# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) Cornelius Kölbel, privacyidea.org
#
# 2016-05-06 Cornelius Kölbel, <cornelius@privacyidea.org>
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
This endpoint is used to create, modify, list and delete Event Handling
Configuration. Event handling configuration is stored in the database table
"eventhandling"

The code of this module is tested in tests/test_api_events.py
"""
from flask import (Blueprint,
                   request)
from .lib.utils import getParam, send_result
from ..lib.log import log_with
from ..lib.event import set_event, delete_event, enable_event
from flask import g
import logging
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.policy import ACTION
from privacyidea.lib.event import AVAILABLE_EVENTS, get_handler_object
from privacyidea.lib.utils import is_true
import json


log = logging.getLogger(__name__)


search_blueprint = Blueprint('search_blueprint', __name__)


@search_blueprint.route('/', methods=['GET'])
@search_blueprint.route('/<searchtype>', methods=['GET'])
@log_with(log)
# Todo: should we check for permissions?
#@prepolicy(check_base_action, request, ACTION.SEARCH)
def get_searchresults(searchtype=None):
    """
    returns a json list of the event handling configuration
    """
    if searchtype == "user":
        realm = getParam(request.all_data, "realm")
        users = get_user_list(request.all_data)

        g.audit_object.log({'success': True,
                            'info': "realm: {0!s}".format(realm)})

    elif searchtype == "token":
        param = request.all_data
        user = request.User
        serial = getParam(param, "serial", optional)
        page = int(getParam(param, "page", optional, default=1))
        tokentype = getParam(param, "type", optional)
        description = getParam(param, "description", optional)
        sort = getParam(param, "sortby", optional, default="serial")
        sdir = getParam(param, "sortdir", optional, default="asc")
        psize = int(getParam(param, "pagesize", optional, default=15))
        realm = getParam(param, "tokenrealm", optional)
        userid = getParam(param, "userid", optional)
        resolver = getParam(param, "resolver", optional)
        ufields = getParam(param, "user_fields", optional)
        output_format = getParam(param, "outform", optional)
        assigned = getParam(param, "assigned", optional)
        active = getParam(param, "active", optional)
        tokeninfokey = getParam(param, "infokey", optional)
        tokeninfovalue = getParam(param, "infovalue", optional)
        tokeninfo = None
        if tokeninfokey and tokeninfovalue:
            tokeninfo = {tokeninfokey: tokeninfovalue}
        if assigned:
            assigned = assigned.lower() == "true"
        if active:
            active = active.lower() == "true"

        user_fields = []
        if ufields:
            user_fields = [u.strip() for u in ufields.split(",")]

        # allowed_realms determines, which realms the admin would be allowed to see
        # In certain cases like for users, we do not have allowed_realms
        allowed_realms = getattr(request, "pi_allowed_realms", None)
        g.audit_object.log({'info': "realm: {0!s}".format((allowed_realms))})

        # get list of tokens as a dictionary
        tokens = get_tokens_paginate(serial=serial, realm=realm, page=page,
                                     user=user, assigned=assigned, psize=psize,
                                     active=active, sortby=sort, sortdir=sdir,
                                     tokentype=tokentype,
                                     resolver=resolver,
                                     description=description,
                                     userid=userid, allowed_realms=allowed_realms,
                                     tokeninfo=tokeninfo)
        g.audit_object.log({"success": True})

    g.audit_object.log({"success": True})
    return send_result(res)