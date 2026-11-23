# (c) NetKnights GmbH 2024,  https://netknights.it
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
# SPDX-FileCopyrightText: 2025 Paul Lettich <paul.lettich@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
"""This is the BaseClass for audit trails

The audit is supposed to work like this. First we need to create an audit
object. E.g. this can be done in the before_request:

    g.audit_object = getAudit(file_config)

During the request, the g.audit_object can be used to add audit information:

    g.audit_object.log({"client": "123.2.3.4", "action": "validate/check"})

Thus, at many different places in the code, audit information can be added to
the audit object.
Finally, the audit_object needs to be stored to the audit storage. So we call::

    g.audit_object.finalize_log()

which creates a signature of the audit data and writes the data to the audit
storage.
"""

import datetime
import logging
import re
from collections import OrderedDict

from privacyidea.config import ConfigKey
from privacyidea.lib.auditmodules.base import TimeInterval
from privacyidea.lib.error import ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.params import parse_timestamp
from privacyidea.lib.utils import naive_utc, parse_timedelta, get_module_class

log = logging.getLogger(__name__)


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
    audit_module = config.get(ConfigKey.AUDIT_MODULE)
    audit = get_module_class(audit_module, "Audit", "log")(config, startdate)
    return audit


# Whitespace before an offset at the end of a timestamp, as in the readable form "2026-11-05 00:00:00 +01:00"
_SPACE_BEFORE_OFFSET = re.compile(r"\s+(?=(Z|[+-]\d{2}(:?\d{2})?)$)")


def _read_interval_bound(value: str, key: str) -> datetime.datetime | None:
    """
    Read one bound of a time interval as naive UTC datetime. An empty bound is None, a bound without
    an offset is UTC.

    :raises ParameterError: if the bound is not a valid ISO 8601 timestamp
    """
    value = _SPACE_BEFORE_OFFSET.sub("", value.strip())
    if not value:
        return None
    return naive_utc(parse_timestamp(value, key))


def read_time_intervals(param: dict) -> None:
    """
    Replace a value of ``startdate`` or ``date`` that is an ISO 8601 time interval ``start/end`` in the
    filter parameters by a :class:`~privacyidea.lib.auditmodules.base.TimeInterval`. A value without a
    ``/`` stays a text filter. Either end may be empty, a ``/`` alone is no filter and is removed. A bound
    is an ISO 8601 timestamp, also in the readable form with spaces, and a bound without an offset is
    UTC. An end in whole seconds includes its whole second.

    :param param: The filter parameters, changed in place
    :raises ParameterError: if an interval has more than one ``/``, a leading ``!``, a ``*``, a bound
        that is not a valid ISO 8601 timestamp or a start after its end
    """
    for key in ("startdate", "date"):
        value = param.get(key)
        if not isinstance(value, str) or "/" not in value:
            continue
        value = value.strip()
        if value.count("/") > 1 or value.startswith("!") or "*" in value:
            raise ParameterError(f"Invalid ISO 8601 time interval for {key}: {value!r}. A time interval "
                                 f"is start/end and can not be negated or contain wildcards.")
        start_value, end_value = value.split("/")
        start = _read_interval_bound(start_value, key)
        end = _read_interval_bound(end_value, key)
        if start is None and end is None:
            param.pop(key)
            continue
        if start is not None and end is not None and start > end:
            raise ParameterError(f"Invalid ISO 8601 time interval for {key}: {value!r}. The start of a time "
                                 f"interval can not lie after its end.")
        end_exclusive = end is not None and end.microsecond == 0
        if end_exclusive:
            end += datetime.timedelta(seconds=1)
        param[key] = TimeInterval(start, end, end_exclusive)


@log_with(log)
def search(config: dict, param: dict | None = None, admin_params: dict | None = None,
           exact_params: dict[str, str] | None = None) -> dict:
    """
    Returns a list of audit entries, supports pagination

    :param config: The config entries from the file config
    :param exact_params: Filter parameters that are compared for equality, without the "!" and "*" operators of
        *param*, such as the identity of a user
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
        page = max(1, int(param["page"]))
        del param["page"]
    if "page_size" in param:
        page_size = int(param["page_size"])
        if page_size < 1:
            log.info("Requested Audit-Log page size is negative. Setting it to 15")
            page_size = 15
        del param["page_size"]
    if "timelimit" in param:
        timelimit = parse_timedelta(param["timelimit"])
        del param["timelimit"]
    read_time_intervals(param)
    if "hidden_columns" in param:
        hidden_columns = param["hidden_columns"]
        del param["hidden_columns"]

    pagination = audit.search(param, admin_params=admin_params, sortorder=sortorder, page=page,
                              page_size=page_size, timelimit=timelimit, exact_params=exact_params)

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
