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
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Unicode, Integer, Boolean, DateTime, UniqueConstraint, and_, select, update
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.utils import convert_column_to_unicode
from privacyidea.models import db
from privacyidea.models.config import SAFE_STORE
from privacyidea.models.realm import Realm
from privacyidea.models.utils import MethodsMixin

log = logging.getLogger(__name__)


class TokenContainer(MethodsMixin, db.Model):
    """
    The "Tokencontainer" table contains the containers and their associated tokens.
    """

    __tablename__ = 'tokencontainer'
    id: Mapped[int] = mapped_column("id", Integer, primary_key=True)
    type: Mapped[str] = mapped_column(Unicode(100), default='Generic', nullable=False)
    description: Mapped[str] = mapped_column(Unicode(1024), default='')
    serial: Mapped[str] = mapped_column(Unicode(40), default='', unique=True, nullable=False, index=True)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    template_id: Mapped[Optional[int]] = mapped_column(Integer, db.ForeignKey('tokencontainertemplate.id', name="tokencontainertemplate_id"))

    tokens: Mapped[List['Token']] = relationship(secondary='tokencontainertoken', back_populates='container')
    owners: Mapped[List['TokenContainerOwner']] = relationship(lazy='dynamic', back_populates='container', cascade="all, delete-orphan")
    states: Mapped[List['TokenContainerStates']] = relationship(lazy='dynamic', back_populates='container', cascade="all, delete-orphan")
    info_list: Mapped[List['TokenContainerInfo']] = relationship(lazy='select', back_populates='container', cascade="all, delete-orphan")
    realms: Mapped[List['Realm']] = relationship(secondary='tokencontainerrealm', back_populates='container')
    template: Mapped['TokenContainerTemplate'] = relationship(back_populates='containers')

    def __init__(self, serial: str, container_type: str = "Generic", tokens: Optional[List['Token']] = None, description: str = "", states: Optional[List['TokenContainerStates']] = None):
        self.serial = serial
        self.type = container_type
        self.description = description
        if tokens:
            # Assumes the tokens list contains Token objects
            self.tokens = tokens
        if states:
            self.states = states

    def set_info(self, info: dict):
        """
        Set the additional container info for this container.

        :param info: The key-values to set for this container
        :type info: dict
        """
        if not self.id:
            # If there is no ID to reference the container, we need to save the container
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
    id: Mapped[int] = mapped_column("id", Integer, primary_key=True)
    container_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("tokencontainer.id"))
    resolver: Mapped[str] = mapped_column(Unicode(120), default='', index=True)
    user_id: Mapped[str] = mapped_column(Unicode(320), default='', index=True)
    realm_id: Mapped[int] = mapped_column(Integer, db.ForeignKey('realm.id'))

    container: Mapped['TokenContainer'] = relationship(back_populates='owners')
    realm: Mapped['Realm'] = relationship(lazy='joined', backref='tokencontainerowners')

    def __init__(self, container_id: Optional[int] = None, container_serial: Optional[str] = None, resolver: Optional[str] = None, user_id: Optional[str] = None, realm_id: Optional[int] = None, realm_name: Optional[str] = None):
        """
        Create a new TokenContainerOwner assignment.
        """
        if realm_id is not None:
            self.realm_id = realm_id
        elif realm_name:
            stmt = select(Realm).filter_by(name=realm_name)
            realm = db.session.execute(stmt).scalar_one_or_none()
            self.realm_id = realm.id if realm else None
        if container_id is not None:
            self.container_id = container_id
        elif container_serial:
            stmt = select(TokenContainer).filter_by(serial=container_serial)
            container = db.session.execute(stmt).scalar_one_or_none()
            self.container_id = container.id if container else None
        self.resolver = resolver
        self.user_id = user_id

    def save(self, persistent: bool = True):
        stmt = select(TokenContainerOwner).filter_by(container_id=self.container_id, user_id=self.user_id, realm_id=self.realm_id, resolver=self.resolver)
        to = db.session.execute(stmt).scalar_one_or_none()
        if to is None:
            # This very assignment does not exist, yet:
            db.session.add(self)
            db.session.commit()
            if get_app_config_value(SAFE_STORE, False):
                to = db.session.execute(stmt).scalar_one_or_none()
                ret = to.id if to else self.id
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
    id: Mapped[int] = mapped_column("id", Integer, primary_key=True)
    container_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("tokencontainer.id"))
    state: Mapped[str] = mapped_column(Unicode(100), default='active', nullable=False)

    container: Mapped['TokenContainer'] = relationship("TokenContainer", back_populates="states")

    def __init__(self, container_id: Optional[int] = None, state: str = "active"):
        self.container_id = container_id
        self.state = state


