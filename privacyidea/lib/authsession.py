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

from flask_babel import _

from privacyidea.lib.error import AuthError
from privacyidea.models import AuthSession
from privacyidea.models.utils import utc_now

log = logging.getLogger(__name__)

# Name of the cookie carrying the persistent session token.
PERSISTENT_COOKIE_NAME = "pi_remember_device"
# Number of random bytes in a series id.
SERIES_ID_BYTES = 32


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


def validate_and_rotate(cookie_value: str, client_id: str) -> str | None:
    """
    Validate a persistent-session cookie and rotate its counter.

    The session is looked up by ``series_id`` **and** ``client_id`` so a cookie
    only ever validates for the client it was issued to.

    * If no matching (or a expired) session exists, ``None`` is returned - the
      caller should treat the request as if no persistent session was presented.
    * If a session exists but the presented counter does not match the stored
      one, the token has been replayed (stolen cookie). The series is deleted
      and an ``AuthError`` is raised.
    * Otherwise the stored counter is incremented, ``last_used_at`` is updated
      and the new cookie value plus its expiry are returned.

    :param cookie_value: the raw cookie value from the request
    :param client_id: the id of the API client making the request (g.client_id)
    :return: a ``(new_cookie_value, expires_at)`` tuple on success, or ``None``
        if there is no valid session to rotate
    :raises AuthError: if cookie reuse (theft) is detected
    """
    series_id, counter = parse_cookie(cookie_value)
    if not series_id or counter is None:
        return None

    session = AuthSession.query.filter_by(series_id=series_id, client_id=client_id).first()
    if not session:
        return None

    if session.expires_at and session.expires_at < utc_now():
        log.info(f"Persistent session {series_id!r} expired; removing it.")
        session.delete()
        return None

    if session.counter != counter:
        # A valid series id with a stale counter means the cookie was replayed.
        # Invalidate the whole series so neither the legitimate client nor the
        # attacker can use it again.
        log.warning(f"Persistent session token reuse detected for series {series_id!r} "
                    f"(client {client_id!r}); deleting the session.")
        session.delete()
        raise AuthError(_("Authentication failure. Session token reuse detected."))

    session.counter += 1
    session.last_used_at = utc_now()
    session.save()
    return build_cookie_value(series_id, session.counter), session.expires_at


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
