# License:  AGPLv3
# (c)
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
__doc__ = """This is the event handler module for posting webhooks.
You can send a webhook to trigger an event on another system or use it to replace
api requests and reduce your traffic this way.

"""

from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib import _
from privacyidea.lib.utils import create_tag_dict, is_true
import json
import logging
import requests
from requests.exceptions import HTTPError, Timeout, ConnectionError, RequestException
from privacyidea.lib.user import User
from privacyidea.lib.error import UserError, ResourceNotFoundError
from privacyidea.lib.webhook import (GuardMode, fire_webhook, get_webhook,
                                     get_webhook_identifiers, guard_target,
                                     media_type, outbound_guard_check)

log = logging.getLogger(__name__)
TIMEOUT = 10

#: Handler definitions already reported as using the deprecated inline shape. The warning belongs
#: in the log once per definition, not once per event: a WebHook handler on validate_check fires
#: on every authentication, and a line per request would bury what it is trying to say.
_INLINE_DEPRECATION_REPORTED = set()


def _warn_inline_shape_is_deprecated(handler_def):
    """
    Report a handler definition that still posts to an inline URL, once per process.

    The inline shape keeps working for now, so this changes nothing about the delivery. It is the
    only notice an administrator gets who never opens the handler in the WebUI, which is the
    normal state of a definition that was set up once and has fired ever since.

    :param handler_def: the event handler definition being run
    """
    key = handler_def.get("id") or handler_def.get("name")
    if key in _INLINE_DEPRECATION_REPORTED:
        return
    _INLINE_DEPRECATION_REPORTED.add(key)
    log.warning(
        f"WebHook handler {handler_def.get('name')!r} posts to an inline URL. The URL and "
        f"content_type options are deprecated since privacyIDEA 3.15 and will be removed in "
        f"3.17; the handler then sends nothing until it is repaired. Configure a webhook under "
        f"Config -> Webhooks and select it in the handler's 'webhook' option. Unlike the inline "
        f"URL, a webhook can carry authentication, headers, TLS, proxy and timeout settings, and "
        f"keeps its URL out of the audit log."
    )


class ContentType:
    """
    Allowed content types sent as the HTTP Content-Type header.
    """
    JSON = "application/json"
    URLENCODED = "application/x-www-form-urlencoded"


# Maps legacy values stored in the database to the proper HTTP Content-Type header values.
# Older entries may have stored "json" or "urlencoded" as shortcuts before the correct
# MIME types were introduced. Both old and new values are accepted.
DB_CONTENT_TYPE_MAP = {
    "json": ContentType.JSON,
    "urlencoded": ContentType.URLENCODED,
    ContentType.JSON: ContentType.JSON,
    ContentType.URLENCODED: ContentType.URLENCODED,
}


class ActionType:
    """
    Allowed actions
    """
    POST_WEBHOOK = "post_webhook"


