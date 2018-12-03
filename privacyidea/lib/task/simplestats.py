# -*- coding: utf-8 -*-
#
#  2018-08-06 Paul Lettich <paul.lettich@netknights.it>
#
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
import logging

from privacyidea.lib.utils import is_true
from privacyidea.lib.tokenclass import TOKENKIND
from privacyidea.lib.token import get_tokens
from privacyidea.lib.monitoringstats import write_stats
from privacyidea.lib.subscriptions import get_users_with_active_tokens
from privacyidea.lib.task.base import BaseTask
# from privacyidea.lib.user import get_user_list
from privacyidea.lib import _

__doc__ = """This is a statistics task which collects simple statistics from the database.
If You want to add more statistic points, simply add them to the options method and add a
corresponding property function (beginning with a '_').
The entry in the monitoringstats table will have the same key as the property name."""

log = logging.getLogger(__name__)


class SimpleStatsTask(BaseTask):
    identifier = "SimpleStats"
    description = "Collect simple statistics"

    @property
    def options(self):
        return {
            "total_tokens": {
                "type": "bool",
                "description": _("Total number of tokens")},
            "hardware_tokens": {
                "type": "bool",
                "description": _("Total number of hardware tokens")},
            "software_tokens": {
                "type": "bool",
                "description": _("Total number of software tokens")},
            "unassigned_hardware_tokens": {
                "type": "bool",
                "description": _("Number of hardware tokens not assigned to a user")},
            "assigned_tokens": {
                "type": "bool",
                "description": _("Number of tokens assigned to users")},
            "user_with_token": {
                "type": "bool",
                "description": _("Number of users with tokens assigned")}
            }

    @property
    def _user_with_token(self):
        return get_users_with_active_tokens()

    @property
    def _total_tokens(self):
        return get_tokens(count=True)

    @property
    def _hardware_tokens(self):
        return get_tokens(count=True, tokeninfo={'tokenkind': TOKENKIND.HARDWARE})

    @property
    def _software_tokens(self):
        return get_tokens(count=True, tokeninfo={'tokenkind': TOKENKIND.SOFTWARE})

    @property
    def _unassigned_hardware_tokens(self):
        return get_tokens(count=True, tokeninfo={'tokenkind': 'hardware'}, assigned=False)

    @property
    def _assigned_tokens(self):
        return get_tokens(count=True, assigned=True)

    def do(self, params):
        for opt in self.options.keys():
            if is_true(params.get(opt)):
                log.debug("Got param {0}".format(opt))
                write_stats(opt, getattr(self, '_' + opt))

        return True
