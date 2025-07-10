# SPDX-FileCopyrightText: (C) 2025 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2025 Paul Lettich <paul.lettich@netknights.it>
# SPDX-FileCopyrightText: (C) 2024 Jelina Unger <jelina.unger@netknights.it>
# SPDX-FileCopyrightText: (C) 2024 Nils Behlen <nils.behlen@netknights.it>
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

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin
from privacyidea.models.realm import Realm
from privacyidea.models.config import SAFE_STORE
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.utils import convert_column_to_unicode


class TokenContainer(MethodsMixin, db.Model):
    """
    The "Tokencontainer" table contains the containers and their associated tokens.
    """

    __tablename__ = 'tokencontainer'
    id = db.Column("id", db.Integer, db.Identity(), primary_key=True)
    type = db.Column(db.Unicode(100), default='Generic', nullable=False)
    description = db.Column(db.Unicode(1024), default='')
    tokens = db.relationship('Token', secondary='tokencontainertoken', back_populates='container')
    serial = db.Column(db.Unicode(40), default='', unique=True, nullable=False, index=True)
    owners = db.relationship('TokenContainerOwner', lazy='dynamic', back_populates='container',
                             cascade="all, delete-orphan")
    last_seen = db.Column(db.DateTime, default=None)
    last_updated = db.Column(db.DateTime, default=None)
    states = db.relationship('TokenContainerStates', lazy='dynamic', back_populates='container',
                             cascade="all, delete-orphan")
    info_list = db.relationship('TokenContainerInfo', lazy='select', back_populates='container',
                                cascade="all, delete-orphan")
    realms = db.relationship('Realm', secondary='tokencontainerrealm', back_populates='container')
    template_id = db.Column(db.ForeignKey('tokencontainertemplate.id', name="tokencontainertemplate_id"))
    template = db.relationship('TokenContainerTemplate', back_populates='containers')

    def __init__(self, serial, container_type="Generic", tokens=None, description="", states=None):
        self.serial = serial
        self.type = container_type
        self.description = description
        if tokens:
            self.tokens = [t.token for t in tokens]
        if states:
            self.states = states

    def set_info(self, info):
        """
        Set the additional container info for this container

        Entries that end with ".type" are used as type for the keys.
        I.e. two entries sshkey="XYZ" and sshkey.type="password" will store
        the key sshkey as type "password".

        :param info: The key-values to set for this container
        :type info: dict
        """
        if not self.id:
            # If there is no ID to reference the container, we need to save the
            # container
            self.save()
        types = {}
        for k, v in info.items():
            if k and k.endswith(".type"):
                types[".".join(k.split(".")[:-1])] = v
        for k, v in info.items():
            if k and not k.endswith(".type"):
                TokenContainerInfo(self.id, k, v,
                                   type=types.get(k)).save(persistent=False)
        db.session.commit()


class TokenContainerOwner(MethodsMixin, db.Model):
    __tablename__ = 'tokencontainerowner'
    id = db.Column("id", db.Integer, db.Identity(), primary_key=True)
    container_id = db.Column(db.Integer(), db.ForeignKey("tokencontainer.id"))
    container = db.relationship('TokenContainer', back_populates='owners')
    resolver = db.Column(db.Unicode(120), default='', index=True)
    user_id = db.Column(db.Unicode(320), default='', index=True)
    realm_id = db.Column(db.Integer(), db.ForeignKey('realm.id'))
    realm = db.relationship('Realm', lazy='joined', backref='tokencontainerowners')

    def __init__(self, container_id=None, container_serial=None, resolver=None, user_id=None, realm_id=None,
                 realm_name=None):
        """
        Create a new TokenContainerOwner assignment.

        :param container_id:
        :param container_serial: alternative to container_id
        :param resolver:
        :param user_id:
        :param realm_id:
        :param realm_name: alternative to realm_id
        """
        if realm_id is not None:
            self.realm_id = realm_id
        elif realm_name:
            realm = Realm.query.filter_by(name=realm_name).first()
            self.realm_id = realm.id
        if container_id is not None:
            self.container_id = container_id
        elif container_serial:
            container = TokenContainer.query.filter_by(serial=container_serial).first()
            self.container_id = container.id
        self.resolver = resolver
        self.user_id = user_id

    def save(self, persistent=True):
        to_func = TokenContainerOwner.query.filter_by(container_id=self.container_id,
                                                      user_id=self.user_id,
                                                      realm_id=self.realm_id,
                                                      resolver=self.resolver).first
        to = to_func()
        if to is None:
            # This very assignment does not exist, yet:
            db.session.add(self)
            db.session.commit()
            if get_app_config_value(SAFE_STORE, False):
                to = to_func()
                ret = to.id
            else:
                ret = self.id
        else:
            ret = to.id
            # There is nothing to update

        if persistent:
            db.session.commit()
        return ret


