"""Shared bases for split test_api_container_*.py files."""
# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
from dataclasses import dataclass
from typing import Optional

from privacyidea.lib.audit import getAudit
from privacyidea.lib.error import Error
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import set_policy, SCOPE, delete_policy
from privacyidea.lib.realm import set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.user import User
from tests.base import MyApiTestCase
from tests.test_lib_tokencontainer import MockSmartphone

UNSPECIFIC_ERROR_MESSAGES: dict[str, str] = {
    "container/rollover": "Failed container rollover",
    "container/synchronize": "Failed container synchronization",
    "container/challenge": "Failed creating container challenge",
    "container/register/finalize": "Failed finalizing container registration",
    "container/register/terminate/client": "Failed terminating container registration",
}


class _AuditContains:
    """Substring matcher for assert_audit_entry, created via ``APIContainerTest.contains``."""
    __slots__ = ("substring",)

    def __init__(self, substring):
        self.substring = substring

    def __repr__(self):
        return f"<contains {self.substring!r}>"


class APIContainerTest(MyApiTestCase):
    FIREBASE_FILE = "tests/testdata/firebase-test.json"
    CLIENT_FILE = "tests/testdata/google-services.json"

    # Sentinel for assert_audit_entry: assert the column is present and truthy without pinning its exact
    # value. Used on failure paths to check the endpoint/handler actually wrote a reason (e.g. `info`),
    # rather than only matching the success=False that before_request seeds for every request anyway.
    NOT_EMPTY = object()

    @staticmethod
    def contains(substring):
        """Matcher for assert_audit_entry: assert the column value contains the given substring.

        Used to tie a failure audit entry to the response error (e.g. ``info=self.contains("ERR601")``)
        without pinning the full, translatable error message.
        """
        return _AuditContains(substring)

    def setUp(self):
        super().setUp()
        # Reuse one audit object for the whole test. Start each test with an empty
        # audit log so audit assertions can not match a stale entry.
        self.audit_object = getAudit(self.app.config)
        self.audit_object.clear()

    def request_assert_success(self, url, data: dict, auth_token, method='POST'):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
            self.assertTrue(res.json["result"]["status"])
        self.reset_flask_g()
        return res.json

    def request_assert_error(self, status_code, url, data: dict, auth_token, method='POST',
                             error_code: Optional[int] = None,
                             error_message: Optional[str] = None,
                             try_unspecific: bool = False):
        if try_unspecific:
            # Exercise the hide_specific_error_message path too, and assert that it also audits the
            # error. It runs first and its audit entry is checked and cleared here, so the default
            # (specific) dispatch below is the entry a following assert_audit_entry inspects. Both
            # dispatches are thereby covered: the hidden one here, the default one by the caller.
            set_policy(name="hide_specific_error_message", scope=SCOPE.CONTAINER,
                       action=f"{PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE}=true")
            try:
                self.request_assert_error(status_code, url, data, auth_token,
                                          method=method, error_code=Error.CONTAINER,
                                          error_message=UNSPECIFIC_ERROR_MESSAGES[url])
            finally:
                delete_policy("hide_specific_error_message")
            hidden_entries = self.audit_object.search({}, sortorder="desc", page_size=1).auditdata
            self.assertTrue(hidden_entries, "The hide_specific_error_message dispatch wrote no audit entry")
            self.assertEqual(0, hidden_entries[0]["success"],
                             "The hide_specific_error_message dispatch should be audited as a failure")
            self.audit_object.clear()

        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(status_code, res.status_code, res.json)
            self.assertFalse(res.json["result"]["status"])
            if error_code is not None:
                self.assertEqual(res.json["result"]["error"]["code"], error_code)
            if error_message is not None:
                self.assertEqual(res.json["result"]["error"]["message"], error_message)
        self.reset_flask_g()
        return res.json

    def request_assert_405(self, url, data: dict, auth_token, method='POST'):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(405, res.status_code, res.json)
        self.reset_flask_g()
        return res.json

    def request_assert_404_no_result(self, url, data: dict, auth_token, method='POST'):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(404, res.status_code, res.json)
        self.reset_flask_g()

    def _audit_entries(self, action):
        """Most-recent-first audit entries for an action, read directly via the audit lib.

        Querying the audit backend directly (instead of the ``/audit`` API) avoids depending on the
        ``auditlog`` policy, which tests may restrict, and skips the full request dispatch.
        """
        return self.audit_object.search({"action": action}, sortorder="desc", page_size=1).auditdata

    def assert_audit_entry(self, action, **expected):
        """Assert the most recent audit entry for the given action holds the expected column values.

        Clears the audit log afterwards so the next assertion can only match a fresh entry: a request
        that logs nothing (e.g. rejected before the audit is written) then finds an empty log and fails
        loudly instead of silently matching a stale entry from an earlier request.
        """
        entries = self._audit_entries(action)
        self.assertTrue(entries, f"No audit entry found for action {action!r}")
        entry = entries[0]
        for column, value in expected.items():
            if value is self.NOT_EMPTY:
                self.assertTrue(entry[column], f"Expected a non-empty '{column}' in the audit entry {entry}")
            elif isinstance(value, _AuditContains):
                self.assertIn(value.substring, entry[column] or "",
                              f"Expected {value.substring!r} in the audit '{column}' ({entry[column]!r})")
            else:
                self.assertEqual(value, entry[column], f"Unexpected value in the audit for '{column}'")
        self.audit_object.clear()
        return entry

    def assert_no_audit_entry(self, action):
        """Assert the request logged no audit entry for this action (e.g. it was rejected before auth)."""
        entries = self._audit_entries(action)
        self.assertFalse(entries, f"Expected no audit entry for action {action!r}, found {entries}")
        self.audit_object.clear()

    def assert_audit_log_empty(self):
        """Assert the request wrote no audit entry at all.

        Use this for mis-routed requests (404/405) that are rejected during routing before any
        ``before_request`` runs: filtering by action can not express "nothing was written" because the
        rejected request never produces an action to filter on, so such an assertion can never fail.
        """
        entries = self.audit_object.search({}, sortorder="desc", page_size=1).auditdata
        self.assertFalse(entries, f"Expected an empty audit log, found {entries}")
        self.audit_object.clear()