class WebHookHandler(BaseEventHandler):
    """
    With the WebHook Handler, a webhook can be sent at a particular event
    """

    identifier = "WebHook"
    description = "This eventhandler can post webhooks"

    @property
    def allowed_positions(self):
        """
        This returns the allowed positions of the event handler definition.

        :return: list of allowed positions
        """
        return ["post", "pre"]

    @property
    def actions(self):
        """
        This method returns a dictionary of allowed actions and possible
        options in this handler module.

        :return: dict with actions
        """
        # The event handler has just one action. Maybe we can  hide action select for the clarity of the UI
        actions = {ActionType.POST_WEBHOOK: {
            "webhook": {
                "type": "str",
                "required": False,
                "description": _("Post to this configured webhook. The webhook definition owns the URL, the HTTP "
                                 "method, the authentication, the headers and the TLS, proxy and timeout settings. "
                                 "When a webhook is selected, the URL and content type below are ignored."),
                "value": get_webhook_identifiers()
            },
            "URL": {
                "type": "str",
                "required": False,
                "description": _("DEPRECATED, removed in privacyIDEA 3.17: the URL the WebHook is posted to. Only "
                                 "used when no webhook is selected above, and it can carry no authentication. "
                                 "Configure a webhook instead and select it above.")
            },
            "content_type": {
                "type": "str",
                "required": False,
                "description": _("DEPRECATED, removed in privacyIDEA 3.17: the MIME type (Content-Type) used for "
                                 "the WebHook payload, for example application/json or "
                                 "application/x-www-form-urlencoded. Only used when no webhook is selected above."),
                "value": [
                    ContentType.JSON,
                    ContentType.URLENCODED]
            },
            "replace": {
                "type": "bool",
                "required": False,
                "description": _("You can use the following placeholders: "
                                 "{admin}, {realm}, {action}, {serial}, {url}, {user}, {surname}, "
                                 "{givenname}, {username}, {userrealm}, {tokentype}, {tokendescription}, "
                                 "{time}, {date}, {client_ip}, {ua_browser}, {ua_string}, {challenge}. "
                                 "For backward compatibility the following aliases also work: "
                                 "{logged_in_user}, {token_serial} (= {serial}), "
                                 "{token_owner} (= {givenname}), {user_realm} (= {userrealm}). "
                                 "Tag availability depends on the endpoint."),
            },
            "data": {
                "type": "str",
                "required": False,
                "description": _("The body posted to the WebHook. Leave it empty to send the "
                                 "selected webhook's own default payload.")
            }
        }}
        return actions

    def _replace_tags(self, webhook_text, content_type, g, request):
        """
        Substitute the placeholders in the payload.

        A JSON payload is parsed and substituted key by key and value by
        value, so that a tag containing a quote cannot break the document.
        Any other content type is substituted as plain text.

        A payload that cannot be substituted is returned unchanged, with a
        warning: a broken tag must not cost the whole notification.

        :param webhook_text: the configured payload
        :param content_type: the MIME type the payload will be sent as
        :param g: the flask g object
        :param request: the request that triggered the event
        :return: the payload with the placeholders replaced
        """
        user = request.User if hasattr(request, 'User') else None
        if not user:
            try:
                user = User(login=g.logged_in_user.get('username'),
                            realm=g.logged_in_user.get('realm'))
            except (UserError, AttributeError) as e:  # pragma: no cover
                log.info(f'Could not determine user: {e}')

        # Gather information about the user and token
        token_serial = request.all_data.get('serial', '') if request else ""
        tokenowner = self._get_tokenowner(request) if request else None
        logged_in_user = g.logged_in_user if hasattr(g, 'logged_in_user') else {}
        try:
            token_serial, tokentype, tokendescription = self._get_token_data(token_serial, tokenowner)

            tags = create_tag_dict(logged_in_user=logged_in_user,
                                   request=request,
                                   client_ip=g.client_ip if hasattr(g, 'client_ip') else None,
                                   tokenowner=tokenowner,
                                   serial=token_serial,
                                   tokentype=tokentype,
                                   tokendescription=tokendescription)
            # Backward-compatible aliases so existing webhook configs keep working.
            # The old {logged_in_user} was sourced from request.User first
            # (the authenticating end-user), falling back to g.logged_in_user
            # (the admin).  create_tag_dict always uses g.logged_in_user for
            # {admin} and {realm}, so we keep {logged_in_user} as a separate
            # alias that preserves the old request.User-first behavior.
            tags["realm"] = user.realm if user else ""
            tags["logged_in_user"] = user.login if user else ""
            tags["token_serial"] = tags.get("serial", "")
            tags["token_owner"] = tags.get("givenname", "")
            tags["user_realm"] = tags.get("userrealm", "")

            # Replace None values with empty strings so .format() doesn't insert 'None'
            tags = {k: (v if v is not None else "") for k, v in tags.items()}

            def replace_recursive(val):
                if isinstance(val, dict):
                    return {
                        k.format(**tags): replace_recursive(v)
                        for k, v in val.items()
                    }
                elif isinstance(val, list):
                    return [replace_recursive(item) for item in val]
                elif isinstance(val, str):
                    return val.format(**tags)
                else:
                    # numbers, booleans, None – pass through unchanged
                    return val

            document = None
            # The media type, not the stored string: a webhook may carry parameters
            # ("application/json; charset=utf-8"), and those name the same type. Comparing the
            # string would send a JSON document down the plain-text branch below, where its own
            # braces are read as placeholder syntax and the substitution fails outright.
            if media_type(content_type) == ContentType.JSON:
                try:
                    document = json.loads(webhook_text)
                except (ValueError, TypeError) as err:
                    # Declared as JSON, but not a JSON document. Substituting key by key exists so
                    # that a tag carrying a quote cannot break the document -- a reason that does
                    # not apply to a payload which is not one. So it is substituted as plain text
                    # rather than returned untouched: untouched is what this did before, and in the
                    # UI it is indistinguishable from replacement being switched off.
                    log.info(f"The payload is not valid JSON ({err}); substituting it as plain "
                             f"text instead.")

            if isinstance(document, (dict, list)):
                webhook_text = json.dumps(replace_recursive(document))
            else:
                # Plain text: a urlencoded body, or a JSON-typed payload that is not a document.
                webhook_text = webhook_text.format(**tags)
        except (KeyError, AttributeError, IndexError) as err:
            log.warning(f"Unable to replace placeholder: ({err})! Please check the webhooks data option.")
        except (ValueError, TypeError) as err:
            log.warning(f"Unable to substitute the payload: {err}")

        return webhook_text

    def do(self, action, options=None):
        """
        This method executes the defined action in the given event.

        :param action: The action to perform
        :type action: str
        :param options: Contains the flask parameters g, URL, data, parameter and the fire and forget
        :type options: dict
        :return:
        """
        g = options.get("g")
        request = options.get("request")
        handler_def = options.get("handler_def")
        handler_options = handler_def.get("options")
        webhook_text = handler_options.get("data")
        replace = is_true(handler_options.get("replace"))

        if action.lower() != ActionType.POST_WEBHOOK:
            log.warning(f'Unknown action value: {action}')
            return False

        webhook_identifier = handler_options.get("webhook")
        if webhook_identifier:
            return self._post_to_webhook_object(webhook_identifier, webhook_text, replace, g, request)

        _warn_inline_shape_is_deprecated(handler_def)
        return self._post_inline(handler_options, webhook_text, replace, g, request)

    def _post_to_webhook_object(self, identifier, webhook_text, replace, g, request):
        """
        Post to a configured webhook definition.

        The webhook object owns the endpoint -- URL, HTTP method,
        authentication, headers, TLS, proxy and timeout -- and this handler
        only contributes the payload.

        :param identifier: the name of the webhook definition
        :param webhook_text: the configured payload
        :param replace: whether the placeholders in the payload are substituted
        :param g: the flask g object
        :param request: the request that triggered the event
        :return: True if the endpoint answered with a 2xx status
        """
        try:
            # The content type is a property of the webhook, and it decides
            # whether the payload is substituted as JSON or as plain text.
            content_type = get_webhook(identifier)["content_type"]
        except ResourceNotFoundError:
            log.warning(f"The webhook {identifier!r} configured in this event handler does not exist.")
            self.run_details = f"webhook {identifier!r} is not configured"
            return False

        if replace and webhook_text:
            webhook_text = self._replace_tags(webhook_text, content_type, g, request)

        # Log the identifier, never the URL: it is a property of the webhook
        # object and may embed a token.
        log.info(f"Posting to the webhook {identifier!r}")
        # An empty payload means this event handler contributes none, which
        # lets the webhook's own default_payload apply.
        # fire_webhook() never raises: a dead endpoint is reported, not propagated.
        result = fire_webhook(identifier, payload=webhook_text or None)

        # What this handler run did, for the audit "info" column: lib.event copies run_details
        # there once the action returns (see EventConfiguration._run_handler). The identifier and
        # what the endpoint answered, never the URL - fire_webhook() has already redacted it out
        # of the error message for the same reason.
        if result["success"]:
            self.run_details = f"webhook {identifier!r}: HTTP {result['status_code']}"
        else:
            self.run_details = f"webhook {identifier!r} failed: {result['error']}"
        return result["success"]

    def _post_inline(self, handler_options, webhook_text, replace, g, request):
        """
        Post to the URL configured inline in the event handler definition.

        This is the pre-3.15 shape, from before a webhook was a configuration
        object of its own. It is read permanently, not for a deprecation
        period: privacyIDEA installations may skip releases, and a definition
        that the data migration did not convert -- or that a config import
        re-created in the old shape -- must keep firing rather than silently
        stop.

        :param handler_options: the options of the event handler definition
        :param webhook_text: the configured payload
        :param replace: whether the placeholders in the payload are substituted
        :param g: the flask g object
        :param request: the request that triggered the event
        :return: True if the request was sent successfully
        """
        webhook_url = handler_options.get("URL")
        # Map the database entries, which might contain the older values, to the actual content type value
        content_type = DB_CONTENT_TYPE_MAP.get(handler_options.get("content_type"))

        if content_type not in (ContentType.JSON, ContentType.URLENCODED):
            log.warning(f'Unknown content type value: {handler_options.get("content_type")}')
            self.run_details = f'unknown content type {handler_options.get("content_type")!r}'
            return False

        if replace:
            webhook_text = self._replace_tags(webhook_text, content_type, g, request)

        # The outbound request guard applies here too. This path does not go through
        # fire_webhook(), so without this an inline definition would be the one way to reach an
        # address the guard refuses - and it is the older, more widely used shape, configured by
        # whoever holds eventhandling_write rather than webhook_write. A control that covers only
        # the new shape protects the installation that has not migrated yet least of all.
        try:
            # guard_target(), not the URL itself: requests runs with trust_env=True, so an
            # http_proxy/https_proxy in the server's environment is used for the post below even
            # though this shape cannot configure one. The connection then goes to the proxy, and
            # checking the destination would approve an address nothing connects to - and refuse a
            # destination that is only ever reached through a proxy the allowlist permits.
            mode, rejection = outbound_guard_check(guard_target(webhook_url))
        except Exception as ex:
            # Reading the config or parsing the URL must not break the handler; the request below
            # is what this method is for, and a guard that cannot judge is a guard that does not.
            log.warning(f"Could not apply the outbound request guard: {ex!r}")
            mode, rejection = GuardMode.OFF, None
        if rejection:
            log.warning(f"Inline webhook: outbound request guard ({mode}) rejected the target: "
                        f"{rejection}")
            if mode == GuardMode.ENFORCE:
                self.run_details = f"blocked by the outbound request guard ({mode})"
                return False

        try:
            log.info(f"A webhook is called at '{webhook_url}' with data: '{webhook_text}'")
            response = requests.post(webhook_url, data=webhook_text,
                                     headers={'Content-Type': content_type}, timeout=TIMEOUT,
                                     # Only ENFORCE withholds a redirect, matching fire_webhook():
                                     # a redirect target was never checked, so following one would
                                     # defeat the guard. OFF and WARN keep the previous default, so
                                     # an installation that has not opted in sees no change and a
                                     # trial run does not alter delivery.
                                     allow_redirects=mode != GuardMode.ENFORCE)
            log.info(response.status_code)
            log.debug(response)
        except (HTTPError, ConnectionError, RequestException, Timeout) as err:
            log.warning(err)
            # The inline URL is part of the handler definition, which the audit entry already
            # carries in its action_detail, so naming it here reveals nothing new. A webhook
            # object's URL is different - it is not in the definition - which is why the branch
            # above reports the identifier instead.
            self.run_details = f"{webhook_url} failed: {err.__class__.__name__}"
            return False

        self.run_details = f"{webhook_url}: HTTP {response.status_code}"
        return True
