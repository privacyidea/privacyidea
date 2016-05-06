# -*- coding: utf-8 -*-
#
#  2016-05-04 Cornelius Kölbel <cornelius.koelbel@netknights.it>
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
import functools
import logging
log = logging.getLogger(__name__)


class event(object):
    """
    This is the event decorator that calls the event handler in the handler
    module. This event decorator can be used at any API call
    """

    def __init__(self, eventname, request, g):
        self.eventname = eventname
        self.request = request
        self.g = g

    def __call__(self, func):
        """
        Returns a wrapper that wraps func.
        The wrapper will evaluate the event handling definitions and call the
        defined action.

        :param func: The function that is decorated
        :return: function
        """
        @functools.wraps(func)
        def event_wrapper(*args, **kwds):
            # TODO here we have to evaluate the event configuration from the
            # DB table eventhandler and based on the self.eventname etc...
            from privacyidea.lib.eventhandler.usernotification import UserNotificationEventHandler
            f_result = func(*args, **kwds)
            # Post events
            event_handler = UserNotificationEventHandler()
            # The "action is determined by the event configuration
            # In the options we can pass the mailserver configuration
            event_handler.do("sendmail", options={
                "request": self.request,
                "g": self.g,
                "emailconfig": "themis"})
            return f_result

        return event_wrapper

