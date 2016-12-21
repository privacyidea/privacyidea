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
from lib.utils import getParam, send_result
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


eventhandling_blueprint = Blueprint('eventhandling_blueprint', __name__)


@eventhandling_blueprint.route('', methods=['GET'])
@eventhandling_blueprint.route('/<eventid>', methods=['GET'])
@log_with(log)
def get_eventhandling(eventid=None):
    """
    returns a json list of the event handling configuration

    Or

    returns a list of available events when calling as /event/available

    Or

    the available handler modules when calling as /event/handlermodules
    """
    if eventid == "available":
        res = AVAILABLE_EVENTS
    elif eventid == "handlermodules":
        # TODO: We need to provide a dynamic list of event handlers
        res = ["UserNotification", "Token", "Script"]
    else:
        res = g.event_config.get_event(eventid)
    g.audit_object.log({"success": True})
    return send_result(res)


@eventhandling_blueprint.route('/actions/<handlermodule>', methods=["GET"])
@log_with(log)
def get_module_actions(handlermodule=None):
    """
    Return the list of actions a handlermodule provides.

    :param handlermodule: Identifier of the handler module like
        "UserNotification"
    :return: list oft actions
    """
    ret = []
    h_obj = get_handler_object(handlermodule)
    if h_obj:
        ret = h_obj.actions
    return send_result(ret)


@eventhandling_blueprint.route('/conditions/<handlermodule>', methods=["GET"])
@log_with(log)
def get_module_conditions(handlermodule=None):
    """
    Return the list of conditions a handlermodule provides.

    :param handlermodule: Identifier of the handler module like
        "UserNotification"
    :return: list oft actions
    """
    ret = []
    h_obj = get_handler_object(handlermodule)
    if h_obj:
        ret = h_obj.conditions
    return send_result(ret)


@eventhandling_blueprint.route('', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.EVENTHANDLINGWRITE)
def set_eventhandling():
    """
    This creates a new event handling definition

    :param name: A describing name of the event.bool
    :param id: (optional) when updating an existing event you need to
        specify the id
    :param event: A comma seperated list of events
    :param handlermodule: A handlermodule
    :param action: The action to perform
    :param ordering: N/A
    :param conditions: Conditions, when the event will trigger
    :param options.: A list of possible options.
    """
    param = request.all_data
    name = getParam(param, "name", optional=False)
    event = getParam(param, "event", optional=False)
    eid = getParam(param, "id", optional=True)
    active = is_true(getParam(param, "active", default=True))
    if eid:
        eid = int(eid)
    handlermodule = getParam(param, "handlermodule", optional=False)
    action = getParam(param, "action", optional=False)
    ordering = getParam(param, "ordering", optional=True, default=0)
    conditions = getParam(param, "conditions", optional=True, default={})
    if type(conditions) is not dict:
        conditions = json.loads(conditions)
    options = {}
    for k, v in param.iteritems():
        if k.startswith("option."):
            options[k[7:]] = v

    res = set_event(name, event, handlermodule=handlermodule,
                    action=action, conditions=conditions,
                    ordering=ordering, id=eid, options=options, active=active)
    g.audit_object.log({"success": True,
                        "info": res})
    return send_result(res)


@eventhandling_blueprint.route('/enable/<eventid>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.EVENTHANDLINGWRITE)
def enable_event_api(eventid):
    """
    Enable a given event by its id.

    :jsonparam eventid: ID of the event
    :return: ID in the database
    """
    p = enable_event(eventid, True)
    g.audit_object.log({"success": True})
    return send_result(p)


@eventhandling_blueprint.route('/disable/<eventid>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.EVENTHANDLINGWRITE)
def disable_event_api(eventid):
    """
    Disable a given policy by its name.

    :jsonparam name: The name of the policy
    :return: ID in the database
    """
    p = enable_event(eventid, False)
    g.audit_object.log({"success": True})
    return send_result(p)


@eventhandling_blueprint.route('/<eid>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.EVENTHANDLINGWRITE)
def delete_eventid(eid=None):
    """
    this function deletes an existing event handling configuration

    :param eid: The id of the event handling configuration
    :return: json with success or fail
    """
    res = delete_event(eid)
    g.audit_object.log({"success": res,
                        "info": eid})

    return send_result(res)

