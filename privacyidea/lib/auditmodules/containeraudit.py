# -*- coding: utf-8 -*-
#
#  2019-11-07 Cornelius Kölbel <cornelius.koelbel@netknights.it>
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
__doc__ = """The Container Audit Module allows to write audit information to several different
audit modules at the same time. E.g. it can write audit information to the SQL Audit Module and to the 
Logger Audit Module. This way audit information can be saved in the SQL database and at the same time
be passed to a file or external services via the Python logging facility. 

The Container Audit Module is configured like this:

    PI_AUDIT_MODULE = 'privacyidea.lib.auditmodules.containeraudit'
    PI_AUDIT_CONTAINER_WRITE = ['privacyidea.lib.auditmodules.sqlaudit','privacyidea.lib.auditmodules.loggeraudit']
    PI_AUDIT_CONTAINER_READ = 'privacyidea.lib.auditmodules.sqlaudit'

You also have to provide the configuration parameters for the referenced audit modules.

"""

import logging
from privacyidea.lib.auditmodules.base import (Audit as AuditBase)
from privacyidea.lib.utils import get_module_class


log = logging.getLogger(__name__)


class Audit(AuditBase):
    """
    This is the ContainerAudit module, which writes the audit entries
    to a list of audit modules.
    """

    def __init__(self, config=None, startdate=None):
        super(Audit, self).__init__(config, startdate)
        self.name = "containeraudit"
        write_conf = self.config.get('PI_AUDIT_CONTAINER_WRITE')
        read_conf = self.config.get('PI_AUDIT_CONTAINER_READ')
        # Initialize all modules
        self.write_modules = [get_module_class(audit_module, "Audit", "log")(config, startdate)
                              for audit_module in write_conf]
        self.read_module = get_module_class(read_conf, "Audit", "log")(config, startdate)
        if not self.read_module.is_readable:
            log.warning("The specified PI_AUDIT_CONTAINER_READ {0!s} is not readable.".format(self.read_module))

    @property
    def has_data(self):
        return any([x.has_data for x in self.write_modules])

    def log(self, param):
        """
        Call the log method for all writeable modules
        """
        for module in self.write_modules:
            module.log(param)

    def add_to_log(self, param, add_with_comma=False):
        """
        Call the add_to_log method for all writeable modules
        """
        for module in self.write_modules:
            module.add_to_log(param, add_with_comma)

    def add_policy(self, policyname):
        """
        Call the add_policy method for all writeable modules
        """
        for module in self.write_modules:
            module.add_policy(policyname)

    def search(self, search_dict, page_size=15, page=1, sortorder="asc",
               timelimit=None):
        """
        Call the search method for the one readable module
        """
        return self.read_module.search(search_dict, page_size=page_size, page=page,
                                       sortorder=sortorder, timelimit=timelimit)

    def get_count(self, search_dict, timedelta=None, success=None):
        """
        Call the count method for the one readable module
        """
        return self.read_module.get_count(search_dict, timedelta=timedelta, success=success)

    def csv_generator(self, param=None, user=None, timelimit=None):
        """
        Call the csv_generator method for the one readable module
        """
        return self.read_module.csv_generator(param=param, user=user,
                                              timelimit=timelimit)

    def get_total(self, param, AND=True, display_error=True, timelimit=None):
        """
        Call the total method for the one readable module
        """
        return self.read_module.get_total(param, AND=AND, display_error=display_error, timelimit=timelimit)

    def finalize_log(self):
        """
        Call the finalize method of all writeable audit modules
        """
        for module in self.write_modules:
            module.finalize_log()
