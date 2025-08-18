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

from datetime import datetime, timedelta
from dateutil.tz import tzutc
import logging
from sqlalchemy import Sequence

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin
from privacyidea.lib.utils import convert_column_to_unicode
from privacyidea.lib.log import log_with

log = logging.getLogger(__name__)

PRIVACYIDEA_TIMESTAMP = "__timestamp__"
SAFE_STORE = "PI_DB_SAFE_STORE"


def save_config_timestamp(invalidate_config=True):
    """
    Save the current timestamp to the database, and optionally
    invalidate the current request-local config object.
    :param invalidate_config: defaults to True
    """
    c1 = Config.query.filter_by(Key=PRIVACYIDEA_TIMESTAMP).first()
    if c1:
        c1.Value = datetime.now().strftime("%s")
    else:
        new_timestamp = Config(PRIVACYIDEA_TIMESTAMP,
                               datetime.now().strftime("%s"),
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


class TimestampMethodsMixin(object):
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
    Key = db.Column(db.Unicode(255),
                    primary_key=True,
                    nullable=False)
    Value = db.Column(db.Unicode(2000), default='')
    Type = db.Column(db.Unicode(2000), default='')
    Description = db.Column(db.Unicode(2000), default='')

    @log_with(log)
    def __init__(self, Key, Value, Type='', Description=''):
        self.Key = convert_column_to_unicode(Key)
        self.Value = convert_column_to_unicode(Value)
        self.Type = convert_column_to_unicode(Type)
        self.Description = convert_column_to_unicode(Description)

    def __str__(self):
        return "<{0!s} ({1!s})>".format(self.Key, self.Type)

    def save(self):
        db.session.add(self)
        save_config_timestamp()
        db.session.commit()
        return self.Key

    def delete(self):
        ret = self.Key
        db.session.delete(self)
        save_config_timestamp()
        db.session.commit()
        return ret


class NodeName(db.Model):
    __tablename__ = "nodename"
    # TODO: we can use the UUID type here when switching to SQLAlchemy 2.0
    #  <https://docs.sqlalchemy.org/en/20/core/custom_types.html#backend-agnostic-guid-type>
    id = db.Column(db.Unicode(36), primary_key=True)
    name = db.Column(db.Unicode(100), index=True)
    lastseen = db.Column(db.DateTime(), index=True, default=datetime.now(tz=tzutc()))


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
    username = db.Column(db.Unicode(120),
                         primary_key=True,
                         nullable=False)
    password = db.Column(db.Unicode(255))
    email = db.Column(db.Unicode(255))

    def save(self):
        c = Admin.query.filter_by(username=self.username).first()
        if c is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.username
        else:
            # update
            update_dict = {}
            if self.email:
                update_dict["email"] = self.email
            if self.password:
                update_dict["password"] = self.password
            Admin.query.filter_by(username=self.username) \
                .update(update_dict)
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
    id = db.Column(db.Integer(), Sequence("pwreset_seq"), primary_key=True,
                   nullable=False)
    recoverycode = db.Column(db.Unicode(255), nullable=False)
    username = db.Column(db.Unicode(64), nullable=False, index=True)
    realm = db.Column(db.Unicode(64), nullable=False, index=True)
    resolver = db.Column(db.Unicode(64))
    email = db.Column(db.Unicode(255))
    timestamp = db.Column(db.DateTime, default=datetime.now())
    expiration = db.Column(db.DateTime)

    @log_with(log)
    def __init__(self, recoverycode, username, realm, resolver="", email=None,
                 timestamp=None, expiration=None, expiration_seconds=3600):
        # The default expiration time is 60 minutes
        self.recoverycode = recoverycode
        self.username = username
        self.realm = realm
        self.resolver = resolver
        self.email = email
        self.timestamp = timestamp or datetime.now()
        self.expiration = expiration or datetime.now() + timedelta(seconds=expiration_seconds)
