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
log = logging.getLogger(__name__)
from privacyidea.lib.log import log_with
from privacyidea.lib.utils import parse_timedelta, get_module_class
from privacyidea.lib.framework import get_app_config_value

@log_with(log, log_entry=False)
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
    audit = get_module_class(audit_module, "Audit", "log")(config)
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

    pagination = audit.search(param, sortorder=sortorder, page=page,
                              page_size=page_size, timelimit=timelimit)

    ret = {"auditdata": pagination.auditdata,
           "prev": pagination.prev,
           "next": pagination.next,
           "current": pagination.page,
           "count": pagination.total}

    return ret


def find_authentication_attempts(audit_object, user_object, endpoint_name, timedelta=None, success=None):
    """
    Search the audit log for authentication attempts at a given endpoint for a given user and
    return the number of authentication attempts matching the given criteria.
    This function also handles the case of authentication attempts at the /auth endpoint in case
    the user is an external admin (i.e. the user realm is contained in SUPERUSER_REALM).
    :param audit_object: an audit object
    :param user_object: a User object, might be an external admin
    :param endpoint_name: the endpoint, normally "/validate/check" or "/auth"
    :param timedelta: optionally, the timedelta in which authentication attempts should be searched
    :param success: optionally, only search for successful/unsuccessful authentication attempts
    :return: number of matching authentication attempts in the audit log
    :rtype: int
    """
    superuser_realms = get_app_config_value("SUPERUSER_REALM", [])
    search_dict = {"realm": user_object.realm,
                   "action": "%" + endpoint_name}
    if endpoint_name == '/auth' and user_object.realm in superuser_realms:
        # Audit entries logging authentication attempts of external administrator at /auth
        # store the username in the "administrator" field
        search_dict["administrator"] = user_object.login
    else:
        search_dict["user"] = user_object.login
    return audit_object.get_count(search_dict, success=success, timedelta=timedelta)
