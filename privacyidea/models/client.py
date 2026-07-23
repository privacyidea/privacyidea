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
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.lib.log import log_with
from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin, utc_now

log = logging.getLogger(__name__)


class Client(MethodsMixin, db.Model):
    """
    The clients table holds API clients that authenticate against privacyIDEA
    with an API key (sent in the ``X-API-Key`` header). Each client represents
    an external integration such as a Windows credential provider, a Keycloak
    plugin or an Entra ID connector.

    An API key has the form ``<prefix>_<key_id>_<secret>``. The ``key_id`` is a
    non-secret, unique identifier that is stored in plaintext and used to look
    up the client; only the ``secret`` half is hashed into ``key_hash``. This
    way the plaintext key is never stored, the lookup is a direct indexed match
    on ``key_id`` (no scanning), and the publicly shown ``key_id`` reveals
    nothing about the secret.
    """
    __tablename__ = 'clients'
    id: Mapped[str] = mapped_column(Unicode(36), primary_key=True, default=lambda: str(uuid4()))
    display_name: Mapped[str] = mapped_column(Unicode(255), default='', nullable=False)
    client_type: Mapped[str] = mapped_column(Unicode(64), default='', nullable=False)
    key_id: Mapped[str] = mapped_column(Unicode(32), unique=True, index=True, nullable=False)
    key_hash: Mapped[str] = mapped_column(Unicode(64), nullable=False)
    status: Mapped[str] = mapped_column(Unicode(16), default='active', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    @log_with(log)
    def __init__(self, display_name, client_type, key_id, key_hash,
                 status='active', config=None):
        self.display_name = display_name
        self.client_type = client_type
        self.key_id = key_id
        self.key_hash = key_hash
        self.status = status
        self.config = config if config is not None else {}
