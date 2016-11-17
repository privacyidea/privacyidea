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
from privacyidea.lib.smtpserver import send_email_identifier
from privacyidea.lib.smsprovider.SMSProvider import send_sms_identifier
from privacyidea.lib.auth import get_db_admin
from privacyidea.lib.token import get_tokens
from privacyidea.lib.smtpserver import get_smtpservers
from privacyidea.lib.smsprovider.SMSProvider import get_smsgateway
from privacyidea.lib.user import User, get_user_list
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


class NOTIFY_TYPE(object):
    """
    Allowed token owner
    """
    TOKENOWNER = "tokenowner"
    LOGGED_IN_USER = "logged_in_user"
    INTERNAL_ADMIN = "internal admin"
    ADMIN_REALM = "admin realm"
    EMAIL = "email"


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
        smtpserver_objs = get_smtpservers()
        smsgateway_dicts = get_smsgateway()
        smsgateways = [sms.identifier for sms in smsgateway_dicts]
        smtpservers = [s.config.identifier for s in smtpserver_objs]
        from privacyidea.lib.token import get_token_types
        actions = {"unassign": {},
                   "assign": {"user": {},
                              "realm": {}
                              },
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
        notify_type = handler_options.get("To", NOTIFY_TYPE.TOKENOWNER)
        try:
            logged_in_user = g.logged_in_user
        except Exception:
            logged_in_user = {}

        tokenowner = self._get_tokenowner(request)
        log.debug("Executing event for action {0!s}, user {1!s},"
                  "logged_in_user {2!s}".format(action, tokenowner,
                                                logged_in_user))

        # Determine recipient
        recipient = None

        if notify_type == NOTIFY_TYPE.TOKENOWNER and not tokenowner.is_empty():
            recipient = {
                "givenname": tokenowner.info.get("givenname"),
                "surname": tokenowner.info.get("surname"),
                "username": tokenowner.login,
                "userrealm": tokenowner.realm,
                "email": tokenowner.info.get("email"),
                "mobile": tokenowner.info.get("mobile")
            }
        elif notify_type == NOTIFY_TYPE.INTERNAL_ADMIN:
            username = handler_options.get("To "+NOTIFY_TYPE.INTERNAL_ADMIN)
            internal_admin = get_db_admin(username)
            recipient = {
                "givenname": username,
                "email": internal_admin.email if internal_admin else ""
            }
        elif notify_type == NOTIFY_TYPE.ADMIN_REALM:
            # Send emails to all the users in the specified admin realm
            admin_realm = handler_options.get("To "+NOTIFY_TYPE.ADMIN_REALM)
            ulist = get_user_list({"realm": admin_realm})
            # create a list of all user-emails, if the user has an email
            emails = [u.get("email") for u in ulist if u.get("email")]
            recipient = {
                "givenname": "admin of realm {0!s}".format(admin_realm),
                "email": emails
            }
        elif notify_type == NOTIFY_TYPE.LOGGED_IN_USER:
            # Send notification to the logged in user
            if logged_in_user.get("user") and not logged_in_user.get("realm"):
                # internal admins have no realm
                internal_admin = get_db_admin(logged_in_user.get("user"))
                if internal_admin:
                    recipient = {
                        "givenname": logged_in_user.get("user"),
                        "email": internal_admin.email if internal_admin else ""
                    }
            else:
                # Try to find the user in the specified realm
                user_obj = User(logged_in_user.get("user"),
                                logged_in_user.get("realm"))
                if user_obj:
                    recipient = {
                        "givenname": user_obj.info.get("givenname"),
                        "surname": user_obj.info.get("surname"),
                        "email": user_obj.info.get("email"),
                        "mobile": user_obj.info.get("mobile")
                    }

        elif notify_type == NOTIFY_TYPE.EMAIL:
            email = handler_options.get("To "+NOTIFY_TYPE.EMAIL, "").split(",")
            recipient = {
                "email": email
            }
        else:
            log.warning("Was not able to determine the recipient for the user "
                        "notification: {0!s}".format(handler_def))

        if recipient:
            # Collect all data
            body = handler_options.get("body") or DEFAULT_BODY
            serial = request.all_data.get("serial") or \
                     content.get("detail", {}).get("serial") or \
                     g.audit_object.audit_data.get("serial")
            registrationcode = content.get("detail", {}).get("registrationcode")
            tokentype = None
            if serial:
                tokens = get_tokens(serial=serial)
                if tokens:
                    tokentype = tokens[0].get_tokentype()
            else:
                token_objects = get_tokens(user=tokenowner)
                serial = ','.join([tok.get_serial() for tok in token_objects])

            body = body.format(
                admin=logged_in_user.get("username"),
                realm=logged_in_user.get("realm"),
                action=request.path,
                serial=serial,
                url=request.url_root,
                user=tokenowner.info.get("givenname"),
                surname=tokenowner.info.get("surname"),
                givenname=recipient.get("givenname"),
                username=tokenowner.login,
                userrealm=tokenowner.realm,
                tokentype=tokentype,
                registrationcode=registrationcode,
                recipient_givenname=recipient.get("givenname"),
                recipient_surname=recipient.get("surname")
            )

            # Send notification
            if action.lower() == "sendmail":
                emailconfig = handler_options.get("emailconfig")
                useremail = recipient.get("email")
                subject = handler_options.get("subject") or \
                          "An action was performed on your token."
                try:
                    ret = send_email_identifier(emailconfig,
                                                recipient=useremail,
                                                subject=subject, body=body)
                except Exception as exx:
                    log.error("Failed to send email: {0!s}".format(exx))
                    ret = False
                if ret:
                    log.info("Sent a notification email to user {0}".format(
                        recipient))
                else:
                    log.warning("Failed to send a notification email to user "
                                "{0}".format(recipient))

            elif action.lower() == "sendsms":
                smsconfig = handler_options.get("smsconfig")
                userphone = recipient.get("mobile")
                try:
                    ret = send_sms_identifier(smsconfig, userphone, body)
                except Exception as exx:
                    log.error("Failed to send sms: {0!s}".format(exx))
                    ret = False
                if ret:
                    log.info("Sent a notification sms to user {0}".format(
                        recipient))
                else:
                    log.warning("Failed to send a notification email to user "
                                "{0}".format(recipient))

        return ret


