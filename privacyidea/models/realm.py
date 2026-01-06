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
from typing import List, Optional

from sqlalchemy import Sequence, Unicode, Integer, Boolean, ForeignKey, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privacyidea.lib.error import DatabaseError
from privacyidea.lib.log import log_with
from privacyidea.models import db
from privacyidea.models.config import (TimestampMethodsMixin,
                                       NodeName)
from privacyidea.models.resolver import Resolver

log = logging.getLogger(__name__)


class Realm(TimestampMethodsMixin, db.Model):
    """
    The realm table contains the defined realms. User Resolvers can be
    grouped to realms. This very table contains just contains the names of
    the realms. The linking to resolvers is stored in the table "resolverrealm".
    """
    __tablename__ = 'realm'
    id: Mapped[int] = mapped_column(Integer, Sequence("realm_seq"), primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(Unicode(255), default='', unique=True, nullable=False)
    default: Mapped[Optional[bool]] = mapped_column(Boolean(), default=False)
    resolver_list = relationship('ResolverRealm', lazy='select', back_populates='realm')
    container = relationship('TokenContainer', secondary='tokencontainerrealm', back_populates='realms')

    tokenowners: Mapped[List['TokenOwner']] = relationship(
        'TokenOwner',
        back_populates='realm'
    )

    token_list: Mapped[List['TokenRealm']] = relationship(
        'TokenRealm',
        back_populates='realm'
    )

    @log_with(log)
    def __init__(self, realm):
        self.name = realm


class ResolverRealm(TimestampMethodsMixin, db.Model):
    """
    This table stores which Resolver is located in which realm
    This is a N:M relation
    """
    __tablename__ = 'resolverrealm'
    id: Mapped[int] = mapped_column(Integer, Sequence("resolverrealm_seq"), primary_key=True)
    resolver_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("resolver.id"))
    realm_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("realm.id"))
    # If there are several resolvers in a realm, the priority is used the
    # find a user first in a resolver with a higher priority (i.e. lower number)
    priority: Mapped[Optional[int]] = mapped_column(Integer)
    # TODO: with SQLAlchemy 2.0 db.UUID will be generally available
    node_uuid: Mapped[Optional[str]] = mapped_column(Unicode(36), default='')
    resolver = relationship(Resolver,
                            lazy="joined",
                            back_populates="realm_list")
    realm = relationship(Realm,
                         lazy="joined",
                         back_populates="resolver_list")
    __table_args__ = (UniqueConstraint('resolver_id',
                                       'realm_id',
                                       'node_uuid',
                                       name='rrix_2'),)

    def __init__(self, resolver_id=None, realm_id=None,
                 resolver_name=None,
                 realm_name=None,
                 priority=None,
                 node_uuid=None,
                 node_name=None):
        self.resolver_id = None
        self.realm_id = None
        if priority:
            self.priority = int(priority)
        if resolver_id:
            self.resolver_id = resolver_id
        elif resolver_name:
            stmt = select(Resolver.id).filter_by(name=resolver_name)
            self.resolver_id = db.session.execute(stmt).scalar_one_or_none()
        if realm_id:
            self.realm_id = realm_id
        elif realm_name:
            stmt = select(Realm.id).filter_by(name=realm_name)
            self.realm_id = db.session.execute(stmt).scalar_one_or_none()
        if node_uuid:
            # Check if the node is already defined in the NodeName table
            # This is already a modern SQLAlchemy statement
            if db.session.scalar(db.select(db.func.count(NodeName.id)).filter(NodeName.id == node_uuid)) > 0:
                self.node_uuid = node_uuid
            else:
                # Did not find a NodeName entry, adding a new one only if node_name is set
                if node_name:
                    self.node_uuid = NodeName(node_uuid, node_name).save().id
                else:
                    raise DatabaseError(f"No NodeName entry found for UUID {node_uuid}")
        elif node_name:
            stmt = select(NodeName.id).filter_by(name=node_name)
            self.node_uuid = db.session.execute(stmt).scalar_one_or_none()
