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
__doc__ = """This is th event handler module for posting webhooks.
You can send an webhook to trigger an event on an other system or use to replace
api requests and reduce your traffic this way.

"""

from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib import _
from privacyidea.lib.token import get_tokens
from privacyidea.lib.utils import create_tag_dict, is_true
import json
import logging
import requests
from requests.exceptions import HTTPError, Timeout, ConnectionError, RequestException
from privacyidea.lib.user import User
from privacyidea.lib.error import UserError

log = logging.getLogger(__name__)
TIMEOUT = 10


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
            "URL": {
                "type": "str",
                "required": True,
                "description": _("The URL the WebHook is posted to")
            },
            "content_type": {
                "type": "str",
                "required": True,
                "description": _("The MIME type (Content-Type) used for the WebHook payload, for example "
                                 "application/json or application/x-www-form-urlencoded"),
                "value": [
                    ContentType.JSON,
                    ContentType.URLENCODED]
            },
            "replace": {
                "type": "bool",
                "required": True,
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
                "required": True,
                "description": _("The data posted in the WebHook")
            }
        }}
        return actions

    def do(self, action, options=None):
        """
        This method executes the defined action in the given event.

        :param action: The action to perform
        :type action: str
        :param options: Contains the flask parameters g, URL, data, parameter and the fire and forget
        :type options: dict
        :return:
        """
        ret = True
        g = options.get("g")
        request = options.get("request")
        handler_def = options.get("handler_def")
        handler_options = handler_def.get("options")
        webhook_url = handler_options.get("URL")
        webhook_text = handler_options.get("data")
        # Map the database entries, which might contain the older values, to the actual content type value
        content_type = DB_CONTENT_TYPE_MAP.get(handler_options.get("content_type"))
        replace = is_true(handler_options.get("replace"))

        user = request.User if hasattr(request, 'User') else None
        if not user:
            try:
                user = User(login=g.logged_in_user.get('username'),
                            realm=g.logged_in_user.get('realm'))
            except (UserError, AttributeError) as e:  # pragma: no cover
                log.info(f'Could not determine user: {e}')

        if replace:
            # If tags should be replaced, gather information about the user and token
            token_serial = request.all_data.get('serial', '') if request else ""
            tokenowner = self._get_tokenowner(request) if request else None
            logged_in_user = g.logged_in_user if hasattr(g, 'logged_in_user') else {}
            tokentype = None
            tokendescription = None
            if token_serial:
                tokens = get_tokens(serial=token_serial)
                if tokens:
                    tokentype = tokens[0].get_tokentype()
                    tokendescription = tokens[0].token.description
            else:
                token_objects = get_tokens(user=tokenowner) if tokenowner else []
                token_serial = ','.join([tok.get_serial() for tok in token_objects])

            try:
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
                tags["logged_in_user"] = user.login if user else ""
                tags["token_serial"] = tags.get("serial", "")
                tags["token_owner"] = tags.get("givenname", "")
                tags["user_realm"] = tags.get("userrealm", "")

                # Replace None values with empty strings so .format() doesn't insert 'None'
                tags = {k: (v if v is not None else "") for k, v in tags.items()}

                if content_type == ContentType.JSON:
                    def replace_recursive(val):
                        if isinstance(val, dict):
                            return {
                                k.format(**tags) if isinstance(k, str) else k:
                                    replace_recursive(v)
                                for k, v in val.items()
                            }
                        elif isinstance(val, list):
                            return [replace_recursive(item) for item in val]
                        elif isinstance(val, str):
                            return val.format(**tags)
                        else:
                            # numbers, booleans, None – pass through unchanged
                            return val

                    new_json = replace_recursive(json.loads(webhook_text))
                    webhook_text = json.dumps(new_json)
                else:
                    # Content Type URLENCODED, simple format
                    webhook_text = webhook_text.format(**tags)
            except (KeyError, AttributeError, IndexError) as err:
                log.warning(f"Unable to replace placeholder: ({err})! Please check the webhooks data option.")
            except (ValueError, TypeError) as err:
                log.warning(f"Unable to parse JSON string '{webhook_text}': {err}")

        # Send the request
        if action.lower() == ActionType.POST_WEBHOOK:
            if content_type in (ContentType.JSON, ContentType.URLENCODED):
                try:
                    log.info(f"A webhook is called at '{webhook_url}' with data: '{webhook_text}'")
                    response = requests.post(webhook_url, data=webhook_text,
                                             headers={'Content-Type': content_type}, timeout=TIMEOUT)
                    # Responses will be logged when running debug. The HTTP response code will be shown in the audit too
                    log.info(response.status_code)
                    log.debug(response)
                except (HTTPError, ConnectionError, RequestException, Timeout) as err:
                    log.warning(err)
                    ret = False
            else:
                log.warning(f'Unknown content type value: {handler_options.get("content_type")}')
                ret = False
        else:
            log.warning(f'Unknown action value: {action}')
            ret = False

        return ret
