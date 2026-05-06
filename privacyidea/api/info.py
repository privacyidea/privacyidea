# (c) NetKnights GmbH 2024,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2024 Cornelius Kölbel <cornelius.koelbel@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#

from flask import (Blueprint, request, g, current_app)
from privacyidea.lib.info.rss import get_news, FETCH_DAYS
import logging
from .lib.utils import send_result, getParam
from ..lib.log import log_with
from privacyidea.api.lib.prepolicy import prepolicy, rss_age
from privacyidea.lib.policy import Match, SCOPE, convert_action_dict_to_python_dict
from ..lib.policies.actions import PolicyAction

info_blueprint = Blueprint('info_blueprint', __name__)
log = logging.getLogger(__name__)

__doc__ = """
The info API can be accessed via /info.

It provides several different information that can be configured by the administrator.

The endpoint /info/rss e.g. returns the contents of configured RSS feeds.

The user or admin must be authenticated to access this API.

To see how to authenticate read :ref:`rest_auth`.
"""


@info_blueprint.route('/rss', methods=['GET'])
@prepolicy(rss_age, request)
@log_with(log, log_entry=False)
def rss():
    """
    Return news items aggregated from the configured RSS feeds.

    The set of feeds that is polled is controlled by the WebUI-scope policy
    action :ref:`policy_rss_feeds`. The maximum age of returned items
    defaults to 180 days and can be overridden per request via the policy
    action :ref:`policy_rss_age`. If no ``rss_feeds`` policy is set for the
    user, a built-in default feed list is used.

    :query channel: Optional channel name to filter on. If omitted, items
        from every configured channel are returned.
    :status 200: JSON response; news items are in ``result.value``.
    """
    feeds = None
    param = request.all_data
    age = int(getParam(param, PolicyAction.RSS_AGE, default=FETCH_DAYS))
    channel = getParam(param, "channel")
    user = request.User if hasattr(request, 'User') else None
    feeds_pol = (Match.user(g, scope=SCOPE.WEBUI, action=PolicyAction.RSS_FEEDS, user_object=user).action_values(
        allow_white_space_in_action=True, unique=True))

    if len(feeds_pol) == 1:
        feeds_list = list(feeds_pol.keys())
        feeds: dict = convert_action_dict_to_python_dict(feeds_list[0])
    r = get_news(channel=channel, days=age, rss_feeds=feeds)
    return send_result(r)
