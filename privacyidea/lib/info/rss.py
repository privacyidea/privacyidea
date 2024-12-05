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
"""
This module reads news from the given RSS feeds
"""
RSS_FEEDS = {"Community News": "https://community.privacyidea.org/c/news.rss",
             "privacyIDEA News": "https://privacyidea.org/feed",
             "NetKnights News": "https://netknights.it/en/feed"}


import feedparser
import logging
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse

log = logging.getLogger(__name__)

RSS_NEWS = {}
FETCH_DAYS = 180


def get_news(rss_feeds=None, channel=None, days=FETCH_DAYS):
    """
    Fetch news from the given RSS feeds

    :param rss_feeds: The RSS feeds to fetch news from
    :type rss_feeds: dict
    :param channel: An optional channel to fetch news from
    :param days: The age of the news to fetch
    :return: A dictionary with the news
    """
    def _parse_rss(rss):
        feed = []
        modified = datetime.now(timezone.utc) - timedelta(days=days)
        for item in rss.entries:
            pub_date = parse(item.published)
            if pub_date > modified:
                feed.append({"title": item.title,
                             "link": item.link,
                             "pub_date": item.published,
                             "summary": item.summary})
        return feed

    rss_feeds = rss_feeds or RSS_FEEDS
    if channel:
        rss_feeds = {channel: rss_feeds[channel]}
    rss_news = {}

    for k, v in rss_feeds.items():
        try:
            # Only fetch news from the last 180 days
            #d = feedparser.parse(v, modified=modified) // does not work correctly/at all
            d = feedparser.parse(v)
            rss_news[k] = _parse_rss(d)
        except Exception as e:
            log.error(f"Error parsing {k}: {e}")

    return rss_news
