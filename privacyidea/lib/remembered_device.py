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
This module implements persistent ("remember this device") authentication
devices using a rotating-token scheme.

A device is represented by a cookie of the form ``series_id:counter``. The
``series_id`` identifies the row in the ``remembered_devices`` table; the ``counter``
is bumped on every use, both in the cookie and in the database. If a request
presents a valid ``series_id`` with a stale ``counter``, the token has been
replayed - a sign the cookie was stolen - so the whole series is deleted and
authentication fails.

The cookie never carries the API key. A device is bound to a specific API
client via ``client_id``, which is matched against ``g.client_id`` (set by the
API-key middleware) on every validation.
"""
import enum
import logging
import secrets
from datetime import datetime, timedelta
from typing import NamedTuple, TYPE_CHECKING

from flask_babel import _

from privacyidea.lib.error import AuthError, ParameterError
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.sqlutils import delete_matching_rows
from privacyidea.models import RememberedDevice, Realm, db

if TYPE_CHECKING:
    from privacyidea.lib.user import User
from privacyidea.models.utils import utc_now, utc_isoformat

log = logging.getLogger(__name__)

# Name of the cookie carrying the remembered device token.
PERSISTENT_COOKIE_NAME = "pi_remember_device"
# Number of random bytes in a series id.
SERIES_ID_BYTES = 32
# Bytes of entropy in the public device_id (the non-secret management handle
# used to list and revoke a device). It is not a credential; randomness only
# keeps it opaque and non-enumerable.
DEVICE_ID_BYTES = 16
# Default grace window (seconds) during which the immediately-previous counter
# is still accepted, to tolerate concurrent/duplicate requests without treating
# them as cookie theft. Overridable via PI_REMEMBER_DEVICE_GRACE_SECONDS in
# pi.cfg; set to 0 for strict fail-secure (no grace).
DEFAULT_GRACE_SECONDS = 10
# Column limits of the identity binding, mirroring the remembered_devices model. The
# identity is a lookup key, so it is stored and matched verbatim (never
# truncated); a user whose identity would overflow simply gets no device.
RESOLVER_MAX_LEN = 120
USER_ID_MAX_LEN = 320
# Hard cap on a device's configured validity, so an absurd
# remember_device_validity policy value cannot overflow timedelta.
MAX_DEVICE_VALIDITY_DAYS = 3650


def _grace_window_seconds() -> int:
    """Return the configured replay grace window in seconds (0 disables it)."""
    try:
        return max(0, int(get_app_config_value("PI_REMEMBER_DEVICE_GRACE_SECONDS",
                                               DEFAULT_GRACE_SECONDS)))
    except (TypeError, ValueError):
        return DEFAULT_GRACE_SECONDS


def build_cookie_value(series_id: str, counter: int) -> str:
    """
    Build the cookie value ``series_id:counter``.

    :param series_id: the series id
    :param counter: the current counter
    :return: the cookie value
    """
    return f"{series_id}:{counter}"


def parse_cookie(cookie_value: str | None) -> tuple[str, int] | tuple[None, None]:
    """
    Parse a remember-device cookie of the form ``series_id:counter``.

    :param cookie_value: the raw cookie value
    :return: a ``(series_id, counter)`` tuple, or ``(None, None)`` if malformed
    """
    if not cookie_value or ":" not in cookie_value:
        return None, None
    series_id, _sep, counter_str = cookie_value.partition(":")
    if not series_id:
        return None, None
    try:
        counter = int(counter_str)
    except ValueError:
        return None, None
    return series_id, counter


class UserIdentity(NamedTuple):
    """
    The resolver-stable identity a remembered device is bound to.

    Binding on ``(resolver, user_id, realm_id)`` - where ``user_id`` is the
    resolver's immutable id, **not** the login - means a remembered device
    survives a login rename and can never be recognised for a *different* account
    that later reuses a freed login name. This mirrors how a token is bound to
    its owner (:class:`~privacyidea.models.TokenOwner`).
    """
    resolver: str
    user_id: str
    realm_id: int


def user_identity(user: "User | None") -> "UserIdentity | None":
    """
    Build the resolver-stable identity a remembered device binds to.

    :param user: the ``User`` object (or None)
    :return: a :class:`UserIdentity`, or ``None`` if the user does not resolve to
        one - a userless (serial-only) auth, or an account that no longer exists
    """
    if not user or not user.resolver or not user.uid or not user.realm_id:
        return None
    resolver, user_id = user.resolver, str(user.uid)
    if len(resolver) > RESOLVER_MAX_LEN or len(user_id) > USER_ID_MAX_LEN:
        # The identity is a lookup key stored verbatim; one that does not fit the
        # column could never be matched, so bind no device to it rather than
        # issue a cookie that is silently never recognised.
        log.warning(f"Remember-device unavailable for a user of realm_id {user.realm_id}: "
                    f"identity exceeds the storable length.")
        return None
    return UserIdentity(resolver, user_id, user.realm_id)


def create_remembered_device(identity: "UserIdentity", client_id: str, ip_address: str = None,
                        user_agent: str = None, validity_days: int = None) -> tuple[RememberedDevice, str]:
    """
    Create and persist a new remembered device.

    :param identity: the resolver-stable identity of the authenticated user (see
        :func:`user_identity`)
    :param client_id: id of the API client the device is bound to
    :param ip_address: the client IP address the device was created from
    :param user_agent: the user agent the device was created from
    :param validity_days: device lifetime in days; ``None`` (or a
        non-positive value) uses the model default (``DEFAULT_DEVICE_VALIDITY``)
    :return: a tuple of the stored ``RememberedDevice`` and the cookie value
        (``series_id:1``) to send to the client
    """
    series_id = secrets.token_urlsafe(SERIES_ID_BYTES)
    device_id = secrets.token_urlsafe(DEVICE_ID_BYTES)
    if validity_days and validity_days > 0:
        # Cap the validity so an absurd policy value cannot overflow timedelta and
        # turn an already-successful auth into a 500.
        expires_at = utc_now() + timedelta(days=min(validity_days, MAX_DEVICE_VALIDITY_DAYS))
    else:
        expires_at = None
    # The identity is a lookup key and is stored verbatim (user_identity
    # has already ensured it fits its columns). Only the free-form metadata
    # (ip/user agent) is truncated, so an over-long value there can never raise on
    # save and turn an already-successful auth into a 500.
    device = RememberedDevice(series_id=series_id, device_id=device_id, client_id=client_id,
                          resolver=identity.resolver, user_id=identity.user_id,
                          realm_id=identity.realm_id,
                          ip_address=(ip_address or None) and ip_address[:64],
                          user_agent=(user_agent or None) and user_agent[:255], counter=1,
                          expires_at=expires_at)
    device.save()
    return device, build_cookie_value(series_id, device.counter)


class ValidDevice(NamedTuple):
    """
    A live device matched by :func:`get_valid_device`.

    ``is_grace`` is ``False`` for a fresh use (the caller should rotate the
    token) and ``True`` for a tolerated grace-window hit (the caller must
    **not** rotate).
    """
    device: RememberedDevice
    is_grace: bool


def get_valid_device(cookie_value: str, client_id: str, identity: "UserIdentity",
                      client_ip: str = None) -> "ValidDevice | None":
    """
    Look up and validate a remember-device cookie **without** rotating it.

    The device is matched on ``series_id`` **and** ``client_id`` **and** the
    full user identity (``resolver`` / ``user_id`` / ``realm_id``) so a cookie
    only ever validates for the client it was issued to and the user it was
    issued for.

    * Returns ``None`` if no matching device exists or it has expired (an
      expired device is deleted).
    * If the presented counter matches the stored one, returns
      ``(device, False)`` (a fresh use; the caller should rotate it).
    * If the presented counter is the immediately-previous one and the request
      arrives within the grace window from the same source IP, returns
      ``(device, True)`` - a tolerated concurrent/duplicate request. The caller
      must **not** rotate in this case (it converges on the current token).
    * Any other counter mismatch is treated as replay (stolen cookie): the whole
      series is deleted and an ``AuthError`` is raised.

    Accepted trade-off: because this is a rotating-token scheme, *any* stale
    counter beyond the grace window is treated as theft - including a benign one.
    If a client rotated the cookie but never received the response and retries
    after the grace window, it still holds the old counter, so the series is
    destroyed and a reuse warning is logged even though nothing was stolen. The
    only cost is that the device must re-register; the user is never wrongly
    authenticated. Widening ``PI_REMEMBER_DEVICE_GRACE_SECONDS`` trades
    theft-detection tightness for fewer such re-registrations.

    :param cookie_value: the raw cookie value from the request
    :param client_id: the id of the API client making the request (g.client_id)
    :param identity: the resolver-stable identity the cookie must be bound to
        (see :func:`user_identity`)
    :param client_ip: the source IP of the request; used to bound the grace
        window (a grace hit must come from the IP the device was last used from)
    :return: ``None`` if there is no live device for this cookie (unknown or
        expired); otherwise a :class:`ValidDevice` ``(device, is_grace)`` where
        ``is_grace`` is ``False`` for a fresh use (the caller should rotate the
        token) and ``True`` for a tolerated grace-window hit (the caller must
        **not** rotate - it converges on the current token)
    :raises AuthError: if cookie reuse (theft) is detected
    """
    series_id, counter = parse_cookie(cookie_value)
    if not series_id or counter is None or not identity:
        return None

    device = RememberedDevice.query.filter_by(series_id=series_id, client_id=client_id,
                                          resolver=identity.resolver, user_id=identity.user_id,
                                          realm_id=identity.realm_id).first()
    if not device:
        return None

    if device.expires_at and device.expires_at < utc_now():
        # Never log the series_id: it is the secret half of the cookie. Correlate
        # on the (non-secret) client_id instead.
        log.info(f"Remembered device for client {client_id!r} expired; removing it.")
        device.delete()
        return None

    if device.counter == counter:
        return ValidDevice(device, False)

    if _is_within_grace(device, counter, client_ip):
        # Concurrent/duplicate request presenting the just-superseded counter -
        # tolerate it without rotating (single-step, time- and IP-bounded).
        # last_used_at is deliberately NOT refreshed here: the window stays
        # anchored to the rotation, so a client that never persists the rotated
        # cookie is tolerated only briefly and then treated as theft, rather than
        # being kept alive indefinitely (which would defeat rotation).
        log.debug(f"Remembered device for client {client_id!r}: accepting previous "
                  f"counter within the grace window.")
        return ValidDevice(device, True)

    # Any other counter mismatch means the cookie was replayed. Invalidate the
    # whole series so neither the legitimate client nor the attacker can use it.
    log.warning(f"Remembered device token reuse detected for client {client_id!r}; "
                f"deleting the device.")
    device.delete()
    raise AuthError(_("Authentication failure. Device token reuse detected."))


def _is_within_grace(device: RememberedDevice, counter: int, client_ip: str) -> bool:
    """
    Whether a presented ``counter`` qualifies for the grace window: it must be
    exactly the immediately-previous counter, the device must have been used
    within the grace window, and (when both are known) the source IP must match
    the one the device was last used from.
    """
    grace = _grace_window_seconds()
    if grace <= 0 or counter != device.counter - 1 or device.last_used_at is None:
        return False
    if (utc_now() - device.last_used_at).total_seconds() > grace:
        return False
    if device.ip_address and client_ip and device.ip_address != client_ip:
        return False
    return True


class RotatedCookie(NamedTuple):
    """A rotated cookie's new value and its expiry (see :func:`rotate_device`)."""
    value: str
    expires_at: datetime | None


