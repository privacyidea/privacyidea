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

from sqlalchemy import BigInteger, DateTime, JSON, Index, Sequence
from sqlalchemy.orm import mapped_column, Mapped, relationship

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin, utc_now, BigIntegerType, case_sensitive_unicode

if TYPE_CHECKING:
    from privacyidea.models import ConditionalAccessOutcome

# Maximum length of the string columns. The lib layer truncates values to these lengths before insert (see
# privacyidea.lib.conditional_access.authentication_log._truncate), so a value can never overflow a column.
#
# The columns that take part in the composite index ix_authlog_user_event_time (resolver, uid, realm, event_type)
# must stay below the 3072-byte InnoDB key limit of MySQL/MariaDB with utf8mb4: (120+320+255+40)*4 + 8 (timestamp)
# = 2948 bytes.
authentication_log_column_length = {
    "resolver": 120,
    "uid": 320,
    "realm": 255,
    "username": 255,
    "user_role": 30,
    "event_type": 40,
    "source_ip": 50,
    "client_label": 1024,
    "serial": 1024,
    # transaction_id (and attempt_id) originate in the challenge table, whose transaction_id is Unicode(64), so a real
    # value never exceeds 64 here either.
    "transaction_id": 64,
    "attempt_id": 64,
}


class AuthenticationLog(MethodsMixin, db.Model):
    """
    Append-only log of authentication events: every authenticated HTTP request produces exactly one row.
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
    id: Mapped[int] = mapped_column(BigIntegerType, Sequence("authentication_log_seq", data_type=BigInteger),
                                    primary_key=True)
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
    serial: Mapped[str | None] = mapped_column(case_sensitive_unicode(authentication_log_column_length["serial"]))
    transaction_id: Mapped[str | None] = mapped_column(
        case_sensitive_unicode(authentication_log_column_length["transaction_id"]))
    attempt_id: Mapped[str | None] = mapped_column(
        case_sensitive_unicode(authentication_log_column_length["attempt_id"]))
    other_info: Mapped[dict | None] = mapped_column(JSON)

    # What conditional access did to this request: zero or more rows of conditional_access_outcome, oldest first.
    #
    # The target is named as a **string** because models/__init__ imports this module before
    # conditional_access_outcome, so the class does not exist yet at import time; SQLAlchemy resolves it at mapper
    # configuration. That is the declarative idiom for two peer models, not a workaround for a layering problem.
    #
    # ``cascade="all, delete-orphan"`` so that deleting an entry *as an object* takes its history with it, the way a
    # token container takes its owners and states. This covers a whole class of callers rather than one code path -
    # including ``MethodsMixin.delete()``, which this model offers - and it works on every backend, because SQLAlchemy
    # issues the child DELETEs itself rather than relying on the foreign key (SQLite does not enforce those:
    # ``PRAGMA foreign_keys`` is off by default and privacyIDEA never enables it).
    #
    # Set-based deletes are **not** covered: SQLAlchemy does not consult relationship cascades for
    # ``table.delete().where(...)``, which is what retention has to use to remove large volumes with bounded memory.
    # Those paths delete the children explicitly - see
    # :func:`~privacyidea.lib.conditional_access.authentication_log._delete_entries`.
    #
    # ``lazy="raise"`` because **nothing on the authentication path may load these**. The engine counts over this table
    # and writes outcomes without reading them back, and one path in particular would pay for a mistake here:
    # ``_count_attempts`` fetches whole AuthenticationLog objects for every in-window row of a subject, so an eager or
    # even lazy relationship would add a fan-out query to every PER_ATTEMPT count. Raising turns that from something to
    # notice in review into an error, and exactly one query opts in - the paginated log listing, via ``selectinload``.
    # The guard does not get in the cascade's way: the unit of work loads the collection through its own path, not
    # through attribute access.
    outcomes: Mapped[list["ConditionalAccessOutcome"]] = relationship(
        "ConditionalAccessOutcome", cascade="all, delete-orphan", lazy="raise",
        order_by="ConditionalAccessOutcome.id")

    @property
    def aware_timestamp(self) -> datetime:
        """
        Return :attr:`timestamp` as a timezone-aware UTC datetime.

        The column itself is stored as a naive datetime because timezone-aware DateTime columns are not portable
        across all supported databases (they are ignored or handled differently per backend). We therefore store
        UTC and re-attach the timezone on read.
        """
        return self.timestamp.replace(tzinfo=timezone.utc)

    def to_dict(self, include_outcomes: bool = False) -> dict:
        """
        Serialize the entry for the API response, with the timestamp as an ISO-8601 UTC string.

        *include_outcomes* adds the conditional-access history of this request as ``conditional_access_outcomes``. It is
        off by default and only the paginated listing turns it on, because the relationship is ``lazy="raise"``: reading
        it on an entry that was not loaded with its outcomes must fail loudly rather than emit a query per entry.
        """
        auth_log_dict = {name: getattr(self, name) for name in self.__table__.columns.keys()}
        auth_log_dict["timestamp"] = self.aware_timestamp.isoformat()
        if include_outcomes:
            auth_log_dict["conditional_access_outcomes"] = [outcome.to_dict() for outcome in self.outcomes]
        return auth_log_dict
