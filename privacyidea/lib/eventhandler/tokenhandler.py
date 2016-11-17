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
from privacyidea.lib.smtpserver import get_smtpservers
from privacyidea.lib.smsprovider.SMSProvider import get_smsgateway
from privacyidea.lib.realm import get_realms
from privacyidea.lib.token import set_realms
from gettext import gettext as _
import json
import logging

log = logging.getLogger(__name__)


class ACTION_TYPE(object):
    """
    Allowed actions
    """
    SET_TOKENREALM = "set tokenrealm"


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
        smtpserver_objs = get_smtpservers()
        smsgateway_dicts = get_smsgateway()
        smsgateways = [sms.identifier for sms in smsgateway_dicts]
        smtpservers = [s.config.identifier for s in smtpserver_objs]
        from privacyidea.lib.token import get_token_types
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
                   "unassign": {},
                   "assign": {},
                   "delete": {},
                   "init": {"tokentype": {"type": "str",
                                          "required": True,
                                          "description": _("Token type to "
                                                           "create"),
                                          "value": get_token_types()},
                            "user": {},
                            "realm": {}
                            },
                   "disable": {},
                   "enable": {},
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

        if serial:
            # DO THE ACTION
            if action.lower() == ACTION_TYPE.SET_TOKENREALM:
                realm = handler_options.get("realm")
                only_realm = handler_options.get("only_realm")
                # Set the realm..
                log.info("Setting realm of token {0!s} to {1!s}".format(
                    serial, realm))
                # Add the token realm
                set_realms(serial, [realm], add=True)

        return ret


