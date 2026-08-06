# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
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

from sqlalchemy import DateTime, ForeignKey, Integer, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.lib.log import log_with
from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin, utc_now

log = logging.getLogger(__name__)

# Default lifetime of a remembered device.
DEFAULT_DEVICE_VALIDITY = timedelta(days=30)


class RememberedDevice(MethodsMixin, db.Model):
    """
    A persistent ("remember this device") authentication device bound to a
    specific API client.

    The device implements a rotating-token scheme: the client stores a cookie
    of the form ``series_id:counter``. On every use the counter is incremented
    both in the cookie and in this row. If a request presents the correct
    ``series_id`` but a stale ``counter``, the token has been replayed (the
    cookie was stolen), the whole series is deleted and authentication fails.

    The cookie never contains the API key; the binding to the client is stored
    server-side in ``client_id`` and checked against ``g.client_id``.

    The remembered user is bound by the resolver-stable identity
    ``(resolver, user_id, realm_id)`` - **not** by the login name. The login is a
    mutable, reusable label in an external user store: binding to it would drop
    the remembered device on a rename and, worse, could recognise a *different*
    account that later reuses a freed login. ``user_id`` is therefore the
    resolver's immutable id (as in :class:`TokenOwner`), and ``realm_id`` is a
    foreign key so a deleted realm cascades its devices away.
    """
    __tablename__ = 'remembered_devices'
    series_id: Mapped[str] = mapped_column(Unicode(64), primary_key=True)
    counter: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    client_id: Mapped[str] = mapped_column(Unicode(36), ForeignKey("clients.id", ondelete="CASCADE"),
                                           index=True, nullable=False)
    resolver: Mapped[str] = mapped_column(Unicode(120), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(Unicode(320), index=True, nullable=False)
    realm_id: Mapped[int] = mapped_column(Integer, ForeignKey("realm.id", ondelete="CASCADE"),
                                          index=True, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(Unicode(64))
    user_agent: Mapped[str | None] = mapped_column(Unicode(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    @log_with(log)
    def __init__(self, series_id, client_id, resolver, user_id, realm_id,
                 ip_address=None, user_agent=None, counter=1, expires_at=None):
        self.series_id = series_id
        self.counter = counter
        self.client_id = client_id
        self.resolver = resolver
        self.user_id = user_id
        self.realm_id = realm_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.expires_at = expires_at if expires_at is not None else utc_now() + DEFAULT_DEVICE_VALIDITY
