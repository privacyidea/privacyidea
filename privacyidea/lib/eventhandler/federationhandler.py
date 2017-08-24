# -*- coding: utf-8 -*-
#
#  2017-08-23 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial federation handler
#
# License:  AGPLv3
# (c) 2017. Cornelius Kölbel
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
__doc__ = """This is the event handler module for privacyIDEA federations.
Requests can be forwarded to other privacyIDEA servers.
"""
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib.privacyideaserver import get_privacyideaservers
from privacyidea.lib import _
import json
import logging
import requests


log = logging.getLogger(__name__)


class ACTION_TYPE(object):
    """
    Allowed actions
    """
    FORWARD = "forward"


class FederationEventHandler(BaseEventHandler):
    """
    An Eventhandler needs to return a list of actions, which it can handle.

    It also returns a list of allowed action and conditions

    It returns an identifier, which can be used in the eventhandlig definitions
    """

    identifier = "Federation"
    description = "This event handler can forward the request to other " \
                  "privacyIDEA servers"

    @property
    def actions(cls):
        """
        This method returns a dictionary of allowed actions and possible
        options in this handler module.

        :return: dict with actions
        """
        pi_servers = [x.config.identifier for x in get_privacyideaservers()]
        actions = {ACTION_TYPE.FORWARD:
                       {"privacyIDEA":
                            {"type": "str",
                             "required": True,
                             "value": pi_servers,
                             "description": _("The remote/child privacyIDEA "
                                              "Server.")
                             },
                        "realm":
                            {"type": "str",
                             "description": _("Change the realm name to a "
                                              "realm on the child privacyIDEA "
                                              "system.")
                            },
                        "resolver":
                            {"type": "str",
                             "description": _("Change the resolver name to a "
                                              "resolver on the child "
                                              "privacyIDEA system.")
                            },
                        "forward_client_ip":
                            {"type": "bool",
                             "description": _("Forward the client IP to the "
                                              "child privacyIDEA server. "
                                              "Otherwise this server will "
                                              "be the client.")
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
        g = options.get("g")
        request = options.get("request")

        # We will modify the response!
        response = options.get("response")
        content = json.loads(response.data)
        handler_def = options.get("handler_def")
        handler_options = handler_def.get("options", {})

        method = request.method
        # request.headers
        path = request.path
        data = request.all_data
        # compose requests to remote server.
        # Then we overwrite the originial response.

        return ret

