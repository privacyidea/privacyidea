# (c) NetKnights GmbH 2026,  https://netknights.it
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
#
# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
__doc__ = """Per-request buffer of the conditional-access work this request will do.

One logical authentication produces its authentication-log row from any of a dozen call sites, and two post-policies
may afterwards *correct* that row. Rather than have each of them write (and re-write) independently, they stage a
:class:`~privacyidea.lib.conditional_access.authentication_log.PendingAuthEvent` here and the rows are written
together - the same shape the audit log uses with ``g.audit_object``.

The buffer lives on ``g``, so it is per app context (and thus per request) exactly like the conditional-access
session it writes on.
"""
import logging

from privacyidea.lib.conditional_access.authentication_log import PendingAuthEvent, write_authentication_events
from privacyidea.lib.framework import get_request_local_store

log = logging.getLogger(__name__)

# Key the context is cached under in the app-context-local store.
_CONTEXT_KEY = "conditional_access_context"


class ConditionalAccessContext:
    """
    The staged conditional-access work of one request: the authentication-log rows it will write.

    Rows are held as a list rather than a single row because one request can legitimately produce several: a
    ``push_wait`` login logs the challenge trigger and then the terminal outcome within the same blocking request.
    They are written in staging order, so the log reconstructs the sequence.
    """

    def __init__(self):
        self.pending: list[PendingAuthEvent] = []

    @property
    def has_data(self) -> bool:
        """Whether anything has been staged at all (written or not). Mirrors ``audit_object.has_data``."""
        return bool(self.pending)

    @property
    def unwritten(self) -> list[PendingAuthEvent]:
        """The staged events that have not been persisted yet, in staging order."""
        return [event for event in self.pending if event.row_id is None]

    def stage(self, event: PendingAuthEvent) -> PendingAuthEvent:
        """
        Add *event* to this request's buffer and return it, so the caller can keep the handle - a later stage can
        still amend the event, and its ``row_id`` becomes available once it is written.
        """
        self.pending.append(event)
        return event

    def flush(self) -> bool:
        """
        Write every staged-but-unwritten event as one transaction, oldest first.

        Idempotent: an event that already carries a ``row_id`` is skipped, so calling this twice writes nothing the
        second time. Guarded internally - a failure is logged and swallowed, and the affected events simply keep
        ``row_id is None``.

        :return: whether everything staged is now persisted
        """
        return write_authentication_events(self.unwritten)


def get_ca_context() -> ConditionalAccessContext:
    """
    Return this app context's :class:`ConditionalAccessContext`, creating it on first use.
    """
    store = get_request_local_store()
    context = store.get(_CONTEXT_KEY)
    if context is None:
        context = ConditionalAccessContext()
        store[_CONTEXT_KEY] = context
    return context


def reset_ca_context() -> None:
    """
    Discard this app context's buffer, staged events and all, so the next :func:`get_ca_context` starts empty.

    A real request gets a fresh ``g`` and therefore a fresh buffer; this exists for the test suite, which pushes one
    app context per test class and would otherwise carry one test's staged events into the next. Deliberately
    *discards* rather than flushes: leftovers from a test body are not rows anybody asked to persist.
    """
    get_request_local_store().pop(_CONTEXT_KEY, None)
