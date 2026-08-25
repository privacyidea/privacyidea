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
from dateutil.parser import isoparse
from flask import Blueprint, request, g

from privacyidea.api.auth import user_required
from privacyidea.api.lib.prepolicy import prepolicy, check_base_action
from privacyidea.api.lib.utils import send_result
from privacyidea.lib.auth import ROLE
from privacyidea.lib.conditional_access.authentication_event_types import (AuthEventType, AuthEventReason,
                                                                           outcome_of)
from privacyidea.lib.conditional_access.authentication_log import (get_authentication_logs_paginate,
                                                                   AuthenticationLogVisibilityScope,
                                                                   AuthLogUserRole,
                                                                   DEFAULT_PAGE_SIZE)
from privacyidea.lib.conditional_access.conditions import AUTHENTICATING_ENDPOINTS
from privacyidea.lib.log import log_with
from privacyidea.lib.params import get_optional
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policies.helper import get_policy_visibility_scopes
from privacyidea.lib.utils import is_true

log = logging.getLogger(__name__)

authentication_log_blueprint = Blueprint("authentication_log_blueprint", __name__)

# The list-valued filter query parameters, mapped to the get_authentication_logs_paginate keyword argument each one
# feeds. Every one of them takes a list of values, so the query parameter is plural while the library keyword names the
# single field it matches. The ca_* ones filter on the entry's conditional-access outcomes rather than on a column of
# its own row; ca_dry_run is parsed separately because it is a boolean, not a list of values.
_FILTER_PARAMS = {"resolvers": "resolver", "uids": "uid", "realms": "realm", "usernames": "username",
                  "user_roles": "user_role", "event_types": "event_type", "reasons": "reason",
                  "source_ips": "source_ip",
                  "serials": "serial", "transaction_ids": "transaction_id", "attempt_ids": "attempt_id",
                  "client_labels": "client_label", "endpoints": "endpoint",
                  "ca_action_types": "ca_action_type",
                  "ca_policy_names": "ca_policy_name"}


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

    Each of ``resolvers``, ``uids``, ``realms``, ``usernames``, ``user_roles``, ``event_types``, ``reasons``,
    ``source_ips``, ``serials``, ``transaction_ids``, ``attempt_ids``, ``client_labels`` and ``endpoints`` may be
    passed as a query
    parameter to filter on it. A value may be a comma-separated list (e.g. ``event_types=MFA_FAIL,PIN_FAIL``), matching
    entries that equal any of the values. A value may contain a ``*`` wildcard (e.g. ``serials=TOTP*``) to match by
    prefix/pattern instead of exactly. Note, using wildcards filtering is always case-insensitive.

    :query page: page number, 1-indexed (default 1).
    :query page_size: entries per page (default 15).
    :query sort_column: column to sort by (id, timestamp, event_type, reason, resolver, uid, realm, username,
        source_ip, client_label, endpoint, serial, transaction_id, attempt_id).
    :query sort_order: ``asc`` or ``desc`` (default ``desc``).
    :query start_time: only entries at/after this ISO 8601 timestamp.
    :query end_time: only entries at/before this ISO 8601 timestamp.
    :query case_insensitive: if set, plain (non-wildcard) filter values match case-insensitively (wildcard values
        always match case-insensitively).
    :query ca_action_types: only entries with a conditional-access outcome of one of these action types
        (e.g. ``LOCK_USER_TEMPORARY``). Takes a list and a wildcard like the other filters, so ``ca_action_types=*``
        means "conditional access acted on this request at all".
    :query ca_policy_names: only entries with an outcome recorded for one of these conditional-access policy names.
    :query ca_dry_run: ``true`` for only entries with a dry-run outcome, ``false`` for only entries with an enforced
        one; omit it to get both. The three ``ca_*`` filters apply to the *same* outcome, so an entry matches when one
        of its outcomes satisfies all of them.
    :status 200: paginated result in ``result.value`` with ``auth_logs``, ``count``, ``current``, ``prev``, ``next``.
    """
    params = request.all_data
    filters = {keyword: _split_csv(get_optional(params, param)) for param, keyword in _FILTER_PARAMS.items()}
    # A tri-state: absent (or empty) does not filter, so that "both" needs no value of its own.
    ca_dry_run = get_optional(params, "ca_dry_run")
    filters["ca_dry_run"] = is_true(ca_dry_run) if ca_dry_run not in (None, "") else None

    start_time = get_optional(params, "start_time")
    start_time = isoparse(start_time) if start_time else None
    end_time = get_optional(params, "end_time")
    end_time = isoparse(end_time) if end_time else None

    visibility_scopes = get_policy_visibility_scopes(PolicyAction.AUTHENTICATION_LOG_READ)
    # A scoped admin always also sees their own entries, added to the policy scope as an extra OR alternative;
    # irrelevant for a user, who already sees only their own entries.
    if g.logged_in_user["role"] == ROLE.ADMIN and visibility_scopes is not None:
        own_realm = g.logged_in_user.get("realm")
        own_username = g.logged_in_user.get("username")
        if own_username and not own_realm:
            # no realm -> local admin
            visibility_scopes = visibility_scopes + [
                AuthenticationLogVisibilityScope(realms=[], resolvers=[], usernames=[own_username],
                                                 user_roles=[str(AuthLogUserRole.ADMIN_INTERNAL)])]
        elif own_username and own_realm:
            # username + realm -> external admin
            visibility_scopes = visibility_scopes + [
                AuthenticationLogVisibilityScope(realms=[own_realm], resolvers=[], usernames=[own_username])]

    result = get_authentication_logs_paginate(
        **filters,
        start_time=start_time,
        end_time=end_time,
        case_insensitive=is_true(get_optional(params, "case_insensitive")),
        visibility_scopes=visibility_scopes,
        page=_positive_int(get_optional(params, "page"), default=1),
        page_size=_positive_int(get_optional(params, "page_size"), default=DEFAULT_PAGE_SIZE),
        sort_column=get_optional(params, "sort_column", default="id"),
        sort_order=get_optional(params, "sort_order", default="desc"))

    g.audit_object.log({"success": True})
    return send_result(result.to_dict())


@authentication_log_blueprint.route("/reasons", methods=["GET"])
@user_required
@prepolicy(check_base_action, request, PolicyAction.AUTHENTICATION_LOG_READ)
@log_with(log)
def get_authentication_log_reasons():
    """
    Return the list of all defined authentication-log reasons.

    Requires the policy action :ref:`policy_authentication_log_read`, like the log read endpoint. The list is the
    authoritative set of :class:`AuthEventReason` values - why an event came out the way it did - exposed for the same
    reason the event types are: so the WebUI offers the vocabulary it can filter on instead of redefining it. It does
    not depend on the caller or on any logged data.

    :status 200: ``result.value`` is a list of reason names, in definition order.
    """
    reasons = [str(reason) for reason in AuthEventReason]
    g.audit_object.log({"success": True})
    return send_result(reasons)


@authentication_log_blueprint.route("/endpoints", methods=["GET"])
@user_required
@prepolicy(check_base_action, request, PolicyAction.AUTHENTICATION_LOG_READ)
@log_with(log)
def get_authentication_log_endpoints():
    """
    Return the list of endpoints an authentication can arrive at.

    Requires the policy action :ref:`policy_authentication_log_read`, like the log read endpoint. The list is
    :data:`AUTHENTICATING_ENDPOINTS`, the request paths that record an authentication-log row, so the WebUI offers the
    ``endpoints`` filter as a selection instead of a path typed by hand. It is not derived from the logged data: a
    path an admin can select but that nothing has hit yet still belongs in the list, and a filter may still name a
    value of its own (a wildcard such as ``/validate/*``, or the path of a route that has since been renamed).

    :status 200: ``result.value`` is a sorted list of request paths.
    """
    g.audit_object.log({"success": True})
    return send_result(sorted(AUTHENTICATING_ENDPOINTS))


@authentication_log_blueprint.route("/eventtypes", methods=["GET"])
@user_required
@prepolicy(check_base_action, request, PolicyAction.AUTHENTICATION_LOG_READ)
@log_with(log)
def get_authentication_log_event_types():
    """
    Return the list of all defined authentication-log event types with their outcome.

    Requires the policy action :ref:`policy_authentication_log_read` (in the admin or user scope, like the log read
    endpoint). The list is the authoritative set of :class:`AuthEventType` values, each with its
    :class:`AuthEventOutcome` (``success`` / ``failure`` / ``pending``), exposed so the WebUI does not have to
    redefine it. It does not depend on the caller or on any logged data.

    :status 200: ``result.value`` is a list of ``{"name", "outcome"}`` objects, in definition order.
    """
    event_types = [{"name": str(event_type), "outcome": str(outcome_of(event_type))}
                   for event_type in AuthEventType]
    g.audit_object.log({"success": True})
    return send_result(event_types)
