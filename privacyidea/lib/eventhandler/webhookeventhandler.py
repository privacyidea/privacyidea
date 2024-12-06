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
import json
import logging
import requests
from requests.exceptions import HTTPError, Timeout, ConnectionError, RequestException
from privacyidea.lib.user import User
from privacyidea.lib.error import UserError

log = logging.getLogger(__name__)
TIMEOUT = 10


class CONTENT_TYPE(object):
    """
    Allowed type off content
    """
    JSON = "json"
    URLENCODED = "urlencoded"


class ACTION_TYPE(object):
    """
    Allowed actions
    """
    POST_WEBHOOK = "post_webhook"


class WebHookHandler(BaseEventHandler):
    """
    With the WebHook Handler, a webhook can be sent at a particular event
    """

    identifier = "WebHookHandler"
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
        actions = {ACTION_TYPE.POST_WEBHOOK: {
            "URL": {
                "type": "str",
                "required": True,
                "description": _("The URL the WebHook is posted to")
            },
            "content_type": {
                "type": "str",
                "required": True,
                "description": _("The encoding that is sent to the WebHook, for example json"),
                "value": [
                    CONTENT_TYPE.JSON,
                    CONTENT_TYPE.URLENCODED]
            },
            "replace": {
                "type": "bool",
                "required": True,
                "description": _("You can use the following placeholders: {logged_in_user}, {realm}, {surname}, "
                                 "{token_owner}, {user_realm}, {token_serial}. "
                                 "However, tag availability is depending on the endpoint."),
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
        content_type = handler_options.get("content_type")
        replace = handler_options.get("replace")

        user = request.User if hasattr(request, 'User') else None
        if not user:
            try:
                user = User(login=g.logged_in_user.get('username'),
                            realm=g.logged_in_user.get('realm'))
            except (UserError, AttributeError) as e:  # pragma: no cover
                log.info(f'Could not determine user: {e}')

        if replace:
            # If tags should be replaced, gather information about the user and token
            token_serial = request.all_data.get('serial') if request else ""
            tokenowner = self._get_tokenowner(request) if request else None

            login = user.login if user else ""
            realm = user.realm if user else ""
            surname = tokenowner.info.get("surname") if tokenowner else ""
            given_name = tokenowner.info.get("givenname") if tokenowner else ""
            user_realm = tokenowner.realm if tokenowner else ""

            try:
                attributes = {
                    "logged_in_user": login,
                    "realm": realm,
                    "surname": surname,
                    "token_owner": given_name,
                    "user_realm": user_realm,
                    "token_serial": token_serial
                }
                if content_type == CONTENT_TYPE.JSON:
                    def replace_recursive(val):
                        for k, v in val.items():
                            k = k.format(**attributes)
                            if isinstance(v, dict):
                                return {k: replace_recursive(v)}
                            else:
                                return {k: v.format(**attributes)}

                    new_json = replace_recursive(json.loads(webhook_text))
                    webhook_text = json.dumps(new_json)
                else:
                    # Content Type URLENCODED, simple format
                    webhook_text = webhook_text.format(**attributes)
            except KeyError as err:
                log.warning(f"Unable to replace placeholder: ({err})! Please check the webhooks data option.")
            except ValueError as err:
                log.warning(f"Unable to parse JSON string '{webhook_text}': {err}")

        # Send the request
        if action.lower() == ACTION_TYPE.POST_WEBHOOK:
            if content_type in [CONTENT_TYPE.JSON, CONTENT_TYPE.URLENCODED]:
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
                log.warning(f'Unknown content type value: {content_type}')
                ret = False
        else:
            log.warning(f'Unknown action value: {action}')
            ret = False

        return ret
