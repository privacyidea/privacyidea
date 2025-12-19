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
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Sequence,
    Unicode,
    Integer,
    select,
    update,
    ForeignKey,
    UnicodeText
)
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.lib.utils import convert_column_to_unicode
from privacyidea.models import db, Config
from privacyidea.models.utils import MethodsMixin

log = logging.getLogger(__name__)

PRIVACYIDEA_TIMESTAMP = "__timestamp__"
SAFE_STORE = "PI_DB_SAFE_STORE"


class CustomUserAttribute(MethodsMixin, db.Model):
    """
    The table "customuserattribute" is used to store additional, custom attributes
    for users.

    A user is identified by the user_id,  the resolver_id and the realm_id.

    The additional attributes are stored in Key and Value.
    The Type can hold extra information like e.g. an encrypted value / password.

    Note: Since the users are external, i.e. no objects in this database,
          there is no logic reference on a database level.
          Since users could be deleted from user stores
          without privacyIDEA realizing that, this table could pile up
          with remnants of attributes.
    """
    __tablename__ = 'customuserattribute'
    id: Mapped[int] = mapped_column(Integer, Sequence("customuserattribute_seq"), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(Unicode(320), default='', index=True)
    resolver: Mapped[Optional[str]] = mapped_column(Unicode(120), default='', index=True)
    realm_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('realm.id'))
    Key: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    Value: Mapped[Optional[str]] = mapped_column(UnicodeText, default='')
    Type: Mapped[Optional[str]] = mapped_column(Unicode(100), default='')

    def __init__(self, user_id, resolver, realm_id, Key, Value, Type=None):
        """
        Create a new customuserattribute for a user tuple
        """
        self.user_id = user_id
        self.resolver = resolver
        self.realm_id = realm_id
        self.Key = Key
        self.Value = convert_column_to_unicode(Value)
        self.Type = Type
