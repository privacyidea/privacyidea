# -*- coding: utf-8 -*-
#
#  2019-09-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial writup
#
# License:  AGPLv3
# (c) 2019. Cornelius Kölbel
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
__doc__ = """This is the event handler module that can mangle the JSON response.
We can add or delete key or even subtrees in the JSON response of a request.

The key is identified by a JSON Pointer
(see https://tools.ietf.org/html/rfc6901)
"""
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib.utils import is_true
from privacyidea.lib import _
import json
import logging


log = logging.getLogger(__name__)


class ACTION_TYPE(object):
    """
    Allowed actions
    """
    SET = "set"
    DELETE = "delete"


class ResponseManglerEventHandler(BaseEventHandler):
    """
    An Eventhandler needs to return a list of actions, which it can handle.

    It also returns a list of allowed action and conditions

    It returns an identifier, which can be used in the eventhandlig definitions
    """

    identifier = "ResponseMangler"
    description = "This event handler can mangle the JSON response."

    @property
    def allowed_positions(cls):
        """
        This returns the allowed positions of the event handler definition.
        The ResponseMangler can only be located at the "post" position

        :return: list of allowed positions
        """
        return ["post"]

    @property
    def actions(cls):
        """
        This method returns a dictionary of allowed actions and possible
        options in this handler module.

        :return: dict with actions
        """
        actions = {ACTION_TYPE.DELETE:
                       {"JSON pointer":
                            {"type": "str",
                             "required": True,
                             "description": _("The JSON pointer (key) that should be deleted. Please "
                                              "specify in the format '/detail/message'.")}
                        },
                   ACTION_TYPE.SET:
                       {"JSON pointer":
                            {"type": "str",
                             "required": True,
                             "description": _("The JSON pointer (key) that should be set. "
                                              "Please specify in the format '/detail/message'.")
                             },
                        "type":
                            {"type": "str",
                             "required": True,
                             "description": _("The type of the value."),
                             "value": ["string", "integer", "bool"]
                            },
                        "value":
                            {"type": "str",
                             "required": True,
                             "description": _("The value of the JSON key that should be set.")
                            }
                        }
                   }
        return actions

    def do(self, action, options=None):
        """
        This method executes the defined action in the given event.

        :param action:
        :param options: Contains the flask parameters g, request, response
            and the handler_def configuration
        :type options: dict
        :return:
        """
        ret = True
        response = options.get("response")
        try:
            content = self._get_response_content(response)
        except Exception:
            # The body could not be decoded to JSON. Actually this would be
            # a BadRequest, but we refrain from importing from werkzeug, here.
            log.info("The body could not be decoded to JSON.")
            # Early exist
            return ret
        handler_def = options.get("handler_def")
        handler_options = handler_def.get("options", {})

        json_pointer = handler_options.get("JSON pointer", "")
        value = handler_options.get("value")
        type = handler_options.get("type")
        comp = json_pointer.split("/")
        comp = [x for x in comp if x]
        if action.lower() == ACTION_TYPE.DELETE:
            try:
                if len(comp) == 1:
                    del(content[comp[0]])
                elif len(comp) == 2:
                    del(content[comp[0]][comp[1]])
                elif len(comp) == 3:
                    del (content[comp[0]][comp[1]][comp[2]])
                else:
                    log.warning("JSON pointer length of {0!s} not supported.".format(len(comp)))
                options.get("response").data = json.dumps(content)
            except KeyError:
                log.warning("Can not delete response JSON Pointer {0!s}.".format(json_pointer))
        elif action.lower() == ACTION_TYPE.SET:
            try:
                if type == "integer":
                    value = int(value)
                elif type == "bool":
                    value = is_true(value)
            except ValueError:
                log.warning("Failed to convert value")

            if len(comp) == 1:
                content[comp[0]] = value
            elif len(comp) == 2:
                content[comp[0]] = content.get(comp[0]) or {}
                content[comp[0]][comp[1]] = value
            elif len(comp) == 3:
                content[comp[0]] = content.get(comp[0]) or {}
                content[comp[0]][comp[1]] = content[comp[0]].get(comp[1]) or {}
                content[comp[0]][comp[1]][comp[2]] = value
            else:
                log.warning("JSON pointer of length {0!s} not supported.".format(len(comp)))
            options.get("response").data = json.dumps(content)

        return ret
