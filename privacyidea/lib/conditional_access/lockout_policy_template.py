# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
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
"""
Ready-made conditional-access lockout policy templates.

The templates are a catalog of default lockout policies.
Each is a :class:`LockoutPolicyTemplate` constant referencing the :class:`AuthEventType`
/ :class:`LockoutAction` members directly (so a renamed event type or action
fails at import, not silently at runtime); ``policy`` is a full payload for
:func:`~privacyidea.lib.conditional_access.lockout_policy.create_lockout_policy`.
The shipped set is the single :data:`_TEMPLATES` tuple - to add a template,
define a constant and add it there.

The REST API returns the whole catalog in one call
(:func:`list_lockout_policy_templates`); a client prefills a policy from a
template and submits it as a normal create request.
"""
import copy
import logging
from dataclasses import dataclass

from privacyidea.lib import lazy_gettext
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType, CountMode
from privacyidea.lib.conditional_access.engine import LockoutAction, LockoutTarget
from privacyidea.lib.log import log_with

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class LockoutPolicyTemplate:
    """
    One shipped lockout policy template.

    :ivar key: stable catalog identifier
    :ivar description: a ``lazy_gettext`` string, translated when serialized
    :ivar policy: the create-policy payload (see
        :mod:`~privacyidea.lib.conditional_access.lockout_policy`)
    """
    key: str
    description: object
    policy: dict


PASSWORD_BRUTEFORCE = LockoutPolicyTemplate(
    key="password_bruteforce",
    description=lazy_gettext("Lock a single user after repeated wrong passwords or PINs (password brute-force)."),
    policy={
        "name": "Password Brute-Force",
        "time_window_seconds": 900,
        "enabled": True,
        "dry_run": False,
        "priority": 1,
        "target": LockoutTarget.USER,
        "counter_types_to_track": [AuthEventType.PASSWORD_FAIL,
                                   AuthEventType.PIN_FAIL],
        "stages": [
            {"failure_threshold": 10, "priority": 1,
             "actions": [{"action_type": LockoutAction.LOCK_USER,
                          "action_value": {"duration_seconds": 900}}]},
        ],
    })

MFA_BRUTEFORCE = LockoutPolicyTemplate(
    key="mfa_bruteforce",
    description=lazy_gettext("Progressively lock a user whose password is correct "
                             "but whose second factor keeps failing (MFA brute-force)."),
    policy={
        "name": "MFA Brute-Force (Password Compromised)",
        "time_window_seconds": 3600,
        "enabled": True,
        "dry_run": False,
        "priority": 1,
        "target": LockoutTarget.USER,
        "counter_types_to_track": [AuthEventType.MFA_FAIL],
        "stages": [
            {"failure_threshold": 3, "priority": 1,
             "actions": [{"action_type": LockoutAction.LOCK_USER,
                          "action_value": {"duration_seconds": 600}}]},
            {"failure_threshold": 5, "priority": 2,
             "actions": [
                 {"action_type": LockoutAction.LOCK_USER,
                  "action_value": {"duration_seconds": 1800}},
                 {"action_type": LockoutAction.EMAIL_ADMIN,
                  "action_value": {
                      "smtp_identifier": "",
                      "recipient_group": "internal_admins",
                      "subject": "[privacyIDEA] MFA brute-force detected for {username}",
                      "body": ("User {username}@{realm} (resolver {resolver}) from "
                               "{client_ip} tripped policy {policy}: {count}/{threshold} "
                               "{event_type} events. Time: {time}.")}},
             ]},

            {"failure_threshold": 10, "priority": 3,
             "actions": [
                 {"action_type": LockoutAction.PERMANENT_LOCK_USER},
                 {"action_type": LockoutAction.EMAIL_ADMIN,
                  "action_value": {
                      "smtp_identifier": "",
                      "recipient_group": "internal_admins",
                      "subject": "[privacyIDEA] MFA brute-force: {username} permanently locked",
                      "body": ("User {username}@{realm} (resolver {resolver}) from "
                               "{client_ip} was permanently locked by policy {policy} "
                               "after {count} {event_type} events. Time: {time}.")}},
             ]},
        ],
    })

