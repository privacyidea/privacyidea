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

import feedparser
import logging
import time
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse

RSS_FEEDS = {"Community News": "https://community.privacyidea.org/c/news.rss",
             "privacyIDEA News": "https://privacyidea.org/feed",
             "NetKnights News": "https://netknights.it/en/feed"}

log = logging.getLogger(__name__)

FETCH_DAYS = 180

# In-memory TTL cache for parsed feed responses. Per-worker; see notes/redis.md
# for the planned Redis-backed alternative.
_CACHE_TTL_SECONDS = 900  # 15 minutes
_CACHE: dict[tuple, tuple[float, dict]] = {}


def _cache_key(rss_feeds: dict, channel, days: int) -> tuple:
    return (tuple(sorted(rss_feeds.items())), channel, days)


def invalidate_news_cache() -> None:
    """Drop all cached feed responses. Intended for tests and manual refresh."""
    _CACHE.clear()


def get_news(rss_feeds: dict[str, str] = None, channel: str = None, days: int = FETCH_DAYS) -> dict:
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

    key = _cache_key(rss_feeds, channel, days)
    cached = _CACHE.get(key)
    now = time.monotonic()
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    rss_news = {}
    for k, v in rss_feeds.items():
        try:
            d = feedparser.parse(v)
            rss_news[k] = _parse_rss(d)
        except Exception as e:
            log.error(f"Error parsing {k}: {e}")

    _CACHE[key] = (now, rss_news)
    return rss_news
