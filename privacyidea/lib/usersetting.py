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
(a local admin or a resolver user). The backend is a pass-through store for
the *values*: on write it checks a document's shape, size and top-level keys
(see :data:`KNOWN_SETTING_KEYS`), and on read it serves it back verbatim. It
does not interpret the settings and does not supply default values -- the
WebUI owns the defaults, so an absent key means "not customized, use the
frontend default".

The data lives in the ``usersetting`` table, one JSON document per
principal. See :class:`privacyidea.models.usersetting.UserSetting` for the
identity model (``local_admin`` keyed by username, ``user`` keyed by the
resolver identity tuple).
"""
import json
import logging
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from privacyidea.lib.auth import ROLE, db_admin_exists
from privacyidea.lib.error import ParameterError, UserError
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.user import User
from privacyidea.models import UserSetting, db

log = logging.getLogger(__name__)

SUBJECT_LOCAL_ADMIN = "local_admin"
SUBJECT_USER = "user"

# Hard cap on the serialized document, so the column cannot be abused as
# arbitrary per-principal storage.
MAX_SETTINGS_BYTES = 16384

# Accepts a list (pi.cfg) or a comma-separated string (environment variable).
USER_SETTINGS_ALLOWED_KEYS_CONFIG = "PI_USER_SETTINGS_ALLOWED_KEYS"

# These are the keys the WebUI writes, as declared by the ``UserSettingKey`` type in
# static_new/src/app/services/user-settings/user-settings.service.ts. A setting that
# is added there has to be added here as well.
KNOWN_SETTING_KEYS = {
    "theme",
    "locale",
    "dashboard",
}


# Budget for the key list in a rejection message, so that neither the number nor
# the length of the sent keys decides how long the message (and audit entry) gets.
MAX_REPORTED_KEYS_LENGTH = 200


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
        NULL realm_id); keying a row on those empty values would make every
        unresolved principal hash to the same ``subject_hash`` and share one
        row (cross-user leak). Mirrors ``User._require_resolved_for_write``.
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


def _describe_unknown_keys(unknown: list) -> str:
    """
    Render the unknown keys for a rejection message, staying within
    :data:`MAX_REPORTED_KEYS_LENGTH`.

    Only whole keys are listed, so the message never shows a half key that reads
    like a name the caller actually sent. A single key that is longer than the
    budget is cut, because there is nothing whole left to keep.

    Non-printable characters are escaped rather than dropped, so the reader sees
    which character was sent. A JSON key may contain a line break, and the
    message reaches the audit log, whose CSV export is line-oriented -- an
    unescaped key could forge an entry there. The test is the same one
    :class:`privacyidea.lib.log.SecureFormatter` uses, which covers the control
    characters beyond the usual line-break suspects (NUL, ESC and friends).
    """
    packed = ""
    for key in unknown:
        key = "".join(char if char.isprintable() else char.encode("unicode_escape").decode("ascii")
                      for char in key)
        candidate = f"{packed}, {key}" if packed else key
        if len(candidate) > MAX_REPORTED_KEYS_LENGTH:
            if not packed:
                return f"{key[:MAX_REPORTED_KEYS_LENGTH]}..."
            return f"{packed}, ... ({len(unknown)} keys in total)"
        packed = candidate
    return packed


def validate_user_settings(settings: dict, check_keys: bool = True) -> None:
    """
    Validate a settings document before it is stored.

    The document must be a JSON object, be JSON-serializable, stay within
    :data:`MAX_SETTINGS_BYTES`, and carry only keys from
    :func:`get_allowed_keys`. Values are not validated -- the backend remains
    a pass-through store.

    :param check_keys: whether to enforce the key allow-list. With ``False``
        only the structure and the size are checked, so that a key which was
        accepted when it was written does not block later writes of unrelated
        settings.

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
    if check_keys:
        allowed = get_allowed_keys()
        unknown = sorted(str(key) for key in settings if key not in allowed)
        if unknown:
            log.debug(f"Rejecting settings with unknown keys: {unknown}")
            raise ParameterError(f"Unknown setting key{'s' if len(unknown) > 1 else ''}: "
                                 f"{_describe_unknown_keys(unknown)}.")


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
    # Lock the row for the read-modify-write so two concurrent partial updates
    # (e.g. two browser tabs) serialize instead of last-writer-wins clobbering
    # each other's keys. No-op on SQLite; a real row lock on Postgres/MariaDB.
    row = db.session.scalars(_select_for_subject(subject).with_for_update()).first()
    new_settings = _merge_settings(row.settings if row else None, settings, replace)
    # Re-validate the full document, not just the incoming delta, so the size
    # cap cannot be bypassed by accumulating keys across repeated partial writes.
    validate_user_settings(new_settings, check_keys=False)
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
        # (uq_usersetting_subject fires for both local admins and resolver
        # users). Recover by re-reading and applying the update.
        db.session.rollback()
        row = db.session.scalars(_select_for_subject(subject).with_for_update()).first()
        if row is None:
            raise
        row.settings = _merge_settings(row.settings, settings, replace)
        validate_user_settings(row.settings, check_keys=False)
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
    # Lock the row so a key removal does not race with a concurrent write.
    row = db.session.scalars(_select_for_subject(subject).with_for_update()).first()
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


def find_orphaned_user_settings(orphaned_on_error: bool = False) -> list[UserSetting]:
    """
    Return the ``usersetting`` rows whose principal no longer exists.

    A row is orphaned when:

    * (``user`` rows) its ``(user_id, resolver, realm_id)`` no longer resolves
      to a user -- the resolver is gone, the uid no longer exists, or the row
      has empty identifiers; or
    * (``local_admin`` rows) its ``username`` is no longer in the ``admin``
      table.

    The realm FK removes rows when a *realm* is deleted, but a user removed
    from the store (or an admin deleted from the DB) leaves a row that the
    normal API can no longer reach. There is no periodic task for this -- like
    ``internaluserattribute``, cleanup is a manual CLI command.

    :param orphaned_on_error: if a resolver raises while looking up the user,
        treat that row as orphaned (mirrors ``find_orphaned_internal_attributes``).
    """
    from privacyidea.lib.resolver import get_resolver_object

    rows = db.session.scalars(select(UserSetting)).all()
    orphans: list[UserSetting] = []
    resolver_cache: dict = {}
    for row in rows:
        if row.subject_type == SUBJECT_LOCAL_ADMIN:
            if not row.username or not db_admin_exists(row.username):
                orphans.append(row)
            continue
        # SUBJECT_USER: reuse the internaluserattribute orphan logic.
        if not row.user_id or not row.resolver:
            orphans.append(row)
            continue
        if row.resolver not in resolver_cache:
            resolver_cache[row.resolver] = get_resolver_object(row.resolver)
        resolver = resolver_cache[row.resolver]
        if resolver is None:
            orphans.append(row)
            continue
        try:
            login = resolver.getUsername(row.user_id)
        except Exception:
            if orphaned_on_error:
                orphans.append(row)
            continue
        if not login:
            orphans.append(row)
    return orphans


def delete_orphaned_user_settings(orphans: list[UserSetting]) -> int:
    """
    Delete the given orphaned ``usersetting`` rows (by id) and return the count.
    Bypasses the normal API on purpose -- orphans cannot be addressed through it.
    """
    if not orphans:
        return 0
    ids = [row.id for row in orphans]
    total = db.session.execute(delete(UserSetting).where(UserSetting.id.in_(ids))).rowcount
    db.session.commit()
    return total