class TokenContainerStates(MethodsMixin, db.Model):
    __tablename__ = 'tokencontainerstates'
    id = db.Column("id", db.Integer, db.Identity(), primary_key=True)
    container_id = db.Column(db.Integer(), db.ForeignKey("tokencontainer.id"))
    container = db.relationship("TokenContainer", back_populates="states")
    state = db.Column(db.Unicode(100), default='active', nullable=False)

    """
    The table "tokencontainerstates" is used to store the states of the container. A container can be in several states.
    """

    def __init__(self, container_id=None, state="active"):
        self.container_id = container_id
        self.state = state


class TokenContainerInfo(MethodsMixin, db.Model):
    """
    The table "tokencontainerinfo" is used to store additional, long information that
    is specific to the containertype.

    The tokencontainerinfo is reference by the foreign key to the "tokencontainer" table.
    """
    __tablename__ = 'tokencontainerinfo'
    id = db.Column(db.Integer, db.Identity(), primary_key=True)
    key = db.Column(db.Unicode(255), nullable=False)
    value = db.Column(db.UnicodeText(), default='')
    type = db.Column(db.Unicode(100), default='')
    description = db.Column(db.Unicode(2000), default='')
    container_id = db.Column(db.Integer(), db.ForeignKey('tokencontainer.id'), index=True)
    container = db.relationship('TokenContainer', back_populates='info_list')
    __table_args__ = (db.UniqueConstraint('container_id', 'key', name='container_id_constraint'),)

    def __init__(self, container_id, key, value,
                 type=None,
                 description=None):
        """
        Create a new tokencontainerinfo for a given token_id
        """
        self.container_id = container_id
        self.key = key
        self.value = convert_column_to_unicode(value)
        self.type = type
        self.description = description

    def save(self, persistent=True):
        ti_func = TokenContainerInfo.query.filter_by(container_id=self.container_id,
                                                     key=self.key).first
        ti = ti_func()
        if ti is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            if get_app_config_value(SAFE_STORE, False):
                ti = ti_func()
                ret = ti.id
            else:
                ret = self.id
        else:
            # update
            TokenContainerInfo.query.filter_by(container_id=self.container_id,
                                               key=self.key).update({'value': self.value,
                                                                     'description': self.description,
                                                                     'type': self.type})
            ret = ti.id
        if persistent:
            db.session.commit()
        return ret


class TokenContainerRealm(MethodsMixin, db.Model):
    """
    This table stores to which realms a container is assigned. A container is in the
    realm of the user it is assigned to. But a container can also be put into
    many additional realms.
    """
    __tablename__ = 'tokencontainerrealm'
    container_id = db.Column(db.Integer(), db.ForeignKey("tokencontainer.id"), primary_key=True)
    realm_id = db.Column(db.Integer(), db.ForeignKey('realm.id'), primary_key=True)


class TokenContainerTemplate(MethodsMixin, db.Model):
    __tablename__ = 'tokencontainertemplate'
    id = db.Column("id", db.Integer, db.Identity(), primary_key=True)
    options = db.Column(db.Unicode(2000), default='')
    name = db.Column(db.Unicode(200), default='')
    container_type = db.Column(db.Unicode(100), default='generic', nullable=False)
    default = db.Column(db.Boolean, default=False, nullable=False)
    containers = db.relationship('TokenContainer', back_populates='template')

    def __init__(self, name, container_type="generic", options='', default=False):
        self.name = name
        self.container_type = container_type
        self.options = options
        self.default = default


class TokenContainerToken(MethodsMixin, db.Model):
    """
    Association table to link tokens to containers.
    """
    __tablename__ = 'tokencontainertoken'
    token_id = db.Column('token_id', db.Integer, db.ForeignKey('token.id'), primary_key=True)
    container_id = db.Column('container_id', db.Integer, db.ForeignKey('tokencontainer.id'), primary_key=True)
