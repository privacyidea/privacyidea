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
from sqlalchemy import Sequence, Unicode, Integer, ForeignKey, UniqueConstraint, delete, select, update, and_
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privacyidea.models import db
from privacyidea.lib.utils import convert_column_to_unicode
from privacyidea.models.config import TimestampMethodsMixin, save_config_timestamp

log = logging.getLogger(__name__)


class Resolver(TimestampMethodsMixin, db.Model):
    """
    The table "resolver" contains the names and types of the defined User
    Resolvers. As each Resolver can have different required config values the
    configuration of the resolvers is stored in the table "resolverconfig".
    """
    __tablename__ = 'resolver'
    id: Mapped[int] = mapped_column(Integer, Sequence("resolver_seq"), primary_key=True,
                                    nullable=False)
    name: Mapped[str] = mapped_column(Unicode(255), default="",
                                      unique=True, nullable=False)
    rtype: Mapped[str] = mapped_column(Unicode(255), default="",
                                       nullable=False)
    # This creates an attribute "resolver" in the ResolverConfig object
    config_list = relationship('ResolverConfig',
                               lazy='select')
    realm_list = relationship('ResolverRealm',
                              lazy='select',
                              back_populates='resolver')

    def __init__(self, name, rtype):
        self.name = name
        self.rtype = rtype

    def delete(self):
        ret = self.id
        stmt = delete(ResolverConfig).where(ResolverConfig.resolver_id == ret)
        db.session.execute(stmt)
        # delete the Resolver itself
        db.session.delete(self)
        save_config_timestamp()
        db.session.commit()
        return ret


class ResolverConfig(TimestampMethodsMixin, db.Model):
    """
    Each Resolver can have multiple configuration entries.
    Each Resolver type can have different required config values. Therefore,
    the configuration is stored in simple key/value pairs. If the type of a
    config entry is set to "password" the value of this config entry is stored
    encrypted.

    The config entries are referenced by the id of the resolver.
    """
    __tablename__ = 'resolverconfig'
    id: Mapped[int] = mapped_column(Integer, Sequence("resolverconf_seq"), primary_key=True)
    resolver_id: Mapped[int] = mapped_column(Integer,
                                             ForeignKey('resolver.id'))
    Key: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    Value: Mapped[str] = mapped_column(Unicode(2000), default='')
    Type: Mapped[str] = mapped_column(Unicode(2000), default='')
    Description: Mapped[str] = mapped_column(Unicode(2000), default='')
    __table_args__ = (UniqueConstraint('resolver_id',
                                       'Key',
                                       name='rcix_2'),)

    def __init__(self, resolver_id=None,
                 Key=None, Value=None,
                 resolver=None,
                 Type="", Description=""):
        if resolver_id:
            self.resolver_id = resolver_id
        elif resolver:
            stmt = select(Resolver.id).filter_by(name=resolver)
            self.resolver_id = db.session.execute(stmt).scalar_one_or_none()
        self.Key = convert_column_to_unicode(Key)
        self.Value = convert_column_to_unicode(Value)
        self.Type = convert_column_to_unicode(Type)
        self.Description = convert_column_to_unicode(Description)

    def save(self):
        stmt = select(ResolverConfig).filter(
            and_(
                ResolverConfig.resolver_id == self.resolver_id,
                ResolverConfig.Key == self.Key
            )
        )
        c = db.session.execute(stmt).scalar_one_or_none()
        if c is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            update_stmt = (
                update(ResolverConfig)
                .where(
                    and_(
                        ResolverConfig.resolver_id == self.resolver_id,
                        ResolverConfig.Key == self.Key
                    )
                )
                .values(
                    Value=self.Value,
                    Type=self.Type,
                    Description=self.Description
                )
            )
            db.session.execute(update_stmt)
            ret = c.id
        save_config_timestamp()
        db.session.commit()
        return ret