def rotate_device(device: RememberedDevice) -> RotatedCookie:
    """
    Rotate a validated device: bump the counter, refresh ``last_used_at`` and
    return the new cookie value plus its expiry.

    :param device: a device returned by :func:`get_valid_device`
    :return: a :class:`RotatedCookie` ``(value, expires_at)``
    """
    device.counter += 1
    device.last_used_at = utc_now()
    device.save()
    return RotatedCookie(build_cookie_value(device.series_id, device.counter), device.expires_at)


class RememberStatus(str, enum.Enum):
    """
    Outcome status of consuming a presented remember-device cookie.

    * ``RECOGNIZED`` - a fresh, valid use; ``cookie_value`` and ``expires_at``
      carry the rotated token to send back to the client.
    * ``GRACE`` - a tolerated concurrent/duplicate request; the client keeps the
      cookie it has, so no new one is sent.
    * ``FOREIGN`` - the series is live but bound to a *different* user on the
      same client (a shared browser). Not recognised, but the caller must **not**
      clear it, or one user logging in would wipe another user's cookie.
    * ``MISS`` - no live device for this cookie (unknown or expired); the caller
      should clear it.
    * ``THEFT`` - replay detected; the series has already been invalidated and
      the caller must clear the cookie.

    Inherits from ``str`` so members compare equal to their plain string value
    (e.g. ``RememberStatus.RECOGNIZED == "recognized"``).
    """
    RECOGNIZED = "recognized"
    GRACE = "grace"
    FOREIGN = "foreign"
    MISS = "miss"
    THEFT = "theft"


