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
"""
Assertion helpers for the conditional-access authentication log, shared across
test modules. Registered for pytest assert-rewriting in tests/conftest.py so the
plain ``assert`` statements still produce rich failure diffs.
"""
from collections import Counter

from privacyidea.lib.conditional_access.authentication_log import get_authentication_logs


class AuthLogEntries(dict):
    """
    The result of :func:`assert_authentication_log`.

    Behaves as a ``{event_type: entry}`` mapping for the common case of looking up a uniquely occurring event by
    name, e.g. ``entries[AuthEventType.LOGIN_SUCCESS]``. The full ordered list of entries is available as ``.all``
    for flows where the same event type occurs more than once. Indexing a duplicated event type by name raises
    (instead of silently returning one of the occurrences), so a specific occurrence must be asserted via
    ``.all[i]``.
    """
    def __init__(self, entries):
        self.all = list(entries)
        self._counts = Counter(entry.event_type for entry in self.all)
        super().__init__((entry.event_type, entry) for entry in self.all)

    def __getitem__(self, event_type):
        if self._counts[event_type] > 1:
            raise AssertionError(
                f"{event_type!s} occurs {self._counts[event_type]} times in the authentication log; assert a "
                f"specific occurrence via .all[i] rather than indexing by event type")
        return super().__getitem__(event_type)


def assert_authentication_log(event_types, transaction_id=None):
    """
    Assert that the authentication log holds exactly the given ordered list of event types, and return the entries.

    The returned :class:`AuthLogEntries` maps event type -> entry for looking up a uniquely occurring event by name
    (``entries[AuthEventType.LOGIN_SUCCESS]``) and exposes the full ordered list as ``.all``. When the same event
    type occurs more than once, assert a specific occurrence via ``.all[i]`` — indexing a duplicated type by name
    raises rather than silently returning one of them.

    :param event_types: the expected AuthEventType values, ordered by creation
    :param transaction_id: if given, only entries of that transaction are checked
        (correlates a triggered challenge with its answer); otherwise all entries are
        checked (clear the log before the request for an exact match)
    :return: an :class:`AuthLogEntries` (a dict of event type -> entry, plus the ordered ``.all`` list)
    """
    if transaction_id is not None:
        entries = get_authentication_logs(transaction_id=transaction_id)
    else:
        entries = get_authentication_logs()
    assert [entry.event_type for entry in entries] == event_types
    return AuthLogEntries(entries)


def assert_authentication_log_entry(entry, user=None, serial=None, client_label=None, other_info=None):
    """
    Assert a single authentication-log entry carries the expected attributes.

    :param entry: an AuthenticationLog entry (e.g. one returned by :func:`assert_authentication_log`)
    :param user: the entry must carry this user's (resolver, uid, realm); when no user is given, the entry must carry
        no user (all three None)
    :param serial: the entry must carry this serial (None means no serial)
    :param client_label: the entry must carry this client_label (None means no client_label)
    :param other_info: the entry must carry this other_info (None means no other_info)
    """
    expected_user = (user.resolver, user.uid, user.realm) if user is not None else (None, None, None)
    assert (entry.resolver, entry.uid, entry.realm) == expected_user
    assert entry.serial == serial
    assert entry.client_label == client_label
    assert entry.other_info == other_info
