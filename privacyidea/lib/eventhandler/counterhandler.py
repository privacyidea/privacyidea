# -*- coding: utf-8 -*-
#
#  2018-23-09 Paul Lettich <paul.lettich@netknights.it>
#             Add decrease and reset counter actions
#  2018-02-28 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial writeup
#
# License:  AGPLv3
# (c) 2018. Cornelius Kölbel
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
__doc__ = """This is the event handler module for
increasing/decreasing/resetting database counters.
These counters can be used by rrdtool to monitor values and print time series of
certain parameters.
"""
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib import _
from privacyidea.lib.counter import increase, decrease, reset
import logging
from privacyidea.lib.utils import is_true
import traceback

log = logging.getLogger(__name__)


class CounterEventHandler(BaseEventHandler):
    """
    An CounterEventHandler needs to return a list of actions, which it can handle.
    It also returns a list of allowed action and conditions
    It returns an identifier, which can be used in the eventhandling definitions
    """

    identifier = "Counter"
    description = "This event handler increases arbitrary counters in the database."

    @property
    def allowed_positions(cls):
        """
        This returns the allowed positions of the event handler definition.
        :return: list of allowed positions
        """
        return ["post", "pre"]

    @property
    def actions(cls):
        """
        This method returns a dictionary of allowed actions and possible
        options in this handler module.

        :return: dict with actions
        """
        actions = {"increase_counter": {
            "counter_name": {
                "type": "str",
                "description": _("The identifier/key of the counter.")}
            },
            "decrease_counter": {
                "counter_name": {
                    "type": "str",
                    "description": _("The identifier/key of the counter.")},
                'allow_negative_values': {
                    "type": "bool",
                    "description": _("Don't stop counter if it reaches zero.")}
            },
            "reset_counter": {
                "counter_name": {
                    "type": "str",
                    "description": _("The identifier/key of the counter.")}
        }}
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
        #g = options.get("g")
        handler_def = options.get("handler_def")
        handler_options = handler_def.get("options", {})
        counter_name = handler_options.get("counter_name")

        if action == "increase_counter":
            increase(counter_name)
            log.debug("Increased the counter {0!s}.".format(counter_name))
        elif action == "decrease_counter":
            allow_negative = is_true(handler_options.get("allow_negative_values", False))
            decrease(counter_name, allow_negative)
            log.debug("Decreased the counter {0!s}.".format(counter_name))
        elif action == "reset_counter":
            reset(counter_name)
            log.debug("Reset the counter {0!s} to 0.".format(counter_name))

        return ret