class ConsumeResult(NamedTuple):
    """
    Outcome of consuming a presented remember-device cookie. See
    :class:`RememberStatus` for the meaning of each ``status``.
    """
    status: RememberStatus
    cookie_value: str | None
    expires_at: datetime | None


def consume_remember_device_cookie(cookie_value: str, client_id: str, identity: "UserIdentity",
                                   client_ip: str = None) -> ConsumeResult:
    """
    Consume a presented remember-device cookie: validate it (see
    :func:`get_valid_device`) and rotate it on a fresh use. This is the single
    place a presented cookie is consumed.

    Recognition only: this performs no authentication, triggers no challenge and
    writes no audit record - the caller decides what to do with the outcome.

    :param cookie_value: the raw cookie value from the request
    :param client_id: the id of the API client making the request (g.client_id)
    :param identity: the resolver-stable identity the cookie must be bound to
        (see :func:`user_identity`)
    :param client_ip: the source IP of the request (bounds the grace window)
    :return: a :class:`ConsumeResult`. Theft is reported as ``status ==
        "theft"`` (the series has already been invalidated) rather than raised,
        so the caller can answer "not recognised" uniformly.
    """
    try:
        result = get_valid_device(cookie_value, client_id, identity, client_ip)
    except AuthError:
        return ConsumeResult(RememberStatus.THEFT, None, None)
    if not result:
        # A miss can mean the cookie is dead (unknown/expired) or that it simply
        # belongs to a different user on this same client - a shared browser,
        # where the cookie is a single browser-level value. Distinguish the two:
        # if the series is still live for some user of this client, treat it as a
        # "foreign" soft miss so we do not clear it and wipe that user's device.
        series_id, _counter = parse_cookie(cookie_value)
        if series_id:
            other = RememberedDevice.query.filter_by(series_id=series_id, client_id=client_id).first()
            if other and not (other.expires_at and other.expires_at < utc_now()):
                return ConsumeResult(RememberStatus.FOREIGN, None, None)
        return ConsumeResult(RememberStatus.MISS, None, None)
    if result.is_grace:
        return ConsumeResult(RememberStatus.GRACE, None, None)
    rotated = rotate_device(result.device)
    return ConsumeResult(RememberStatus.RECOGNIZED, rotated.value, rotated.expires_at)


