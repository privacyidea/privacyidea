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
__doc__ = """This is the base class for an event handler module.
The event handler module is bound to an event together with

* a condition and
* an action
* optional options ;-)
"""
import logging
log = logging.getLogger(__name__)


class BaseEventHandler(object):
    """
    An Eventhandler needs to return a list of actions, which it can handle.

    It also returns a list of allowed action and conditions

    It returns an identifier, which can be used in the eventhandlig definitions
    """

    identifier = "BaseEventHandler"
    description = "This is the base class of an EventHandler with no " \
                  "functionality"

    def __init__(self):
        pass

    @property
    def actions(cls):
        """
        This method returns a list of available actions, that are provided
        by this event handler.
        :return: list of actions
        """
        actions = ["sample_action_1", "sample_action_2"]
        return actions

    @property
    def events(cls):
        """
        This method returns a list allowed events, that this event handler
        can be bound to and which it can handle with the corresponding actions.

        An eventhandler may return an asterisk ["*"] indicating, that it can
        be used in all events.
        :return: list of events
        """
        events = ["*"]
        return events

    def check_condition(self):
        """
        TODO
        :return:
        """
        # TODO
        return True

    def do(self, action, options=None):
        """
        This method executes the defined action in the given event.

        :param action:
        :param options:
        :return:
        """
        log.info("In fact we are doing nothing, be we presume we are doing"
                 "{0!s}".format(action))
        return True
