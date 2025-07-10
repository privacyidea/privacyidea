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
from sqlalchemy import Sequence

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin


class AuthCache(MethodsMixin, db.Model):
    __tablename__ = 'authcache'
    id = db.Column(db.Integer, Sequence("authcache_seq"), primary_key=True)
    first_auth = db.Column(db.DateTime, index=True)
    last_auth = db.Column(db.DateTime, index=True)
    username = db.Column(db.Unicode(64), default="", index=True)
    resolver = db.Column(db.Unicode(120), default='', index=True)
    realm = db.Column(db.Unicode(120), default='', index=True)
    client_ip = db.Column(db.Unicode(40), default="")
    user_agent = db.Column(db.Unicode(120), default="")
    auth_count = db.Column(db.Integer, default=0)
    # We can hash the password like this:
    # binascii.hexlify(hashlib.sha256("secret123456").digest())
    authentication = db.Column(db.Unicode(255), default="")

    def __init__(self, username, realm, resolver, authentication,
                 first_auth=None, last_auth=None):
        self.username = username
        self.realm = realm
        self.resolver = resolver
        self.authentication = authentication
        self.first_auth = first_auth if first_auth else datetime.utcnow()
        self.last_auth = last_auth if last_auth else self.first_auth


class UserCache(MethodsMixin, db.Model):
    __tablename__ = 'usercache'
    id = db.Column(db.Integer, Sequence("usercache_seq"), primary_key=True)
    username = db.Column(db.Unicode(64), default="", index=True)
    used_login = db.Column(db.Unicode(64), default="", index=True)
    resolver = db.Column(db.Unicode(120), default='')
    user_id = db.Column(db.Unicode(320), default='', index=True)
    timestamp = db.Column(db.DateTime, index=True)

    def __init__(self, username, used_login, resolver, user_id, timestamp):
        self.username = username
        self.used_login = used_login
        self.resolver = resolver
        self.user_id = user_id
        self.timestamp = timestamp