def set_persistent_cookie(response, cookie_value: str, expires_at) -> None:
    """
    Attach the remember-device cookie to a response.

    The cookie is ``HttpOnly``, ``Secure`` and ``SameSite=Strict`` and never
    contains the API key - only the ``series_id:counter`` token.

    :param response: the Flask response to attach the cookie to
    :param cookie_value: the ``series_id:counter`` value
    :param expires_at: the cookie's expiry (a datetime)
    """
    # Emit both Max-Age and Expires: Max-Age is a relative lifetime that takes
    # precedence per RFC 6265 and is robust against client clock skew, which a
    # non-browser client (e.g. a credential provider relaying the cookie) needs;
    # Expires stays as a fallback. On a rotation this is the *remaining* lifetime,
    # since the window is fixed at issuance.
    max_age = max(0, int((expires_at - utc_now()).total_seconds()))
    response.set_cookie(PERSISTENT_COOKIE_NAME, cookie_value,
                        max_age=max_age, expires=expires_at,
                        httponly=True, secure=True, samesite="Strict")


def clear_persistent_cookie(response) -> None:
    """
    Remove the remember-device cookie from the client.

    Used when a presented cookie is invalid, expired or has been invalidated
    (e.g. after reuse detection), so the client stops sending it.

    :param response: the Flask response to clear the cookie on
    """
    response.delete_cookie(PERSISTENT_COOKIE_NAME, httponly=True, secure=True, samesite="Strict")


