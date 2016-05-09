# -*- coding: utf-8 -*-
#
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
from privacyidea.models import EventHandler, EventHandlerOption, db
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
            # TODO: do Pre-Event Handling
            f_result = func(*args, **kwds)
            # Post-Event Handling
            e_handles = self.g.event_config.get_handled_events(self.eventname)
            for e_handler_def in e_handles:
                log.debug("Handling event {eventname} with "
                          "{eventDef}".format(eventname=self.eventname,
                                             eventDef=e_handler_def ))
                event_handler_name = e_handler_def.get("handlermodule")
                event_handler = get_handler_object(event_handler_name)
                # The "action is determined by the event configuration
                # In the options we can pass the mailserver configuration
                options = {"request": self.request,
                           "g": self.g,}
                options.update(e_handler_def.get("options"))
                log.debug("Handling event {eventname} with options"
                          "{options}".format(eventname=self.eventname,
                                             options=options))
                event_handler.do(e_handler_def.get("action"),
                                 options=options)
            return f_result

        return event_wrapper


def get_handler_object(handlername):
    """
    Return an event hanlder object based on the Name of the event handler class

    :param handlername: The identifier of the Handler Class
    :type hanldername: basestring
    :return:
    """
    # TODO: beautify and make this work with several different handlers
    from privacyidea.lib.eventhandler.usernotification import \
        UserNotificationEventHandler
    h_obj = None
    if handlername == "UserNotification":
        h_obj = UserNotificationEventHandler()
    return h_obj


def set_event(event, handlermodule, action, condition="",
              ordering=0, options=None, id=None):

    """
    Set and event handling conifugration. This writes an entry to the
    database eventhandler.

    :param event: The name of the event to react on. Can be a single event or
        a comma separated list.
    :type event: basestring
    :param handlermodule: The identifier of the event handler module. This is
        an identifier string like "UserNotification"
    :type handlermodule: basestring
    :param action: The action to perform. This is an action defined by the
        handler module
    :type action: basestring
    :param condition: A condition. Only if this condition is met, the action is
        performed.
    :param ordering: An optional ordering of the event definitions.
    :type ordering: integer
    :param options: Additional options, that are needed as parameters for the
        action
    :type options: dict
    :param id: The DB id of the event. If the id is given, the event is
        updated. Otherwiese a new entry is generated.
    :type id: int
    :return: The id of the event.
    """
    if id:
        id = int(id)
    event = EventHandler(event, handlermodule, action, condition=condition,
                 ordering=ordering, options=options, id=id)
    return event.id


def delete_event(event_id):
    """
    Delete the event configuration with this given ID.
    :param event_id: The database ID of the event.
    :type event_id: int
    :return:
    """
    event_id = int(event_id)
    ev = EventHandler.query.filter_by(id=event_id).first()
    r = ev.delete()
    return r


class EventConfiguration(object):
    """
    This class is supposed to contain the event handling configuration during
    the Request. It can be read initially (in the init method) an can be
    accessed later during the request.
    """

    def __init__(self):
        self.eventlist = []
        self._read_events()

    @property
    def events(self):
        return self.eventlist

    def get_handled_events(self, eventname):
        """
        Return a list of the event handling definitions for the given eventname

        :param eventname:
        :return:
        """
        eventlist = [e for e in self.eventlist if eventname in e.get("event")]
        return eventlist

    def get_event(self, eventid):
        """
        Return the reduced list with the given eventid. This list should only
        have one element.

        :param eventid: id of the event
        :type eventid: int
        :return: list with one element
        """
        if eventid is not None:
            eventid = int(eventid)
            eventlist = [e for e in self.eventlist if e.get("id") == eventid]
            return eventlist
        else:
            return self.eventlist

    def _read_events(self):
        q = EventHandler.query.order_by(EventHandler.ordering)
        for e in q:
            self.eventlist.append(e.get())

