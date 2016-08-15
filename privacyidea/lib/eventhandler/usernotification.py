# -*- coding: utf-8 -*-
#
#  2016-07-18 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add notification conditions
#  2016-05-06 Cornelius Kölbel <cornelius.koelbel@netknights.it>
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
__doc__ = """This is the event handler module for user notifications.
It can be bound to each event and can perform the action:

  * sendmail: Send an email to the user/token owner
  * sendsms: We can also notify the user with an SMS.

The module is tested in tests/test_lib_events.py
"""
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib.smtpserver import send_email_identifier
from privacyidea.lib.smsprovider.SMSProvider import send_sms_identifier
from privacyidea.lib.auth import ROLE
from privacyidea.lib.user import get_user_from_param
from privacyidea.lib.token import get_token_owner, get_tokens
from privacyidea.lib.realm import get_realms
from privacyidea.lib.smtpserver import get_smtpservers
from privacyidea.lib.smsprovider.SMSProvider import get_smsgateway
from gettext import gettext as _
import json
import logging
log = logging.getLogger(__name__)

DEFAULT_BODY = """
Hello {user},

the administrator {admin}@{realm} performed the action
{action} on your token {serial}.

To check your tokens you may login to the Web UI:
{url}
"""


class UserNotificationEventHandler(BaseEventHandler):
    """
    An Eventhandler needs to return a list of actions, which it can handle.

    It also returns a list of allowed action and conditions

    It returns an identifier, which can be used in the eventhandlig definitions
    """

    identifier = "UserNotification"
    description = "This eventhandler notifies the user about actions on his " \
                  "tokens"

    @property
    def actions(cls):
        """
        This method returns a dictionary of allowed actions and possible
        options in this handler module.

        :return: dict with actions
        """
        smtpserver_objs = get_smtpservers()
        smsgateway_dicts = get_smsgateway()
        smsgateways = [sms.identifier for sms in smsgateway_dicts]
        smtpservers = [s.config.identifier for s in smtpserver_objs]
        actions = {"sendmail": {"emailconfig":
                                     {"type": "str",
                                      "required": True,
                                      "description": _("Send notification "
                                                       "email via this "
                                                       "email server."),
                                      "value": smtpservers},
                                "subject": {"type": "str",
                                            "required": False,
                                            "description": _("The subject of "
                                                             "the mail that "
                                                             "is sent.")


                                },
                                "body": {"type": "text",
                                         "required": False,
                                         "description": _("The body of the "
                                                          "mail that is sent.")}
                                },
                   "sendsms": {"smsconfig":
                                   {"type": "str",
                                    "required": True,
                                    "description": _("Send the user "
                                                     "notification via a "
                                                     "predefined SMS "
                                                     "gateway."),
                                    "value": smsgateways},
                               "body": {"type": "text",
                                    "required": False,
                                    "description": _("The text of the SMS.")}
                               }
                   }
        return actions

    @property
    def conditions(cls):
        """
        The UserNotification can filter for conditions like
        * type of logged in user and
        * successful or failed value.success

        :return: dict
        """
        realms = get_realms()
        cond = {
            "realm": {
                "type": "str",
                "desc": _("The user realm, for which this event should aply."),
                "value": realms.keys()
            },
            "logged_in_user": {
                "type": "str",
                "desc": _("The logged in user is of the following type."),
                "value": (ROLE.ADMIN, ROLE.USER)
            },
            "result_value": {
                "type": "str",
                "desc": _("The result.value within the response is "
                          "True or False."),
                "value": ("True", "False")
            },
            "token_locked": {
                "type": "str",
                "desc": _("Check if the max failcounter of the token is "
                          "reached."),
                "value": ("True", "False")
            }
        }
        return cond

    @staticmethod
    def _get_user(request):
        user = get_user_from_param(request.all_data)
        serial = request.all_data.get("serial")
        if user.is_empty() and serial:
            # maybe the user is empty, but a serial was passed.
            # Then we determine the user by the serial
            user = get_token_owner(serial)
        return user

    def check_condition(self, options):
        """
        Check if all conditions are met and if the action should be executed.
        The the conditions are met, we return "True"
        :return: True
        """
        res = True
        g = options.get("g")
        request = options.get("request")
        response = options.get("response")
        e_handler_def = options.get("handler_def")
        # conditions can be correspnding to the property conditions
        conditions = e_handler_def.get("conditions")
        content = json.loads(response.data)
        user = self._get_user(request)
        if "realm" in conditions:
            res = user.realm == conditions.get("realm")

        if "logged_in_user" in conditions and res:
            # Determine the role of the user
            try:
                logged_in_user = g.logged_in_user
                user_role = logged_in_user.get("role")
            except Exception:
                # A non-logged-in-user is a User, not an admin
                user_role = ROLE.USER
            res = user_role == conditions.get("logged_in_user")

        # Check result_value only if the check condition is still True
        if "result_value" in conditions and res:
            res = content.get("result", {}).get("value") == conditions.get(
                "result_value")

        # checking of max-failcounter state of the token
        if "token_locked" in conditions and res:
            serial = request.all_data.get("serial") or \
                     content.get("detail", {}).get("serial")
            if serial:
                tokens = get_tokens(serial=serial)
                if tokens:
                    token_obj = tokens[0]
                    locked = token_obj.get_failcount() >= \
                             token_obj.get_max_failcount()
                    res = (conditions.get("token_locked") in ["True", True]) \
                          == locked

        return res

    def do(self, action, options=None):
        """
        This method executes the defined action in the given event.

        :param action:
        :param options: Contains the flask parameters g and request and the
            handler_def configuration
        :type options: dict
        :return:
        """
        ret = True
        g = options.get("g")
        request = options.get("request")
        handler_def = options.get("handler_def")
        try:
            logged_in_user = g.logged_in_user
        except Exception:
            logged_in_user = {}
        user = self._get_user(request)
        if not user.is_empty() and user.login and logged_in_user.get("role") ==\
                ROLE.ADMIN:
            body = handler_def.get("body") or DEFAULT_BODY
            body = body.format(
                admin=logged_in_user.get("username"),
                realm=logged_in_user.get("realm"),
                action=request.path,
                serial=g.audit_object.audit_data.get("serial"),
                url=request.url_root,
                user=user.info.get("givenname")
            )

            if action.lower() == "sendmail":
                emailconfig = handler_def.get("emailconfig")
                useremail = user.info.get("email")
                subject = handler_def.get("subject") or \
                          "An action was performed on your token."
                try:
                    ret = send_email_identifier(emailconfig,
                                                recipient=useremail,
                                                subject=subject, body=body)
                except Exception as exx:
                    log.error("Failed to send email: {0!s}".format(exx))
                    ret = False
                if ret:
                    log.info("Sent a notification email to user {0}".format(user))
                else:
                    log.warning("Failed to send a notification email to user "
                                "{0}".format(user))

            elif action.lower() == "sendsms":
                smsconfig = handler_def.get("smsconfig")
                userphone = user.info.get("mobile")
                try:
                    ret = send_sms_identifier(smsconfig, userphone, body)
                except Exception as exx:
                    log.error("Failed to send sms: {0!s}".format(exx))
                    ret = False
                if ret:
                    log.info("Sent a notification sms to user {0}".format(user))
                else:
                    log.warning("Failed to send a notification email to user "
                                "{0}".format(user))

        return ret


