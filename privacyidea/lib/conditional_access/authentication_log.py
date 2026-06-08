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
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select

from privacyidea.models import AuthenticationLog, authentication_log_column_length, db
from privacyidea.lib.conditional_access.authentication_error_codes import AuthEventType
from privacyidea.lib.sqlutils import delete_matching_rows

log = logging.getLogger(__name__)


def _naive_utc(value: datetime) -> datetime:
    """
    Normalize a datetime to naive UTC, matching how the ``timestamp`` column is stored. A timezone-aware value is
    converted to UTC and stripped of its tzinfo; a naive value is assumed to already be in UTC and returned unchanged.
    This lets callers pass either form without risking a naive-vs-aware comparison against the column.
    """
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _truncate(column: str, value) -> str | None:
    """
    Convert *value* to a string and truncate it to the length of the given column of the authentication_log table, so a
    pathological value (e.g. a very long User-Agent or login name) can never overflow the column on insert.

    :param column: the column name, a key of
        :data:`~privacyidea.models.authentication_log.authentication_log_column_length`
    :param value: the value to store, or None
    :return: the truncated string, or None if *value* is None
    """
    if value is None:
        return None
    value = str(value)
    max_length = authentication_log_column_length[column]
    if len(value) > max_length:
        log.debug(f"Truncating authentication log column {column!r} to {max_length} characters.")
        value = value[:max_length]
    return value


def log_authentication_event(event_type: AuthEventType,
                             transaction_id: str | None = None,
                             resolver: str | None = None,
                             uid: str | None = None,
                             realm: str | None = None,
                             source_ip: str | None = None,
                             client_label: str | None = None,
                             serial: str | None = None,
                             other_info: dict | None = None) -> int | None:
    """
    Create a new authentication log entry and return its id.

    Writing the authentication log must never break the authentication itself, so any failure here is logged and
    swallowed: the entry is not written, the session is rolled back so the rest of the request can still commit, and
    ``None`` is returned instead of an id.
    """
    try:
        entry = AuthenticationLog(
            event_type=_truncate("event_type", event_type),
            transaction_id=_truncate("transaction_id", transaction_id),
            resolver=_truncate("resolver", resolver),
            uid=_truncate("uid", uid),
            realm=_truncate("realm", realm),
            source_ip=_truncate("source_ip", source_ip),
            client_label=_truncate("client_label", client_label),
            serial=_truncate("serial", serial),
            other_info=other_info
        )
        db.session.add(entry)
        db.session.commit()
        return entry.id
    except Exception as ex:
        log.warning(f"Failed to write the authentication log entry: {ex!r}")
        db.session.rollback()
        return None


def delete_authentication_log_event(event_id: int) -> None:
    """
    Delete a single authentication log entry by id.
    """
    stmt = delete(AuthenticationLog).where(AuthenticationLog.id == event_id)
    db.session.execute(stmt)
    db.session.commit()


def get_authentication_log_event(event_id: int) -> AuthenticationLog | None:
    """
    Return a single AuthenticationLog entry by event_id, or None if not found.
    """
    return db.session.get(AuthenticationLog, event_id)


def get_authentication_logs(resolver: str | None = None,
                            uid: str | None = None,
                            realm: str | None = None,
                            event_type: str | None = None,
                            source_ip: str | None = None,
                            serial: str | None = None,
                            transaction_id: str | None = None,
                            start_timestamp: datetime | None = None,
                            end_timestamp: datetime | None = None) -> list[AuthenticationLog]:
    """
    Return authentication log entries matching all provided filter criteria, ordered by id (i.e. chronologically).
    All parameters are optional; omitting a parameter means no filtering on that field.
    timestamp filters are inclusive on both ends.
    """
    stmt = select(AuthenticationLog)
    if resolver is not None:
        stmt = stmt.where(AuthenticationLog.resolver == resolver)
    if uid is not None:
        stmt = stmt.where(AuthenticationLog.uid == uid)
    if realm is not None:
        stmt = stmt.where(AuthenticationLog.realm == realm)
    if event_type is not None:
        stmt = stmt.where(AuthenticationLog.event_type == event_type)
    if source_ip is not None:
        stmt = stmt.where(AuthenticationLog.source_ip == source_ip)
    if serial is not None:
        stmt = stmt.where(AuthenticationLog.serial == serial)
    if transaction_id is not None:
        stmt = stmt.where(AuthenticationLog.transaction_id == transaction_id)
    if start_timestamp is not None:
        stmt = stmt.where(AuthenticationLog.timestamp >= _naive_utc(start_timestamp))
    if end_timestamp is not None:
        stmt = stmt.where(AuthenticationLog.timestamp <= _naive_utc(end_timestamp))
    stmt = stmt.order_by(AuthenticationLog.id)
    return db.session.scalars(stmt).all()


def cleanup_authentication_log(older_than: datetime, chunk_size: int | None = None) -> int:
    """
    Delete all authentication log entries with a timestamp strictly older than the given datetime.

    :param older_than: delete entries whose timestamp is older than this (naive or timezone-aware; aware values are
        converted to UTC)
    :param chunk_size: if given, delete in chunks of this size to avoid long locks / deadlocks on large tables
    :return: the number of deleted rows
    """
    criterion = AuthenticationLog.timestamp < _naive_utc(older_than)
    return delete_matching_rows(db.session, AuthenticationLog.__table__, criterion, chunk_size)
