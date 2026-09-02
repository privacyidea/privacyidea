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
from flask import Blueprint, request, g

from privacyidea.api.auth import user_required
from privacyidea.api.lib.prepolicy import prepolicy, check_base_action
from privacyidea.api.lib.utils import send_result
from privacyidea.lib.auth import ROLE
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType, outcome_of
from privacyidea.lib.conditional_access.authentication_log import (get_authentication_log_statistics,
                                                                   get_authentication_logs_paginate,
                                                                   AuthenticationLogVisibilityScope,
                                                                   AuthLogUserRole,
                                                                   DEFAULT_PAGE_SIZE,
                                                                   DEFAULT_STATISTICS_BINS)
from privacyidea.lib.log import log_with
from privacyidea.lib.params import get_optional, get_optional_timestamp, get_required_timestamp
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policies.helper import get_policy_visibility_scopes
from privacyidea.lib.utils import is_true

log = logging.getLogger(__name__)

authentication_log_blueprint = Blueprint("authentication_log_blueprint", __name__)

# Filters naming a column of the authentication_log row itself.
_ROW_FILTER_PARAMS = ["resolver", "uid", "realm", "username", "user_role", "event_type", "source_ip", "serial",
                      "transaction_id", "attempt_id", "client_label"]
# The same filters as the statistics endpoint names them, and passes straight through to the lib. Plural, because each
# takes a list of values: the name says so to the caller as much as it does in the signature behind it.
_STATISTICS_FILTER_PARAMS = ["resolvers", "uids", "realms", "usernames", "user_roles", "event_types", "source_ips",
                             "serials", "transaction_ids", "attempt_ids", "client_labels"]
# The ca_* filters match the entry's conditional-access outcomes rather than a column of its own row, so only the
# listing offers them; ca_dry_run is parsed separately because it is a boolean, not a list of values.
_OUTCOME_FILTER_PARAMS = ["ca_action_type", "ca_policy_name"]
# Each filter parameter maps 1:1 to a get_authentication_logs_paginate keyword argument.
_FILTER_PARAMS = _ROW_FILTER_PARAMS + _OUTCOME_FILTER_PARAMS


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


