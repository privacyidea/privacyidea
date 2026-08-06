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
sessions using a rotating-token scheme.

A session is represented by a cookie of the form ``series_id:counter``. The
``series_id`` identifies the row in the ``auth_sessions`` table; the ``counter``
is bumped on every use, both in the cookie and in the database. If a request
presents a valid ``series_id`` with a stale ``counter``, the token has been
replayed - a sign the cookie was stolen - so the whole series is deleted and
authentication fails.

The cookie never carries the API key. A session is bound to a specific API
client via ``client_id``, which is matched against ``g.client_id`` (set by the
API-key middleware) on every validation.
"""
import enum
import logging
import secrets
from datetime import datetime, timedelta
from typing import NamedTuple, TYPE_CHECKING

from flask_babel import _

from privacyidea.lib.error import AuthError, ParameterError, ResourceNotFoundError
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.sqlutils import delete_matching_rows
from privacyidea.models import AuthSession, Realm, db

if TYPE_CHECKING:
    from privacyidea.lib.user import User
from privacyidea.models.utils import utc_now

log = logging.getLogger(__name__)

# Name of the cookie carrying the persistent session token.
PERSISTENT_COOKIE_NAME = "pi_remember_device"
# Number of random bytes in a series id.
SERIES_ID_BYTES = 32
# Default grace window (seconds) during which the immediately-previous counter
# is still accepted, to tolerate concurrent/duplicate requests without treating
# them as cookie theft. Overridable via PI_REMEMBER_DEVICE_GRACE_SECONDS in
# pi.cfg; set to 0 for strict fail-secure (no grace).
DEFAULT_GRACE_SECONDS = 10
# Column limits of the identity binding, mirroring the auth_sessions model. The
# identity is a lookup key, so it is stored and matched verbatim (never
# truncated); a user whose identity would overflow simply gets no session.
RESOLVER_MAX_LEN = 120
USER_ID_MAX_LEN = 320
# Hard cap on a session's configured validity, so an absurd
# remember_device_validity policy value cannot overflow timedelta.
MAX_SESSION_VALIDITY_DAYS = 3650


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


def parse_cookie(cookie_value: str) -> tuple[str, int] | tuple[None, None]:
    """
    Parse a persistent-session cookie of the form ``series_id:counter``.

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


def session_user_identity(user: "User | None") -> "UserIdentity | None":
    """
    Build the resolver-stable identity a persistent session binds to.

    :param user: the ``User`` object (or None)
    :return: a :class:`UserIdentity`, or ``None`` if the user does not resolve to
        one - a userless (serial-only) auth, or an account that no longer exists
    """
    if not user or not user.resolver or not user.uid or not user.realm_id:
        return None
    resolver, user_id = user.resolver, str(user.uid)
    if len(resolver) > RESOLVER_MAX_LEN or len(user_id) > USER_ID_MAX_LEN:
        # The identity is a lookup key stored verbatim; one that does not fit the
        # column could never be matched, so bind no session to it rather than
        # issue a cookie that is silently never recognised.
        log.warning(f"Remember-device unavailable for a user of realm_id {user.realm_id}: "
                    f"identity exceeds the storable length.")
        return None
    return UserIdentity(resolver, user_id, user.realm_id)


