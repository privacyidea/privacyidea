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
from privacyidea.lib.info.rss import get_news, RSS_FEEDS
import logging
from .lib.utils import optional, send_result, send_csv_result, required, getParam
from ..lib.log import log_with


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
@log_with(log, log_entry=False)
def rss():
    """
    Get the news from the configured RSS feeds.

    :param channel: The channel to get the news from. If not given, the news from all channels are returned.
    :type channel: str

    :return: JSON response with the news
    """
    param = request.all_data
    channel = getParam(param, "channel")
    r = get_news(channel=channel)
    return send_result(r)
