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
Shared test support for the conditional-access authentication log: the :class:`AuthLogTestCase` base fixture and the
``assert_authentication_log*`` helpers, used across the authentication-log test modules. Registered for pytest
assert-rewriting in tests/conftest.py so the plain ``assert`` statements still produce rich failure diffs.
"""
import datetime
import json
from collections import Counter

from flask import Response

from privacyidea.lib.cache import redis_feature_enabled
from privacyidea.lib.cache.redis import redis_client_for_feature, _TXN_KEY
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.conditional_access.authentication_log import get_authentication_logs, AuthLogUserRole
from privacyidea.lib.policy import set_policy, SCOPE, PolicyAction
from privacyidea.lib.token import init_token, remove_token, get_tokens
from privacyidea.lib.user import User
from privacyidea.models import AuthenticationLog, Audit, db
from privacyidea.models.utils import utc_now
from .base import MyApiTestCase


class AuthLogTestCase(MyApiTestCase):
    """
    Shared fixture for the authentication-log tests: a resolvable user ``cornelius`` with one HOTP token, a clean
    authentication log around each test, and thin request/challenge helpers. Subclassed by the recording-behaviour
    tests (one subclass per authenticating endpoint) and by the /authenticationlog/ API tests.
    """

    serial = "AUTHLOG_HOTP"
    second_serial = "AUTHLOG_HOTP2"
    username = "cornelius"
    pin = "pin"

    def setUp(self) -> None:
        super().setUp()
        self.setUp_user_realms()
        self.user = User(self.username, self.realm1)
        init_token({"serial": self.serial, "type": "hotp", "otpkey": self.otpkey, "pin": self.pin},
                   user=self.user)
        self._clear_log()
        self._clear_audit_log()

    def tearDown(self) -> None:
        for serial in (self.serial, self.second_serial):
            if get_tokens(serial=serial):
                remove_token(serial)
        self._clear_log()
        self._clear_audit_log()
        super().tearDown()

    @staticmethod
    def _clear_log() -> None:
        db.session.query(AuthenticationLog).delete()
        db.session.commit()

    @staticmethod
    def _clear_audit_log() -> None:
        # Cleared only at the test boundary (setUp/tearDown), never mid-test: the classic AUTHMAXFAIL /
        # AUTHMAXSUCCESS policies count from the audit log over a time window, so leftover entries from a preceding
        # test (methods run alphabetically, sharing one audit table) would make those counts order-dependent. It must
        # not be cleared inside a test (unlike _clear_log), where those very entries are what the policy counts.
        db.session.query(Audit).delete()
        db.session.commit()

    @staticmethod
    def _enable_challenge_response() -> None:
        set_policy("authlog_cr", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")

    @staticmethod
    def _expire_challenges(transaction_id: str) -> None:
        """Make every challenge of a transaction expired-but-present, so the next answer is rejected as an expired
        challenge on both backends. A DB update is a no-op under Redis (and _update_challenge_in_cache refuses to
        persist an already-expired challenge), so rewrite the cached payload directly, keeping the key alive."""
        past = utc_now() - datetime.timedelta(minutes=10)
        if redis_feature_enabled("challenges"):
            client = redis_client_for_feature("challenges")
            key = _TXN_KEY.format(transaction_id)
            for serial, payload in client.hgetall(key).items():
                data = json.loads(payload)
                data["expiration"] = past.isoformat()
                client.hset(key, serial, json.dumps(data))
        else:
            for challenge in get_challenges(transaction_id=transaction_id):
                challenge.expiration = past
                challenge.save()

    def _add_second_token(self, pin: str) -> None:
        # A second HOTP token for the same user, sharing the first token's OTP key.
        init_token({"serial": self.second_serial, "type": "hotp", "otpkey": self.otpkey, "pin": pin},
                   user=self.user)

    def _post(self, path: str, data: dict, headers: dict | None = None) -> Response:
        with self.app.test_request_context(path, method='POST', data=data, headers=headers or {}):
            return self.app.full_dispatch_request()

    def _check(self, data: dict, headers: dict | None = None) -> dict:
        # /validate/check convenience for tests that inspect the body directly; always HTTP 200.
        response = self._post('/validate/check', data, headers)
        self.assertEqual(200, response.status_code, response.json)
        return response.json


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


def assert_authentication_log(event_types, transaction_id=None, same_attempt=True):
    """
    Assert that the authentication log holds exactly the given ordered list of event types, and return the entries.

    The returned :class:`AuthLogEntries` maps event type -> entry for looking up a uniquely occurring event by name
    (``entries[AuthEventType.LOGIN_SUCCESS]``) and exposes the full ordered list as ``.all``. When the same event
    type occurs more than once, assert a specific occurrence via ``.all[i]`` — indexing a duplicated type by name
    raises rather than silently returning one of them.

    ``attempt_id`` is validated here rather than per entry (:func:`assert_authentication_log_entry`), because its
    value is a server-minted random id that a test cannot know up front. Every entry must carry one, and — since the
    entries asserted together normally belong to one logical authentication attempt (one flow, which may span several
    transaction_ids in multichallenge) — they must all share it. This is the end-to-end proof that attempt chaining
    holds across requests. Tests that deliberately assert rows from *several* attempts pass ``same_attempt=False``.

    :param event_types: the expected AuthEventType values, ordered by creation
    :param transaction_id: if given, only entries of that transaction are checked
        (correlates a triggered challenge with its answer); otherwise all entries are
        checked (clear the log before the request for an exact match)
    :param same_attempt: assert all entries share one non-null ``attempt_id`` (default). Set ``False`` when the
        asserted entries span more than one attempt (only presence is checked then).
    :return: an :class:`AuthLogEntries` (a dict of event type -> entry, plus the ordered ``.all`` list)
    """
    if transaction_id is not None:
        entries = get_authentication_logs(transaction_id=transaction_id)
    else:
        entries = get_authentication_logs()
    assert [entry.event_type for entry in entries] == event_types
    # Every row is auto-assigned an attempt_id (see resolve_attempt_id).
    assert all(entry.attempt_id is not None for entry in entries)
    if same_attempt and entries:
        assert len({entry.attempt_id for entry in entries}) == 1
    return AuthLogEntries(entries)


def assert_authentication_log_entry(entry: AuthenticationLog, user: User = None,
                                    serials: set[str] = None,
                                    client_label: str = None, other_info: dict = None,
                                    transaction_id: str = None, previous_transaction_id: str = None,
                                    source_ip: str = None, user_role: AuthLogUserRole = AuthLogUserRole.USER):
    """
    Assert a single authentication-log entry carries the expected attributes.

    The server-minted ``attempt_id`` is not checked here (its value is not knowable per entry); it is validated at the
    flow level in :func:`assert_authentication_log` (presence on every row, and shared across one attempt).

    Every other column of the authentication_log table is checked. The nullable columns default to their database default
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
    :param previous_transaction_id: the entry must carry this previous_transaction_id (default None: none)
    :param source_ip: the entry must carry this source_ip (default None: no source_ip)
    :param user_role: the entry must carry this user_role (default ``"user"``, the role of a regular user)
    """
    expected_resolver = (user.resolver or None) if user is not None else None
    expected_uid = (user.uid or None) if user is not None else None
    expected_realm = (user.realm or None) if user is not None else None
    expected_username = (user.login or None) if user is not None else None
    assert (entry.resolver, entry.uid, entry.realm) == (expected_resolver, expected_uid, expected_realm)
    assert entry.username == expected_username
    assert entry.user_role == user_role
    assert entry.client_label == client_label
    assert entry.other_info == other_info
    assert entry.transaction_id == transaction_id
    assert entry.previous_transaction_id == previous_transaction_id
    assert entry.source_ip == source_ip
    entry_serials = entry.serial
    if entry_serials is not None:
        entry_serials = set(entry_serials.split(","))
    assert entry_serials == serials

    # The id (primary key) and timestamp are populated by the database / model on insert and must always be present.
    assert entry.id is not None
    assert entry.timestamp is not None
