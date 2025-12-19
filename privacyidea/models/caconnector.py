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
from typing import Optional

from sqlalchemy import (
    Sequence,
    Unicode,
    Integer,
    ForeignKey,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privacyidea.lib.utils import convert_column_to_unicode
from privacyidea.models import db
from privacyidea.models.config import TimestampMethodsMixin


class CAConnector(TimestampMethodsMixin, db.Model):
    """
    The table "caconnector" contains the names and types of the defined
    CA connectors. Each connector has a different configuration, that is
    stored in the table "caconnectorconfig".
    """
    __tablename__ = 'caconnector'
    id: Mapped[int] = mapped_column(Sequence("caconnector_seq"), primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(Unicode(255), default="", unique=True, nullable=False)
    catype: Mapped[str] = mapped_column(Unicode(255), default="", nullable=False)

    caconfig = relationship('CAConnectorConfig', lazy='dynamic', backref='caconnector', cascade="all, delete-orphan")

    def __init__(self, name, catype):
        self.name = name
        self.catype = catype


class CAConnectorConfig(db.Model):
    """
    Each CAConnector can have multiple configuration entries.
    Each CA Connector type can have different required config values. Therefore,
    the configuration is stored in simple key/value pairs. If the type of
    config entry is set to "password" the value of this config entry is stored
    encrypted.

    The config entries are referenced by the id of the resolver.
    """
    __tablename__ = 'caconnectorconfig'
    id: Mapped[int] = mapped_column(Integer, Sequence("caconfig_seq"), primary_key=True)
    caconnector_id: Mapped[int] = mapped_column(ForeignKey('caconnector.id'))
    Key: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    Value: Mapped[Optional[str]] = mapped_column(Unicode(2000), default='')
    Type: Mapped[Optional[str]] = mapped_column(Unicode(2000), default='')
    Description: Mapped[Optional[str]] = mapped_column(Unicode(2000), default='')
    __table_args__ = (UniqueConstraint('caconnector_id', 'Key', name='ccix_2'),)

    def __init__(self, caconnector_id=None, Key=None, Value=None, caconnector=None, Type="", Description=""):
        if caconnector_id:
            self.caconnector_id = caconnector_id
        elif caconnector:
            # Replaced .query with a select() statement
            stmt = select(CAConnector).filter_by(name=caconnector)
            # Execute the statement to get the result
            connector = db.session.execute(stmt).scalar_one_or_none()
            if connector:
                self.caconnector_id = connector.id
        self.Key = Key
        self.Value = convert_column_to_unicode(Value)
        self.Type = Type
        self.Description = Description