class CookieAction(NamedTuple):
    """
    What to do with the remember-device cookie on a response: ``kind`` is
    ``"set"`` (send ``value`` with ``expires_at``) or ``"clear"`` (drop it).
    See :func:`apply_cookie_action`.
    """
    kind: str
    value: str | None = None
    expires_at: datetime | None = None


def apply_cookie_action(response, action: CookieAction | None) -> None:
    """
    Apply a :class:`CookieAction` to a response: set, clear, or (for ``None``)
    leave the cookie untouched.

    :param response: the Flask response to act on
    :param action: the action to apply, or ``None`` for no change
    """
    if not action:
        return
    if action.kind == "set":
        set_persistent_cookie(response, action.value, action.expires_at)
    elif action.kind == "clear":
        clear_persistent_cookie(response)


def cleanup_expired_remembered_devices(chunk_size: int = None) -> int:
    """
    Delete expired remembered devices from the remembered_devices
    table.

    A presented cookie deletes its own expired row lazily during validation, but
    devices that are never presented again (abandoned or superseded) are only
    reclaimed here. Run this periodically and out of band from request handling
    (see the packaged crontab); the delete is chunked to avoid table-wide locks.

    :param chunk_size: delete in chunks of this size to avoid deadlocks (``None``
        runs a single delete statement)
    :return: the number of deleted rows
    """
    criterion = RememberedDevice.expires_at < utc_now()
    return delete_matching_rows(db.session, RememberedDevice.__table__, criterion, chunk_size)


def get_client_device(client_id: str, device_id: str) -> "RememberedDevice | None":
    """
    Return a single remembered device of a client by its public ``device_id``, or
    ``None``. Scoped to ``client_id`` so a client id cannot reach another client's
    device. The lookup uses ``device_id``, never the secret ``series_id``.

    :param client_id: the id of the API client the device must belong to
    :param device_id: the public management id of the device
    :return: the ``RememberedDevice`` or ``None``
    """
    return RememberedDevice.query.filter_by(device_id=device_id, client_id=client_id).first()