def create_auth_session(identity: "UserIdentity", client_id: str, ip_address: str = None,
                        user_agent: str = None, validity_days: int = None) -> tuple[AuthSession, str]:
    """
    Create and persist a new persistent authentication session.

    :param identity: the resolver-stable identity of the authenticated user (see
        :func:`session_user_identity`)
    :param client_id: id of the API client the session is bound to
    :param ip_address: the client IP address the session was created from
    :param user_agent: the user agent the session was created from
    :param validity_days: session lifetime in days; ``None`` (or a
        non-positive value) uses the model default (``DEFAULT_SESSION_VALIDITY``)
    :return: a tuple of the stored ``AuthSession`` and the cookie value
        (``series_id:1``) to send to the client
    """
    series_id = secrets.token_urlsafe(SERIES_ID_BYTES)
    if validity_days and validity_days > 0:
        # Cap the validity so an absurd policy value cannot overflow timedelta and
        # turn an already-successful auth into a 500.
        expires_at = utc_now() + timedelta(days=min(validity_days, MAX_SESSION_VALIDITY_DAYS))
    else:
        expires_at = None
    # The identity is a lookup key and is stored verbatim (session_user_identity
    # has already ensured it fits its columns). Only the free-form metadata
    # (ip/user agent) is truncated, so an over-long value there can never raise on
    # save and turn an already-successful auth into a 500.
    session = AuthSession(series_id=series_id, client_id=client_id,
                          resolver=identity.resolver, user_id=identity.user_id,
                          realm_id=identity.realm_id,
                          ip_address=(ip_address or None) and ip_address[:64],
                          user_agent=(user_agent or None) and user_agent[:255], counter=1,
                          expires_at=expires_at)
    session.save()
    return session, build_cookie_value(series_id, session.counter)


class ValidSession(NamedTuple):
    """
    A live session matched by :func:`get_valid_session`.

    ``is_grace`` is ``False`` for a fresh use (the caller should rotate the
    token) and ``True`` for a tolerated grace-window hit (the caller must
    **not** rotate).
    """
    session: AuthSession
    is_grace: bool


def get_valid_session(cookie_value: str, client_id: str, identity: "UserIdentity",
                      client_ip: str = None) -> "ValidSession | None":
    """
    Look up and validate a persistent-session cookie **without** rotating it.

    The session is matched on ``series_id`` **and** ``client_id`` **and** the
    full user identity (``resolver`` / ``user_id`` / ``realm_id``) so a cookie
    only ever validates for the client it was issued to and the user it was
    issued for.

    * Returns ``None`` if no matching session exists or it has expired (an
      expired session is deleted).
    * If the presented counter matches the stored one, returns
      ``(session, False)`` (a fresh use; the caller should rotate it).
    * If the presented counter is the immediately-previous one and the request
      arrives within the grace window from the same source IP, returns
      ``(session, True)`` - a tolerated concurrent/duplicate request. The caller
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
        (see :func:`session_user_identity`)
    :param client_ip: the source IP of the request; used to bound the grace
        window (a grace hit must come from the IP the session was last used from)
    :return: ``None`` if there is no live session for this cookie (unknown or
        expired); otherwise a :class:`ValidSession` ``(session, is_grace)`` where
        ``is_grace`` is ``False`` for a fresh use (the caller should rotate the
        token) and ``True`` for a tolerated grace-window hit (the caller must
        **not** rotate - it converges on the current token)
    :raises AuthError: if cookie reuse (theft) is detected
    """
    series_id, counter = parse_cookie(cookie_value)
    if not series_id or counter is None or not identity:
        return None

    session = AuthSession.query.filter_by(series_id=series_id, client_id=client_id,
                                          resolver=identity.resolver, user_id=identity.user_id,
                                          realm_id=identity.realm_id).first()
    if not session:
        return None

    if session.expires_at and session.expires_at < utc_now():
        # Never log the series_id: it is the secret half of the cookie. Correlate
        # on the (non-secret) client_id instead.
        log.info(f"Persistent session for client {client_id!r} expired; removing it.")
        session.delete()
        return None

    if session.counter == counter:
        return ValidSession(session, False)

    if _is_within_grace(session, counter, client_ip):
        # Concurrent/duplicate request presenting the just-superseded counter -
        # tolerate it without rotating (single-step, time- and IP-bounded).
        # last_used_at is deliberately NOT refreshed here: the window stays
        # anchored to the rotation, so a client that never persists the rotated
        # cookie is tolerated only briefly and then treated as theft, rather than
        # being kept alive indefinitely (which would defeat rotation).
        log.debug(f"Persistent session for client {client_id!r}: accepting previous "
                  f"counter within the grace window.")
        return ValidSession(session, True)

    # Any other counter mismatch means the cookie was replayed. Invalidate the
    # whole series so neither the legitimate client nor the attacker can use it.
    log.warning(f"Persistent session token reuse detected for client {client_id!r}; "
                f"deleting the session.")
    session.delete()
    raise AuthError(_("Authentication failure. Session token reuse detected."))


