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
)
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.lib.utils import convert_column_to_unicode
from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin

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
    id: Mapped[int] = mapped_column(Sequence("audit_seq"), primary_key=True)
    date: Mapped[datetime] = mapped_column(default=datetime.now, index=True)
    startdate: Mapped[datetime]
    duration: Mapped[Interval] = mapped_column(Interval(second_precision=6))
    signature: Mapped[str] = mapped_column(Unicode(audit_column_length.get("signature")), default="")
    action: Mapped[str] = mapped_column(Unicode(audit_column_length.get("action")), default="")
    success: Mapped[int] = mapped_column(Integer, default=0)
    authentication: Mapped[str] = mapped_column(Unicode(audit_column_length.get("authentication")), default="")
    serial: Mapped[str] = mapped_column(Unicode(audit_column_length.get("serial")), default="")
    token_type: Mapped[str] = mapped_column(Unicode(audit_column_length.get("token_type")), default="")
    container_serial: Mapped[str] = mapped_column(Unicode(audit_column_length.get("container_serial")), default="")
    container_type: Mapped[str] = mapped_column(Unicode(audit_column_length.get("container_type")), default="")
    user: Mapped[str] = mapped_column(Unicode(audit_column_length.get("user")), default="", index=True)
    realm: Mapped[str] = mapped_column(Unicode(audit_column_length.get("realm")), default="")
    resolver: Mapped[str] = mapped_column(Unicode(audit_column_length.get("resolver")), default="")
    administrator: Mapped[str] = mapped_column(Unicode(audit_column_length.get("administrator")), default="")
    action_detail: Mapped[str] = mapped_column(Unicode(audit_column_length.get("action_detail")), default="")
    info: Mapped[str] = mapped_column(Unicode(audit_column_length.get("info")), default="")
    privacyidea_server: Mapped[str] = mapped_column(Unicode(audit_column_length.get("privacyidea_server")), default="")
    client: Mapped[str] = mapped_column(Unicode(audit_column_length.get("client")), default="")
    user_agent: Mapped[str] = mapped_column(Unicode(audit_column_length.get("user_agent")), default="")
    user_agent_version: Mapped[str] = mapped_column(Unicode(audit_column_length.get("user_agent_version")), default="")
    loglevel: Mapped[str] = mapped_column(Unicode(audit_column_length.get("loglevel")), default="default")
    clearance_level: Mapped[str] = mapped_column(Unicode(audit_column_length.get("clearance_level")), default="default")
    thread_id: Mapped[str] = mapped_column(Unicode(audit_column_length.get("thread_id")), default="0")
    policies: Mapped[str] = mapped_column(Unicode(audit_column_length.get("policies")), default="")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.signature = convert_column_to_unicode(self.signature)
        self.action = convert_column_to_unicode(self.action)
        self.authentication = convert_column_to_unicode(self.authentication)
        self.serial = convert_column_to_unicode(self.serial)
        self.token_type = convert_column_to_unicode(self.token_type)
        self.container_serial = convert_column_to_unicode(self.container_serial)
        self.container_type = convert_column_to_unicode(self.container_type)
        self.user = convert_column_to_unicode(self.user)
        self.realm = convert_column_to_unicode(self.realm)
        self.resolver = convert_column_to_unicode(self.resolver)
        self.administrator = convert_column_to_unicode(self.administrator)
        self.action_detail = convert_column_to_unicode(self.action_detail)
        self.info = convert_column_to_unicode(self.info)
        self.privacyidea_server = convert_column_to_unicode(self.privacyidea_server)
        self.client = convert_column_to_unicode(self.client)
        self.loglevel = convert_column_to_unicode(self.loglevel)
        self.clearance_level = convert_column_to_unicode(self.clearance_level)
        self.thread_id = convert_column_to_unicode(self.thread_id)
        self.policies = convert_column_to_unicode(self.policies)
        self.user_agent = convert_column_to_unicode(self.user_agent)
        self.user_agent_version = convert_column_to_unicode(self.user_agent_version)
