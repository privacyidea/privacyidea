# -*- coding: utf-8 -*-
#
#  2020-27-12 Paul Lettich <paul.lettich@netknights.it>
#             Initial Version of the logging event handler
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
__doc__ = """This is the event handler module for logging.
It can be bound to each event and can perform the action:

  * logging: Send a log message to the configured python logging facility

The module is tested in tests/test_lib_eventhandler_logging.py
"""
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib.token import get_tokens
from privacyidea.lib.utils import create_tag_dict, to_unicode
from privacyidea.lib import _
import logging

log = logging.getLogger(__name__)


class LOGGING_LEVEL(object):
    """
    Allowed logging levels
    """
    ERROR = logging.getLevelName(logging.ERROR)
    WARNING = logging.getLevelName(logging.WARNING)
    INFO = logging.getLevelName(logging.INFO)
    DEBUG = logging.getLevelName(logging.DEBUG)


DEFAULT_LOGMSG = "event={action} triggered"
DEFAULT_LOGGER_NAME = 'pi-eventlogger'
DEFAULT_LOGLEVEL = LOGGING_LEVEL.INFO


class LoggingEventHandler(BaseEventHandler):
    """
    The LoggingEventHandler issues a log message every time the event occurs.
    """

    identifier = "Logging"
    description = "This eventhandler logs the event to the specified python " \
                  "logging facility"

    @property
    def allowed_positions(self):
        """
        This returns the allowed positions of the event handler definition.
        :return: list of allowed positions
        :rtype: list
        """
        return ["post", "pre"]

    @property
    def actions(self):
        """
        This method returns a dictionary of allowed actions and possible
        options in this handler module.

        :return: Dictionary with actions
        :rtype: dict
        """
        actions = {
            "logging": {
                'name': {
                    'type': 'str',
                    'required': False,
                    'default': DEFAULT_LOGGER_NAME,
                    'description': _('The name of the logging facility')
                },
                'message': {
                    'type': 'str',
                    'required': False,
                    'default': DEFAULT_LOGMSG,
                    'description': _('The string to write to the log')
                },
                'level': {
                    'type': 'str',
                    'required': False,
                    'default': DEFAULT_LOGLEVEL,
                    'description': _('The logging level for this logging notification'),
                    'value': [
                        LOGGING_LEVEL.ERROR,
                        LOGGING_LEVEL.WARNING,
                        LOGGING_LEVEL.INFO,
                        LOGGING_LEVEL.DEBUG
                    ]
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
        :rtype: bool
        """
        ret = False

        if action.lower() == 'logging':
            tokentype = None
            g = options.get("g")
            handler_def = options.get("handler_def")
            handler_options = handler_def.get("options", {})
            logged_in_user = g.logged_in_user if hasattr(g, 'logged_in_user') else {}
            request = options.get("request")
            response = options.get("response")
            tokenowner = self._get_tokenowner(request)
            content = self._get_response_content(response)
            serial = (request.all_data.get("serial")
                      or content.get("detail", {}).get("serial")
                      or g.audit_object.audit_data.get("serial"))
            if serial:
                tokens = get_tokens(serial=serial)
                if tokens:
                    tokentype = tokens[0].get_tokentype()
            else:
                token_objects = get_tokens(user=tokenowner)
                serial = ','.join([tok.get_serial() for tok in token_objects])

            tags = create_tag_dict(logged_in_user=logged_in_user,
                                   request=request,
                                   client_ip=g.client_ip,
                                   tokenowner=tokenowner,
                                   serial=serial,
                                   tokentype=tokentype)

            logger_name = handler_options.get('name', DEFAULT_LOGGER_NAME)
            log_action = logging.getLogger(logger_name)
            log_level = getattr(logging,
                                handler_options.get('level', DEFAULT_LOGLEVEL),
                                logging.INFO)
            log_template = handler_options.get('message') or DEFAULT_LOGMSG
            log_action.log(log_level, to_unicode(log_template).format(**tags))
            ret = True

        return ret
