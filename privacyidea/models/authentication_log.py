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
    from privacyidea.models import ConditionalAccessOutcome

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
    "peer_ip": 50,
    "source_ip_source": 40,
    "client_label": 1024,
    "client_label_source": 40,
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

    The client of a request is recorded as what was decided *and* how it was decided:

    * ``source_ip`` is the effective client IP - the one authorization is evaluated against and the only one the
      conditional-access engine counts and enforces on. It is unchanged by the provenance columns below.
    * ``peer_ip`` is the TCP peer the request actually arrived from (``request.remote_addr``), which is the same
      address unless a proxy mapping moved it. It is indexed, because "what came from this machine" is the
      second question a forensic query asks.
    * ``source_ip_source`` names where ``source_ip`` was taken from, as a
      :class:`~privacyidea.lib.utils.ClientIpSource` value. ``REMOTE_ADDR_UNMAPPED`` is deliberately distinct
      from ``REMOTE_ADDR``: the peer was used *despite* an ``OverrideAuthorizationClient`` being configured.
    * ``ip_chain`` is the whole path that was considered, recorded even when no override is configured and the
      ``X-Forwarded-For`` header is therefore ignored - recording what a request claimed is not trusting it.
      Everything past ``peer_ip`` is client-supplied and must never gate a decision.
    * ``client_label`` is the ``client_id`` parameter or the User-Agent, and ``client_label_source`` says which.

    **NULL in any of the four provenance columns means the row predates them**, and nothing may be inferred
    from it - in particular a NULL ``source_ip_source`` must never be rendered as "direct connection".
    """
    __tablename__ = "authentication_log"
    __table_args__ = (
        Index("ix_authlog_user_event_time", "resolver", "uid", "realm", "event_type", "timestamp"),
        Index("ix_authlog_ip_event_time", "source_ip", "event_type", "timestamp"),
        # PER_ATTEMPT counting (count_user_attempts / count_ip_attempts) range-scans a subject's rows by time with no
        # event_type predicate, so each needs timestamp right after the subject column(s).
        Index("ix_authlog_user_time", "resolver", "uid", "realm", "timestamp"),
        Index("ix_authlog_ip_time", "source_ip", "timestamp"),
        # The TCP peer is the second pivot a forensic query starts from - "what came from this machine",
        # whatever it claimed to be forwarding for. 50*4 + 8 = 208 bytes, well under the same key limit.
        Index("ix_authlog_peer_ip_time", "peer_ip", "timestamp"),
        # The one index not scoped to a subject: the statistics query
        # (:func:`~privacyidea.lib.conditional_access.authentication_log.get_authentication_log_statistics`) and the
        # retention delete (``cleanup_authentication_log``) both range over ``timestamp`` alone, and the indexes
        # above cannot serve that - their leading columns are unconstrained, so the rows of a window are scattered
        # across each of them in subject order rather than lying contiguous.
        Index("ix_authlog_time", "timestamp"),
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
    peer_ip: Mapped[str | None] = mapped_column(
        case_sensitive_unicode(authentication_log_column_length["peer_ip"]))
    source_ip_source: Mapped[str | None] = mapped_column(
        case_sensitive_unicode(authentication_log_column_length["source_ip_source"]))
    client_label: Mapped[str | None] = mapped_column(
        case_sensitive_unicode(authentication_log_column_length["client_label"]))
    client_label_source: Mapped[str | None] = mapped_column(
        case_sensitive_unicode(authentication_log_column_length["client_label_source"]))
    # The path privacyIDEA considered when deriving source_ip, peer first and the claimed origin last:
    # ``[{"ip": "...", "source": "REMOTE_ADDR|X_FORWARDED_FOR|CLIENT_PARAM", "effective": true}, ...]``.
    # Written only when there is more than one hop, so NULL means the path was exactly ``[peer_ip]``.
    ip_chain: Mapped[list | None] = mapped_column(JSON)
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
