# -*- coding: utf-8 -*-
#
#  2017-07-18 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Allow setting time with timedelta
#  2017-01-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add required mobile number and email address when enrolling tokens
#             added with the help of splashx
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
    SET_TOKENREALM = "set tokenrealm"
    DELETE = "delete"
    UNASSIGN = "unassign"
    DISABLE = "disable"
    ENABLE = "enable"
    INIT = "enroll"
    SET_DESCRIPTION = "set description"
    SET_VALIDITY = "set validity"
    SET_COUNTWINDOW = "set countwindow"
    SET_TOKENINFO = "set tokeninfo"
    SET_FAILCOUNTER = "set failcounter"


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
                                              "request or to tokenowner.")},
                        "realm":
                            {"type": "str",
                             "required": False,
                             "description": _("Set the realm of the newly "
                                              "created token."),
                             "value": realm_list},
                        "dynamic_phone": {
                            "type": "bool",
                            "visibleIf": "tokentype",
                            "visibleValue": "sms",
                            "description": _("Dynamically read the mobile number "
                                             "from the user store.")
                        },
                        "motppin": {
                            "type": "str",
                            "visibleIf": "tokentype",
                            "visibleValue": "motp",
                            "description": _("Set the MOTP PIN of the MOTP "
                                             "token during enrollment. This "
                                             "is a required value for "
                                             "enrolling MOTP tokens.")}
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
                       },
                   ACTION_TYPE.SET_COUNTWINDOW:
                       {"count window":
                            {
                                # TODO: should be "int" but we do not support
                                #  this at the moment.
                                "type": "str",
                                "required": True,
                                "description": _("Set the new count window of "
                                                 "the token.")
                            }
                       },
                   ACTION_TYPE.SET_FAILCOUNTER:
                       {
                           "fail counter":
                               {
                                   "type": "str",
                                   "required": True,
                                   "description": _("Set the failcounter of "
                                                    "the token.")
                               }
                       },
                   ACTION_TYPE.SET_TOKENINFO:
                       {"key":
                           {
                               "type": "str",
                               "required": True,
                               "description": _("Set this tokeninfo key.")
                           },
                        "value":
                            {
                                "type": "str",
                                "description": _("Set the above key the this "
                                                 "value.")
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
                              ACTION_TYPE.SET_VALIDITY,
                              ACTION_TYPE.SET_COUNTWINDOW,
                              ACTION_TYPE.SET_TOKENINFO,
                              ACTION_TYPE.SET_FAILCOUNTER]:
            if serial:
                log.info("{0!s} for token {1!s}".format(action, serial))
                if action.lower() == ACTION_TYPE.SET_TOKENREALM:
                    realm = handler_options.get("realm")
                    only_realm = is_true(handler_options.get("only_realm"))
                    # Set the realm..
                    log.info("Setting realm of token {0!s} to {1!s}".format(
                        serial, realm))
                    # Add the token realm
                    set_realms(serial, [realm], add=not only_realm)
                elif action.lower() == ACTION_TYPE.DELETE:
                    remove_token(serial=serial)
                elif action.lower() == ACTION_TYPE.DISABLE:
                    enable_token(serial, enable=False)
                elif action.lower() == ACTION_TYPE.ENABLE:
                    enable_token(serial, enable=True)
                elif action.lower() == ACTION_TYPE.UNASSIGN:
                    unassign_token(serial)
                elif action.lower() == ACTION_TYPE.SET_DESCRIPTION:
                    description = handler_options.get("description") or ""
                    description, td = parse_time_offset_from_now(description)
                    s_now = (datetime.datetime.now(tzlocal()) + td).strftime(
                        AUTH_DATE_FORMAT)
                    set_description(serial,
                                    description.format(
                                        current_time=s_now,
                                        now=s_now,
                                        client_ip=g.client_ip,
                                        ua_browser=request.user_agent.browser,
                                        ua_string=request.user_agent.string))
                elif action.lower() == ACTION_TYPE.SET_COUNTWINDOW:
                    set_count_window(serial,
                                     int(handler_options.get("count window",
                                                             50)))
                elif action.lower() == ACTION_TYPE.SET_TOKENINFO:
                    tokeninfo = handler_options.get("value") or ""
                    tokeninfo, td = parse_time_offset_from_now(tokeninfo)
                    s_now = (datetime.datetime.now(tzlocal()) + td).strftime(
                        AUTH_DATE_FORMAT)
                    try:
                        username = request.User.loginname
                        realm = request.User.realm
                    except Exception:
                        username = "N/A"
                        realm = "N/A"
                    add_tokeninfo(serial, handler_options.get("key"),
                                  tokeninfo.format(
                                      current_time=s_now,
                                      now=s_now,
                                      client_ip=g.client_ip,
                                      username=username,
                                      realm=realm,
                                      ua_browser=request.user_agent.browser,
                                      ua_string=request.user_agent.string))
                elif action.lower() == ACTION_TYPE.SET_VALIDITY:
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
                elif action.lower() == ACTION_TYPE.SET_FAILCOUNTER:
                    try:
                        set_failcounter(serial,
                                        int(handler_options.get("fail counter")))
                    except Exception as exx:
                        log.warning("Misconfiguration: Failed to set fail "
                                    "counter!")
            else:
                log.info("Action {0!s} requires serial number. But no serial "
                         "number could be found in request.")

        if action.lower() == ACTION_TYPE.INIT:
            log.info("Initializing new token")
            init_param = {"type": handler_options.get("tokentype"),
                          "genkey": 1,
                          "realm": handler_options.get("realm", "")}
            user = None
            if is_true(handler_options.get("user")):
                user = self._get_tokenowner(request)
                tokentype = handler_options.get("tokentype")
                # Some tokentypes need additional parameters or otherwise
                # will fail to enroll.
                # TODO: Other tokentypes will require additional parameters
                if tokentype == "sms":
                    if handler_options.get("dynamic_phone"):
                        init_param["dynamic_phone"] = 1
                    else:
                        init_param['phone'] = user.get_user_phone(
                            phone_type='mobile')
                        if not init_param['phone']:
                            log.warning("Enrolling SMS token. But the user "
                                        "{0!r} has no mobile number!".format(user))
                elif tokentype == "email":
                    init_param['email'] = user.info.get("email", "")
                    if not init_param['email']:
                        log.warning("Enrolling EMail token. But the user {0!s}"
                                    "has no email address!".format(user))
                elif tokentype == "motp":
                    init_param['motppin'] = handler_options.get("motppin")

            t = init_token(param=init_param, user=user)
            log.info("New token {0!s} enrolled.".format(t.token.serial))

        return ret

