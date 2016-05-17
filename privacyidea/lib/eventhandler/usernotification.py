# -*- coding: utf-8 -*-
#
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

TODO:
  * sendsms: We could also notify the user with an SMS.

The module is tested in tests/test_lib_events.py
"""
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib.smtpserver import send_email_identifier
from privacyidea.lib.error import ParameterError
from privacyidea.lib.auth import ROLE
from privacyidea.lib.user import get_user_from_param
from privacyidea.lib.smtpserver import get_smtpservers
from gettext import gettext as _
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
                   "sendsms (not implemented)": {"smsconfig":
                                                      {"type": "str"}
                                                  }
                   }
        return actions

    def check_condition(self):
        """
        Check if all conditions are met and if the action should be executed
        :return: True
        """
        # TODO: Only do this, if someone else performs an action on the token
        # Maybe only perform, if the admin is in a certain realm...
        pass

    def do(self, action, options=None):
        """
        This method executes the defined action in the given event.

        :param action:
        :param environment:
        :param options:
        :return:
        """
        ret = True
        g = options.get("g")
        request = options.get("request")
        logged_in_user = g.logged_in_user
        user = get_user_from_param(request.all_data)
        if action.lower() == "sendmail" and logged_in_user.get("role") == \
                ROLE.ADMIN and not user.is_empty() and user.login:
            emailconfig = options.get("emailconfig")
            if not emailconfig:
                log.error("Missing parameter 'emailconfig'")
                raise ParameterError("Missing parameter 'emailconfig'")
            useremail = user.info.get("email")
            subject = options.get("subject") or "An action was performed on " \
                                                "your token."
            body = options.get("body") or DEFAULT_BODY
            body = body.format(
                admin=logged_in_user.get("username"),
                realm=logged_in_user.get("realm"),
                action=request.path,
                serial=g.audit_object.audit_data.get("serial"),
                url=request.url_root,
                user=user.info.get("givenname")
                )
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

        return ret


