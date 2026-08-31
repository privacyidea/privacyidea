"""
This test file tests that request data can not prevent a request from being written to the
audit log, and that it can not turn a request into a server error.

The tests are written so that they also fail on SQLite, which does not enforce column
lengths: they check the length of the stored value instead of relying on the database to
reject it.
"""
from flask import Response
from sqlalchemy import select

from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
from privacyidea.lib.token import init_token, remove_token
from privacyidea.lib.user import User
from privacyidea.models import db
from privacyidea.models.audit import audit_column_length
from privacyidea.models.subscription import ClientApplication
from .base import MyApiTestCase


class AuditRobustnessTestCase(MyApiTestCase):

    def _validate_check(self, data: dict = None, headers: dict = None) -> Response:
        with self.app.test_request_context('/validate/check', method='POST', data=data or {},
                                           headers=headers or {},
                                           environ_base={"REMOTE_ADDR": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            return res

    def _client_types(self) -> list[str]:
        db.session.commit()
        return db.session.execute(select(ClientApplication.clienttype)).scalars().all()

    def test_01_unknown_resolver_is_audited(self):
        """A request naming a resolver that does not exist is answered with an error, and
        the error is written to the audit log."""
        self.setUp_user_realms()
        res = self._validate_check({"user": "cornelius", "resolver": "nonexistent",
                                    "pass": "wrong"})
        self.assertEqual(400, res.status_code, res.json)
        self.assertIn("does not exist", res.json.get("result").get("error").get("message"))

        audit_entry = self.find_most_recent_audit_entry(action='POST /validate/check')
        # The user is logged the way it was requested, since it could not be resolved
        self.assertEqual("cornelius", audit_entry.get("user"), audit_entry)
        self.assertEqual("nonexistent", audit_entry.get("resolver"), audit_entry)
        self.assertEqual(0, audit_entry.get("success"), audit_entry)

    def test_02_unknown_realm_is_audited(self):
        """The same for a realm that does not exist."""
        self.setUp_user_realms()
        res = self._validate_check({"user": "cornelius", "realm": "nonexistent",
                                    "pass": "wrong"})
        self.assertEqual(400, res.status_code, res.json)

        audit_entry = self.find_most_recent_audit_entry(action='POST /validate/check')
        self.assertEqual("cornelius", audit_entry.get("user"), audit_entry)
        self.assertEqual("nonexistent", audit_entry.get("realm"), audit_entry)

    def test_03_long_user_agent_does_not_fail_the_request(self):
        """A user agent longer than the client type column is stored cut, and the request
        it was sent with is answered normally."""
        self.setUp_user_realms()
        column_length = ClientApplication.__table__.c.clienttype.type.length
        long_agent = f"PAM/1.0 {'A' * (column_length * 2)!s}"

        res = self._validate_check({"user": "cornelius", "pass": "wrong"},
                                   headers={"User-Agent": long_agent})
        self.assertEqual(200, res.status_code, res.json)
        self.assertFalse(res.json.get("result").get("value"))

        stored = [client_type for client_type in self._client_types()
                  if client_type.startswith("PAM/1.0 A")]
        self.assertEqual(1, len(stored), stored)
        self.assertEqual(column_length, len(stored[0]))

        # The request is in the audit log, with the agent name the header started with
        audit_entry = self.find_most_recent_audit_entry(action='POST /validate/check')
        self.assertEqual("PAM", audit_entry.get("user_agent"), audit_entry)

    def test_04_user_agent_without_version_does_not_fail_the_request(self):
        """A user agent that is only a long token, without a version, behaves the same."""
        self.setUp_user_realms()
        column_length = ClientApplication.__table__.c.clienttype.type.length
        res = self._validate_check({"user": "cornelius", "pass": "wrong"},
                                   headers={"User-Agent": "B" * (column_length * 2)})
        self.assertEqual(200, res.status_code, res.json)

        stored = [client_type for client_type in self._client_types()
                  if client_type.startswith("BBB")]
        self.assertEqual(1, len(stored), stored)
        self.assertEqual(column_length, len(stored[0]))

    def test_05_long_values_shorten_the_entry_instead_of_losing_it(self):
        """Request data that is longer than its audit column is shortened, so the request
        is still logged."""
        self.setUp_user_realms()
        for label, data, headers, column in [
                ("user", {"user": "U" * 600, "pass": "wrong"}, {}, "user"),
                ("realm", {"user": "cornelius", "realm": "R" * 600, "pass": "wrong"}, {},
                 "realm"),
                ("user agent", {"user": "cornelius", "pass": "wrong"},
                 {"User-Agent": "A" * 600}, "user_agent")]:
            with self.subTest(label):
                self._validate_check(data, headers)
                audit_entry = self.find_most_recent_audit_entry(action='POST /validate/check')
                self.assertEqual(audit_column_length.get(column),
                                 len(audit_entry.get(column)), audit_entry)

    def test_06_long_login_name_is_audited(self):
        """A login attempt with an over-long user name is logged as a failed login. The
        name of a login that failed is logged as the user, no administrator was found."""
        with self.app.test_request_context('/auth', method='POST',
                                           data={"username": "N" * 600,
                                                 "password": "wrong"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)

        audit_entry = self.find_most_recent_audit_entry(action='POST /auth')
        self.assertEqual(audit_column_length.get("user"),
                         len(audit_entry.get("user")), audit_entry)
        self.assertEqual(0, audit_entry.get("success"), audit_entry)

    def test_07_invalid_forwarded_for_falls_back_to_the_peer(self):
        """A forwarding chain that is no list of IP addresses is ignored, the request is
        answered and logged with the address it really came from."""
        self.setUp_user_realms()
        set_privacyidea_config("OverrideAuthorizationClient", "10.1.2.3")
        try:
            res = self._validate_check({"user": "cornelius", "pass": "wrong"},
                                       {"X-Forwarded-For": "not-an-ip-address"})
            self.assertEqual(200, res.status_code, res.json)
            audit_entry = self.find_most_recent_audit_entry(action='POST /validate/check')
            self.assertEqual("10.1.2.3", audit_entry.get("client"), audit_entry)
        finally:
            set_privacyidea_config("OverrideAuthorizationClient", "")

    def test_08_challenge_of_another_user_is_not_named(self):
        """Answering the transaction of another user logs no token: the tokens that were
        challenged are not the tokens of the user this request authenticates."""
        self.setUp_user_realms()
        init_token({"serial": "OWNER001", "type": "hotp", "genkey": 1, "pin": "ownerpin"},
                   User("cornelius", self.realm1))
        init_token({"serial": "OTHER001", "type": "hotp", "genkey": 1, "pin": "otherpin"},
                   User("selfservice", self.realm1))
        set_policy("robust_cr", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.CHALLENGERESPONSE!s}=hotp")
        try:
            res = self._validate_check({"user": "cornelius", "pass": "ownerpin"})
            transaction_id = res.json.get("detail").get("transaction_id")

            # The other user answers the challenge of the owner
            self._validate_check({"user": "selfservice", "transaction_id": transaction_id,
                                  "pass": "123456"})
            audit_entry = self.find_most_recent_audit_entry(action='POST /validate/check')
            self.assertEqual("selfservice", audit_entry.get("user"), audit_entry)
            self.assertEqual("", audit_entry.get("serial"), audit_entry)
        finally:
            delete_policy("robust_cr")
            remove_token("OWNER001")
            remove_token("OTHER001")
