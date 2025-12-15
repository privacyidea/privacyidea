# SPDX-FileCopyrightText: (C) 2025 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2025 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
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
from datetime import datetime
from typing import Optional

from sqlalchemy import Sequence, Unicode, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin


class AuthCache(MethodsMixin, db.Model):
    __tablename__ = 'authcache'
    id: Mapped[int] = mapped_column(Integer, Sequence("authcache_seq"), primary_key=True)
    first_auth: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    last_auth: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    username: Mapped[Optional[str]] = mapped_column(Unicode(64), default="", index=True)
    resolver: Mapped[Optional[str]] = mapped_column(Unicode(120), default='', index=True)
    realm: Mapped[Optional[str]] = mapped_column(Unicode(120), default='', index=True)
    client_ip: Mapped[Optional[str]] = mapped_column(Unicode(40), default="")
    user_agent: Mapped[Optional[str]] = mapped_column(Unicode(120), default="")
    auth_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    authentication: Mapped[Optional[str]] = mapped_column(Unicode(255), default="")

    def __init__(self, username: str, realm: str, resolver: str, authentication: str,
                 first_auth: datetime = None, last_auth: datetime = None):
        if first_auth:
            self.first_auth = first_auth
        if last_auth:
            self.last_auth = last_auth
        self.username = username
        self.realm = realm
        self.resolver = resolver
        self.authentication = authentication


class UserCache(MethodsMixin, db.Model):
    """
    This class stores the cached information for a user to improve lookup performance.
    """
    __tablename__ = 'usercache'
    id: Mapped[int] = mapped_column(Integer, Sequence("usercache_seq"), primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(Unicode(64), default="", index=True)
    used_login: Mapped[Optional[str]] = mapped_column(Unicode(64), default="", index=True)
    resolver: Mapped[Optional[str]] = mapped_column(Unicode(120), default='')
    user_id: Mapped[Optional[str]] = mapped_column(Unicode(320), default='', index=True)
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)

    def __init__(self, username, used_login, resolver, user_id, timestamp):
        self.username = username
        self.used_login = used_login
        self.resolver = resolver
        self.user_id = user_id
        self.timestamp = timestamp
