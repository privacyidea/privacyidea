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
The request context the conditional-access engine evaluates against.

:class:`CAContext` is the single parameter object carrying everything the engine
knows about the request under evaluation. It exists so that a new evaluation
input - an API-key status, a request header - is a new *field*
rather than a new parameter on every entry point and every internal helper along
the way. The engine's two entry points
(:func:`~privacyidea.lib.conditional_access.engine.evaluate_access_decision` and
:func:`~privacyidea.lib.conditional_access.engine.evaluate_conditional_access_policies`)
take it instead of the individual values.

It is deliberately free of Flask: the lib layer must stay usable outside a
request (an authentication event can be recorded from outside a view, e.g. the
push_wait flow). The API-layer factory
:func:`~privacyidea.api.lib.utils.build_ca_context` reads ``g`` / ``request`` and
fills the fields in; outside a request context the request-scoped fields are
simply ``None``.

Every field is optional. A field that could not be determined is ``None``, and it
is the *consumer's* job to decide what that means - a policy condition declares
whether missing data makes it match or not match, and the engine's counting paths
already skip a subject they cannot identify (an unresolved user, an absent source
IP). Nothing here raises.
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from privacyidea.lib.user import User


@dataclass(frozen=True)
class CAContext:
    """
    What the conditional-access engine knows about the request being evaluated.

    Frozen because the context describes one request and must read identically at
    every point of the evaluation: the pre-auth decision, the counting, and the
    post-response actions all have to agree on who and what they are judging.

    :ivar user: the authenticating user. ``user``-target policies key their count
        and their lock on this user's ``(resolver, uid, realm)`` tuple and
        therefore ignore an unresolved one; ``source_ip``-target policies act
        regardless of it.
    :ivar source_ip: the resolved client IP, as used by the audit log.
        ``source_ip``-target policies count and block on it.
    :ivar endpoint: the endpoint the request authenticates against, as its path
        (``/auth``, ``/validate/check``, ``/ttype/push``). An ``ENDPOINT``
        condition compares against it, so a policy can restrict itself to - or
        exempt - one way in; it is the same value the authentication log's
        ``endpoint`` column stores, which is what lets such a condition also scope
        the counting query. See
        :func:`~privacyidea.api.lib.utils.request_endpoint`.
    :ivar user_role: the principal's role
        (:class:`~privacyidea.lib.conditional_access.authentication_log.AuthLogUserRole`),
        as recorded in the authentication log. Pre-auth this is the *claimed*
        role - an admin realm, or a local admin name that exists - since no
        credential has been checked yet; that is what lets a break-glass condition
        exempt an emergency admin from a pre-auth DENY. See
        :func:`~privacyidea.api.lib.utils.build_ca_context` for where it comes
        from.
    :ivar use_default_error_message: Whether a rejection with no error message of its own falls back to the
        default wording for what it did (the ``show_default_ca_error_message`` policy), rather than saying nothing.
        Not about the generic "Authentication failed." - that is what a rejection with nothing to say ends up
        carrying, decided in the API layer. Resolved there too, because matching a policy needs Flask and this
        package deliberately does not.
    Note what is deliberately *absent*: the authentication log's ``client_label``
    (the ``client_id`` parameter, falling back to the User-Agent header). It
    identifies the calling application well enough to be worth recording
    forensically, but a client picks it itself, so it must not gate a security
    decision - a policy scoped to it would be bypassed by editing a header. The
    calling application becomes a usable condition input once API keys give it an
    identity the server verifies.
    """
    user: "User | None" = None
    source_ip: str | None = None
    endpoint: str | None = None
    user_role: str | None = None
    use_default_error_message: bool = False
