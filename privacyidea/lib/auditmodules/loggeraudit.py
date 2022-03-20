# -*- coding: utf-8 -*-
#
#  2019-11-06 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             initial code for writing audit information to a file
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
__doc__ = """The Logger Audit Module is used to write audit entries to the Python logging module.

The Logger Audit Module is configured like this:

    PI_AUDIT_MODULE = "privacyidea.lib.auditmodules.loggeraudit"
    PI_AUDIT_SERVERNAME = "your choice"

    PI_LOGCONFIG = "/etc/privacyidea/logging.cfg"

The LoggerAudit Class uses the same PI logging config as you could use anyways.
To explicitly write audit logs, you need to add something like the following to
the logging.cfg

Example:

[handlers]
keys=file,audit

[loggers]
keys=root,privacyidea,audit

...

[logger_audit]
handlers=audit
qualname=privacyidea.lib.auditmodules.loggeraudit
level=INFO

[handler_audit]
class=logging.handlers.RotatingFileHandler
backupCount=14
maxBytes=10000000
formatter=detail
level=INFO
args=('/var/log/privacyidea/audit.log',)

"""

import logging
import json
from privacyidea.lib.auditmodules.base import (Audit as AuditBase)
from datetime import datetime


class Audit(AuditBase):
    """
    This is the LoggerAudit module, which writes the audit entries
    to the Python logging

    .. note:: This audit module does not provide a *Read* capability.
    """

    def __init__(self, config=None, startdate=None):
        super(Audit, self).__init__(config, startdate)
        self.name = "loggeraudit"
        self.qualname = self.config.get('PI_AUDIT_LOGGER_QUALNAME', __name__)
        self.logger = logging.getLogger(self.qualname)

    def finalize_log(self):
        """
        This method is used to log the data
        e.g. write the data to a file.
        """
        self.audit_data["policies"] = ",".join(self.audit_data.get("policies", []))
        self.audit_data["timestamp"] = datetime.utcnow().isoformat()
        if self.audit_data.get("startdate"):
            duration = datetime.utcnow() - self.audit_data.get("startdate")
            self.audit_data["duration"] = "{0!s}".format(duration)
            self.audit_data["startdate"] = self.audit_data.get("startdate").isoformat()
        self.logger.info("{0!s}".format(json.dumps(self.audit_data, sort_keys=True)))
        self.audit_data = {}