def _get_visibility_scopes() -> list[AuthenticationLogVisibilityScope] | None:
    """
    Return the visibility scopes restricting what the logged-in caller may read, or ``None`` for no restriction.

    Shared by every endpoint reading the log: a divergence here would not fail loudly, it would quietly show one
    endpoint entries the other hides, so the aggregate and the listing must derive the restriction the same way.

    A scoped admin always also sees their own entries, added to the policy scope as an extra OR alternative. A local
    admin has no realm, so their own entries are matched by username plus the internal-admin role instead.
    """
    visibility_scopes = get_policy_visibility_scopes(PolicyAction.AUTHENTICATION_LOG_READ)
    if g.logged_in_user["role"] != ROLE.ADMIN or visibility_scopes is None:
        return visibility_scopes
    own_realm = g.logged_in_user.get("realm")
    own_username = g.logged_in_user.get("username")
    if own_username and not own_realm:
        return visibility_scopes + [
            AuthenticationLogVisibilityScope(realms=[], resolvers=[], usernames=[own_username],
                                             user_roles=[str(AuthLogUserRole.ADMIN_INTERNAL)])]
    if own_username and own_realm:
        return visibility_scopes + [
            AuthenticationLogVisibilityScope(realms=[own_realm], resolvers=[], usernames=[own_username])]
    return visibility_scopes


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

    Each of ``resolver``, ``uid``, ``realm``, ``username``, ``user_role``, ``event_type``, ``source_ip``, ``serial``,
    ``transaction_id``, ``attempt_id`` and ``client_label`` may be passed as a query
    parameter to filter on it. A value may be a comma-separated list (e.g. ``event_type=MFA_FAIL,PIN_FAIL``), matching
    entries that equal any of the values. A value may contain a ``*`` wildcard (e.g. ``serial=TOTP*``) to match by
    prefix/pattern instead of exactly. Note, using wildcards filtering is always case-insensitive.

    :query page: page number, 1-indexed (default 1).
    :query page_size: entries per page (default 15).
    :query sort_column: column to sort by (id, timestamp, event_type, resolver, uid, realm, username, source_ip,
        client_label, serial, transaction_id, attempt_id).
    :query sort_order: ``asc`` or ``desc`` (default ``desc``).
    :query start_time: only entries at/after this ISO 8601 timestamp.
    :query end_time: only entries at/before this ISO 8601 timestamp.
    :query case_insensitive: if set, plain (non-wildcard) filter values match case-insensitively (wildcard values
        always match case-insensitively).
    :query ca_action_type: only entries with a conditional-access outcome of this action type (e.g. ``LOCK_USER``).
        Takes a list and a wildcard like the other filters, so ``ca_action_type=*`` means "conditional access acted on
        this request at all".
    :query ca_policy_name: only entries with an outcome recorded for this conditional-access policy name.
    :query ca_dry_run: ``true`` for only entries with a dry-run outcome, ``false`` for only entries with an enforced
        one; omit it to get both. The three ``ca_*`` filters apply to the *same* outcome, so an entry matches when one
        of its outcomes satisfies all of them.
    :status 200: paginated result in ``result.value`` with ``auth_logs``, ``count``, ``current``, ``prev``, ``next``.
    """
    params = request.all_data
    filters = {name: _split_csv(get_optional(params, name)) for name in _FILTER_PARAMS}
    # A tri-state: absent (or empty) does not filter, so that "both" needs no value of its own.
    ca_dry_run = get_optional(params, "ca_dry_run")
    filters["ca_dry_run"] = is_true(ca_dry_run) if ca_dry_run not in (None, "") else None

    start_time = get_optional_timestamp(params, "start_time")
    end_time = get_optional_timestamp(params, "end_time")

    visibility_scopes = _get_visibility_scopes()

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


@authentication_log_blueprint.route("/statistics", methods=["GET"])
@user_required
@prepolicy(check_base_action, request, PolicyAction.AUTHENTICATION_LOG_READ)
@log_with(log)
def get_authentication_log_statistics_endpoint():
    """
    Return a summary of the authentication log over a time window, as counts of authentication **attempts** grouped by
    the event type that classifies each of them and bucketed over the window.

    Requires the policy action :ref:`policy_authentication_log_read` and is restricted to the same entries the log
    listing shows the caller, so an admin scoped to a realm counts only that realm's attempts.

    The rows sharing an ``attempt_id`` are one attempt and are counted once, classified by the event that ended them:
    a challenge-response login writes several rows but is a single successful attempt. ``event_type`` therefore
    selects attempts that *ended* that way, rather than every attempt that passed through such an event.

    The attempts counted may be filtered on any column of the classifying row: ``resolvers``, ``uids``, ``realms``,
    ``usernames``, ``user_roles``, ``event_types``, ``source_ips``, ``serials``, ``transaction_ids``, ``attempt_ids``
    and ``client_labels``. Each is named in the plural because it takes a comma-separated list of values and matches
    an attempt equal to any of them, a value containing a ``*`` wildcard matching by pattern instead. The ``ca_*``
    filters are not offered: they match the conditional-access outcomes of a request rather than the attempt itself.

    :query start_time: start of the window, an ISO 8601 timestamp (required).
    :query end_time: end of the window, an ISO 8601 timestamp (required). Both ends are inclusive.
    :query bins: how many equal-width buckets to split the window into, between 1 and 100 (default 48). More than the
        maximum is rejected with a 400 naming the limit rather than quietly reduced, so a caller is never handed a
        coarser resolution than it asked for without being told. A value that is not a positive number at all falls
        back to the default, as ``page_size`` does on the listing.
    :query case_insensitive: if set, plain (non-wildcard) filter values match case-insensitively.
    :status 200: ``result.value`` holds ``window`` (``start_time``, ``end_time``, ``total``), ``bins`` (``count`` and
        the ``starts`` of each bucket) and ``events``, one entry per classification present in the window with its
        ``event_type``, ``outcome``, per-bucket ``counts`` and window ``total``, most frequent first.
    """
    params = request.all_data
    filters = {name: _split_csv(get_optional(params, name)) for name in _STATISTICS_FILTER_PARAMS}

    result = get_authentication_log_statistics(
        **filters,
        start_time=get_required_timestamp(params, "start_time"),
        end_time=get_required_timestamp(params, "end_time"),
        bins=_positive_int(get_optional(params, "bins"), default=DEFAULT_STATISTICS_BINS),
        case_insensitive=is_true(get_optional(params, "case_insensitive")),
        visibility_scopes=_get_visibility_scopes())

    g.audit_object.log({"success": True})
    return send_result(result.to_dict())


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
