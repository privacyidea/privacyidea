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
The event-handling REST API manages event handler bindings: which
handler module reacts to which event, on which condition, with which
action and options. See :ref:`eventhandler` for the conceptual chapter
covering the available handler modules and their actions.

All endpoints require admin authentication. Read access for the
binding list and the lookup endpoints (handler module positions,
actions, conditions) is gated by the admin policy action
:ref:`policy_eventhandling_read`; create, update, enable, disable and
delete are gated by :ref:`policy_eventhandling_write`.
"""
from flask import (Blueprint,
                   request)
from .lib.utils import getParam, send_result, get_required
from ..lib.log import log_with
from ..lib.event import set_event, delete_event, enable_event
from flask import g
import logging
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.policies.actions import PolicyAction
from privacyidea.lib.event import AVAILABLE_EVENTS, get_handler_object, get_handler_modules
from privacyidea.lib.utils import is_true
import json


log = logging.getLogger(__name__)


eventhandling_blueprint = Blueprint('eventhandling_blueprint', __name__)


@eventhandling_blueprint.route('/', methods=['GET'])
@eventhandling_blueprint.route('/<eventid>', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.EVENTHANDLINGREAD)
def get_eventhandling(eventid=None):
    """
    Return event handler bindings, or one of two special introspection
    results, depending on the path:

    * ``/event/`` — return all configured event handler bindings.
    * ``/event/<eventid>`` — return the binding with the given numeric id.
    * ``/event/available`` — return the list of event names privacyIDEA
      emits, as a flat list of strings. (Special path; no binding lookup.)
    * ``/event/handlermodules`` — return the list of available handler
      module identifiers (e.g. ``UserNotification``, ``Token``,
      ``Federation``, ``Counter``, ...). (Special path; no binding
      lookup.)

    Requires admin authentication and the policy action
    :ref:`policy_eventhandling_read`.

    :param eventid: optional path component, the numeric id of a binding,
        or one of the literal strings ``available`` / ``handlermodules``
        for the special introspection results.
    :status 200: list of binding dicts, list of event names, list of
        handler module names, or a single binding dict — depending on the
        path.
    """
    if eventid == "available":
        res = AVAILABLE_EVENTS
    elif eventid == "handlermodules":
        res = get_handler_modules()
    else:
        res = g.event_config.get_event(eventid)
    g.audit_object.log({"success": True})
    return send_result(res)


@eventhandling_blueprint.route('/positions/<handlermodule>', methods=["GET"])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.EVENTHANDLINGREAD)
def get_module_positions(handlermodule=None):
    """
    Return the positions a handler module supports — typically ``pre``
    and/or ``post``, indicating where in the request lifecycle the handler
    can fire.

    Requires admin authentication and the policy action
    :ref:`policy_eventhandling_read`.

    :param handlermodule: path component, the handler module identifier
        (e.g. ``UserNotification``).
    :status 200: list of position names in ``result.value``.
    """
    ret = []
    h_obj = get_handler_object(handlermodule)
    if h_obj:
        ret = h_obj.allowed_positions
    g.audit_object.log({"success": True})
    return send_result(ret)


@eventhandling_blueprint.route('/actions/<handlermodule>', methods=["GET"])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.EVENTHANDLINGREAD)
def get_module_actions(handlermodule=None):
    """
    Return the actions a handler module supports. Each entry includes the
    action name and any per-action option schema the WebUI uses to render
    its form.

    Requires admin authentication and the policy action
    :ref:`policy_eventhandling_read`.

    :param handlermodule: path component, the handler module identifier
        (e.g. ``UserNotification``).
    :status 200: dict of action descriptors in ``result.value``.
    """
    ret = []
    h_obj = get_handler_object(handlermodule)
    if h_obj:
        ret = h_obj.actions
    g.audit_object.log({"success": True})
    return send_result(ret)


@eventhandling_blueprint.route('/conditions/<handlermodule>', methods=["GET"])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.EVENTHANDLINGREAD)
def get_module_conditions(handlermodule=None):
    """
    Return the conditions a handler module supports — the predicates that
    can gate whether the handler fires for a given event.

    Requires admin authentication and the policy action
    :ref:`policy_eventhandling_read`.

    :param handlermodule: path component, the handler module identifier
        (e.g. ``UserNotification``).
    :status 200: dict of condition descriptors in ``result.value``.
    """
    ret = []
    h_obj = get_handler_object(handlermodule)
    if h_obj:
        ret = h_obj.conditions
    g.audit_object.log({"success": True})
    return send_result(ret)


@eventhandling_blueprint.route('', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.EVENTHANDLINGWRITE)
def set_eventhandling():
    """
    Create or update an event handler binding. Pass an existing ``id`` to
    update; omit it to create a new binding.

    .. warning::
       Updates are not partial. The full set of fields must be supplied on
       every update — ``action`` and ``position`` are silently set to empty
       strings if omitted, and ``options`` / ``conditions`` are deleted and
       replaced with whatever you send (so omitting them wipes them).

    Requires admin authentication and the policy action
    :ref:`policy_eventhandling_write`.

    :jsonparam id: id of an existing binding to update; omit to create.
    :jsonparam name: human-readable name of the binding (required).
    :jsonparam event: comma-separated list of event names that should
        trigger this binding (required); see :http:get:`/event/available`.
    :jsonparam handlermodule: handler module identifier (required); see
        :http:get:`/event/handlermodules`.
    :jsonparam action: action the handler should perform (required); see
        :http:get:`/event/actions/(handlermodule)`.
    :jsonparam position: ``post`` (default) or ``pre`` — when in the
        request lifecycle the handler fires.
    :jsonparam ordering: integer >= 0; bindings with lower ordering run
        first. Default ``0``.
    :jsonparam active: ``True`` (default) to enable the binding, ``False``
        to create it disabled.
    :jsonparam conditions: dict (or JSON-encoded dict) of per-binding
        conditions; see :http:get:`/event/conditions/(handlermodule)`.
        On update, replaces all conditions.
    :jsonparam option.*: per-action options. Field names are taken after
        the ``option.`` prefix (e.g. ``option.subject`` becomes the
        ``subject`` option). On update, replaces all options.
    :status 200: id of the binding in ``result.value``.
    """
    param = request.all_data
    name = get_required(param, "name")
    event = get_required(param, "event")
    eid = param.get("id")
    active = is_true(param.get("active", True))
    if eid:
        eid = int(eid)
    handlermodule = get_required(param, "handlermodule")
    action = get_required(param, "action")
    ordering = param.get("ordering", 0)
    position = param.get("position", "post")
    conditions = param.get("conditions", {})
    if type(conditions) is not dict:
        conditions = json.loads(conditions)
    options = {}
    for k, v in param.items():
        if k.startswith("option."):
            options[k[7:]] = v

    res = set_event(name, event, handlermodule=handlermodule,
                    action=action, conditions=conditions,
                    ordering=ordering, id=eid, options=options, active=active,
                    position=position)
    g.audit_object.log({"success": True,
                        "info": res})
    return send_result(res)


@eventhandling_blueprint.route('/enable/<eventid>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.EVENTHANDLINGWRITE)
def enable_event_api(eventid):
    """
    Enable an event handler binding.

    Requires admin authentication and the policy action
    :ref:`policy_eventhandling_write`.

    :param eventid: path component, the numeric id of the binding.
    :status 200: id of the binding in ``result.value``.
    """
    p = enable_event(eventid, True)
    g.audit_object.log({"success": True})
    return send_result(p)


@eventhandling_blueprint.route('/disable/<eventid>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.EVENTHANDLINGWRITE)
def disable_event_api(eventid):
    """
    Disable an event handler binding. The binding is preserved but will
    not fire on its events until enabled again.

    Requires admin authentication and the policy action
    :ref:`policy_eventhandling_write`.

    :param eventid: path component, the numeric id of the binding.
    :status 200: id of the binding in ``result.value``.
    """
    p = enable_event(eventid, False)
    g.audit_object.log({"success": True})
    return send_result(p)


@eventhandling_blueprint.route('/<eid>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.EVENTHANDLINGWRITE)
def delete_eventid(eid=None):
    """
    Delete the event handler binding with the given id.

    Requires admin authentication and the policy action
    :ref:`policy_eventhandling_write`.

    :param eid: path component, the numeric id of the binding.
    :status 200: id of the deleted binding in ``result.value``.
    """
    res = delete_event(eid)
    g.audit_object.log({"success": True,
                        "info": eid})

    return send_result(res)

