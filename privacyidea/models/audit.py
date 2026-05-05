# SPDX-FileCopyrightText: (C) 2025 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2025 Paul Lettich <paul.lettich@netknights.it>
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
    Integer,
    Sequence,
    Interval,
    Unicode,
    BigInteger,
)
from sqlalchemy.dialects import sqlite
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin

# Use a variant type for sqlite since it does not allow auto-increment with BigInteger type.
# (See https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#allowing-autoincrement-behavior-sqlalchemy-types-other-than-integer-integer)
BigIntegerType = BigInteger()
BigIntegerType = BigIntegerType.with_variant(sqlite.INTEGER(), "sqlite")

audit_column_length = {"signature": 1100,
                       "action": 200,
                       "serial": 40,
                       "token_type": 12,
                       "user": 100,
                       "realm": 255,
                       "resolver": 255,
                       "administrator": 100,
                       "action_detail": 500,
                       "info": 500,
                       "privacyidea_server": 255,
                       "client": 50,
                       "loglevel": 12,
                       "clearance_level": 12,
                       "thread_id": 20,
                       "authentication": 12,
                       "user_agent": 50,
                       "user_agent_version": 20,
                       "policies": 255,
                       "container_serial": 40,
                       "container_type": 100}

AUDIT_TABLE_NAME = 'pidea_audit'


class Audit(MethodsMixin, db.Model):
    __tablename__ = AUDIT_TABLE_NAME
    id: Mapped[int] = mapped_column(BigIntegerType,
                                    Sequence("audit_seq", data_type=BigInteger), primary_key=True)
    date: Mapped[datetime | None] = mapped_column(default=datetime.now, index=True)
    startdate: Mapped[datetime | None]
    duration: Mapped[Interval | None] = mapped_column(Interval(second_precision=6))
    signature: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("signature")), default="")
    action: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("action")), default="")
    success: Mapped[int | None] = mapped_column(Integer, default=0)
    authentication: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("authentication")),
                                                          default="")
    serial: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("serial")), default="")
    token_type: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("token_type")), default="")
    container_serial: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("container_serial")),
                                                            default="")
    container_type: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("container_type")),
                                                          default="")
    user: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("user")), default="", index=True)
    realm: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("realm")), default="")
    resolver: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("resolver")), default="")
    administrator: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("administrator")), default="")
    action_detail: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("action_detail")), default="")
    info: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("info")), default="")
    privacyidea_server: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("privacyidea_server")),
                                                              default="")
    client: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("client")), default="")
    user_agent: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("user_agent")), default="")
    user_agent_version: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("user_agent_version")),
                                                              default="")
    loglevel: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("loglevel")), default="default")
    clearance_level: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("clearance_level")),
                                                           default="default")
    thread_id: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("thread_id")), default="0")
    policies: Mapped[str | None] = mapped_column(Unicode(audit_column_length.get("policies")), default="")
