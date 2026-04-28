# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2026 Nils Behlen <nils.behlen@netknights.it>
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
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Sequence,
    Unicode,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin

log = logging.getLogger(__name__)


class InternalUserAttribute(MethodsMixin, db.Model):
    """
    Generic key-value store for *internal* per-user state written by
    privacyIDEA itself (not by admins or resolvers).

    Use this table for things like cached FIDO2 user IDs or the last-used
    token type per client. The ``customuserattribute`` table is reserved
    for admin/resolver-facing attributes that may be referenced from
    policy conditions; do not put internal state there.

    Values are stored as JSON, so a single row can hold a structured
    dict instead of synthesizing keys with prefixes.
    """
    __tablename__ = 'internaluserattribute'
    __table_args__ = (
        Index('ix_internaluserattribute_user',
              'user_id', 'resolver', 'realm_id'),
        UniqueConstraint('user_id', 'resolver', 'realm_id', 'Key',
                         name='uq_internaluserattribute_user_key'),
    )

    id: Mapped[int] = mapped_column(Integer, Sequence("internaluserattribute_seq"), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(Unicode(320), default='')
    resolver: Mapped[str | None] = mapped_column(Unicode(120), default='')
    realm_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('realm.id', ondelete='CASCADE'))
    Key: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    Value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_modified: Mapped[datetime | None] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    # Reserved for future HA use: NULL means the value is global (valid on any node).
    node: Mapped[str | None] = mapped_column(Unicode(120), nullable=True, default=None)

    def __init__(self, user_id, resolver, realm_id, Key, Value=None, node=None):
        self.user_id = user_id
        self.resolver = resolver
        self.realm_id = realm_id
        self.Key = Key
        self.Value = Value
        self.node = node
