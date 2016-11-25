# -*- coding: utf-8 -*-
#
#  2016-11-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
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
__doc__ = """This is the event handler module for token actions.
You can attach token actions like enable, disable, delete, unassign,... of the

 * current token
 * all the user's tokens
 * all unassigned tokens
 * all disabled tokens
 * ...
"""
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib.token import (get_token_types, set_validity_period_end,
                                   set_validity_period_start)
from privacyidea.lib.realm import get_realms
from privacyidea.lib.token import (set_realms, remove_token, enable_token,
                                   unassign_token, init_token, set_description)
from privacyidea.lib.utils import parse_date
from privacyidea.lib.tokenclass import DATE_FORMAT
from datetime import datetime
from gettext import gettext as _
import json
import logging

log = logging.getLogger(__name__)


class ACTION_TYPE(object):
    """
    Allowed actions
    """
    SET_TOKENREALM = "set tokenrealm"
    DELETE = "delete"
    UNASSIGN = "unassign"
    DISABLE = "disable"
    ENABLE = "enable"
    INIT = "enroll"
    SET_DESCRIPTION = "set description"
    SET_VALIDITY = "set validity"


class VALIDITY(object):
    """
    Allowed validity options
    """
    START= "valid from"
    END = "valid till"



class TokenEventHandler(BaseEventHandler):
    """
    An Eventhandler needs to return a list of actions, which it can handle.

    It also returns a list of allowed action and conditions

    It returns an identifier, which can be used in the eventhandlig definitions
    """

    identifier = "Token"
    description = "This event handler can trigger new actions on tokens."

    @property
    def actions(cls):
        """
        This method returns a dictionary of allowed actions and possible
        options in this handler module.

        :return: dict with actions
        """
        realm_list = get_realms().keys()
        actions = {ACTION_TYPE.SET_TOKENREALM:
                       {"realm":
                            {"type": "str",
                             "required": True,
                             "description": _("set a new realm of the token"),
                             "value": realm_list},
                        "only_realm":
                            {"type": "bool",
                             "description": _("The new realm will be the only "
                                              "realm of the token. I.e. all "
                                              "other realms will be removed "
                                              "from this token. Otherwise the "
                                              "realm will be added to the token.")
                            }
                        },
                   ACTION_TYPE.DELETE: {},
                   ACTION_TYPE.UNASSIGN: {},
                   ACTION_TYPE.DISABLE: {},
                   ACTION_TYPE.ENABLE: {},
                   ACTION_TYPE.INIT:
                       {"tokentype":
                            {"type": "str",
                             "required": True,
                             "description": _("Token type to create"),
                             "value": get_token_types()
                             },
                        "user":
                            {"type": "bool",
                             "description": _("Assign token to user in "
                                              "request or tokenowner.")},
                        "realm":
                            {"type": "str",
                             "required": False,
                             "description": _("Set the realm of the newly "
                                              "created token."),
                             "value": realm_list},
                        },
                   ACTION_TYPE.SET_DESCRIPTION:
                       {"description":
                            {
                                "type": "str",
                                "description": _("The new description of the "
                                                 "token.")
                            }
                       },
                   ACTION_TYPE.SET_VALIDITY:
                       {VALIDITY.START: {
                           "type": "str",
                           "description": _("The token will be valid starting "
                                            "at the given date. Can be a fixed "
                                            "date or an offset like +10m, "
                                            "+24h, +7d.")
                       },
                        VALIDITY.END: {
                            "type": "str",
                            "description": _("The token will be valid until "
                                             "the given date. Can be a fixed "
                                             "date or an offset like +10m, "
                                             "+24h, +7d.")
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

        serial = request.all_data.get("serial") or \
                 content.get("detail", {}).get("serial") or \
                 g.audit_object.audit_data.get("serial")

        if action.lower() in [ACTION_TYPE.SET_TOKENREALM,
                              ACTION_TYPE.SET_DESCRIPTION,
                              ACTION_TYPE.DELETE, ACTION_TYPE.DISABLE,
                              ACTION_TYPE.ENABLE, ACTION_TYPE.UNASSIGN,
                              ACTION_TYPE.SET_VALIDITY]:
            if serial:
                if action.lower() == ACTION_TYPE.SET_TOKENREALM:
                    realm = handler_options.get("realm")
                    only_realm = handler_options.get("only_realm")
                    # Set the realm..
                    log.info("Setting realm of token {0!s} to {1!s}".format(
                        serial, realm))
                    # Add the token realm
                    set_realms(serial, [realm], add=True)
                elif action.lower() == ACTION_TYPE.DELETE:
                    log.info("Delete token {0!s}".format(serial))
                    remove_token(serial=serial)
                elif action.lower() == ACTION_TYPE.DISABLE:
                    log.info("Disable token {0!s}".format(serial))
                    enable_token(serial, enable=False)
                elif action.lower() == ACTION_TYPE.ENABLE:
                    log.info("Enable token {0!s}".format(serial))
                    enable_token(serial, enable=True)
                elif action.lower() == ACTION_TYPE.UNASSIGN:
                    log.info("Unassign token {0!s}".format(serial))
                    unassign_token(serial)
                elif action.lower() == ACTION_TYPE.SET_DESCRIPTION:
                    log.info("Set description of token {0!s}".format(serial))
                    set_description(serial, handler_options.get(
                        "description", ""))
                elif action.lower() == ACTION_TYPE.SET_VALIDITY:
                    log.info("Set validity period for token {0!s}".format(
                        serial))
                    start_date = handler_options.get(VALIDITY.START)
                    end_date = handler_options.get(VALIDITY.END)
                    if start_date:
                         d = parse_date(start_date)
                         set_validity_period_start(serial, None,
                                                   d.strftime(DATE_FORMAT))
                    if end_date:
                        d = parse_date(end_date)
                        set_validity_period_end(serial, None,
                                                d.strftime(DATE_FORMAT))

            else:
                log.info("Action {0!s} requires serial number. But no serial "
                         "number could be found in request.")

        if action.lower() == ACTION_TYPE.INIT:
            log.info("Initializing new token")
            if handler_options.get("user") in ["1", 1, True]:
                user = self._get_tokenowner(request)
            else:
                user = None
            t = init_token({"type": handler_options.get("tokentype"),
                            "genkey": 1,
                            "realm": handler_options.get("realm", "")},
                           user=user)
            log.info("New token {0!s} enrolled.".format(t.token.serial))

        return ret

