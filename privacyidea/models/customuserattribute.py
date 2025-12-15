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


def save_config_timestamp(invalidate_config=True):
    """
    Save the current timestamp to the database, and optionally
    invalidate the current request-local config object.
    :param invalidate_config: defaults to True
    """
    # Replaced .query with a modern select statement
    stmt = select(Config).filter_by(Key=PRIVACYIDEA_TIMESTAMP)
    c1 = db.session.execute(stmt).scalar_one_or_none()

    if c1:
        c1.Value = str(datetime.utcnow().timestamp())
    else:
        new_timestamp = Config(PRIVACYIDEA_TIMESTAMP,
                               str(datetime.utcnow().timestamp()),
                               Description="config timestamp. last changed.")
        db.session.add(new_timestamp)
    if invalidate_config:
        # We have just modified the config. From now on, the request handling
        # should operate on the *new* config. Hence, we need to invalidate
        # the current request-local config object. The next access to the config
        # during this request will reload the config from the database and create
        # a new request-local config object, which holds the *new* config.
        from privacyidea.lib.config import invalidate_config_object
        invalidate_config_object()
    # Commit the changes at the end of the function.
    db.session.commit()


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

    def save(self, persistent=True):
        # Replaced .query with a modern select statement
        stmt = select(CustomUserAttribute).filter_by(
            user_id=self.user_id,
            resolver=self.resolver,
            realm_id=self.realm_id,
            Key=self.Key
        )
        ua = db.session.execute(stmt).scalar_one_or_none()

        if ua is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # Replaced .query.update() with a modern update statement
            update_stmt = (
                update(CustomUserAttribute)
                .where(
                    CustomUserAttribute.user_id == self.user_id,
                    CustomUserAttribute.resolver == self.resolver,
                    CustomUserAttribute.realm_id == self.realm_id,
                    CustomUserAttribute.Key == self.Key,
                )
                .values(Value=self.Value, Type=self.Type)
            )
            db.session.execute(update_stmt)
            ret = ua.id
        if persistent:
            db.session.commit()
        return ret