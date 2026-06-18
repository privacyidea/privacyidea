# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2026 Nils Behlen <nils.behlen@netknights.it>
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
Per-principal frontend settings.

This module stores and serves the WebUI settings of whoever is logged in
(a local admin or a resolver user). The backend does not act on these
settings; it only validates them on write and merges them over the
declared defaults on read.

The data lives in the ``usersetting`` table, one JSON document per
principal. See :class:`privacyidea.models.usersetting.UserSetting` for the
identity model (``local_admin`` keyed by username, ``user`` keyed by the
resolver identity tuple).
"""
import json
import logging
from dataclasses import dataclass

from sqlalchemy import select

from privacyidea.lib.error import ParameterError
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.user import User
from privacyidea.models import UserSetting, db

log = logging.getLogger(__name__)

SUBJECT_LOCAL_ADMIN = "local_admin"
SUBJECT_USER = "user"

# Hard cap on the serialized settings document, so the column cannot be abused
# as arbitrary per-principal storage. The settings are small UI preferences.
MAX_SETTINGS_BYTES = 8192

# pi.cfg / environment option letting admins extend the set of accepted setting
# keys without a code change, e.g. PI_USER_SETTINGS_ALLOWED_KEYS = ["foo", "bar"].
# Accepts a list (pi.cfg) or a comma-separated string (environment variable).
# Placeholder for now: get_allowed_keys() is wired up but not yet enforced (see
# the TODO in validate_user_settings).
USER_SETTINGS_ALLOWED_KEYS_CONFIG = "PI_USER_SETTINGS_ALLOWED_KEYS"

# Declarative registry of the settings the WebUI may store. The backend is the
# source of truth for *which* settings exist; adding a new setting is a one-line
# entry here. ``default`` is merged in on read; ``type`` will be checked on write
# once key enforcement is turned on. Admins can add further accepted keys via
# PI_USER_SETTINGS_ALLOWED_KEYS without touching this registry.
#
# NOTE: the keys below are PLACEHOLDERS to exercise the mechanism. The frontend
# team defines the real set; do not treat these names as a committed API yet.
SETTINGS_SCHEMA = {
    "theme": {"type": str, "default": "light"},
    "language": {"type": str, "default": "en"},
    "tokens_per_page": {"type": int, "default": 25},
    "advanced_mode": {"type": bool, "default": False},
}


def get_allowed_keys() -> set:
    """
    The set of accepted setting keys: the keys declared in
    :data:`SETTINGS_SCHEMA` plus any added by the admin via the
    ``PI_USER_SETTINGS_ALLOWED_KEYS`` config option.
    """
    allowed = set(SETTINGS_SCHEMA)
    configured = get_app_config_value(USER_SETTINGS_ALLOWED_KEYS_CONFIG, [])
    if isinstance(configured, str):
        configured = [key.strip() for key in configured.split(",") if key.strip()]
    allowed.update(configured or [])
    return allowed


@dataclass
class SettingsSubject:
    """The principal a settings document belongs to."""
    subject_type: str
    username: str = ""
    user_id: str = ""
    resolver: str = ""
    realm_id: int | None = None

    @classmethod
    def from_logged_in_user(cls, logged_in_user: dict) -> "SettingsSubject":
        """
        Derive the settings subject from ``g.logged_in_user`` (carrying
        ``username``, ``realm`` and ``role`` from the JWT).

        A logged-in admin without a realm is an internal/local admin. Any
        principal with a realm (including realm-admins) is treated as a
        resolver user and keyed by its stable ``(user_id, resolver, realm_id)``
        identity.
        """
        username = logged_in_user.get("username") or ""
        realm = logged_in_user.get("realm") or ""
        role = logged_in_user.get("role")
        if role == "admin" and not realm:
            return cls(subject_type=SUBJECT_LOCAL_ADMIN, username=username)
        user = User(login=username, realm=realm)
        if not user.uid:
            log.warning(f"Could not resolve settings subject for user '{username}' in realm '{realm}'.")
        return cls(subject_type=SUBJECT_USER, username=username,
                   user_id=user.uid or "", resolver=user.resolver or "", realm_id=user.realm_id)


def validate_user_settings(settings: dict) -> None:
    """
    Validate a settings document before it is stored.

    For now this only enforces structure: the document must be a JSON object
    and stay within :data:`MAX_SETTINGS_BYTES`. Any key with any value is
    accepted so the frontend can iterate on the setting set without a backend
    change.

    Raises :class:`ParameterError` on the first problem found.
    """
    if not isinstance(settings, dict):
        raise ParameterError("The settings must be a JSON object.")
    if len(json.dumps(settings).encode("utf-8")) > MAX_SETTINGS_BYTES:
        raise ParameterError(f"The settings exceed the maximum size of {MAX_SETTINGS_BYTES} bytes.")
    # TODO: Enforce the set of allowed keys once the frontend has settled them.
    #  Reject any key not in get_allowed_keys() (SETTINGS_SCHEMA +
    #  PI_USER_SETTINGS_ALLOWED_KEYS) and type-check the SETTINGS_SCHEMA entries
    #  against their declared "type" here (bool is a subclass of int, guard that).


def _select_for_subject(subject: SettingsSubject):
    if subject.subject_type == SUBJECT_LOCAL_ADMIN:
        return select(UserSetting).filter_by(subject_type=SUBJECT_LOCAL_ADMIN, username=subject.username)
    return select(UserSetting).filter_by(subject_type=SUBJECT_USER, user_id=subject.user_id,
                                         resolver=subject.resolver, realm_id=subject.realm_id)


def get_user_settings(subject: SettingsSubject) -> dict:
    """
    Return the principal's settings, with every declared default filled in
    for keys the principal has not overridden.
    """
    defaults = {key: spec["default"] for key, spec in SETTINGS_SCHEMA.items()}
    row = db.session.scalars(_select_for_subject(subject)).first()
    if row and row.settings:
        defaults.update(row.settings)
    return defaults


def set_user_settings(subject: SettingsSubject, settings: dict, replace: bool = False) -> dict:
    """
    Store settings for the principal and return the stored (raw) document.

    ``settings`` is validated first. By default the given keys are merged into
    the existing document (partial update); pass ``replace=True`` to overwrite
    the whole document.

    :return: the raw stored settings (without defaults merged in)
    """
    validate_user_settings(settings)
    row = db.session.scalars(_select_for_subject(subject)).first()
    if row is None:
        row = UserSetting(subject_type=subject.subject_type, username=subject.username,
                          user_id=subject.user_id, resolver=subject.resolver,
                          realm_id=subject.realm_id, settings=settings)
    else:
        if replace:
            row.settings = settings
        else:
            merged = dict(row.settings or {})
            merged.update(settings)
            row.settings = merged
    row.save()
    return row.settings or {}
