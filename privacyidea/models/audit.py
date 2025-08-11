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

from sqlalchemy import Sequence

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin
from privacyidea.lib.utils import convert_column_to_unicode

audit_column_length = {"signature": 620,
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
    """
    This class stores the Audit entries
    """
    __tablename__ = AUDIT_TABLE_NAME
    id = db.Column(db.Integer, Sequence("audit_seq"), primary_key=True)
    date = db.Column(db.DateTime, index=True)
    startdate = db.Column(db.DateTime)
    duration = db.Column(db.Interval(second_precision=6))
    signature = db.Column(db.Unicode(audit_column_length.get("signature")))
    action = db.Column(db.Unicode(audit_column_length.get("action")))
    success = db.Column(db.Integer)
    authentication = db.Column(db.Unicode(audit_column_length.get("authentication")))
    serial = db.Column(db.Unicode(audit_column_length.get("serial")))
    token_type = db.Column(db.Unicode(audit_column_length.get("token_type")))
    container_serial = db.Column(db.Unicode(audit_column_length.get("container_serial")))
    container_type = db.Column(db.Unicode(audit_column_length.get("container_type")))
    user = db.Column(db.Unicode(audit_column_length.get("user")), index=True)
    realm = db.Column(db.Unicode(audit_column_length.get("realm")))
    resolver = db.Column(db.Unicode(audit_column_length.get("resolver")))
    administrator = db.Column(db.Unicode(audit_column_length.get("administrator")))
    action_detail = db.Column(db.Unicode(audit_column_length.get("action_detail")))
    info = db.Column(db.Unicode(audit_column_length.get("info")))
    privacyidea_server = db.Column(db.Unicode(audit_column_length.get("privacyidea_server")))
    client = db.Column(db.Unicode(audit_column_length.get("client")))
    user_agent = db.Column(db.Unicode(audit_column_length.get("user_agent")))
    user_agent_version = db.Column(db.Unicode(audit_column_length.get("user_agent_version")))
    loglevel = db.Column(db.Unicode(audit_column_length.get("loglevel")))
    clearance_level = db.Column(db.Unicode(audit_column_length.get("clearance_level")))
    thread_id = db.Column(db.Unicode(audit_column_length.get("thread_id")))
    policies = db.Column(db.Unicode(audit_column_length.get("policies")))

    def __init__(self,
                 action="",
                 success=0,
                 authentication="",
                 serial="",
                 token_type="",
                 container_serial="",
                 container_type="",
                 user="",
                 realm="",
                 resolver="",
                 administrator="",
                 action_detail="",
                 info="",
                 privacyidea_server="",
                 client="",
                 user_agent="",
                 user_agent_version="",
                 loglevel="default",
                 clearance_level="default",
                 thread_id="0",
                 policies="",
                 startdate=None,
                 duration=None
                 ):
        self.signature = ""
        self.date = datetime.now()
        self.startdate = startdate
        self.duration = duration
        self.action = convert_column_to_unicode(action)
        self.success = success
        self.authentication = convert_column_to_unicode(authentication)
        self.serial = convert_column_to_unicode(serial)
        self.token_type = convert_column_to_unicode(token_type)
        self.container_serial = convert_column_to_unicode(container_serial)
        self.container_type = convert_column_to_unicode(container_type)
        self.user = convert_column_to_unicode(user)
        self.realm = convert_column_to_unicode(realm)
        self.resolver = convert_column_to_unicode(resolver)
        self.administrator = convert_column_to_unicode(administrator)
        self.action_detail = convert_column_to_unicode(action_detail)
        self.info = convert_column_to_unicode(info)
        self.privacyidea_server = convert_column_to_unicode(privacyidea_server)
        self.client = convert_column_to_unicode(client)
        self.loglevel = convert_column_to_unicode(loglevel)
        self.clearance_level = convert_column_to_unicode(clearance_level)
        self.thread_id = convert_column_to_unicode(thread_id)
        self.policies = convert_column_to_unicode(policies)
        self.user_agent = convert_column_to_unicode(user_agent)
        self.user_agent_version = convert_column_to_unicode(user_agent_version)
