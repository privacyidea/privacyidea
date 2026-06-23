# (c) NetKnights GmbH 2026,  https://netknights.it
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
#
# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from datetime import datetime, timezone

from dateutil.parser import isoparse
from flask import Blueprint, request, g

from privacyidea.api.auth import admin_required, user_required
from privacyidea.api.lib.prepolicy import prepolicy, check_base_action
from privacyidea.api.lib.utils import send_result
from privacyidea.lib.auth import ROLE
from privacyidea.lib.conditional_access.authentication_log import (get_authentication_logs_paginate,
                                                                   delete_authentication_logs,
                                                                   AuthenticationLogVisibilityScope,
                                                                   DEFAULT_PAGE_SIZE)
from privacyidea.lib.log import log_with
from privacyidea.lib.params import get_optional
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policies.helper import get_authentication_log_visibility_scopes
from privacyidea.lib.utils import parse_timedelta, is_true

log = logging.getLogger(__name__)

authentication_log_blueprint = Blueprint("authentication_log_blueprint", __name__)

# Filter parameters that map 1:1 to a get_authentication_logs_paginate keyword argument.
_FILTER_PARAMS = ["resolver", "uid", "realm", "username", "event_type", "source_ip", "serial",
                  "transaction_id", "previous_transaction_id", "client_label"]


def _split_csv(value: str | None) -> list[str] | None:
    """
    Split a comma-separated filter value into a list of non-empty, stripped entries (so a single value yields a
    one-element list and several values can be matched at once). Returns ``None`` for a missing or empty value, i.e.
    no filter on that field.
    """
    if value is None:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


def _positive_int(value: int | str, default: int) -> int:
    """
    Parse a positive paging parameter, falling back to *default* for a missing, non-numeric or non-positive value.
    This keeps a bad ``page``/``page_size`` from casting straight to a negative SQL offset or an empty/undefined limit.
    """
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 1 else default


@authentication_log_blueprint.route("/", methods=["GET"])
@user_required
@prepolicy(check_base_action, request, PolicyAction.AUTHENTICATION_LOG_READ)
@log_with(log)
def get_authentication_log():
    """
    Return a paginated, filtered page of authentication-log entries.

    Requires the policy action :ref:`policy_authentication_log_read`. An **admin** with that action set in the admin
    scope may read the log; if the policy is scoped to realms, resolvers and/or users, only entries matching that
    scope are returned. A **user** with the action set in the user scope may read only their own entries.

    Each of ``resolver``, ``uid``, ``realm``, ``username``, ``event_type``, ``source_ip``, ``serial``,
    ``transaction_id``, ``previous_transaction_id`` and ``client_label`` may be passed as a query parameter to filter
    on it. A value may be a comma-separated list (e.g. ``event_type=MFA_FAIL,PIN_FAIL``), matching entries that equal
    any of the values. A value may contain a ``*`` wildcard (e.g. ``serial=TOTP*``) to match by prefix/pattern instead
    of exactly.

    :query page: page number, 1-indexed (default 1).
    :query page_size: entries per page (default 15).
    :query sort_column: column to sort by (id, timestamp, event_type, realm, username, source_ip, serial).
    :query sort_order: ``asc`` or ``desc`` (default ``desc``).
    :query timelimit: only entries newer than now minus this delta (e.g. ``1d``, ``2h``). Overrides ``start``.
    :query start: only entries at/after this ISO 8601 timestamp.
    :query end: only entries at/before this ISO 8601 timestamp.
    :query include_own: if set, a scoped admin also sees their own entries (matched by username + realm), in
        addition to the policy scope (ignored for users, who already see only their own).
    :status 200: paginated result in ``result.value`` with ``auth_logs``, ``count``, ``current``, ``prev``, ``next``.
    """
    params = request.all_data
    filters = {name: _split_csv(get_optional(params, name)) for name in _FILTER_PARAMS}

    timelimit = get_optional(params, "timelimit")
    if timelimit:
        start_timestamp = datetime.now(timezone.utc) - parse_timedelta(timelimit)
    else:
        start = get_optional(params, "start")
        start_timestamp = isoparse(start) if start else None
    end = get_optional(params, "end")
    end_timestamp = isoparse(end) if end else None

    visibility_scopes = get_authentication_log_visibility_scopes(PolicyAction.AUTHENTICATION_LOG_READ)
    # A scoped admin may opt in to also see their own entries (username + realm), added to the policy scope as an
    # extra OR alternative. (A user already sees only their own entries, so include_own is irrelevant for them.)
    if (g.logged_in_user["role"] == ROLE.ADMIN and visibility_scopes is not None
            and is_true(get_optional(params, "include_own"))):
        own_realm = g.logged_in_user.get("realm")
        own_username = g.logged_in_user.get("username")
        if own_realm and own_username:
            visibility_scopes = visibility_scopes + [
                AuthenticationLogVisibilityScope(realms=[own_realm], resolvers=[], usernames=[own_username])]

    result = get_authentication_logs_paginate(
        **filters,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        visibility_scopes=visibility_scopes,
        page=_positive_int(get_optional(params, "page"), default=1),
        page_size=_positive_int(get_optional(params, "page_size"), default=DEFAULT_PAGE_SIZE),
        sort_column=get_optional(params, "sort_column", default="id"),
        sort_order=get_optional(params, "sort_order", default="desc"))

    g.audit_object.log({"success": True})
    return send_result(result.to_dict())


@authentication_log_blueprint.route("/", methods=["DELETE"])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.AUTHENTICATION_LOG_DELETE)
@log_with(log)
def delete_authentication_log():
    """
    Delete authentication-log entries matching the given filters and return the number deleted.

    Requires admin authentication and the policy action :ref:`policy_authentication_log_delete`. If that policy is
    scoped to realms, resolvers and/or users, only entries matching that scope are deleted. At least one filter must
    be given; an unfiltered request is rejected so the whole log cannot be wiped by accident. To delete entries older
    than a point in time, pass ``end`` (entries with a timestamp at or before it).

    Each of ``resolver``, ``uid``, ``realm``, ``username``, ``event_type``, ``source_ip``, ``serial``,
    ``transaction_id``, ``previous_transaction_id`` and ``client_label`` may be passed as a query parameter to filter
    on it. A value may be a comma-separated list (e.g. ``event_type=MFA_FAIL,PIN_FAIL``), matching entries that equal
    any of the values. A value may contain a ``*`` wildcard (e.g. ``serial=TOTP*``) to match by prefix/pattern instead
    of exactly.

    :query start: only entries at/after this ISO 8601 timestamp.
    :query end: only entries at/before this ISO 8601 timestamp (i.e. "older than").
    :status 200: ``result.value`` is the number of deleted entries.
    :status 400: no filter was given.
    """
    params = request.all_data
    filters = {name: _split_csv(get_optional(params, name)) for name in _FILTER_PARAMS}
    start = get_optional(params, "start")
    end = get_optional(params, "end")

    count = delete_authentication_logs(
        **filters,
        start_timestamp=isoparse(start) if start else None,
        end_timestamp=isoparse(end) if end else None,
        visibility_scopes=get_authentication_log_visibility_scopes(PolicyAction.AUTHENTICATION_LOG_DELETE))

    g.audit_object.log({"success": True})
    return send_result(count)