class TokenContainerInfo(MethodsMixin, db.Model):
    """
    The table "tokencontainerinfo" is used to store additional, long information that
    is specific to the containertype.
    """
    __tablename__ = 'tokencontainerinfo'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    value: Mapped[str] = mapped_column(Unicode(2000), default='')
    type: Mapped[str] = mapped_column(Unicode(100), default='')
    description: Mapped[str] = mapped_column(Unicode(2000), default='')
    container_id: Mapped[int] = mapped_column(Integer, db.ForeignKey('tokencontainer.id'), index=True)

    container: Mapped['TokenContainer'] = relationship('TokenContainer', back_populates='info_list')
    __table_args__ = (UniqueConstraint('container_id', 'key', name='container_id_constraint'),)

    def __init__(self, container_id: int, key: str, value: str, type: Optional[str] = None, description: Optional[str] = None):
        """
        Create a new tokencontainerinfo for a given token_id
        """
        self.container_id = container_id
        self.key = key
        self.value = convert_column_to_unicode(value)
        self.type = type
        self.description = description

    def save(self, persistent: bool = True):
        stmt = select(TokenContainerInfo).filter_by(container_id=self.container_id, key=self.key)
        ti = db.session.execute(stmt).scalar_one_or_none()
        if ti is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            if get_app_config_value(SAFE_STORE, False):
                ti = db.session.execute(stmt).scalar_one_or_none()
                ret = ti.id if ti else self.id
            else:
                ret = self.id
        else:
            # update
            update_stmt = (
                update(TokenContainerInfo)
                .where(and_(TokenContainerInfo.container_id == self.container_id, TokenContainerInfo.key == self.key))
                .values(value=self.value, description=self.description, type=self.type)
            )
            db.session.execute(update_stmt)
            ret = ti.id
        if persistent:
            db.session.commit()
        return ret


class TokenContainerRealm(MethodsMixin, db.Model):
    """
    This table stores to which realms a container is assigned.
    """
    __tablename__ = 'tokencontainerrealm'
    container_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("tokencontainer.id"), primary_key=True)
    realm_id: Mapped[int] = mapped_column(Integer, db.ForeignKey('realm.id'), primary_key=True)


class TokenContainerTemplate(MethodsMixin, db.Model):
    __tablename__ = 'tokencontainertemplate'
    id: Mapped[int] = mapped_column("id", Integer, primary_key=True)
    options: Mapped[str] = mapped_column(Unicode(2000), default='')
    name: Mapped[str] = mapped_column(Unicode(200), default='')
    container_type: Mapped[str] = mapped_column(Unicode(100), default='generic', nullable=False)
    default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    containers: Mapped[List['TokenContainer']] = relationship('TokenContainer', back_populates='template')

    def __init__(self, name: str, container_type: str = "generic", options: str = '', default: bool = False):
        self.name = name
        self.container_type = container_type
        self.options = options
        self.default = default


class TokenContainerToken(MethodsMixin, db.Model):
    """
    Association table to link tokens to containers.
    """
    __tablename__ = 'tokencontainertoken'
    token_id: Mapped[int] = mapped_column('token_id', Integer, db.ForeignKey('token.id'), primary_key=True)
    container_id: Mapped[int] = mapped_column('container_id', Integer, db.ForeignKey('tokencontainer.id'), primary_key=True)
