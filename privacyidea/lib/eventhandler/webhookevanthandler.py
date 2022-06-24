# -*- coding: utf-8 -*-

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
from collections import defaultdict

log = logging.getLogger(__name__)


class CONTENT_TYPE(object):
    """
    Allowed type off content
    """
    JSON = "json"
    URLENCODED = "urlendcode"


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
    def allowed_positions(cls):
        """
        This returns the allowed positions of the event handler definition.

        :return: list of allowed positions
        """
        return ["post", "pre"]

    @property
    def actions(cls):
        """
        This method returns a dictionary of allowed actions and possible
        options in this handler module.

        :return: dict with actions
        """
        #The event handler has just one action. Maybe we can  hide action selct for the clarity of the UI
        actions = {ACTION_TYPE.POST_WEBHOOK: {
            "URL": {
                "type": "str",
                "required": True,
                "description": _("The URL the WebHook is posted to")
            },
            "cotent_type": {
                "type": "str",
                "required": True,
                "description": _("The form the WebHook is sent, for example json"),
                "value": [
                    CONTENT_TYPE.JSON,
                    CONTENT_TYPE.URLENCODED]
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
        :param options: Contains the flask parameters g,  URL, data, parameter and the fire and forget
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

        #Replace placeholder in data
        logged_in_user = g.logged_in_user.get("username")
        attributes = {
            'logged_in_user': logged_in_user
        }
        webhook_text = webhook_text.format_map(defaultdict(str, attributes))

        
        if action.lower() == ACTION_TYPE.POST_WEBHOOK:
            try:
                if (content_type == "urlendcode") or (content_type == "json"):
                    #This is the main function where the webhook is sent.
                    #Documationon of the requests function is fond her docs.python-requests.org
                    resp = requests.post(webhook_url, data=json.dumps(webhook_text, sort_keys=True, default=str),
                                         headers={'Content-Type': content_type}, timeout=1.0)
                    #all answers will be logged in the debug. The HTTP response code will be shown in the audit too
                    httpcode = resp.status_code
                    log.info('A webhook is send to {0!r} with the text: {1!r}'.format(
                        webhook_url, webhook_text))
                    log.info(httpcode)
                    log.debug(resp)
                else:
                    log.warning('Unknown content type value: {0!s}'.format(content_type))
                    ret = False
            #error handling
            except requests.exceptions.HTTPError as err:
                log.warning(err)
                return False
            except requests.exceptions.ConnectionError as err:
                log.warning(err)
                return False
            except requests.exceptions.Timeout as err:
                log.warning(err)
                return False
            except requests.exceptions.RequestException as err:
                log.warning(err)
                return False
        else:
            log.warning('Unknown action value: {0!s}'.format(action))
            ret = False
        return ret
