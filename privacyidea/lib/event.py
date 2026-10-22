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
import re
import traceback

from sqlalchemy import select, delete

from privacyidea.lib.audit import getAudit
from privacyidea.lib.conditional_access.request_context import recheck_conditional_access_gate
from privacyidea.lib.config import get_config_object
from privacyidea.lib.error import ConfigAdminError, HandlerAbortError
from privacyidea.lib.utils import fetch_one_resource, is_true
from privacyidea.lib.utils.export import (register_import, register_export)
from privacyidea.lib.webhook import get_webhook, get_webhook_identifiers, set_webhook
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

    The result is bounded to the length of the ``info`` column, so that the message says what happened rather than
    being shortened by the audit module.

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

    def _new_handler_audit(self, position: str, e_handler_def: dict) -> tuple:
        """
        Create the audit object and the audit data for a single run of an event handler.

        :param position: "PRE-EVENT" or "POST-EVENT"
        :param e_handler_def: The definition of the event handler
        :return: The audit object and its audit data
        """
        event_audit = getAudit(self.g.audit_object.config)
        # copy all values from the original audit entry
        event_audit_data = dict(self.g.audit_object.audit_data)
        event_audit_data["action"] = (f"{position} {self.eventname}>>"
                                      f"{e_handler_def.get('handlermodule')}:{e_handler_def.get('action')}")
        event_audit_data["action_detail"] = f"{e_handler_def.get('options')}"
        event_audit_data["info"] = e_handler_def.get("name")
        return event_audit, event_audit_data

    def _log_handler_failure(self, position: str, e_handler_def: dict, exception: Exception,
                             event_audit=None, event_audit_data: dict | None = None):
        """
        Write the audit entry of an event handler that did not complete.

        The entry of the handler is reused if it was already created, otherwise a new one is created: a handler
        that fails while its conditions are evaluated has no pending entry yet. Failing to write the entry must
        not replace the exception of the handler, so such an error is only logged.

        :param position: "PRE-EVENT" or "POST-EVENT"
        :param e_handler_def: The definition of the event handler
        :param exception: The exception raised by the handler
        :param event_audit: The audit object of the handler, if it was created before the failure
        :param event_audit_data: The audit data of the handler, if it was created before the failure
        """
        try:
            if event_audit is None:
                event_audit, event_audit_data = self._new_handler_audit(position, e_handler_def)
            event_audit_data["info"] = _handler_failure_info(e_handler_def, exception)
            event_audit.log(event_audit_data)
            event_audit.log({"success": False})
            event_audit.finalize_log()
        except Exception as audit_exception:
            log.error(f"Failed to audit handler failure: {audit_exception!r}")

    def _run_handler(self, event_handler, e_handler_def: dict, options: dict, position: str) -> bool:
        """
        Evaluate the conditions of one event handler and run its action.

        A failure of either is logged, rolled back and audited. Whether it also aborts the request is decided
        by the configuration of the handler, see ``_aborts_on_error``. Evaluating the conditions is part of
        this: an error while checking them is a failure of the handler, not an unmet condition, and a handler
        that is configured to be best-effort must not fail the request because its conditions could not be
        evaluated.

        :param event_handler: The handler object
        :param e_handler_def: The definition of the event handler
        :param options: The options passed to the handler
        :param position: "PRE-EVENT" or "POST-EVENT"
        :return: True if the action of the handler ran, so the caller knows the response may have been replaced
        """
        event_audit = None
        event_audit_data = None
        try:
            if not event_handler.check_condition(options=options):
                return False
            log.debug(f"{position} handling event {self.eventname} with options {options}")
            event_audit, event_audit_data = self._new_handler_audit(position, e_handler_def)
            event_audit.log(event_audit_data)
            result = event_handler.do(e_handler_def.get("action"), options=options)
        except Exception as e:
            log.warning(f"{position.capitalize()} handler {e_handler_def.get('name')!r} "
                        f"({e_handler_def.get('handlermodule')}:"
                        f"{e_handler_def.get('action')}) failed: {e!r}")
            log.debug(traceback.format_exc())
            # A handler that failed in the middle of a transaction leaves the session in a failed state.
            # Without the rollback the following handlers and the wrapped API function die on their own commit.
            db.session.rollback()
            self._log_handler_failure(position, e_handler_def, e, event_audit, event_audit_data)
            if _aborts_on_error(e_handler_def, e):
                raise
            return False

        if event_handler.run_details:
            # The name of a handler definition is optional, so it is formatted instead of concatenated
            event_audit_data["info"] = f"{e_handler_def.get('name')} ({event_handler.run_details})"
            event_audit.log(event_audit_data)
        # set audit object to success
        event_audit.log({"success": result})
        event_audit.finalize_log()
        return True

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
                user_before_handler = getattr(self.request, "User", None)
                self._run_handler(event_handler, e_handler_def, options, "PRE-EVENT")
                if getattr(self.request, "User", None) != user_before_handler:
                    # The handler replaced the user after the conditional-access gate checked the one the request
                    # named, so the new user is gated before any later handler or the view acts for them.
                    rejection = recheck_conditional_access_gate()
                    if rejection is not None:
                        return rejection

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
                if self._run_handler(event_handler, e_handler_def, options, "POST-EVENT"):
                    # In case the handler has modified the response
                    f_result = options.get("response")

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


