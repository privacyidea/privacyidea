# (c) NetKnights GmbH 2026,  https://netknights.it
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
#
# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime

from sqlalchemy import BigInteger, Unicode, DateTime, JSON, Index, Sequence
from sqlalchemy.orm import mapped_column, Mapped

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin, utc_now, BigIntegerType

# Maximum length of the string columns. The lib layer truncates values to these lengths before insert (see
# privacyidea.lib.conditional_access.authentication_log._truncate), so a pathological User-Agent or login name can
# never overflow a column. The lengths are also chosen so the composite index ix_authlog_user_event_time stays below
# the 3072-byte InnoDB key limit of MySQL/MariaDB with utf8mb4: (120+320+255+40)*4 + 8 (timestamp) = 2948 bytes.
authentication_log_column_length = {
    "resolver": 120,
    "uid": 320,
    "realm": 255,
    "event_type": 40,
    "source_ip": 50,
    "client_label": 255,
    "serial": 40,
    "transaction_id": 64,
}


class AuthenticationLog(MethodsMixin, db.Model):
    """
    Append-only log of authentication events: every authenticated HTTP request produces exactly one row.
    Several rows may share a ``transaction_id`` to correlate the multiple requests of one logical authentication
    attempt (e.g. a challenge trigger and its later response) at query time.
    """
    __tablename__ = "authentication_log"
    __table_args__ = (
        Index("ix_authlog_user_event_time", "resolver", "uid", "realm", "event_type", "timestamp"),
        Index("ix_authlog_ip_event_time", "source_ip", "event_type", "timestamp"),
    )
    id: Mapped[int] = mapped_column(BigIntegerType, Sequence("authentication_log_seq", data_type=BigInteger),
                                    primary_key=True)
    resolver: Mapped[str | None] = mapped_column(Unicode(authentication_log_column_length["resolver"]))
    uid: Mapped[str | None] = mapped_column(Unicode(authentication_log_column_length["uid"]))
    realm: Mapped[str | None] = mapped_column(Unicode(authentication_log_column_length["realm"]))
    event_type: Mapped[str] = mapped_column(Unicode(authentication_log_column_length["event_type"]), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    source_ip: Mapped[str | None] = mapped_column(Unicode(authentication_log_column_length["source_ip"]))
    client_label: Mapped[str | None] = mapped_column(Unicode(authentication_log_column_length["client_label"]))
    serial: Mapped[str | None] = mapped_column(Unicode(authentication_log_column_length["serial"]))
    transaction_id: Mapped[str | None] = mapped_column(Unicode(authentication_log_column_length["transaction_id"]))
    other_info: Mapped[dict | None] = mapped_column(JSON)
