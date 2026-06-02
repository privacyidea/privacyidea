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

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    JSON,
    Sequence,
    Unicode,
)
from sqlalchemy.dialects import sqlite
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin, utc_now

# Use a variant type for sqlite since it does not allow auto-increment with BigInteger type.
# (See https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#allowing-autoincrement-behavior-sqlalchemy-types-other-than-integer-integer)
BigIntegerType = BigInteger()
BigIntegerType = BigIntegerType.with_variant(sqlite.INTEGER(), "sqlite")

# Column lengths are aligned with the rest of the schema (TokenOwner.resolver,
# TokenOwner.user_id, Realm.name). Do not increase them without checking the
# size of the composite user index below: with utf8mb4 (4 bytes per char) it
# must stay below the 3072 byte InnoDB index key limit of MySQL/MariaDB.
# Currently: (120 + 320 + 255 + 40) * 4 + 8 = 2948 bytes.
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
    Dedicated log of authentication events, separate from the audit log.

    The audit log remains the verifiable record of *all things that happened*
    (including management operations); this table is optimised for the queries
    the conditional access policy engine and the dashboard need, e.g.
    "how often did this user fail with a wrong password in the last hour?"
    or "how many distinct users did this IP try in the last 5 minutes?"
    (password spraying).

    The user identity is the tuple ``(resolver, uid, realm)``: users live in
    resolvers, the uid is resolver-local and the same user may be reachable
    through more than one realm. All three columns are nullable so that events
    that cannot be resolved to a user (``USER_UNKNOWN``) can be logged as well.

    A logical authentication attempt may span multiple HTTP requests
    (challenge-response, push, passkey). Each request produces its own entry;
    the ``transaction_id`` correlates them into one attempt.

    Timestamps are stored as naive datetimes in UTC, like everywhere else in
    the schema (see :func:`~privacyidea.models.utils.utc_now`).
    """
    __tablename__ = "authentication_log"
    id: Mapped[int] = mapped_column(BigIntegerType,
                                    Sequence("authentication_log_seq", data_type=BigInteger),
                                    primary_key=True)
    # The resolver-local user identity tuple. Nullable for USER_UNKNOWN events.
    resolver: Mapped[str | None] = mapped_column(Unicode(authentication_log_column_length["resolver"]))
    uid: Mapped[str | None] = mapped_column(Unicode(authentication_log_column_length["uid"]))
    realm: Mapped[str | None] = mapped_column(Unicode(authentication_log_column_length["realm"]))
    # One of the codes from privacyidea.lib.conditional_access.event_types
    event_type: Mapped[str] = mapped_column(Unicode(authentication_log_column_length["event_type"]),
                                            nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    # The client IP as resolved by the API layer (same X-Forwarded-For trust
    # configuration as the audit log, see lib.utils.get_client_ip).
    source_ip: Mapped[str | None] = mapped_column(Unicode(authentication_log_column_length["source_ip"]))
    # Externally supplied client identifier. privacyIDEA has no strong client
    # identity today, so this is a generic string populated from whatever
    # signal is available (a "client_id" request parameter or the User-Agent
    # header, see lib.conditional_access.authentication_log). A future
    # stronger binding (e.g. per-client API keys) can fill the same column.
    client_label: Mapped[str | None] = mapped_column(Unicode(authentication_log_column_length["client_label"]))
    # The token serial, if the event can be attributed to a token
    serial: Mapped[str | None] = mapped_column(Unicode(authentication_log_column_length["serial"]))
    # Correlates the multiple HTTP requests of one logical authentication attempt
    transaction_id: Mapped[str | None] = mapped_column(Unicode(authentication_log_column_length["transaction_id"]))
    # Free-form JSON for forward compatibility
    other_info: Mapped[dict | None] = mapped_column(JSON)

    __table_args__ = (
        # The "golden" index for the hot policy engine query:
        # COUNT(*) WHERE resolver/uid/realm/event_type match AND timestamp > ?
        Index("ix_authentication_log_user_event_time",
              "resolver", "uid", "realm", "event_type", "timestamp"),
        # For spraying detection: COUNT(DISTINCT (resolver, uid, realm))
        # WHERE source_ip/event_type match AND timestamp > ?
        Index("ix_authentication_log_ip_event_time",
              "source_ip", "event_type", "timestamp"),
    )
