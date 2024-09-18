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
             "NetKnights News": "https://netknights.it/feed"}


import feedparser

RSS_NEWS = {}


def parse_rss(rss):
    feed = []
    for item in rss.entries:
        feed.append({"title": item.title,
                     "link": item.link,
                     "pub_date": item.published,
                     "summary": item.summary})
    return feed


for k, v in RSS_FEEDS.items():
    try:
        d = feedparser.parse(v)
        RSS_NEWS[k] = parse_rss(d)
    except Exception as e:
        print(f"Error parsing {k}: {e}")

print(RSS_NEWS)


