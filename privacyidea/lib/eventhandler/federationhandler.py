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
from privacyidea.lib.token import (get_token_types, set_validity_period_end,
                                   set_validity_period_start)
from privacyidea.lib.realm import get_realms
from privacyidea.lib.token import (set_realms, remove_token, enable_token,
                                   unassign_token, init_token, set_description,
                                   set_count_window, add_tokeninfo,
                                   set_failcounter)
from privacyidea.lib.utils import (parse_date, is_true,
                                   parse_time_offset_from_now)
from privacyidea.lib.tokenclass import DATE_FORMAT, AUTH_DATE_FORMAT
from privacyidea.lib import _
import json
import logging
import datetime
from dateutil.parser import parse as parse_date_string
from dateutil.tz import tzlocal

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
        actions = {ACTION_TYPE.FORWARD:
                       {"URL":
                            {"type": "str",
                             "required": True,
                             "description": _("The URL of the child "
                                              "privacyIDEA server.")
                             },
                        "do_not_check_ssl":
                            {"type": "bool",
                             "description": _("The SSL certificate of the "
                                              "privacyIDEA server will not be "
                                              "checked. Do not use this in "
                                              "production!")
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
        response = options.get("response")
        content = json.loads(response.data)
        handler_def = options.get("handler_def")
        handler_options = handler_def.get("options", {})

        return ret

