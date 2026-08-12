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
import functools
import logging
import traceback

from sqlalchemy import select, delete

from privacyidea.lib.audit import getAudit
from privacyidea.lib.config import get_config_object
from privacyidea.lib.error import HandlerAbortError
from privacyidea.lib.utils import fetch_one_resource, is_true
from privacyidea.lib.utils.export import (register_import, register_export)
from privacyidea.models import (EventHandler, db, save_config_timestamp, EventHandlerOption, EventHandlerCondition,
                                audit_column_length)

log = logging.getLogger(__name__)

AVAILABLE_EVENTS = []


def _handler_failure_info(e_handler_def: dict, exception: Exception) -> str:
    """
    Return the audit ``info`` text for an event handler that did not complete.

    Only the exception class is recorded. The message of an exception raised by a handler that talks to a remote
    system can contain the forwarded request parameters, including the password or OTP value, which must not be
    written to the audit database. The full exception and its traceback go to the log instead.

    The result is bounded to the length of the ``info`` column: the SQL audit module only truncates its data if
    PI_AUDIT_SQL_TRUNCATE is enabled, so an oversized value would otherwise make the audit entry fail to write.

    :param e_handler_def: The definition of the event handler
    :param exception: The exception raised by the handler
    :return: The value for the audit ``info`` column
    """
    info = f"{e_handler_def.get('name')} ({type(exception).__name__})"
    return info[:audit_column_length.get("info")]


def _aborts_on_error(e_handler_def: dict, exception: Exception) -> bool:
    """
    Return whether the failure of an event handler must abort the request.

    A failing handler is best-effort by default: the failure is logged and audited, and the request continues
    without it. That is wrong for a handler whose result the request itself consumes - a response mangler that
    does not run leaves the data it was configured to remove in the response - so such a binding can be
    configured to abort instead. A handler that raises ``HandlerAbortError`` always aborts, regardless of the
    configuration, which is how a handler decides by its own options (see the Script handler's ``raise_error``)
    that the request must not succeed.

    :param e_handler_def: The definition of the event handler
    :param exception: The exception raised by the handler
    :return: True if the exception should be re-raised
    """
    return isinstance(exception, HandlerAbortError) or is_true(e_handler_def.get("abort_on_error"))


def _log_handler_failure(event_audit, event_audit_data: dict, e_handler_def: dict, exception: Exception):
    """
    Mark the pending audit entry of an event handler as failed and write it.

    Failing to write the audit entry must not replace the exception of the handler, so such an error is only
    logged.

    :param event_audit: The audit object created for this handler
    :param event_audit_data: The audit data of this handler
    :param e_handler_def: The definition of the event handler
    :param exception: The exception raised by the handler
    """
    try:
        event_audit_data["info"] = _handler_failure_info(e_handler_def, exception)
        event_audit.log(event_audit_data)
        event_audit.log({"success": False})
        event_audit.finalize_log()
    except Exception as audit_exception:
        log.error(f"Failed to audit handler failure: {audit_exception!r}")


