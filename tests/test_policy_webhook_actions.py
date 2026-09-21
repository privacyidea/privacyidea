# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the ``webhook_read`` / ``webhook_write`` admin policy actions
(Phase 3 of #5751 -- make webhooks a first-class object).

The REST API for webhooks does not exist yet (that is Phase 4), so these
tests exercise the layer the API endpoints will sit on: the action
constants, their registration in the static admin policy definitions and
the ``check_base_action`` prepolicy that the endpoints will be decorated
with.
"""
import json
from pathlib import Path

from flask import Request, g
from werkzeug.test import EnvironBuilder

from privacyidea.api.lib.prepolicy import check_base_action
from privacyidea.lib.error import PolicyError
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import (set_policy, delete_policy, PolicyClass,
                                    SCOPE, GROUP, MAIN_MENU,
                                    get_static_policy_definitions)
from privacyidea.lib.user import User

from .base import MyApiTestCase

#: Repository root, derived from this file's location.
ROOT = Path(__file__).resolve().parent.parent

POLICY_TEMPLATES = [
    ROOT / "privacyidea" / "static_old" / "policy-templates" / "superuser.json",
    ROOT / "privacyidea" / "static" / "public" / "policy-templates" / "superuser.json",
]

POLICY_ACTIONS_TS = (ROOT / "privacyidea" / "static" / "src" / "app" /
                     "services" / "auth" / "policy-actions.ts")


class WebhookPolicyActionDefinitionTestCase(MyApiTestCase):
    """The constants exist and are registered as admin policy actions."""

    def test_01_action_constants(self):
        self.assertEqual("webhook_read", PolicyAction.WEBHOOKREAD)
        self.assertEqual("webhook_write", PolicyAction.WEBHOOKWRITE)

    def test_02_registered_in_admin_scope(self):
        admin_actions = get_static_policy_definitions(SCOPE.ADMIN)
        for action in (PolicyAction.WEBHOOKREAD, PolicyAction.WEBHOOKWRITE):
            with self.subTest(action=action):
                self.assertIn(action, admin_actions)
                definition = admin_actions[action]
                self.assertEqual("bool", definition["type"])
                self.assertEqual(GROUP.SYSTEM, definition["group"])
                self.assertEqual([MAIN_MENU.CONFIG], definition["mainmenu"])
                self.assertTrue(definition["desc"])

    def test_03_not_registered_in_other_scopes(self):
        # Webhook management is an administrative task. A user must not be
        # able to grant it to themselves through a user-scope policy.
        for scope in (SCOPE.USER, SCOPE.AUTH, SCOPE.AUTHZ, SCOPE.WEBUI,
                      SCOPE.ENROLL):
            definitions = get_static_policy_definitions(scope)
            for action in (PolicyAction.WEBHOOKREAD, PolicyAction.WEBHOOKWRITE):
                with self.subTest(scope=scope, action=action):
                    self.assertNotIn(action, definitions)

    def test_04_grouped_with_the_other_configuration_objects(self):
        # The webhook rights must look exactly like the rights of the other
        # configuration objects they were modelled on, otherwise they end up
        # in a different section of the policy UI.
        admin_actions = get_static_policy_definitions(SCOPE.ADMIN)
        for webhook_action, reference in (
                (PolicyAction.WEBHOOKREAD, PolicyAction.SMSGATEWAYREAD),
                (PolicyAction.WEBHOOKWRITE, PolicyAction.SMSGATEWAYWRITE)):
            with self.subTest(action=webhook_action):
                webhook_definition = dict(admin_actions[webhook_action])
                reference_definition = dict(admin_actions[reference])
                # The description differs, everything else must match.
                webhook_definition.pop("desc")
                reference_definition.pop("desc")
                self.assertEqual(reference_definition, webhook_definition)


class WebhookPolicyEnforcementTestCase(MyApiTestCase):
    """``check_base_action`` enforces the new rights as the API will."""

    @staticmethod
    def _admin_request(username="adminA"):
        """Build the minimal request/context ``check_base_action`` needs."""
        request = Request(EnvironBuilder(method="POST").get_environ())
        request.User = User()
        request.all_data = {}
        g.policy_object = PolicyClass()
        g.logged_in_user = {"username": username, "role": "admin", "realm": ""}
        return request

    def test_01_no_policy_at_all_allows_everything(self):
        # Without any admin policy every admin is a superuser. This is
        # privacyIDEA's documented default and must not change just because
        # a new right was added.
        request = self._admin_request()
        self.assertTrue(check_base_action(request, action=PolicyAction.WEBHOOKREAD))
        self.assertTrue(check_base_action(request, action=PolicyAction.WEBHOOKWRITE))

    def test_02_read_right_does_not_imply_write(self):
        set_policy("webhookReader", scope=SCOPE.ADMIN,
                   action=PolicyAction.WEBHOOKREAD, adminuser="adminA")
        try:
            request = self._admin_request("adminA")
            self.assertTrue(check_base_action(request,
                                              action=PolicyAction.WEBHOOKREAD))
            self.assertRaises(PolicyError, check_base_action, request,
                              action=PolicyAction.WEBHOOKWRITE)
        finally:
            delete_policy("webhookReader")

    def test_03_write_right_does_not_imply_read(self):
        # Mirrors smtpserver/smsgateway: the two rights are independent, a
        # write right does not silently grant listing.
        set_policy("webhookWriter", scope=SCOPE.ADMIN,
                   action=PolicyAction.WEBHOOKWRITE, adminuser="adminA")
        try:
            request = self._admin_request("adminA")
            self.assertTrue(check_base_action(request,
                                              action=PolicyAction.WEBHOOKWRITE))
            self.assertRaises(PolicyError, check_base_action, request,
                              action=PolicyAction.WEBHOOKREAD)
        finally:
            delete_policy("webhookWriter")

    def test_04_both_rights(self):
        set_policy("webhookAdmin", scope=SCOPE.ADMIN,
                   action=f"{PolicyAction.WEBHOOKREAD}, {PolicyAction.WEBHOOKWRITE}",
                   adminuser="adminA")
        try:
            request = self._admin_request("adminA")
            self.assertTrue(check_base_action(request,
                                              action=PolicyAction.WEBHOOKREAD))
            self.assertTrue(check_base_action(request,
                                              action=PolicyAction.WEBHOOKWRITE))
        finally:
            delete_policy("webhookAdmin")

    def test_05_admin_without_the_rights_is_denied(self):
        # As soon as *any* admin policy exists, an admin who is not covered
        # by a webhook policy loses the right.
        set_policy("webhookAdmin", scope=SCOPE.ADMIN,
                   action=f"{PolicyAction.WEBHOOKREAD}, {PolicyAction.WEBHOOKWRITE}",
                   adminuser="adminA")
        try:
            request = self._admin_request("adminB")
            for action in (PolicyAction.WEBHOOKREAD, PolicyAction.WEBHOOKWRITE):
                with self.subTest(action=action):
                    self.assertRaises(PolicyError, check_base_action, request,
                                      action=action)
        finally:
            delete_policy("webhookAdmin")

    def test_06_unrelated_rights_do_not_grant_webhook_access(self):
        # A right on a neighbouring configuration object must not leak into
        # the webhook rights (guards against a copy-paste in the action map).
        set_policy("smtpAdmin", scope=SCOPE.ADMIN,
                   action=f"{PolicyAction.SMTPSERVERREAD}, "
                          f"{PolicyAction.SMTPSERVERWRITE}",
                   adminuser="adminA")
        try:
            request = self._admin_request("adminA")
            self.assertTrue(check_base_action(request,
                                              action=PolicyAction.SMTPSERVERREAD))
            for action in (PolicyAction.WEBHOOKREAD, PolicyAction.WEBHOOKWRITE):
                with self.subTest(action=action):
                    self.assertRaises(PolicyError, check_base_action, request,
                                      action=action)
        finally:
            delete_policy("smtpAdmin")


class WebhookPolicyActionMirrorsTestCase(MyApiTestCase):
    """The action lists outside of Python must stay in sync with actions.py.

    Nothing enforces this at runtime, so a missing entry would only show up
    as a webhook page the superuser template cannot reach or a TypeScript
    compile error much later.
    """

    def test_01_superuser_templates(self):
        for path in POLICY_TEMPLATES:
            with self.subTest(template=path.name):
                template = json.loads(path.read_text())
                self.assertEqual(SCOPE.ADMIN, template["scope"])
                actions = template["action"]
                self.assertTrue(actions.get(PolicyAction.WEBHOOKREAD))
                self.assertTrue(actions.get(PolicyAction.WEBHOOKWRITE))

    def test_02_superuser_templates_are_identical(self):
        # The old and the new WebUI ship the same file. A mismatch means one
        # UI offers a template the other does not.
        first, second = (json.loads(path.read_text()) for path in POLICY_TEMPLATES)
        self.assertEqual(first, second)

    def test_03_typescript_action_union(self):
        content = POLICY_ACTIONS_TS.read_text()
        for action in (PolicyAction.WEBHOOKREAD, PolicyAction.WEBHOOKWRITE):
            with self.subTest(action=action):
                self.assertIn(f'"{action}"', content)
