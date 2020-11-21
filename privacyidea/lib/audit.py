# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2016-11-29 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add timelimit, to only display recent entries
#  2014-10-17 Fix the empty result problem
#             Cornelius Kölbel, <cornelius@privacyidea.org>
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
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
__doc__="""This is the BaseClass for audit trails

The audit is supposed to work like this. First we need to create an audit
object. E.g. this can be done in the before_request:

    g.audit_object = getAudit(file_config)

During the request, the g.audit_object can be used to add audit information:

    g.audit_object.log({"client": "123.2.3.4", "action": "validate/check"})

Thus at many different places in the code, audit information can be added to
the audit object.
Finally the audit_object needs to be stored to the audit storage. So we call:

    g.audit_object.finalize_log()

which creates a signature of the audit data and writes the data to the audit
storage.
"""

import logging
from collections import OrderedDict

log = logging.getLogger(__name__)
from privacyidea.lib.log import log_with
from privacyidea.lib.utils import parse_timedelta, get_module_class


@log_with(log, log_entry=False)
def getAudit(config, startdate=None):
    """
    This wrapper function creates a new audit object based on the config
    from the config file. The config file entry could look like this:

        PI_AUDIT_MODULE = privacyidea.lib.auditmodules.sqlaudit

    Each audit module (at the moment only SQL) has its own additional config
    entries.

    :param config: The config entries from the file config
    :param startdate: The datetime startdate of the request
    :return: Audit Object
    """
    audit_module = config.get("PI_AUDIT_MODULE")
    audit = get_module_class(audit_module, "Audit", "log")(config, startdate)
    return audit


@log_with(log)
def search(config, param=None, user=None):
    """
    Returns a list of audit entries, supports pagination

    :param config: The config entries from the file config
    :return: Audit dictionary with information about the previous and next
    pages.
    """
    audit = getAudit(config)
    sortorder = "desc"
    page_size = 15
    page = 1
    timelimit = None
    hidden_columns = []
    # The filtering dictionary
    param = param or {}
    # special treatment for:
    # sortorder, page, pagesize
    if "sortorder" in param:
        sortorder = param["sortorder"]
        del param["sortorder"]
    if "page" in param:
        page = param["page"]
        del param["page"]
    if "page_size" in param:
        page_size = param["page_size"]
        del param["page_size"]
    if "timelimit" in param:
        timelimit = parse_timedelta(param["timelimit"])
        del param["timelimit"]
    if "hidden_columns" in param:
        hidden_columns = param["hidden_columns"]
        del param["hidden_columns"]

    pagination = audit.search(param, sortorder=sortorder, page=page,
                              page_size=page_size, timelimit=timelimit)

    # delete hidden columns from response
    if hidden_columns:
        for i in range(len(pagination.auditdata)):
            pagination.auditdata[i] = OrderedDict({audit_col: value for audit_col, value in
                                                   pagination.auditdata[i].items()
                                                   if audit_col not in hidden_columns})
    visible_columns = [col for col in audit.available_audit_columns if col not in hidden_columns]

    ret = {"auditdata": pagination.auditdata,
           "auditcolumns": visible_columns,
           "prev": pagination.prev,
           "next": pagination.next,
           "current": pagination.page,
           "count": pagination.total}

    return ret