class event:
    """
    This is the event decorator that calls the event handler in the handler
    module. This event decorator can be used at any API call
    """

    def __init__(self, eventname, request, g):
        self.eventname = eventname
        if eventname not in AVAILABLE_EVENTS:
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
                log.debug(f"Pre-Handling event {self.eventname} with {e_handler_def}")
                event_handler_name = e_handler_def.get("handlermodule")
                event_handler = get_handler_object(event_handler_name)
                # The action is determined by the event configuration
                # In the options we can pass the mailserver configuration
                options = {"request": self.request, "g": self.g, "handler_def": e_handler_def}
                if event_handler.check_condition(options=options):
                    log.debug(f"Pre-Handling event {self.eventname} with options {options}")
                    # create a new audit object for this action
                    event_audit = getAudit(self.g.audit_object.config)
                    # copy all values from the original audit entry
                    event_audit_data = dict(self.g.audit_object.audit_data)
                    event_audit_data["action"] = (f"PRE-EVENT {self.eventname}>>"
                                                  f"{e_handler_def.get('handlermodule')}:"
                                                  f"{e_handler_def.get('action')}")
                    event_audit_data["action_detail"] = f"{e_handler_def.get('options')}"
                    event_audit_data["info"] = e_handler_def.get("name")
                    event_audit.log(event_audit_data)

                    try:
                        result = event_handler.do(e_handler_def.get("action"), options=options)
                    except Exception as e:
                        log.warning(f"Pre-event handler {e_handler_def.get('name')!r} "
                                    f"({e_handler_def.get('handlermodule')}:"
                                    f"{e_handler_def.get('action')}) failed: {e!r}")
                        log.debug(traceback.format_exc())
                        # A handler that failed in the middle of a transaction leaves the session in a failed
                        # state. Without the rollback the wrapped API function dies on its own commit.
                        db.session.rollback()
                        _log_handler_failure(event_audit, event_audit_data, e_handler_def, e)
                        if _aborts_on_error(e_handler_def, e):
                            raise
                    else:
                        if event_handler.run_details:
                            event_audit_data["info"] += f" ({event_handler.run_details})"
                            event_audit.log(event_audit_data)
                        # set audit object to success
                        event_audit.log({"success": result})
                        event_audit.finalize_log()

            f_result = func(*args, **kwds)

            # Post-Event Handling
            e_handles = self.g.event_config.get_handled_events(self.eventname)
            for e_handler_def in e_handles:
                log.debug(f"Post-Handling event {self.eventname} with {e_handler_def}")
                event_handler_name = e_handler_def.get("handlermodule")
                event_handler = get_handler_object(event_handler_name)
                # The action is determined by the event configuration
                # In the options we can pass the mailserver configuration
                options = {"request": self.request,
                           "g": self.g,
                           "response": f_result,
                           "handler_def": e_handler_def}
                if event_handler.check_condition(options=options):
                    log.debug(f"Post-Handling event {self.eventname} with options {options}")
                    # create a new audit object
                    event_audit = getAudit(self.g.audit_object.config)
                    # copy all values from the original audit entry
                    event_audit_data = dict(self.g.audit_object.audit_data)
                    event_audit_data["action"] = (f"POST-EVENT {self.eventname}>>"
                                                  f"{e_handler_def.get('handlermodule')}:"
                                                  f"{e_handler_def.get('action')}")
                    event_audit_data["action_detail"] = f"{e_handler_def.get('options')}"
                    event_audit_data["info"] = e_handler_def.get("name")
                    event_audit.log(event_audit_data)

                    try:
                        result = event_handler.do(e_handler_def.get("action"), options=options)
                    except Exception as e:
                        log.warning(f"Post-event handler {e_handler_def.get('name')!r} "
                                    f"({e_handler_def.get('handlermodule')}:"
                                    f"{e_handler_def.get('action')}) failed: {e!r}")
                        log.debug(traceback.format_exc())
                        # A handler that failed in the middle of a transaction leaves the session in a failed
                        # state. Without the rollback the following handlers die on their own commit.
                        db.session.rollback()
                        _log_handler_failure(event_audit, event_audit_data, e_handler_def, e)
                        if _aborts_on_error(e_handler_def, e):
                            raise
                    else:
                        if event_handler.run_details:
                            event_audit_data["info"] += f" ({event_handler.run_details})"
                            event_audit.log(event_audit_data)
                        # In case the handler has modified the response
                        f_result = options.get("response")
                        # set audit object to success
                        event_audit.log({"success": result})
                        event_audit.finalize_log()

            return f_result

        return event_wrapper


def _get_handler_classes():
    """
    Return the list of available event handler classes. Imports are kept
    local to avoid circular imports during application startup.
    """
    from privacyidea.lib.eventhandler.usernotification import UserNotificationEventHandler
    from privacyidea.lib.eventhandler.tokenhandler import TokenEventHandler
    from privacyidea.lib.eventhandler.scripthandler import ScriptEventHandler
    from privacyidea.lib.eventhandler.federationhandler import FederationEventHandler
    from privacyidea.lib.eventhandler.counterhandler import CounterEventHandler
    from privacyidea.lib.eventhandler.requestmangler import RequestManglerEventHandler
    from privacyidea.lib.eventhandler.responsemangler import ResponseManglerEventHandler
    from privacyidea.lib.eventhandler.logginghandler import LoggingEventHandler
    from privacyidea.lib.eventhandler.customuserattributeshandler import CustomUserAttributesHandler
    from privacyidea.lib.eventhandler.webhookeventhandler import WebHookHandler
    from privacyidea.lib.eventhandler.containerhandler import ContainerEventHandler
    return [UserNotificationEventHandler, TokenEventHandler, ScriptEventHandler,
            FederationEventHandler, CounterEventHandler, RequestManglerEventHandler,
            ResponseManglerEventHandler, LoggingEventHandler,
            CustomUserAttributesHandler, WebHookHandler, ContainerEventHandler]


