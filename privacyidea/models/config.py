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
from datetime import datetime, timedelta

from dateutil.tz import tzutc
from sqlalchemy import (
    Sequence,
    Unicode,
    Integer,
    DateTime,
    select,
    update,
)
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.lib.log import log_with
from privacyidea.lib.utils import convert_column_to_unicode
from privacyidea.models import db
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


class TimestampMethodsMixin:
    """
    This class mixes in the table functions including update of the timestamp
    """

    def save(self):
        db.session.add(self)
        save_config_timestamp()
        db.session.commit()
        return self.id

    def delete(self):
        ret = self.id
        db.session.delete(self)
        save_config_timestamp()
        db.session.commit()
        return ret


class Config(TimestampMethodsMixin, db.Model):
    """
    The config table holds all the system configuration in key value pairs.
    Additional configuration for realms, resolvers and machine resolvers is
    stored in specific tables.
    """
    __tablename__ = "config"
    Key: Mapped[str] = mapped_column(Unicode(255), primary_key=True, nullable=False)
    Value: Mapped[str] = mapped_column(Unicode(2000), default='')
    Type: Mapped[str] = mapped_column(Unicode(2000), default='')
    Description: Mapped[str] = mapped_column(Unicode(2000), default='')

    def __init__(self, Key, Value, Type='', Description=''):
        self.Key = convert_column_to_unicode(Key)
        self.Value = convert_column_to_unicode(Value)
        self.Type = convert_column_to_unicode(Type)
        self.Description = convert_column_to_unicode(Description)

    def __str__(self):
        return "<{0!s} ({1!s})>".format(self.Key, self.Type)

    # Note: The save and delete methods are inherited from TimestampMethodsMixin


class NodeName(db.Model, TimestampMethodsMixin):
    __tablename__ = "nodename"
    # TODO: we can use the UUID type here when switching to SQLAlchemy 2.0
    #  <https://docs.sqlalchemy.org/en/20/core/custom_types.html#backend-agnostic-guid-type>
    id: Mapped[str] = mapped_column(Unicode(36), primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(100), index=True)
    lastseen: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.now(tz=tzutc()))


class Admin(db.Model):
    """
    The administrators for managing the system.
    To manage the administrators use the command pi-manage.

    In addition, certain realms can be defined to be administrative realms.

    :param username: The username of the admin
    :type username: basestring
    :param password: The password of the admin (stored using PBKDF2,
       salt and pepper)
    :type password: basestring
    :param email: The email address of the admin (not used at the moment)
    :type email: basestring
    """
    __tablename__ = "admin"
    username: Mapped[str] = mapped_column(Unicode(120), primary_key=True, nullable=False)
    password: Mapped[str] = mapped_column(Unicode(255))
    email: Mapped[str] = mapped_column(Unicode(255))

    def save(self):
        # Replaced .query with a modern select statement
        stmt = select(Admin).filter_by(username=self.username)
        c = db.session.execute(stmt).scalar_one_or_none()

        if c is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.username
        else:
            # Replaced .query.update() with a modern update statement
            update_dict = {}
            if self.email:
                update_dict["email"] = self.email
            if self.password:
                update_dict["password"] = self.password

            update_stmt = (
                update(Admin)
                .where(Admin.username == self.username)
                .values(**update_dict)
            )
            db.session.execute(update_stmt)
            ret = c.username
        db.session.commit()
        return ret

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class PasswordReset(MethodsMixin, db.Model):
    """
    Table for handling password resets.
    This table stores the recoverycodes sent to a given user
    The application should save the HASH of the recovery code. Just like the
    password for the Admins the application shall salt and pepper the hash of
    the recoverycode. A database admin will not be able to inject a rogue
    recovery code.
    A user can get several recoverycodes.
    A recovery code has a validity period
    Optional: The email to which the recoverycode was sent, can be stored.
    """
    __tablename__ = "passwordreset"
    id: Mapped[int] = mapped_column(Integer, Sequence("pwreset_seq"), primary_key=True, nullable=False)
    recoverycode: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    username: Mapped[str] = mapped_column(Unicode(64), nullable=False, index=True)
    realm: Mapped[str] = mapped_column(Unicode(64), nullable=False, index=True)
    resolver: Mapped[str] = mapped_column(Unicode(64))
    email: Mapped[str] = mapped_column(Unicode(255))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expiration: Mapped[datetime] = mapped_column(DateTime)

    @log_with(log)
    def __init__(self, recoverycode, username, realm, resolver="", email=None,
                 timestamp=None, expiration=None, expiration_seconds=3600):
        # We manually assign attributes here as they depend on the function parameters
        self.recoverycode = recoverycode
        self.username = username
        self.realm = realm
        self.resolver = resolver
        self.email = email
        self.timestamp = timestamp or datetime.utcnow()
        self.expiration = expiration or datetime.utcnow() + timedelta(seconds=expiration_seconds)
