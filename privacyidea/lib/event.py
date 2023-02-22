# -*- coding: utf-8 -*-
#
#  2018-08-03 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Allow Pre-Handling events
#  2016-05-04 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial writup
#
# License:  AGPLv3
# (c) 2016. Cornelius Kölbel
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
from privacyidea.lib.config import get_config_object
from privacyidea.lib.utils import fetch_one_resource
from privacyidea.models import EventHandler, EventHandlerOption, db
from privacyidea.lib.audit import getAudit
from privacyidea.lib.utils.export import (register_import, register_export)
import functools
import logging
log = logging.getLogger(__name__)

AVAILABLE_EVENTS = []


class event(object):
    """
    This is the event decorator that calls the event handler in the handler
    module. This event decorator can be used at any API call
    """

    def __init__(self, eventname, request, g):
        self.eventname = eventname
        if not eventname in AVAILABLE_EVENTS:
            AVAILABLE_EVENTS.append(eventname)
        self.request = request
        self.g = g

    def __call__(self, func):
        """
        Returns a wrapper that wraps func.
        The wrapper will evaluate the event handling definitions and call the
        defined action.

        :param func: The function that is decorated
        :return: function
        """
        @functools.wraps(func)
        def event_wrapper(*args, **kwds):
            # here we have to evaluate the event configuration from the
            # DB table eventhandler and based on the self.eventname etc...
            # do Pre-Event Handling
            e_handles = self.g.event_config.get_handled_events(self.eventname, position="pre")
            for e_handler_def in e_handles:
                log.debug("Pre-Handling event {eventname} with "
                          "{eventDef}".format(eventname=self.eventname,
                                              eventDef=e_handler_def))
                event_handler_name = e_handler_def.get("handlermodule")
                event_handler = get_handler_object(event_handler_name)
                # The "action is determined by the event configuration
                # In the options we can pass the mailserver configuration
                options = {"request": self.request,
                           "g": self.g,
                           "handler_def": e_handler_def}
                if event_handler.check_condition(options=options):
                    log.debug("Pre-Handling event {eventname} with options"
                              "{options}".format(eventname=self.eventname,
                                                  options=options))
                    # create a new audit object for this action
                    event_audit = getAudit(self.g.audit_object.config)
                    # copy all values from the original audit entry
                    event_audit_data = dict(self.g.audit_object.audit_data)
                    event_audit_data["action"] = "PRE-EVENT {trigger}>>" \
                                                 "{handler}:{action}".format(
                        trigger=self.eventname,
                        handler=e_handler_def.get("handlermodule"),
                        action=e_handler_def.get("action"))
                    event_audit_data["action_detail"] = "{0!s}".format(
                        e_handler_def.get("options"))
                    event_audit_data["info"] = e_handler_def.get("name")
                    event_audit.log(event_audit_data)

                    result = event_handler.do(e_handler_def.get("action"),
                                               options=options)
                    # set audit object to success
                    event_audit.log({"success": result})
                    event_audit.finalize_log()

            f_result = func(*args, **kwds)

            # Post-Event Handling
            e_handles = self.g.event_config.get_handled_events(self.eventname)
            for e_handler_def in e_handles:
                log.debug("Post-Handling event {eventname} with "
                          "{eventDef}".format(eventname=self.eventname,
                                              eventDef=e_handler_def))
                event_handler_name = e_handler_def.get("handlermodule")
                event_handler = get_handler_object(event_handler_name)
                # The "action is determined by the event configuration
                # In the options we can pass the mailserver configuration
                options = {"request": self.request,
                           "g": self.g,
                           "response": f_result,
                           "handler_def": e_handler_def}
                if event_handler.check_condition(options=options):
                    log.debug("Post-Handling event {eventname} with options"
                              "{options}".format(eventname=self.eventname,
                                                 options=options))
                    # create a new audit object
                    event_audit = getAudit(self.g.audit_object.config)
                    # copy all values from the original audit entry
                    event_audit_data = dict(self.g.audit_object.audit_data)
                    event_audit_data["action"] = "POST-EVENT {trigger}>>" \
                                                 "{handler}:{action}".format(
                            trigger=self.eventname,
                            handler=e_handler_def.get("handlermodule"),
                            action=e_handler_def.get("action"))
                    event_audit_data["action_detail"] = "{0!s}".format(
                        e_handler_def.get("options"))
                    event_audit_data["info"] = e_handler_def.get("name")
                    event_audit.log(event_audit_data)

                    result = event_handler.do(e_handler_def.get("action"),
                                               options=options)
                    # In case the handler has modified the response
                    f_result = options.get("response")
                    # set audit object to success
                    event_audit.log({"success": result})
                    event_audit.finalize_log()

            return f_result

        return event_wrapper