def get_handler_modules():
    """
    Return the identifiers of all available event handler modules.
    """
    return [cls.identifier for cls in _get_handler_classes()]


def get_handler_object(handler_name):
    """
    Return an event handler object based on the Name of the event handler class

    :param handler_name: The identifier of the Handler Class
    :type handler_name: basestring
    :return:
    """
    for cls in _get_handler_classes():
        if cls.identifier == handler_name:
            return cls()
    return None


def enable_event(event_id, enable=True):
    """
    Enable or disable the event

    :param event_id: ID of the event
    :type event_id: int
    :param enable: enable or disable the event
    :type enable: bool
    :return:
    """
    ev = fetch_one_resource(EventHandler, id=event_id)
    # Update the event
    ev.active = enable
    r = ev.save()
    save_config_timestamp()
    return r


def set_event(name=None, event=None, handlermodule=None, action=None, conditions=None,
              ordering=0, options=None, id=None, active=True, position="post", abort_on_error=False):
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
        updated. Otherwise, a new entry is generated.
    :type id: int
    :param position: The position of the event handler being "post" or "pre"
    :type position: basestring
    :param abort_on_error: Abort the request if the handler raises an exception. By default, a failing handler
        only adds a failure entry to the audit log and the request continues without it.
    :type abort_on_error: bool
    :return: The id of the event.
    """
    if isinstance(event, list):
        event = ",".join(event)
    conditions = conditions or {}

    # --- Event Handler ---
    stmt_exists = select(EventHandler).where(EventHandler.id == id)
    existing_event_handler = db.session.scalars(stmt_exists).one_or_none()

    if existing_event_handler:
        if name is not None:
            existing_event_handler.name = name
        if event is not None:
            existing_event_handler.event = event
        if handlermodule is not None:
            existing_event_handler.handlermodule = handlermodule
        existing_event_handler.action = action or ""
        if ordering is not None:
            existing_event_handler.ordering = ordering
        if active is not None:
            existing_event_handler.active = active
        existing_event_handler.position = position or ""
        if abort_on_error is not None:
            existing_event_handler.abort_on_error = abort_on_error
    else:
        id = EventHandler(name=name, event=event, handlermodule=handlermodule, action=action, ordering=ordering,
                          id=id, active=active, position=position, abort_on_error=abort_on_error).save()
    save_config_timestamp()

    # --- Event Handler Options ---
    # Delete existing options
    options = options or {}
    delete_stmt = delete(EventHandlerOption).where(EventHandlerOption.eventhandler_id == id)
    db.session.execute(delete_stmt)

    # Add the options to the event handler
    for k, v in options.items():
        db.session.add(EventHandlerOption(eventhandler_id=id, Key=k, Value=v))

    # --- Event Handler Conditions ---
    # Delete existing conditions
    delete_stmt = delete(EventHandlerCondition).where(EventHandlerCondition.eventhandler_id == id)
    db.session.execute(delete_stmt)

    conditions = conditions or {}
    for k, v in conditions.items():
        db.session.add(EventHandlerCondition(eventhandler_id=id, Key=k, Value=v))

    db.session.commit()
    return id


def delete_event(event_id: int) -> int:
    """
    Delete the event configuration with this given ID.
    :param event_id: The database ID of the event.
    :return: event ID
    """
    event_id = int(event_id)
    db.session.delete(fetch_one_resource(EventHandler, id=event_id))
    save_config_timestamp()
    db.session.commit()
    return event_id


class EventConfiguration:
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
    log.debug(f'Import event config: {data!s}')
    for res_data in data:
        if name and name != res_data.get('name'):
            continue
        # condition is apparently not used anymore
        del res_data["condition"]
        rid = set_event(**res_data)
        log.info('Import of event "{!s}" finished,'
                 ' id: {!s}'.format(res_data['name'], rid))
