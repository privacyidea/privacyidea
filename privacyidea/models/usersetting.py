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
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Sequence,
    Unicode,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin, utc_now

log = logging.getLogger(__name__)


class UserSetting(MethodsMixin, db.Model):
    """
    Per-principal frontend settings (one row per principal, the whole
    settings document stored as a single JSON value).

    The backend does not interpret these settings; it stores and serves
    them for the WebUI. A "principal" is whoever logged in, which is not
    always a resolver user:

    * ``subject_type='local_admin'`` — an internal admin from the
      ``admin`` table. Identified by ``username`` alone; ``user_id``,
      ``resolver`` and ``realm_id`` are empty/NULL.
    * ``subject_type='user'`` — a resolver user (this also covers
      realm-admins). Identified by the ``(user_id, resolver, realm_id)``
      tuple, the same stable identity used by ``tokenowner``;
      ``username`` is kept only as a convenience for logging/lookups.

    Only principals that deviate from the defaults get a row, so the
    table stays small even with a large user base.
    """
    __tablename__ = 'usersetting'
    __table_args__ = (
        # One settings document per principal. For local admins only username is
        # set; for users the (user_id, resolver, realm_id) tuple identifies the
        # row. Uniqueness for local admins (realm_id NULL) is additionally
        # guaranteed by the get-or-create logic in lib.usersetting, since SQL
        # treats NULLs in a unique key as distinct.
        UniqueConstraint('subject_type', 'username', 'user_id', 'resolver', 'realm_id',
                         name='uq_usersetting_subject'),
    )

    id: Mapped[int] = mapped_column(Integer, Sequence("usersetting_seq"), primary_key=True)
    subject_type: Mapped[str] = mapped_column(Unicode(20), nullable=False)
    username: Mapped[str | None] = mapped_column(Unicode(320), default='')
    user_id: Mapped[str | None] = mapped_column(Unicode(320), default='')
    resolver: Mapped[str | None] = mapped_column(Unicode(120), default='')
    realm_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('realm.id', ondelete='CASCADE'))
    settings: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    last_modified: Mapped[datetime | None] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
    )
    # Reserved for future HA use: NULL means the value is global (valid on any node).
    node: Mapped[str | None] = mapped_column(Unicode(120), nullable=True, default=None)

    def __init__(self, subject_type, username='', user_id='', resolver='', realm_id=None, settings=None, node=None):
        self.subject_type = subject_type
        self.username = username
        self.user_id = user_id
        self.resolver = resolver
        self.realm_id = realm_id
        self.settings = settings
        self.node = node
