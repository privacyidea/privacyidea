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
from typing import Tuple

from privacyidea.lib.conditional_access.authentication_log import get_authentication_logs
from privacyidea.lib.user import User
from privacyidea.models import AuthenticationLog


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


def assert_authentication_log_entry(entry: AuthenticationLog, user: User = None,
                                    serials: set[str] = None,
                                    client_label: str = None, other_info: dict = None,
                                    transaction_id: str = None, source_ip: str = None):
    """
    Assert a single authentication-log entry carries the expected attributes.

    Every column of the authentication_log table is checked. The nullable columns default to their database default
    (None), so a column that is not passed is asserted to be empty — this enforces that a row carries *only* the data
    it should and no leftover values. The auto-populated id and timestamp are checked for presence. The non-nullable
    event_type is covered by the ordered list in :func:`assert_authentication_log`.

    :param entry: an AuthenticationLog entry (e.g. one returned by :func:`assert_authentication_log`)
    :param user: the expected identity. All four fields — resolver, uid, realm, and username (login) — are read from
        this object, with empty strings normalised to None. Pass a fully resolved User for authenticated requests;
        pass a partially resolved User (resolver and uid will be None, realm and login still set) for cases where the
        user was not found in a resolver (e.g. USER_UNKNOWN or PASSONNOUSER). Pass None when no identity at all is
        expected (e.g. userless challenges or local-admin logins).
    :param serials: the entry must carry a comma separated list of these serials (default None: no serial)
    :param client_label: the entry must carry this client_label (default None: no client_label)
    :param other_info: the entry must carry this other_info (default None: no other_info)
    :param transaction_id: the entry must carry this transaction_id (default None: no transaction_id)
    :param source_ip: the entry must carry this source_ip (default None: no source_ip)
    """
    expected_resolver = (user.resolver or None) if user is not None else None
    expected_uid = (user.uid or None) if user is not None else None
    expected_realm = (user.realm or None) if user is not None else None
    expected_username = (user.login or None) if user is not None else None
    assert (entry.resolver, entry.uid, entry.realm) == (expected_resolver, expected_uid, expected_realm)
    assert entry.username == expected_username
    assert entry.client_label == client_label
    assert entry.other_info == other_info
    assert entry.transaction_id == transaction_id
    assert entry.source_ip == source_ip
    entry_serials = entry.serial
    if entry_serials is not None:
        entry_serials = set(entry_serials.split(","))
    assert entry_serials == serials

    # The id (primary key) and timestamp are populated by the database / model on insert and must always be present.
    assert entry.id is not None
    assert entry.timestamp is not None
