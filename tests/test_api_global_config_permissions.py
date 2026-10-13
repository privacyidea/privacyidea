# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the endpoints that change configuration applying to all realms - policies, conditional-access policies,
event handlers and API clients. An admin permission for them counts only if it is not restricted to individual realms,
resolvers or users.
"""
import jwt
from werkzeug.test import TestResponse

from privacyidea.lib.clients import create_client, get_client
from privacyidea.lib.event import set_event
from privacyidea.lib.policies.actions import PolicyAction, ADMIN_ACTIONS_WITHOUT_TARGET
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy, get_policies, enable_policy
from privacyidea.models import db
from privacyidea.models.client import Client
from privacyidea.models.event import EventHandler
from .base import MyApiTestCase

GLOBAL_CONFIG_WRITE_ACTIONS = [
    PolicyAction.POLICYWRITE, PolicyAction.POLICYDELETE, PolicyAction.EVENTHANDLINGWRITE,
    PolicyAction.CONDITIONAL_ACCESS_POLICY_WRITE, PolicyAction.API_CLIENT_ADD, PolicyAction.API_CLIENT_EDIT,
    PolicyAction.API_CLIENT_ROTATE, PolicyAction.API_CLIENT_DELETE,
]

RESTRICTED_PERMISSION_MESSAGE = "not restricted to individual realms, resolvers or users"

TARGET_POLICY = "global_config_target"
SCOPED_POLICY = "global_config_scoped"
EVENT_HANDLER = "global_config_event"


class GlobalConfigurationPermissionTestCase(MyApiTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.setUp_user_realms()
        self.authenticate()
        set_policy(TARGET_POLICY, scope=SCOPE.USER, action=str(PolicyAction.DISABLE), realm=self.realm1)
        self.event_id = set_event(EVENT_HANDLER, event=["token_init"], handlermodule="UserNotification",
                                  action="sendmail", conditions={}, options={})
        self.client_object, _ = create_client("global config client", "privacyidea-cp")
        self.client_key_id = self.client_object.key_id

    def tearDown(self) -> None:
        for name in (SCOPED_POLICY, TARGET_POLICY, "global_config_unscoped", "global_config_new"):
            if get_policies(name=name):
                delete_policy(name)
        db.session.query(EventHandler).delete()
        db.session.query(Client).delete()
        db.session.commit()
        super().tearDown()

    def _request(self, path: str, method: str = "GET", json_data: dict | None = None) -> TestResponse:
        kwargs: dict = {"method": method, "headers": {"Authorization": self.at}}
        if json_data is not None:
            kwargs["json"] = json_data
        with self.app.test_request_context(path, **kwargs):
            return self.app.full_dispatch_request()

    def _event_handler_active(self) -> bool:
        db.session.expire_all()
        return db.session.get(EventHandler, self.event_id).active

    def _write_requests(self) -> list[tuple[str, str, dict | None]]:
        client_id = self.client_object.id
        new_policy = {"scope": SCOPE.USER, "action": str(PolicyAction.DISABLE), "realm": self.realm1}
        new_event = {"name": "global config new event", "event": "token_init", "action": "sendmail",
                     "handlermodule": "UserNotification", "conditions": {}, "options": {}}
        return [
            ("POST", "/policy/global_config_new", new_policy),
            ("POST", f"/policy/enable/{TARGET_POLICY}", None),
            ("POST", f"/policy/disable/{TARGET_POLICY}", None),
            ("PATCH", f"/policy/{TARGET_POLICY}", {"name": "global_config_renamed"}),
            ("DELETE", f"/policy/{TARGET_POLICY}", None),
            ("DELETE", f"/policy/{SCOPED_POLICY}", None),
            ("POST", "/policy/import/policies.cfg", None),
            ("POST", "/event", new_event),
            ("POST", f"/event/enable/{self.event_id}", None),
            ("POST", f"/event/disable/{self.event_id}", None),
            ("DELETE", f"/event/{self.event_id}", None),
            ("POST", "/conditionalaccess/policy", {"name": "global config ca policy"}),
            ("PATCH", "/conditionalaccess/policy/1", {"active": False}),
            ("PUT", "/conditionalaccess/policy/order", {"order": [1]}),
            ("DELETE", "/conditionalaccess/policy/1", None),
            ("POST", "/clients/", {"display_name": "global config new client", "client_type": "privacyidea-cp"}),
            ("PATCH", f"/clients/{client_id}", {"status": "suspended"}),
            ("POST", f"/clients/{client_id}/rotate", None),
            ("DELETE", f"/clients/{client_id}", None),
        ]

    def _assert_configuration_unchanged(self) -> None:
        target_policy = get_policies(name=TARGET_POLICY)
        self.assertEqual(1, len(target_policy))
        self.assertTrue(target_policy[0].get("active"))
        self.assertEqual(1, len(get_policies(name=SCOPED_POLICY)))
        self.assertEqual([], get_policies(name="global_config_new"))
        self.assertEqual([EVENT_HANDLER], [handler.name for handler in EventHandler.query.all()])
        self.assertTrue(self._event_handler_active())
        client = get_client(self.client_object.id)
        self.assertEqual("active", client.status)
        self.assertEqual(self.client_key_id, client.key_id)
        self.assertEqual(1, Client.query.count())

    def _assert_refused(self, method: str, path: str, json_data: dict | None) -> None:
        response = self._request(path, method=method, json_data=json_data)
        self.assertEqual(403, response.status_code, response.json)
        self.assertIn(RESTRICTED_PERMISSION_MESSAGE, response.json["result"]["error"]["message"])

    def test_01_a_realm_restricted_permission_changes_no_global_configuration(self):
        set_policy(SCOPED_POLICY, scope=SCOPE.ADMIN, realm=self.realm1, action=GLOBAL_CONFIG_WRITE_ACTIONS)
        for method, path, json_data in self._write_requests():
            with self.subTest(method=method, path=path):
                self._assert_refused(method, path, json_data)
        self._assert_configuration_unchanged()

    def test_02_naming_a_realm_of_the_permission_in_the_request_does_not_help(self):
        set_policy(SCOPED_POLICY, scope=SCOPE.ADMIN, realm=self.realm1, action=GLOBAL_CONFIG_WRITE_ACTIONS)
        self._assert_refused("POST", "/policy/global_config_new",
                             {"scope": SCOPE.ADMIN, "action": "*", "realm": self.realm1})
        self._assert_refused("POST", f"/event/disable/{self.event_id}", {"realm": self.realm1})
        self._assert_configuration_unchanged()

    def test_03_resolver_and_user_restricted_permissions_change_no_global_configuration(self):
        self.setUp_user_realm2()
        for restriction in ({"resolver": self.resolvername1}, {"user": "cornelius"},
                            {"realm": f"*, !{self.realm2}"}):
            with self.subTest(restriction=restriction):
                set_policy(SCOPED_POLICY, scope=SCOPE.ADMIN, action=GLOBAL_CONFIG_WRITE_ACTIONS, **restriction)
                self._assert_refused("POST", "/event", {"name": "global config new event", "event": "token_init",
                                                        "action": "sendmail", "handlermodule": "UserNotification"})
                self._assert_refused("POST", f"/clients/{self.client_object.id}/rotate", None)
                delete_policy(SCOPED_POLICY)
        set_policy(SCOPED_POLICY, scope=SCOPE.ADMIN, realm=self.realm1, action=GLOBAL_CONFIG_WRITE_ACTIONS)
        self._assert_configuration_unchanged()

    def test_04_a_permission_for_every_realm_changes_global_configuration(self):
        set_policy(SCOPED_POLICY, scope=SCOPE.ADMIN, realm="*", adminuser=self.testadmin,
                   action=GLOBAL_CONFIG_WRITE_ACTIONS)
        response = self._request(f"/event/disable/{self.event_id}", method="POST")
        self.assertEqual(200, response.status_code, response.json)
        self.assertFalse(self._event_handler_active())
        response = self._request(f"/policy/disable/{TARGET_POLICY}", method="POST")
        self.assertEqual(200, response.status_code, response.json)
        self.assertFalse(get_policies(name=TARGET_POLICY)[0].get("active"))
        response = self._request(f"/clients/{self.client_object.id}/rotate", method="POST")
        self.assertEqual(200, response.status_code, response.json)
        self.assertNotEqual(self.client_key_id, get_client(self.client_object.id).key_id)

    def test_05_an_unrestricted_permission_next_to_a_restricted_one_is_enough(self):
        set_policy(SCOPED_POLICY, scope=SCOPE.ADMIN, realm=self.realm1, action=GLOBAL_CONFIG_WRITE_ACTIONS)
        set_policy("global_config_unscoped", scope=SCOPE.ADMIN, action=str(PolicyAction.POLICYWRITE))
        response = self._request(f"/policy/disable/{TARGET_POLICY}", method="POST")
        self.assertEqual(200, response.status_code, response.json)
        enable_policy(TARGET_POLICY)
        # The unrestricted permission covers policies only.
        self._assert_refused("POST", f"/event/disable/{self.event_id}", None)
        self._assert_configuration_unchanged()

    def test_06_without_admin_policies_every_admin_changes_global_configuration(self):
        response = self._request(f"/event/disable/{self.event_id}", method="POST")
        self.assertEqual(200, response.status_code, response.json)
        response = self._request(f"/policy/disable/{TARGET_POLICY}", method="POST")
        self.assertEqual(200, response.status_code, response.json)

    def test_07_a_realm_restricted_permission_still_reads_global_configuration(self):
        set_policy(SCOPED_POLICY, scope=SCOPE.ADMIN, realm=self.realm1,
                   action=[PolicyAction.EVENTHANDLINGREAD, PolicyAction.POLICYREAD, PolicyAction.SMTPSERVERREAD])
        for path in ("/event/", "/policy/", "/smtpserver/"):
            with self.subTest(path=path):
                response = self._request(path)
                self.assertEqual(200, response.status_code, response.json)

    def test_08_a_missing_permission_is_refused_as_before(self):
        set_policy(SCOPED_POLICY, scope=SCOPE.ADMIN, action=str(PolicyAction.POLICYREAD))
        response = self._request(f"/event/disable/{self.event_id}", method="POST")
        self.assertEqual(403, response.status_code, response.json)
        self.assertNotIn(RESTRICTED_PERMISSION_MESSAGE, response.json["result"]["error"]["message"])
        self._assert_configuration_unchanged()

    def _login_rights(self) -> list[str]:
        with self.app.test_request_context("/auth", method="POST",
                                           data={"username": self.testadmin, "password": self.testadminpw}):
            response = self.app.full_dispatch_request()
        self.assertEqual(200, response.status_code, response.json)
        value = response.json["result"]["value"]
        token_rights = jwt.decode(value["token"], options={"verify_signature": False})["rights"]
        self.assertEqual(sorted(value["rights"]), sorted(token_rights))
        return value["rights"]

    def test_09_a_restricted_permission_is_not_among_the_login_rights(self):
        read_actions = [PolicyAction.EVENTHANDLINGREAD, PolicyAction.POLICYREAD, PolicyAction.SMTPSERVERREAD]
        self.setUp_user_realm2()
        for restriction in ({"realm": self.realm1}, {"resolver": self.resolvername1}, {"user": "cornelius"},
                            {"realm": f"*, !{self.realm2}"}):
            with self.subTest(restriction=restriction):
                set_policy(SCOPED_POLICY, scope=SCOPE.ADMIN, action=sorted(ADMIN_ACTIONS_WITHOUT_TARGET) + read_actions,
                           **restriction)
                rights = self._login_rights()
                self.assertEqual(set(), ADMIN_ACTIONS_WITHOUT_TARGET & set(rights))
                self.assertTrue(set(read_actions) <= set(rights), rights)
                delete_policy(SCOPED_POLICY)

    def test_10_an_unrestricted_permission_is_among_the_login_rights(self):
        set_policy(SCOPED_POLICY, scope=SCOPE.ADMIN, realm=self.realm1, action=sorted(ADMIN_ACTIONS_WITHOUT_TARGET))
        set_policy("global_config_unscoped", scope=SCOPE.ADMIN, realm="*", adminuser=self.testadmin,
                   action=[PolicyAction.POLICYWRITE, PolicyAction.BLOCKLIST_READ])
        rights = set(self._login_rights())
        self.assertEqual({PolicyAction.POLICYWRITE, PolicyAction.BLOCKLIST_READ}, ADMIN_ACTIONS_WITHOUT_TARGET & rights)