def count_user_devices(client_id: str, resolver: str, user_id: str, realm_id: int) -> int:
    """
    Number of **live** (non-expired) remembered devices a user has on a client,
    counted by the resolver-stable identity. Used to enforce a per-user device
    cap at issuance (see the ``remember_device_max_devices`` policy).

    :return: the count of the user's non-expired devices for this client
    """
    return RememberedDevice.query.filter(
        RememberedDevice.client_id == client_id,
        RememberedDevice.resolver == resolver,
        RememberedDevice.user_id == user_id,
        RememberedDevice.realm_id == realm_id,
        (RememberedDevice.expires_at.is_(None)) | (RememberedDevice.expires_at >= utc_now()),
    ).count()


def get_client_devices(client_id: str, realm_ids: "list[int] | set[int]" = None) -> list[RememberedDevice]:
    """
    Return the remembered devices belonging to a client, newest first, optionally
    restricted to a set of realms.

    :param client_id: the id of the API client
    :param realm_ids: if given, only devices bound to one of these realms are
        returned (used to scope a listing to a realm-restricted admin's allowed
        realms); ``None`` returns all, an empty set returns nothing
    :return: a list of ``RememberedDevice`` objects
    """
    query = RememberedDevice.query.filter_by(client_id=client_id)
    if realm_ids is not None:
        query = query.filter(RememberedDevice.realm_id.in_(realm_ids))
    return query.order_by(RememberedDevice.created_at.desc()).all()


def revoke_client_devices(client_id: str, realm_id: int = None, resolver: str = None,
                           user_id: str = None, realm_ids: "list[int]" = None) -> int:
    """
    Revoke (delete) remembered devices of a client in bulk, optionally narrowed
    to a single realm (``realm_id``), a set of realms (``realm_ids``), or a
    single ``(resolver, user_id, realm_id)`` identity.

    The delete is always scoped to ``client_id`` so a client's id can never be
    used to revoke another client's devices. Unlike collecting series ids in the
    caller and deleting them one by one, this is a single atomic server-side
    delete, so devices created between listing and revoking are still caught -
    which is the point of a bulk revoke (incident response).

    :param client_id: the id of the API client whose devices to revoke
    :param realm_id: if given, only devices bound to this realm are revoked
    :param resolver: if given (with ``user_id`` and ``realm_id``), narrows to one
        user's identity
    :param user_id: if given (with ``resolver`` and ``realm_id``), narrows to one
        user's identity
    :param realm_ids: if given, only devices bound to one of these realms are
        revoked (used to scope an unfiltered revoke to an admin's allowed realms
        in a single statement); an empty list revokes nothing
    :return: the number of revoked remembered devices
    """
    query = RememberedDevice.query.filter_by(client_id=client_id)
    if realm_id is not None:
        query = query.filter_by(realm_id=realm_id)
    if resolver is not None:
        query = query.filter_by(resolver=resolver)
    if user_id is not None:
        query = query.filter_by(user_id=user_id)
    if realm_ids is not None:
        query = query.filter(RememberedDevice.realm_id.in_(realm_ids))
    count = query.delete(synchronize_session=False)
    db.session.commit()
    return count


def revoke_devices(realm_id: int = None, resolver: str = None, user_id: str = None) -> int:
    """
    Revoke (delete) remembered devices across **all** clients, filtered by realm
    and/or a ``(resolver, user_id, realm_id)`` user identity. This is the
    client-independent counterpart to :func:`revoke_client_devices`, for
    realm-wide or per-user incident response and offboarding.

    Refuses to run with no filter at all, so it can never wipe every device on
    the system by omission.

    :param realm_id: if given, restrict to devices bound to this realm
    :param resolver: if given, restrict to this resolver (part of a user identity)
    :param user_id: if given, restrict to this resolver user id (part of a user identity)
    :return: the number of revoked remembered devices
    :raises ParameterError: if no filter is given
    """
    criteria = {}
    if realm_id is not None:
        criteria["realm_id"] = realm_id
    if resolver is not None:
        criteria["resolver"] = resolver
    if user_id is not None:
        criteria["user_id"] = user_id
    if not criteria:
        raise ParameterError("Refusing to revoke devices without a realm or user filter.")
    count = RememberedDevice.query.filter_by(**criteria).delete(synchronize_session=False)
    db.session.commit()
    return count


