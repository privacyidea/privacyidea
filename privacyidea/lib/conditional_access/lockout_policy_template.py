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
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
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
                 {"action_type": LockoutAction.PERMANENT_LOCK_USER.value},
                 {"action_type": LockoutAction.EMAIL_ADMIN.value,
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
        "counter_types_to_track": [AuthEventType.PASSWORD_FAIL, AuthEventType.PIN_FAIL],
        "stages": [
            {"failure_threshold": 20, "priority": 1,
             "actions": [{"action_type": LockoutAction.BLOCK_IP,
                          "action_value": {"duration_seconds": 3600}}]},
        ],
    })

# The shipped catalog. Add a template by defining a constant and listing it here.
_TEMPLATES = (PASSWORD_BRUTEFORCE, MFA_BRUTEFORCE, PASSWORD_SPRAYING)


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
