# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2018-11-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Remove the audit log based statistics
# 2016-12-20 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Restrict download to certain time
# 2015-07-16 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
#            Add statistics endpoint
# 2015-01-20 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Complete rewrite during flask migration
#            Try to provide REST API
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
"""
The audit REST API exposes the privacyIDEA audit log: a paginated search
endpoint and a CSV download endpoint. See :ref:`audit` for the conceptual
chapter and the available audit modules (SQL, logger, container).

All endpoints require admin authentication. Search is gated by the admin
policy action :ref:`policy_auditlog`; the CSV download by
:ref:`policy_auditlog_download`. Both endpoints honor the
:ref:`policy_auditlog_age` policy that limits how far back an admin may
look. The :ref:`policy_hide_audit_columns` policy is applied only to the
search endpoint, not to the CSV download.
"""
from flask import (Blueprint, request, current_app, stream_with_context)
from .lib.utils import (send_result, send_file)
from ..api.lib.prepolicy import prepolicy, check_base_action, auditlog_age, hide_audit_columns
from ..api.auth import admin_required
from ..lib.policies.actions import PolicyAction
from flask import g
import logging
from ..lib.audit import search, getAudit
from privacyidea.lib.utils import parse_timedelta
from ..lib.policies.helper import get_admin_audit_params

log = logging.getLogger(__name__)

audit_blueprint = Blueprint('audit_blueprint', __name__)


@audit_blueprint.route('/', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.AUDIT)
@prepolicy(auditlog_age, request)
@prepolicy(hide_audit_columns, request)
def search_audit():
    """
    Return a paginated page of audit entries. All filter parameters are
    accepted as query parameters; column names from the audit schema can be
    used directly as filter keys (``realm``, ``user``, ``serial``, ``action``,
    ``success``, ...). Filter values support the wildcard ``*``.

    Requires admin authentication and the policy action :ref:`policy_auditlog`.
    The :ref:`policy_auditlog_age` policy may shrink ``timelimit`` to the
    configured maximum, and :ref:`policy_hide_audit_columns` may strip
    configured columns from the response.

    **Example request**:

    .. sourcecode:: http

       GET /audit/?realm=realm1&page=1&page_size=15 HTTP/1.1
       Host: example.com
       Accept: application/json

    :query timelimit: only consider entries newer than this (e.g. ``1d``,
        ``2h``, ``30m``). Capped by the :ref:`policy_auditlog_age` policy.
    :query page: page number, 1-indexed.
    :query page_size: entries per page.
    :query sortname: column to sort by.
    :query sortorder: ``asc`` or ``desc``.
    :query: any audit column name as a filter key.
    :status 200: paginated audit dictionary in ``result.value`` with
        ``count``, ``current``, ``next``, ``prev``, ``auditdata``.
    """
    admin_params = get_admin_audit_params()
    audit_dict = search(current_app.config, request.all_data, admin_params)
    g.audit_object.log({'success': True})

    return send_result(audit_dict)


@audit_blueprint.route('/<csvfile>', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.AUDIT_DOWNLOAD)
@prepolicy(auditlog_age, request)
@admin_required
def download_csv(csvfile=None):
    """
    Stream the audit log as a CSV file. The path component is the desired
    download filename (e.g. ``audit.csv``); the actual filter is given by
    the query parameters, which use the same syntax as the search endpoint.

    Requires admin authentication and the policy action
    :ref:`policy_auditlog_download`. The :ref:`policy_auditlog_age` policy
    caps how far back the export may go. Hidden-column policies do **not**
    apply to the download — disallow downloading if you need that
    restriction.

    **Example request**:

    .. sourcecode:: http

       GET /audit/audit.csv?realm=realm1 HTTP/1.1
       Host: example.com
       Accept: text/csv

    :param csvfile: filename to use for the download.
    :query timelimit: only export entries newer than this. Capped by the
        :ref:`policy_auditlog_age` policy.
    :query: any audit column name as a filter key (same as for the search
        endpoint).
    :status 200: ``text/csv`` body containing the audit entries.
    """
    audit = getAudit(current_app.config)
    g.audit_object.log({'success': True})
    param = request.all_data
    admin_params = get_admin_audit_params()
    if "timelimit" in param:
        timelimit = parse_timedelta(param["timelimit"])
        del param["timelimit"]
    else:
        timelimit = None
    return send_file(stream_with_context(
        audit.csv_generator(param=param, admin_params=admin_params, timelimit=timelimit)), csvfile)
