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
import logging
import secrets
from datetime import datetime

from flask_babel import _

from privacyidea.lib.error import AuthError, ResourceNotFoundError
from privacyidea.lib.framework import get_app_config_value
from privacyidea.models import AuthSession
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


def create_auth_session(user_id: str, client_id: str, ip_address: str = None,
                        user_agent: str = None) -> tuple[AuthSession, str]:
    """
    Create and persist a new persistent authentication session.

    :param user_id: identifier of the authenticated user
    :param client_id: id of the API client the session is bound to
    :param ip_address: the client IP address the session was created from
    :param user_agent: the user agent the session was created from
    :return: a tuple of the stored ``AuthSession`` and the cookie value
        (``series_id:1``) to send to the client
    """
    series_id = secrets.token_urlsafe(SERIES_ID_BYTES)
    session = AuthSession(series_id=series_id, user_id=user_id, client_id=client_id,
                          ip_address=ip_address, user_agent=user_agent, counter=1)
    session.save()
    return session, build_cookie_value(series_id, session.counter)


def session_user_id(user) -> str | None:
    """
    Build the stable identifier a persistent session is bound to for a user.

    A remembered device is bound to the exact authenticating user (login **and**
    realm), so a cookie can only ever authenticate the user it was issued for -
    never a different user who happens to share the same API client / device.

    :param user: the ``User`` object (or None)
    :return: ``"login@realm"`` or ``None`` if there is no resolvable user
    """
    if not user or not getattr(user, "login", None):
        return None
    return f"{user.login}@{user.realm or ''}"


def get_valid_session(cookie_value: str, client_id: str, user_id: str,
                      client_ip: str = None) -> tuple[AuthSession, bool] | None:
    """
    Look up and validate a persistent-session cookie **without** rotating it.

    The session is matched on ``series_id`` **and** ``client_id`` **and**
    ``user_id`` so a cookie only ever validates for the client it was issued to
    and the user it was issued for.

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

    :param cookie_value: the raw cookie value from the request
    :param client_id: the id of the API client making the request (g.client_id)
    :param user_id: the identifier of the authenticating user (see
        :func:`session_user_id`)
    :param client_ip: the source IP of the request; used to bound the grace
        window (a grace hit must come from the IP the session was last used from)
    :raises AuthError: if cookie reuse (theft) is detected
    """
    series_id, counter = parse_cookie(cookie_value)
    if not series_id or counter is None or not user_id:
        return None

    session = AuthSession.query.filter_by(series_id=series_id, client_id=client_id,
                                          user_id=user_id).first()
    if not session:
        return None

    if session.expires_at and session.expires_at < utc_now():
        log.info(f"Persistent session {series_id!r} expired; removing it.")
        session.delete()
        return None

    if session.counter == counter:
        return session, False

    if _is_within_grace(session, counter, client_ip):
        # Concurrent/duplicate request presenting the just-superseded counter -
        # tolerate it without rotating (single-step, time- and IP-bounded).
        log.debug(f"Persistent session {series_id!r}: accepting previous counter "
                  f"within the grace window.")
        return session, True

    # Any other counter mismatch means the cookie was replayed. Invalidate the
    # whole series so neither the legitimate client nor the attacker can use it.
    log.warning(f"Persistent session token reuse detected for series {series_id!r} "
                f"(client {client_id!r}); deleting the session.")
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


def validate_and_rotate(cookie_value: str, client_id: str, user_id: str,
                        client_ip: str = None) -> tuple[str, datetime] | None:
    """
    Convenience wrapper: validate a cookie (see :func:`get_valid_session`) and
    rotate it on a fresh use. A grace-window (concurrent duplicate) hit is not
    rotated - the current cookie value is returned unchanged.

    :return: a ``(cookie_value, expires_at)`` tuple on success, or ``None`` if
        there is no valid session
    :raises AuthError: if cookie reuse (theft) is detected
    """
    result = get_valid_session(cookie_value, client_id, user_id, client_ip)
    if not result:
        return None
    session, is_grace = result
    if is_grace:
        return build_cookie_value(session.series_id, session.counter), session.expires_at
    return rotate_session(session)


def set_persistent_cookie(response, cookie_value: str, expires_at) -> None:
    """
    Attach the persistent-session cookie to a response.

    The cookie is ``HttpOnly``, ``Secure`` and ``SameSite=Strict`` and never
    contains the API key - only the ``series_id:counter`` token.

    :param response: the Flask response to attach the cookie to
    :param cookie_value: the ``series_id:counter`` value
    :param expires_at: the cookie's expiry (a datetime)
    """
    response.set_cookie(PERSISTENT_COOKIE_NAME, cookie_value,
                        expires=expires_at, httponly=True, secure=True, samesite="Strict")


def clear_persistent_cookie(response) -> None:
    """
    Remove the persistent-session cookie from the client.

    Used when a presented cookie is invalid, expired or has been invalidated
    (e.g. after reuse detection), so the client stops sending it.

    :param response: the Flask response to clear the cookie on
    """
    response.delete_cookie(PERSISTENT_COOKIE_NAME, httponly=True, secure=True, samesite="Strict")


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


def session_to_dict(session: AuthSession) -> dict:
    """
    Serialise a persistent session for API output. The rotating token
    (``counter``) is intentionally not exposed; ``series_id`` is only an
    identifier used to target revocation.

    :param session: the ``AuthSession`` to serialise
    :return: a JSON-serialisable dict
    """
    return {
        "series_id": session.series_id,
        "user_id": session.user_id,
        "ip_address": session.ip_address,
        "user_agent": session.user_agent,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "last_used_at": session.last_used_at.isoformat() if session.last_used_at else None,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
    }
