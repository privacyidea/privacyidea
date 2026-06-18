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
(a local admin or a resolver user). The backend is a pass-through store: it
validates a document's shape and size on write and serves it back verbatim
on read. It does not interpret the settings and does not supply default
*values* -- the WebUI owns the defaults, so an absent key means "not
customized, use the frontend default".

The data lives in the ``usersetting`` table, one JSON document per
principal. See :class:`privacyidea.models.usersetting.UserSetting` for the
identity model (``local_admin`` keyed by username, ``user`` keyed by the
resolver identity tuple).
"""
import json
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from privacyidea.lib.auth import ROLE
from privacyidea.lib.error import ParameterError, UserError
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.user import User
from privacyidea.models import UserSetting, db

log = logging.getLogger(__name__)

SUBJECT_LOCAL_ADMIN = "local_admin"
SUBJECT_USER = "user"

# Hard cap on the serialized settings document, so the column cannot be abused
# as arbitrary per-principal storage. Generous enough for a dashboard layout
# plus a pinned-item list, which are the largest expected settings.
MAX_SETTINGS_BYTES = 16384

# pi.cfg / environment option letting admins extend the set of accepted setting
# keys without a code change, e.g. PI_USER_SETTINGS_ALLOWED_KEYS = ["foo", "bar"].
# Accepts a list (pi.cfg) or a comma-separated string (environment variable).
# Placeholder for now: get_allowed_keys() is wired up but not yet enforced (see
# the TODO in validate_user_settings).
USER_SETTINGS_ALLOWED_KEYS_CONFIG = "PI_USER_SETTINGS_ALLOWED_KEYS"

# Registry of the top-level setting keys the WebUI may store. Only used to seed
# the (not-yet-enforced) allow-list; the backend stores the *values* verbatim
# and never validates their structure. Admins can add further accepted keys via
# PI_USER_SETTINGS_ALLOWED_KEYS without touching this registry.
#
# NOTE: these names are PLACEHOLDERS reflecting the intended settings. The
# frontend team defines the real set; do not treat them as a committed API yet.
KNOWN_SETTING_KEYS = {
    "theme",
    "starting_page",
    "token_columns",
    "dashboard",
    "pinned_items",
}


def get_allowed_keys() -> set:
    """
    The set of accepted top-level setting keys: :data:`KNOWN_SETTING_KEYS` plus
    any added by the admin via the ``PI_USER_SETTINGS_ALLOWED_KEYS`` config
    option.
    """
    allowed = set(KNOWN_SETTING_KEYS)
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

    def is_identified(self) -> bool:
        """
        Whether the subject has a concrete identity to key a row on.

        A local admin needs a username; a resolver user needs both a user_id
        and a realm_id. An unresolved user has an empty user_id (and possibly a
        NULL realm_id), and since SQL treats NULLs in the unique key as
        distinct, keying a row on those empty values would make every
        unresolved principal share one row (cross-user leak). Mirrors
        ``User._require_resolved_for_write``.
        """
        if self.subject_type == SUBJECT_LOCAL_ADMIN:
            return bool(self.username)
        return bool(self.user_id) and bool(self.realm_id)

    @classmethod
    def from_logged_in_user(cls, logged_in_user: dict, resolved_user: "User | None" = None) -> "SettingsSubject":
        """
        Derive the settings subject from ``g.logged_in_user`` (carrying
        ``username``, ``realm`` and ``role`` from the JWT).

        A logged-in admin without a realm is an internal/local admin. Any
        principal with a realm (including realm-admins) is treated as a
        resolver user and keyed by its stable ``(user_id, resolver, realm_id)``
        identity.

        ``resolved_user`` may be ``request.User`` to avoid a second resolver
        lookup. It is only trusted for the ``user`` role: ``resolve_logged_in_user``
        forces ``request.User`` to the JWT identity for users, whereas for an
        admin it can reflect a ``user=`` request parameter, which must never
        decide whose settings are read or written.
        """
        username = logged_in_user.get("username") or ""
        realm = logged_in_user.get("realm") or ""
        role = logged_in_user.get("role")
        if role == ROLE.ADMIN and not realm:
            return cls(subject_type=SUBJECT_LOCAL_ADMIN, username=username)
        if (role == ROLE.USER and resolved_user is not None and resolved_user.login == username
                and (resolved_user.realm or "") == realm.lower() and resolved_user.uid):
            user = resolved_user
        else:
            user = User(login=username, realm=realm)
        if not user.uid:
            log.warning(f"Could not resolve settings subject for user '{username}' in realm '{realm}'.")
        return cls(subject_type=SUBJECT_USER, username=username,
                   user_id=user.uid or "", resolver=user.resolver or "", realm_id=user.realm_id)


def validate_user_settings(settings: dict) -> None:
    """
    Validate a settings document before it is stored.

    For now this only enforces structure: the document must be a JSON object,
    be JSON-serializable, and stay within :data:`MAX_SETTINGS_BYTES`. Any key
    with any value is accepted so the frontend can iterate on the setting set
    without a backend change.

    Raises :class:`ParameterError` on the first problem found.
    """
    if not isinstance(settings, dict):
        raise ParameterError("The settings must be a JSON object.")
    try:
        # ensure_ascii=False so the byte count matches what the JSON column
        # actually stores; the default would inflate non-ASCII characters into
        # \uXXXX escapes and reject valid documents below the real limit.
        serialized = json.dumps(settings, ensure_ascii=False)
    except (TypeError, ValueError) as error:
        raise ParameterError(f"The settings must be JSON-serializable: {error}")
    if len(serialized.encode("utf-8")) > MAX_SETTINGS_BYTES:
        raise ParameterError(f"The settings exceed the maximum size of {MAX_SETTINGS_BYTES} bytes.")
    # TODO: Enforce the top-level key allow-list once the frontend has settled
    #  the set of settings: reject any key not in get_allowed_keys()
    #  (KNOWN_SETTING_KEYS + PI_USER_SETTINGS_ALLOWED_KEYS). Values stay
    #  unvalidated -- the backend remains a pass-through store.


def _select_for_subject(subject: SettingsSubject):
    if subject.subject_type == SUBJECT_LOCAL_ADMIN:
        return select(UserSetting).filter_by(subject_type=SUBJECT_LOCAL_ADMIN, username=subject.username)
    return select(UserSetting).filter_by(subject_type=SUBJECT_USER, user_id=subject.user_id,
                                         resolver=subject.resolver, realm_id=subject.realm_id)


def _merge_settings(existing: dict | None, incoming: dict, replace: bool) -> dict:
    """Compute the new settings document: ``incoming`` replaces or is merged onto ``existing``."""
    if replace:
        return incoming
    return {**(existing or {}), **incoming}


def get_user_settings(subject: SettingsSubject) -> dict:
    """
    Return the principal's stored settings verbatim, or an empty dict if the
    principal has not stored any. Defaults are not filled in -- the WebUI owns
    those.
    """
    # An unidentified subject must not query with empty/NULL keys: it would
    # match the shared row of every other unidentified principal. Reads are
    # tolerated and just return an empty document.
    if not subject.is_identified():
        return {}
    row = db.session.scalars(_select_for_subject(subject)).first()
    return (row.settings if row else None) or {}


def set_user_settings(subject: SettingsSubject, settings: dict, replace: bool = False) -> dict:
    """
    Store settings for the principal and return the stored document.

    ``settings`` is validated first. By default the given keys are merged into
    the existing document (partial update); pass ``replace=True`` to overwrite
    the whole document. If the resulting document is empty the row is removed,
    so an absent row and an empty document are the same state.

    :return: the stored settings
    """
    validate_user_settings(settings)
    if not subject.is_identified():
        raise UserError("Cannot store settings for an unidentified subject "
                        f"(subject_type={subject.subject_type!r}, username={subject.username!r}).")
    row = db.session.scalars(_select_for_subject(subject)).first()
    new_settings = _merge_settings(row.settings if row else None, settings, replace)
    # Re-validate the full document, not just the incoming delta, so the size
    # cap cannot be bypassed by accumulating keys across repeated partial writes.
    validate_user_settings(new_settings)
    if not new_settings:
        # Store absence rather than an empty document (absent == empty).
        if row is not None:
            row.delete()
        return {}
    if row is None:
        row = UserSetting(subject_type=subject.subject_type, username=subject.username,
                          user_id=subject.user_id, resolver=subject.resolver,
                          realm_id=subject.realm_id, settings=new_settings)
    else:
        row.settings = new_settings
    try:
        row.save()
    except IntegrityError:
        # A concurrent request created the row between our SELECT and INSERT
        # (the unique constraint fires for resolver users; for local admins the
        # NULL realm_id makes the key non-unique, so that race can still leave a
        # duplicate row). Recover by re-reading and applying the update.
        db.session.rollback()
        row = db.session.scalars(_select_for_subject(subject)).first()
        if row is None:
            raise
        row.settings = _merge_settings(row.settings, settings, replace)
        validate_user_settings(row.settings)
        row.save()
    return row.settings or {}


def delete_user_settings(subject: SettingsSubject, key: str | None = None) -> dict:
    """
    Delete one setting (``key``) or the whole document (``key=None``) and
    return the remaining stored settings.

    Deleting a key is the way to "reset to default": with the key gone the
    WebUI falls back to its own default, which also tracks future default
    changes (unlike pinning the current default value). When the last key is
    removed the row is dropped, keeping absent == empty.
    """
    # Same guard as reads: never match the shared row of unidentified principals.
    if not subject.is_identified():
        return {}
    row = db.session.scalars(_select_for_subject(subject)).first()
    if row is None:
        return {}
    if key is None:
        row.delete()
        return {}
    current = dict(row.settings or {})
    if key not in current:
        return current
    del current[key]
    if not current:
        row.delete()
        return {}
    row.settings = current
    row.save()
    return row.settings or {}
