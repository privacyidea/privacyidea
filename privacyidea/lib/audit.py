# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
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
log = logging.getLogger(__name__)
from privacyidea.lib.log import log_with


@log_with(log)
def getAuditClass(packageName, className):
    """
    helper method to load the Audit class from a given
    package in literal:

    example:

        getAuditClass("privacyidea.lib.auditmodules.sqlaudit", "Audit")

    check:
        checks, if the log method exists
        if not an error is thrown

    """
    mod = __import__(packageName, globals(), locals(), [className])
    klass = getattr(mod, className)
    log.debug("klass: %s" % klass)
    if not hasattr(klass, "log"):  # pragma: no cover
        raise NameError("Audit AttributeError: " + packageName + "." +
                        className + " instance has no attribute 'log'")
    return klass


@log_with(log)
def getAudit(config):
    """
    This wrapper function creates a new audit object based on the config
    from the config file. The config file entry could look like this:

        PI_AUDIT_MODULE = privacyidea.lib.auditmodules.sqlaudit

    Each audit module (at the moment only SQL) has its own additional config
    entries.

    :param config: The config entries from the file config
    :return: Audit Object
    """
    audit_module = config.get("PI_AUDIT_MODULE")
    audit = getAuditClass(audit_module, "Audit")(config)
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

    pagination = audit.search(param, sortorder=sortorder, page=page,
                              page_size=page_size)

    ret = {"auditdata": pagination.auditdata,
           "prev": pagination.prev,
           "next": pagination.next,
           "current": pagination.page,
           "count": pagination.total}

    return ret
