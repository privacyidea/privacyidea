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

from sqlalchemy import update, delete, select

from privacyidea.models import AuthenticationLog, db


def create_authentication_log(event_type: str,
                              resolver: str | None = None,
                              uid: str | None = None,
                              realm: str | None = None,
                              source_ip: str | None = None,
                              client_label: str | None = None,
                              serial: str | None = None,
                              transaction_id: str | None = None,
                              other_info: dict | None = None) -> int:
    """
    Create a new authentication log entry and return its event_id.
    """
    entry = AuthenticationLog(resolver=resolver, uid=uid, realm=realm, event_type=event_type,
                              source_ip=source_ip, client_label=client_label,
                              serial=serial, transaction_id=transaction_id,
                              other_info=other_info)
    db.session.add(entry)
    db.session.commit()
    return entry.event_id


def update_authentication_log(event_id: int,
                               resolver: str | None = None,
                               uid: str | None = None,
                               realm: str | None = None,
                               event_type: str | None = None,
                               source_ip: str | None = None,
                               client_label: str | None = None,
                               serial: str | None = None,
                               transaction_id: str | None = None,
                               other_info: dict | None = None) -> None:
    """
    Update fields of an existing authentication log entry by event_id.
    Only provided (non-None) fields are updated.
    """
    values = {k: v for k, v in {
        "resolver": resolver,
        "uid": uid,
        "realm": realm,
        "event_type": event_type,
        "source_ip": source_ip,
        "client_label": client_label,
        "serial": serial,
        "transaction_id": transaction_id,
        "other_info": other_info,
    }.items() if v is not None}
    if not values:
        return
    stmt = update(AuthenticationLog).where(AuthenticationLog.event_id == event_id).values(**values)
    db.session.execute(stmt)
    db.session.commit()


def delete_authentication_log(event_id: int) -> None:
    """
    Delete a single authentication log entry by event_id.
    """
    stmt = delete(AuthenticationLog).where(AuthenticationLog.event_id == event_id)
    db.session.execute(stmt)
    db.session.commit()


def get_authentication_log(event_id: int) -> AuthenticationLog | None:
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
    Return authentication log entries matching all provided filter criteria.
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
        stmt = stmt.where(AuthenticationLog.timestamp >= start_timestamp)
    if end_timestamp is not None:
        stmt = stmt.where(AuthenticationLog.timestamp <= end_timestamp)
    return db.session.scalars(stmt).all()


def cleanup_authentication_log(older_than: datetime) -> int:
    """
    Delete all authentication log entries with a timestamp strictly older than
    the given datetime. Returns the number of deleted rows.
    """
    stmt = delete(AuthenticationLog).where(AuthenticationLog.timestamp < older_than)
    result = db.session.execute(stmt)
    db.session.commit()
    return result.rowcount