# The authentication-failure event types the failed-attempt rate limits count. Explicit and curated on purpose -
# deliberately NOT derived from the FAILURE outcome class - because a "FAILURE" outcome does not by itself mean a
# type belongs in an authentication rate limit: a new failure type must be a conscious decision, never silently
# pulled in.
_USER_AUTH_FAILURES = [
    AuthEventType.PASSWORD_FAIL,
    AuthEventType.PIN_FAIL,
    AuthEventType.TOKEN_ONLY_FAIL,
    AuthEventType.MFA_FAIL,
    AuthEventType.CHALLENGE_ANSWERED_FAIL,
    AuthEventType.CHALLENGE_DECLINED,
    AuthEventType.NO_TOKEN,
    AuthEventType.NO_USABLE_TOKEN,
    AuthEventType.UNKNOWN_FAIL_REASON,
]
# The per-IP failed set is the per-user set plus USER_UNKNOWN: a source IP failing against many *distinct* accounts
# includes probing non-existent usernames (enumeration), which a per-user target cannot see.
_IP_AUTH_FAILURES = _USER_AUTH_FAILURES + [AuthEventType.USER_UNKNOWN]

USER_RATE_LIMITING = LockoutPolicyTemplate(
    key="user_rate_limiting",
    description=lazy_gettext("Rate-limit a single user's authentication: once too many attempts happen in a short "
                             "window, further attempts are briefly denied. Counts every attempt - successful, failed "
                             "or abandoned - and never locks the account (the denial lifts as the window drains)."),
    policy={
        "name": "Per-User Rate Limit",
        "time_window_seconds": 60,
        "enabled": True,
        "dry_run": False,
        "priority": 1,
        "target": LockoutTarget.USER,
        # PER_ATTEMPT so a multichallenge / push login counts as one attempt; every AuthEventType is tracked so
        # successes and abandoned (pending) attempts count too - this caps the request rate, it does not lock.
        "count_mode": CountMode.PER_ATTEMPT,
        "counter_types_to_track": list(AuthEventType),
        "stages": [
            {"failure_threshold": 20, "priority": 1,
             "actions": [{"action_type": LockoutAction.DENY}]},
        ],
    })

USER_FAILED_RATE_LIMITING = LockoutPolicyTemplate(
    key="user_failed_rate_limiting",
    description=lazy_gettext("Rate-limit a single user's failed authentication attempts: after too many failures in "
                             "a short window, further attempts are briefly denied. Successful logins are not counted, "
                             "so a busy legitimate user is unaffected - only a guessing burst is throttled."),
    policy={
        "name": "Per-User Failed-Attempt Rate Limit",
        "time_window_seconds": 60,
        "enabled": True,
        "dry_run": False,
        "priority": 1,
        "target": LockoutTarget.USER,
        "count_mode": CountMode.PER_ATTEMPT,
        "counter_types_to_track": list(_USER_AUTH_FAILURES),
        "stages": [
            {"failure_threshold": 10, "priority": 1,
             "actions": [{"action_type": LockoutAction.DENY}]},
        ],
    })

PASSWORD_SPRAYING = LockoutPolicyTemplate(
    key="password_spraying",
    description=lazy_gettext("Block a source IP that fails first-factor authentication (wrong password "
                             "or PIN) against many different users in a short time (password spraying / "
                             "credential stuffing)."),
    policy={
        "name": "Password Spraying",
        "time_window_seconds": 300,
        "enabled": True,
        "dry_run": False,
        "priority": 1,
        "target": LockoutTarget.SOURCE_IP,
        "count_mode": CountMode.DISTINCT_USERS,
        "counter_types_to_track": [AuthEventType.PASSWORD_FAIL, AuthEventType.PIN_FAIL],
        "stages": [
            {"failure_threshold": 20, "priority": 1,
             "actions": [{"action_type": LockoutAction.BLOCK_IP,
                          "action_value": {"duration_seconds": 3600}}]},
        ],
    })