def get_handler_object(handlername):
    """
    Return an event handler object based on the Name of the event handler class

    :param handlername: The identifier of the Handler Class
    :type hanldername: basestring
    :return:
    """
    # TODO: beautify and make this work with several different handlers
    from privacyidea.lib.eventhandler.usernotification import \
        UserNotificationEventHandler
    from privacyidea.lib.eventhandler.tokenhandler import TokenEventHandler
    from privacyidea.lib.eventhandler.scripthandler import ScriptEventHandler
    from privacyidea.lib.eventhandler.federationhandler import \
        FederationEventHandler
    from privacyidea.lib.eventhandler.counterhandler import CounterEventHandler
    from privacyidea.lib.eventhandler.requestmangler import RequestManglerEventHandler
    from privacyidea.lib.eventhandler.responsemangler import ResponseManglerEventHandler
    from privacyidea.lib.eventhandler.logginghandler import LoggingEventHandler
    from privacyidea.lib.eventhandler.customuserattributeshandler import CustomUserAttributesHandler
    from privacyidea.lib.eventhandler.webhookeventhandler import WebHookHandler
    h_obj = None
    if handlername == "UserNotification":
        h_obj = UserNotificationEventHandler()
    elif handlername == "Token":
        h_obj = TokenEventHandler()
    elif handlername == "Script":
        h_obj = ScriptEventHandler()
    elif handlername == "Federation":
        h_obj = FederationEventHandler()
    elif handlername == "Counter":
        h_obj = CounterEventHandler()
    elif handlername == "RequestMangler":
        h_obj = RequestManglerEventHandler()
    elif handlername == "ResponseMangler":
        h_obj = ResponseManglerEventHandler()
    elif handlername == "Logging":
        h_obj = LoggingEventHandler()
    elif handlername == "CustomUserAttributes":
        h_obj = CustomUserAttributesHandler()
    elif handlername == "WebHook":
        h_obj = WebHookHandler()
    return h_obj


def enable_event(event_id, enable=True):
    """
    Enable or disable the and event
    :param event_id: ID of the event
    :return:
    """
    ev = fetch_one_resource(EventHandler, id=event_id)
    # Update the event
    ev.active = enable
    r = ev.save()
    return r


def set_event(name=None, event=None, handlermodule=None, action=None, conditions=None,
              ordering=0, options=None, id=None, active=True, position="post"):

    """
    Set an event handling configuration. This writes an entry to the
    database eventhandler.

    :param name: The name of the event definition
    :param event: The name of the event to react on. Can be a single event or
        a comma separated list.
    :type event: basestring
    :param handlermodule: The identifier of the event handler module. This is
        an identifier string like "UserNotification"
    :type handlermodule: basestring
    :param action: The action to perform. This is an action defined by the
        handler module
    :type action: basestring
    :param conditions: A condition. Only if this condition is met, the action is
        performed.
    :type conditions: dict
    :param ordering: An optional ordering of the event definitions.
    :type ordering: integer
    :param options: Additional options, that are needed as parameters for the
        action
    :type options: dict
    :param id: The DB id of the event. If the id is given, the event is
        updated. Otherwise a new entry is generated.
    :type id: int
    :param position: The position of the event handler being "post" or "pre"
    :type position: basestring
    :return: The id of the event.
    """
    if type(event) == list:
        event = ",".join(event)
    conditions = conditions or {}
    if id:
        id = int(id)
    event = EventHandler(name, event, handlermodule, action,
                         conditions=conditions, ordering=ordering,
                         options=options, id=id, active=active,
                         position=position)
    return event.id


def delete_event(event_id):
    """
    Delete the event configuration with this given ID.
    :param event_id: The database ID of the event.
    :type event_id: int
    :return:
    """
    event_id = int(event_id)
    return fetch_one_resource(EventHandler, id=event_id).delete()


class EventConfiguration(object):
    """
    This class is supposed to contain the event handling configuration during
    the Request.
    The currently defined events are fetched from the request-local config object.
    """

    def __init__(self):
        pass

    @property
    def events(self):
        """
        Shortcut for retrieving the currently defined event handlers from the request-local config object.
        """
        return get_config_object().events

    def get_handled_events(self, eventname, position="post"):
        """
        Return a list of the event handling definitions for the given eventname
        and the given position.

        :param eventname: The name of the event
        :param position: the position of the event definition
        :return:
        """
        eventlist = [e for e in self.events if (
            eventname in e.get("event") and e.get("active") and e.get("position") == position)]
        return eventlist

    def get_event(self, eventid):
        """
        Return the reduced list with the given eventid. This list should only
        have one element.

        :param eventid: id of the event
        :type eventid: int or None
        :return: list with one element
        """
        if eventid is not None:
            eventlist = [e for e in self.events if e.get("id") == int(eventid)]
            return eventlist
        else:
            return self.events


@register_export('event')
def export_event(name=None):
    """ Export given or all event configuration """
    event_cls = EventConfiguration()
    if name:
        return [e for e in event_cls.events if (e.get("name") == name)]
    else:
        return event_cls.events


@register_import('event')
def import_event(data, name=None):
    """Import policy configuration"""
    log.debug('Import event config: {0!s}'.format(data))
    for res_data in data:
        if name and name != res_data.get('name'):
            continue
        # condition is apparently not used anymore
        del res_data["condition"]
        rid = set_event(**res_data)
        log.info('Import of event "{0!s}" finished,'
                 ' id: {1!s}'.format(res_data['name'], rid))