class APIContainerAuthorization(APIContainerTest):
    def setUp(self):
        super().setUp()
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": "tests/testdata/passwords"})
        self.assertGreater(rid, 0)

        (added, failed) = set_realm(self.realm1, [{'name': self.resolvername1}])
        self.assertEqual(0, len(failed))
        self.assertEqual(1, len(added))

        user = User(login="root",
                    realm=self.realm1,
                    resolver=self.resolvername1)

        user_str = "{0!s}".format(user)
        self.assertEqual("<root.resolver1@realm1>", user_str)

        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        user_repr = "{0!r}".format(user)
        expected = "User(login='root', realm='realm1', resolver='resolver1')"
        self.assertEqual(expected, user_repr)
        self.authenticate_selfservice_user()

    def request_denied_assert_403(self, url, data: dict, auth_token, method='POST',
                                  error_message: Optional[str] = None):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(403, res.status_code, res.json)
            self.assertEqual(res.json["result"]["error"]["code"], 303)
            if error_message is not None:
                self.assertEqual(res.json["result"]["error"]["message"], error_message)
        self.reset_flask_g()
        return res.json

    def create_container_for_user(self, ctype="generic"):
        set_policy("user_container_create", scope=SCOPE.USER, action=PolicyAction.CONTAINER_CREATE)
        with self.app.test_request_context('/container/init',
                                           method='POST',
                                           data={"type": ctype},
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
        container_serial = res.json["result"]["value"]["container_serial"]
        self.assertGreater(len(container_serial), 0)
        delete_policy("user_container_create")
        return container_serial


@dataclass
class SmartphoneRequests:
    mock_smph: MockSmartphone = MockSmartphone()
    response: dict = None