def set_event(name=None, event=None, handlermodule=None, action=None, conditions: dict = None,
              ordering=0, options: dict = None, id=None, active=True, position="post", abort_on_error=None):
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
        performed. If ``None`` (the default) the stored conditions are kept
        untouched. A dict replaces all stored conditions; an empty dict clears
        them.
    :type conditions: dict
    :param ordering: An optional ordering of the event definitions.
    :type ordering: integer
    :param options: Additional options, that are needed as parameters for the
        action. If ``None`` (the default) the stored options are kept untouched.
        A dict replaces all stored options; an empty dict clears them.
    :type options: dict
    :param id: The DB id of the event. If the id is given, the event is
        updated. Otherwise, a new entry is generated.
    :type id: int
    :param position: The position of the event handler being "post" or "pre"
    :type position: basestring
    :param abort_on_error: Abort the request if the handler raises an exception. A failing handler otherwise
        only adds a failure entry to the audit log and the request continues without it. If it is None, an
        existing event keeps its value and a new event gets the default of its handler module.
    :type abort_on_error: bool
    :return: The id of the event.
    """
    if isinstance(event, list):
        event = ",".join(event)

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
        if abort_on_error is None:
            # A handler whose result the request consumes defaults to aborting, so that a new binding of it is
            # not silently best-effort. Once stored, only the binding decides.
            handler_object = get_handler_object(handlermodule)
            abort_on_error = handler_object.default_abort_on_error if handler_object else False
        id = EventHandler(name=name, event=event, handlermodule=handlermodule, action=action, ordering=ordering,
                          id=id, active=active, position=position, abort_on_error=abort_on_error).save()
    save_config_timestamp()

    # --- Event Handler Options ---
    # Only touch the options if a value was supplied. ``None`` means "keep the
    # existing options untouched", while a dict (even an empty one) means
    # "replace all options with this set" (an empty dict clears them).
    if options is not None:
        delete_stmt = delete(EventHandlerOption).where(EventHandlerOption.eventhandler_id == id)
        db.session.execute(delete_stmt)

        # Add the options to the event handler
        for k, v in options.items():
            db.session.add(EventHandlerOption(eventhandler_id=id, Key=k, Value=v))

    # --- Event Handler Conditions ---
    # Same semantics as the options: ``None`` keeps the stored conditions, a
    # dict replaces them and an empty dict clears them.
    if conditions is not None:
        delete_stmt = delete(EventHandlerCondition).where(EventHandlerCondition.eventhandler_id == id)
        db.session.execute(delete_stmt)

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


#: Written into the ``description`` of a webhook created while importing a configuration.
#: Deliberately *not* the marker the e1f2a3b4c5d6 migration uses for its own rows: that marker is
#: what tells the migration which rows it may adopt when it resumes after a failed run, and a row
#: this importer created is not one of them.
IMPORT_MARKER = "pi-import:webhook-from-inline-handler"


def _free_webhook_identifier(base, handler_id):
    """
    Return the identifier to create the webhook under: *base*, or the next free variant of it.

    :param base: the identifier the naming rule produces for this handler
    :param handler_id: the handler being converted, for the log message
    :return: a free identifier, or the one of our own rows that may be reused
    """
    existing = set(get_webhook_identifiers())
    candidate = base
    suffix = 1
    while candidate in existing:
        description = get_webhook(candidate).get("description") or ""
        if description.startswith(IMPORT_MARKER):
            # Ours, from an earlier import of this configuration. Reusing it is what makes
            # importing the same file twice leave one webhook rather than a trail of them.
            return candidate
        suffix += 1
        candidate = f"{base}_{suffix}"

    if candidate != base:
        log.info(f"The webhook {base!r} already exists and was not created by a configuration "
                 f"import, so imported WebHook handler {handler_id} gets {candidate!r} instead.")
    return candidate


def _inline_webhook_defect(options):
    """
    Return why a WebHook definition in the inline shape cannot be converted, or None.

    :param options: the handler options as imported
    :return: a short reason, or None when the definition can be converted
    """
    # Imported lazily: lib.event is imported by the handler modules' own dependencies, and this
    # is the only place in it that needs the handler's content-type table.
    from privacyidea.lib.eventhandler.webhookeventhandler import (ContentType,
                                                                  DB_CONTENT_TYPE_MAP)

    if not options.get("URL"):
        return "it has no URL"
    raw_content_type = options.get("content_type") or ContentType.JSON
    if "/" not in DB_CONTENT_TYPE_MAP.get(raw_content_type, raw_content_type):
        return (f"its content_type {options.get('content_type')!r} is neither "
                f"{ContentType.JSON} nor {ContentType.URLENCODED}")
    return None


def _convert_inline_webhook_handler(handler_id, handler_name, options):
    """
    Give an imported WebHook handler a webhook object in place of its inline URL.

    The e1f2a3b4c5d6 migration converts the inline shape at upgrade time, but an import is not an
    upgrade: a configuration exported from privacyIDEA 3.14 or older re-creates the inline options
    on an installation that has long since migrated, and no migration will ever see them. Without
    this, such a handler would keep the shape past the release that removes it and then silently
    stop sending.

    The caller has already ruled out the definitions that cannot be converted
    (:func:`_inline_webhook_defect`), so this always produces a webhook.

    :param handler_id: the id ``set_event()`` gave the imported handler
    :param handler_name: the name of the imported handler, which may be empty
    :param options: the handler options as imported
    :return: the identifier of the webhook the handler is to be linked to
    """
    from privacyidea.lib.eventhandler.webhookeventhandler import (ContentType,
                                                                  DB_CONTENT_TYPE_MAP)

    raw_content_type = options.get("content_type") or ContentType.JSON
    content_type = DB_CONTENT_TYPE_MAP.get(raw_content_type, raw_content_type)

    if handler_name:
        base = f"from_{re.sub(r'[^a-zA-Z0-9_-]', '_', handler_name)[:40]}_{handler_id}"
    else:
        base = f"webhook_from_handler_{handler_id}"
    identifier = _free_webhook_identifier(base, handler_id)

    # timeout=10 is the inline shape's fixed TIMEOUT, kept so the imported handler behaves
    # exactly as it did (a webhook created by hand defaults to 3).
    set_webhook(identifier,
                url=options["URL"],
                description=f"{IMPORT_MARKER} - created from the inline options of WebHook "
                            f"event handler {handler_id} (#5751)",
                http_method="POST",
                content_type=content_type,
                auth_type="none",
                verify_tls=True,
                timeout=10)
    return identifier


@register_import('event')
def import_event(data, name=None, skip_invalid=False):
    """
    Import event handler configuration.

    Each definition is imported independently. A WebHook definition still in the pre-3.15 inline
    shape is converted to a webhook object on the way in - the migration that does this at upgrade
    time has already run on this installation and will not run again, so an export taken from an
    older release would otherwise bring the shape back past the release that removes it.

    :param data: the exported event handler definitions
    :param name: import only the definition of this name (default: import all)
    :param skip_invalid: If True, a WebHook definition that cannot be converted because it sends
        nothing as it stands - no ``URL``, or a ``content_type`` that is neither JSON nor
        urlencoded - is skipped instead of failing the import. Without it such a definition is
        reported at the end, the way an unimportable policy is, so that a configuration that
        cannot be restored faithfully does not look like one that was.
    """
    log.debug(f'Import event config: {data!s}')
    skipped = []
    failed = {}
    for entry in data:
        if name and name != entry.get('name'):
            continue
        # Worked on as a copy: the caller's data has to survive the import. "condition" is
        # dropped because it is not used any more, but deleting it from the caller's dict made
        # a second import of the same data fail with a KeyError - and ``pop`` rather than ``del``
        # so a hand-edited export without the key imports too.
        res_data = {key: value for key, value in entry.items() if key != "condition"}
        options = res_data.get("options") or {}
        inline_webhook = (res_data.get("handlermodule") == "WebHook"
                          and not options.get("webhook"))
        if inline_webhook:
            defect = _inline_webhook_defect(options)
            if defect:
                handler_name = res_data.get("name")
                if not skip_invalid:
                    failed[handler_name] = defect
                    continue
                log.warning(f'Skipping the import of WebHook event handler "{handler_name}": '
                            f'{defect}, so it sends nothing and cannot be given a webhook. '
                            f'Correct it in the exported configuration and import again.')
                skipped.append(handler_name)
                continue

        rid = set_event(**res_data)

        if inline_webhook:
            # Converted after the handler is stored, because the identifier is built from the id
            # set_event() just assigned. The inline options are kept, exactly as the migration
            # keeps them: the webhook option wins in WebHookHandler.do(), and they stay readable
            # until the release that removes the inline shape drops them.
            identifier = _convert_inline_webhook_handler(rid, res_data.get("name"), options)
            # The one option row is written directly rather than through a second set_event().
            # That call takes the whole definition, and the fields it is not given fall back to
            # the signature defaults rather than being left alone: action would become "" (the
            # handler then never fires, do() refuses an action it does not know), position would
            # become "post", ordering 0, and a definition exported as inactive would come back
            # enabled.
            db.session.add(EventHandlerOption(
                eventhandler_id=rid, Key="webhook", Value=identifier,
                Description="Added by the configuration import: links this WebHook handler to "
                            "the webhook created from its inline options (#5751)"))
            save_config_timestamp()
            db.session.commit()
            log.info(f"Imported WebHook handler {rid} was converted to the webhook "
                     f"{identifier!r}.")

        log.info('Import of event "{!s}" finished,'
                 ' id: {!s}'.format(res_data['name'], rid))

    if skipped:
        log.warning(f"Skipped WebHook event handlers that send nothing as they stand: {skipped}")

    if failed:
        failure_summary = ', '.join(f'"{n}" ({reason})' for n, reason in failed.items())
        raise ConfigAdminError(f"Could not import the following WebHook event handlers: "
                               f"{failure_summary}.")