USER_ENUMERATION = LockoutPolicyTemplate(
    key="user_enumeration",
    description=lazy_gettext("Block a source IP that probes many different non-existent usernames in a short "
                             "time (user enumeration)."),
    policy={
        "name": "User Enumeration",
        "time_window_seconds": 300,
        "enabled": True,
        "dry_run": False,
        "priority": 1,
        "target": LockoutTarget.SOURCE_IP,
        # DISTINCT_USERS keys on the attempted username, so each probed non-existent login counts as a distinct
        # targeted account - the enumeration signal, and NAT-safe (fan-out, not raw request volume).
        "count_mode": CountMode.DISTINCT_USERS,
        "counter_types_to_track": [AuthEventType.USER_UNKNOWN],
        "stages": [
            {"failure_threshold": 10, "priority": 1,
             "actions": [{"action_type": LockoutAction.BLOCK_IP,
                          "action_value": {"duration_seconds": 3600}}]},
        ],
    })

IP_FAILED_RATE_LIMITING = LockoutPolicyTemplate(
    key="ip_failed_rate_limiting",
    description=lazy_gettext("Rate-limit a source IP that fails authentication against many different accounts in a "
                             "short window (credential stuffing, spraying or user enumeration): further requests from "
                             "that IP are briefly denied."),
    policy={
        "name": "Per-IP Failed-Attempt Rate Limit (Distinct Accounts)",
        "time_window_seconds": 300,
        "enabled": True,
        "dry_run": False,
        "priority": 1,
        "target": LockoutTarget.SOURCE_IP,
        # For an IP, "attempts" is the number of DISTINCT accounts (attempted usernames) it targeted - the fan-out
        # signal, never raw request volume, so a busy shared egress is judged only by how many accounts it fails on.
        "count_mode": CountMode.DISTINCT_USERS,
        "counter_types_to_track": list(_IP_AUTH_FAILURES),
        "stages": [
            {"failure_threshold": 20, "priority": 1,
             "actions": [{"action_type": LockoutAction.DENY}]},
        ],
    })

IP_RATE_LIMITING = LockoutPolicyTemplate(
    key="ip_rate_limiting",
    description=lazy_gettext("Rate-limit a source IP by how many different accounts it authenticates as in a short "
                             "window, regardless of success."),
    policy={
        "name": "Per-IP Rate Limit (Distinct Accounts)",
        "time_window_seconds": 300,
        "enabled": True,
        # Dry-run by default: this is the one IP template that counts successes, so a legitimate shared-egress IP can
        # trip it. It logs the decision it *would* make and enforces nothing until an admin turns dry_run off.
        "dry_run": True,
        "priority": 1,
        "target": LockoutTarget.SOURCE_IP,
        "count_mode": CountMode.DISTINCT_USERS,
        "counter_types_to_track": list(AuthEventType),
        "stages": [
            {"failure_threshold": 30, "priority": 1,
             "actions": [{"action_type": LockoutAction.DENY}]},
        ],
    })

# The shipped catalog. Add a template by defining a constant and listing it here.
_TEMPLATES = (PASSWORD_BRUTEFORCE, MFA_BRUTEFORCE, USER_RATE_LIMITING, USER_FAILED_RATE_LIMITING,
              PASSWORD_SPRAYING, USER_ENUMERATION, IP_FAILED_RATE_LIMITING, IP_RATE_LIMITING)


@log_with(log)
def list_lockout_policy_templates() -> list:
    """
    Return the whole shipped catalog, each entry as
    ``{"key": str, "description": str, "policy": dict}`` where ``policy`` is the
    payload a client submits to create a policy.
    """
    return [{"key": template.key,
             "description": str(template.description),
             "policy": copy.deepcopy(template.policy)} for template in _TEMPLATES]