def _is_within_grace(session: AuthSession, counter: int, client_ip: str) -> bool:
    """
    Whether a presented ``counter`` qualifies for the grace window: it must be
    exactly the immediately-previous counter, the session must have been used
    within the grace window, and (when both are known) the source IP must match
    the one the session was last used from.
    """
    grace = _grace_window_seconds()
    if grace <= 0 or counter != session.counter - 1 or session.last_used_at is None:
        return False
    if (utc_now() - session.last_used_at).total_seconds() > grace:
        return False
    if session.ip_address and client_ip and session.ip_address != client_ip:
        return False
    return True


def rotate_session(session: AuthSession) -> tuple[str, datetime]:
    """
    Rotate a validated session: bump the counter, refresh ``last_used_at`` and
    return the new cookie value plus its expiry.

    :param session: a session returned by :func:`get_valid_session`
    :return: a ``(new_cookie_value, expires_at)`` tuple
    """
    session.counter += 1
    session.last_used_at = utc_now()
    session.save()
    return build_cookie_value(session.series_id, session.counter), session.expires_at


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
    * ``MISS`` - no live session for this cookie (unknown or expired); the caller
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
    :func:`get_valid_session`) and rotate it on a fresh use. This is the single
    place a presented cookie is consumed.

    Recognition only: this performs no authentication, triggers no challenge and
    writes no audit record - the caller decides what to do with the outcome.

    :param cookie_value: the raw cookie value from the request
    :param client_id: the id of the API client making the request (g.client_id)
    :param identity: the resolver-stable identity the cookie must be bound to
        (see :func:`session_user_identity`)
    :param client_ip: the source IP of the request (bounds the grace window)
    :return: a :class:`ConsumeResult`. Theft is reported as ``status ==
        "theft"`` (the series has already been invalidated) rather than raised,
        so the caller can answer "not recognised" uniformly.
    """
    try:
        result = get_valid_session(cookie_value, client_id, identity, client_ip)
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
            other = AuthSession.query.filter_by(series_id=series_id, client_id=client_id).first()
            if other and not (other.expires_at and other.expires_at < utc_now()):
                return ConsumeResult(RememberStatus.FOREIGN, None, None)
        return ConsumeResult(RememberStatus.MISS, None, None)
    if result.is_grace:
        return ConsumeResult(RememberStatus.GRACE, None, None)
    new_cookie, expires_at = rotate_session(result.session)
    return ConsumeResult(RememberStatus.RECOGNIZED, new_cookie, expires_at)


def set_persistent_cookie(response, cookie_value: str, expires_at) -> None:
    """
    Attach the persistent-session cookie to a response.

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
    Remove the persistent-session cookie from the client.

    Used when a presented cookie is invalid, expired or has been invalidated
    (e.g. after reuse detection), so the client stops sending it.

    :param response: the Flask response to clear the cookie on
    """
    response.delete_cookie(PERSISTENT_COOKIE_NAME, httponly=True, secure=True, samesite="Strict")


def cleanup_expired_auth_sessions(chunk_size: int = None) -> int:
    """
    Delete expired persistent authentication sessions from the auth_sessions
    table.

    A presented cookie deletes its own expired row lazily during validation, but
    sessions that are never presented again (abandoned or superseded) are only
    reclaimed here. Run this periodically and out of band from request handling
    (see the packaged crontab); the delete is chunked to avoid table-wide locks.

    :param chunk_size: delete in chunks of this size to avoid deadlocks (``None``
        runs a single delete statement)
    :return: the number of deleted rows
    """
    criterion = AuthSession.expires_at < utc_now()
    return delete_matching_rows(db.session, AuthSession.__table__, criterion, chunk_size)


def get_client_sessions(client_id: str) -> list[AuthSession]:
    """
    Return all persistent sessions belonging to a client, newest first.

    :param client_id: the id of the API client
    :return: a list of ``AuthSession`` objects
    """
    return AuthSession.query.filter_by(client_id=client_id).order_by(AuthSession.created_at.desc()).all()


def revoke_client_session(client_id: str, series_id: str) -> str:
    """
    Revoke (delete) a single persistent session of a client.

    The lookup is scoped to ``client_id`` so a client's id can never be used to
    revoke a session that belongs to a different client.

    :param client_id: the id of the API client the session must belong to
    :param series_id: the series id of the session to revoke
    :return: the series id of the revoked session
    :raises ResourceNotFoundError: if no such session exists for this client
    """
    session = AuthSession.query.filter_by(series_id=series_id, client_id=client_id).first()
    if not session:
        raise ResourceNotFoundError(f"The session {series_id!r} does not exist for this client.")
    session.delete()
    return series_id


def revoke_client_sessions(client_id: str, realm_id: int = None, resolver: str = None,
                           user_id: str = None) -> int:
    """
    Revoke (delete) persistent sessions of a client in bulk, optionally narrowed
    to a single realm or a single ``(resolver, user_id, realm_id)`` identity.

    The delete is always scoped to ``client_id`` so a client's id can never be
    used to revoke another client's sessions. Unlike collecting series ids in the
    caller and deleting them one by one, this is a single atomic server-side
    delete, so sessions created between listing and revoking are still caught -
    which is the point of a bulk revoke (incident response).

    :param client_id: the id of the API client whose sessions to revoke
    :param realm_id: if given, only sessions bound to this realm are revoked
    :param resolver: if given (with ``user_id`` and ``realm_id``), narrows to one
        user's identity
    :param user_id: if given (with ``resolver`` and ``realm_id``), narrows to one
        user's identity
    :return: the number of revoked sessions
    """
    criteria = {"client_id": client_id}
    if realm_id is not None:
        criteria["realm_id"] = realm_id
    if resolver is not None:
        criteria["resolver"] = resolver
    if user_id is not None:
        criteria["user_id"] = user_id
    count = AuthSession.query.filter_by(**criteria).delete(synchronize_session=False)
    db.session.commit()
    return count


def revoke_sessions(realm_id: int = None, resolver: str = None, user_id: str = None) -> int:
    """
    Revoke (delete) persistent sessions across **all** clients, filtered by realm
    and/or a ``(resolver, user_id, realm_id)`` user identity. This is the
    client-independent counterpart to :func:`revoke_client_sessions`, for
    realm-wide or per-user incident response and offboarding.

    Refuses to run with no filter at all, so it can never wipe every session on
    the system by omission.

    :param realm_id: if given, restrict to sessions bound to this realm
    :param resolver: if given, restrict to this resolver (part of a user identity)
    :param user_id: if given, restrict to this resolver user id (part of a user identity)
    :return: the number of revoked sessions
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
        raise ParameterError("Refusing to revoke sessions without a realm or user filter.")
    count = AuthSession.query.filter_by(**criteria).delete(synchronize_session=False)
    db.session.commit()
    return count


def session_to_dict(session: AuthSession) -> dict:
    """
    Serialise a persistent session for API output. The rotating token
    (``counter``) is intentionally not exposed; ``series_id`` is only an
    identifier used to target revocation.

    The bound user is reported both as the resolver-stable identity it is stored
    as (``resolver`` / ``user_id`` / ``realm``) and, best-effort, as the current
    ``user`` login for display. The login is resolved on read (it can change in
    the backing store), so it may be ``None`` if the account no longer resolves.

    :param session: the ``AuthSession`` to serialise
    :return: a JSON-serialisable dict
    """
    realm = Realm.query.filter_by(id=session.realm_id).first()
    realm_name = realm.name if realm else None
    return {
        "series_id": session.series_id,
        "resolver": session.resolver,
        "user_id": session.user_id,
        "realm": realm_name,
        "user": _resolve_login(session.resolver, session.user_id, realm_name),
        "ip_address": session.ip_address,
        "user_agent": session.user_agent,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "last_used_at": session.last_used_at.isoformat() if session.last_used_at else None,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
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
