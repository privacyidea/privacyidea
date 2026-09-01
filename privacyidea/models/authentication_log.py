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

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Identity, JSON, Index
from sqlalchemy.orm import mapped_column, Mapped, relationship

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin, utc_now, BigIntegerType, case_sensitive_unicode

if TYPE_CHECKING:
    from privacyidea.models import AuthenticationLogReason, ConditionalAccessOutcome

# Maximum length of the string columns; the lib layer truncates values to these lengths before insert (see
# privacyidea.lib.conditional_access.authentication_log._truncate), so a value can never overflow a column.
# The composite index ix_authlog_user_event_time (resolver, uid, realm, event_type) must stay under the
# 3072-byte InnoDB key limit for utf8mb4: (120+320+255+40)*4 + 8 (timestamp) = 2948 bytes.
authentication_log_column_length = {
    "resolver": 120,
    "uid": 320,
    "realm": 255,
    "username": 255,
    "user_role": 30,
    "event_type": 40,
    "source_ip": 50,
    "client_label": 1024,
    # The request path of the authenticating endpoint ("/auth", "/validate/check", ...). Sized well past the longest
    # route privacyIDEA registers, so a value is never actually cut.
    "endpoint": 255,
    "serial": 1024,
    # transaction_id (and attempt_id) originate in the challenge table, whose transaction_id is Unicode(64), so a real
    # value never exceeds 64 here either.
    "transaction_id": 64,
    "attempt_id": 64,
}