def devices_to_dicts(devices: list[RememberedDevice]) -> list[dict]:
    """
    Serialise a list of remembered devices, resolving all their realm names in a
    single query instead of one per device (avoiding an N+1 pattern when listing
    a client's devices).

    :param devices: the remembered devices to serialise
    :return: a list of JSON-serialisable dicts, in input order
    """
    realm_ids = {device.realm_id for device in devices if device.realm_id is not None}
    realm_names = {}
    if realm_ids:
        realm_names = {realm.id: realm.name
                       for realm in Realm.query.filter(Realm.id.in_(realm_ids)).all()}
    # Resolve each distinct user identity only once: a client accumulates a new
    # device per opt-in, so many rows share the same (resolver, user_id, realm),
    # and each login resolution hits the user store (an LDAP round trip for LDAP
    # resolvers). Deduping turns an N-device listing into one lookup per user.
    logins = {}
    for device in devices:
        realm_name = realm_names.get(device.realm_id)
        identity = (device.resolver, device.user_id, realm_name)
        if identity not in logins:
            logins[identity] = _resolve_login(device.resolver, device.user_id, realm_name)
    return [device_to_dict(device, realm_names=realm_names, logins=logins) for device in devices]


def device_to_dict(device: RememberedDevice, realm_names: dict[int, str] = None,
                   logins: dict = None) -> dict:
    """
    Serialise a remembered device for API output. Neither the secret
    ``series_id`` nor the rotating ``counter`` (i.e. no part of the cookie) is
    exposed; the device is identified only by its non-secret ``device_id``, which
    is what listing and revocation target.

    The bound user is reported both as the resolver-stable identity it is stored
    as (``resolver`` / ``user_id`` / ``realm``) and, best-effort, as the current
    ``user`` login for display. The login is resolved on read (it can change in
    the backing store), so it may be ``None`` if the account no longer resolves.

    :param device: the ``RememberedDevice`` to serialise
    :param realm_names: an optional pre-resolved ``{realm_id: name}`` map (see
        :func:`devices_to_dicts`); when omitted the realm name is looked up here
    :param logins: an optional pre-resolved ``{(resolver, user_id, realm): login}``
        map (see :func:`devices_to_dicts`); when omitted the login is resolved here
    :return: a JSON-serialisable dict
    """
    if realm_names is not None:
        realm_name = realm_names.get(device.realm_id)
    else:
        realm = Realm.query.filter_by(id=device.realm_id).first()
        realm_name = realm.name if realm else None
    if logins is not None:
        login = logins.get((device.resolver, device.user_id, realm_name))
    else:
        login = _resolve_login(device.resolver, device.user_id, realm_name)
    return {
        "device_id": device.device_id,
        "resolver": device.resolver,
        "user_id": device.user_id,
        "realm": realm_name,
        "user": login,
        "ip_address": device.ip_address,
        "user_agent": device.user_agent,
        "created_at": utc_isoformat(device.created_at),
        "last_used_at": utc_isoformat(device.last_used_at),
        "expires_at": utc_isoformat(device.expires_at),
    }


def _resolve_login(resolver: str, user_id: str, realm_name: str) -> str | None:
    """
    Best-effort resolution of a stored ``(resolver, user_id, realm)`` identity to
    the current login, for display only. Returns ``None`` if the account no
    longer resolves (e.g. it was deleted).
    """
    if not realm_name:
        return None
    # Imported lazily: privacyidea.lib.user pulls in a large part of the library.
    from privacyidea.lib.user import User
    try:
        return User(uid=user_id, resolver=resolver, realm=realm_name).login or None
    except Exception:  # noqa: BLE001 - display resolution must never break the listing
        return None