class AuthenticationLog(MethodsMixin, db.Model):
    """
    Append-only log of authentication events: every authenticated HTTP request produces a row, and normally exactly
    one (a ``push_wait`` request writes two, since it triggers the challenge and awaits the answer within the one
    request).
    Several rows may share a ``transaction_id`` to correlate the multiple requests of one logical authentication
    attempt (e.g. a challenge trigger and its later response) at query time. Rows of one logical attempt - including a
    multi-challenge flow where answering one challenge triggers another - share an ``attempt_id``; ordering an
    attempt's rows by ``id`` reconstructs the full chain, and each row's own ``transaction_id`` still links back to the
    challenge table.
    """
    __tablename__ = "authentication_log"
    __table_args__ = (
        Index("ix_authlog_user_event_time", "resolver", "uid", "realm", "event_type", "timestamp"),
        Index("ix_authlog_ip_event_time", "source_ip", "event_type", "timestamp"),
        # PER_ATTEMPT counting (count_user_attempts / count_ip_attempts) range-scans a subject's rows by time with no
        # event_type predicate, so each needs timestamp right after the subject column(s).
        Index("ix_authlog_user_time", "resolver", "uid", "realm", "timestamp"),
        Index("ix_authlog_ip_time", "source_ip", "timestamp"),
    )
    id: Mapped[int] = mapped_column(BigIntegerType, Identity(always=False), primary_key=True)
    resolver: Mapped[str | None] = mapped_column(case_sensitive_unicode(authentication_log_column_length["resolver"]))
    uid: Mapped[str | None] = mapped_column(case_sensitive_unicode(authentication_log_column_length["uid"]))
    realm: Mapped[str | None] = mapped_column(case_sensitive_unicode(authentication_log_column_length["realm"]))
    username: Mapped[str | None] = mapped_column(case_sensitive_unicode(authentication_log_column_length["username"]))
    user_role: Mapped[str | None] = mapped_column(
        case_sensitive_unicode(authentication_log_column_length["user_role"]))
    event_type: Mapped[str] = mapped_column(
        case_sensitive_unicode(authentication_log_column_length["event_type"]), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    source_ip: Mapped[str | None] = mapped_column(
        case_sensitive_unicode(authentication_log_column_length["source_ip"]))
    client_label: Mapped[str | None] = mapped_column(
        case_sensitive_unicode(authentication_log_column_length["client_label"]))
    # The endpoint the request authenticated against, as its request path ("/auth", "/validate/check", "/ttype/push").
    # Every authentication reaches the server as a request - there is no authentication from the CLI, and push_wait
    # runs inside the request that triggered the challenge - so an entry an authentication wrote always names one.
    # Nullable only for an entry staged outside a view, which nothing on the authentication path does.
    endpoint: Mapped[str | None] = mapped_column(
        case_sensitive_unicode(authentication_log_column_length["endpoint"]))
    serial: Mapped[str | None] = mapped_column(case_sensitive_unicode(authentication_log_column_length["serial"]))
    transaction_id: Mapped[str | None] = mapped_column(
        case_sensitive_unicode(authentication_log_column_length["transaction_id"]))
    attempt_id: Mapped[str | None] = mapped_column(
        case_sensitive_unicode(authentication_log_column_length["attempt_id"]))
    other_info: Mapped[dict | None] = mapped_column(JSON)

    # What conditional access did to this request: zero or more rows of conditional_access_outcome, oldest first.
    #
    # The target is named as a string because models/__init__ imports this module before conditional_access_outcome
    # exists; SQLAlchemy resolves the name at mapper configuration - the standard idiom for two peer models.
    #
    # cascade="all, delete-orphan" so deleting an entry as an object takes its outcomes with it on every backend,
    # covering every caller including MethodsMixin.delete(); SQLAlchemy issues the child deletes itself, without
    # relying on the foreign key, which SQLite does not enforce by default.
    #
    # Set-based deletes are not covered by the cascade: retention deletes the child rows itself to remove large
    # volumes with bounded memory (see _delete_entries).
    #
    # lazy="raise" because nothing on the authentication path may load these: _count_attempts fetches every
    # in-window row for a subject, so any relationship load here would add a fan-out query to every PER_ATTEMPT
    # count. Only the paginated log listing opts in, via selectinload; the delete-orphan cascade still works because
    # the unit of work loads the collection through its own path, not through attribute access.
    outcomes: Mapped[list["ConditionalAccessOutcome"]] = relationship(
        "ConditionalAccessOutcome", cascade="all, delete-orphan", lazy="raise",
        order_by="ConditionalAccessOutcome.id")

    # Why this event came out the way it did: zero or more AuthEventReason values, in the order that vocabulary
    # declares them (a success needs none). Declared exactly like the outcomes above and for the same reasons - the
    # cascade covers deleting an entry as an object on every backend, while the set-based delete paths remove the
    # child rows themselves, and lazy="raise" keeps the authentication path from ever fanning out a query per row.
    reasons: Mapped[list["AuthenticationLogReason"]] = relationship(
        "AuthenticationLogReason", cascade="all, delete-orphan", lazy="raise",
        order_by="AuthenticationLogReason.id")

    @property
    def aware_timestamp(self) -> datetime:
        """
        Return :attr:`timestamp` as a timezone-aware UTC datetime.

        The column itself is stored as a naive datetime because timezone-aware DateTime columns are not portable
        across all supported databases (they are ignored or handled differently per backend). We therefore store
        UTC and re-attach the timezone on read.
        """
        return self.timestamp.replace(tzinfo=timezone.utc)

    def to_dict(self, include_outcomes: bool = False, include_reasons: bool = False) -> dict:
        """
        Serialize the entry for the API response, with the timestamp as an ISO-8601 UTC string.

        *include_outcomes* adds the conditional-access history of this request as ``conditional_access_outcomes``. It is
        off by default and only the paginated listing turns it on, because the relationship is ``lazy="raise"``: reading
        it on an entry that was not loaded with its outcomes must fail loudly rather than emit a query per entry.

        *include_reasons* adds the classified reasons as the ``reasons`` list, in the order they were recorded,
        under the same rule and for the same reason: that relationship is ``lazy="raise"`` too.
        """
        auth_log_dict = {name: getattr(self, name) for name in self.__table__.columns.keys()}
        auth_log_dict["timestamp"] = self.aware_timestamp.isoformat()
        if include_reasons:
            auth_log_dict["reasons"] = [entry.reason for entry in self.reasons]
        if include_outcomes:
            auth_log_dict["conditional_access_outcomes"] = [outcome.to_dict() for outcome in self.outcomes]
        return auth_log_dict
