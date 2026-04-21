# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import json
import mock
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from typing import Optional

import passlib
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey

from privacyidea.lib.applications.offline import MachineApplication, REFILLTOKEN_LENGTH
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.container import (create_container_template, get_template_obj, delete_container_by_serial,
                                       get_container_realms, set_container_states, unregister)
from privacyidea.lib.container import (init_container, find_container_by_serial, add_token_to_container, assign_user,
                                       add_container_realms, remove_token_from_container)
from privacyidea.lib.containers.container_info import PI_INTERNAL, TokenContainerInfoData, RegistrationState
from privacyidea.lib.containers.container_states import ContainerStates
from privacyidea.lib.containers.smartphone import SmartphoneOptions
from privacyidea.lib.crypto import generate_keypair_ecc, decrypt_aes
from privacyidea.lib.error import Error
from privacyidea.lib.machine import attach_token
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policies.conditions import ConditionSection, ConditionHandleMissingData
from privacyidea.lib.policy import set_policy, SCOPE, delete_policy
from privacyidea.lib.privacyideaserver import add_privacyideaserver
from privacyidea.lib.realm import set_realm, set_default_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.serviceid import set_serviceid
from privacyidea.lib.smsprovider.FirebaseProvider import FirebaseConfig
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
from privacyidea.lib.token import (get_one_token, get_tokens_from_serial_or_user,
                                   get_tokeninfo, get_tokens)
from privacyidea.lib.token import init_token, get_tokens_paginate, unassign_token
from privacyidea.lib.tokens.papertoken import PAPERACTION
from privacyidea.lib.tokens.pushtoken import PushAction
from privacyidea.lib.tokens.tantoken import TANAction
from privacyidea.lib.user import User
from privacyidea.lib.utils.compare import PrimaryComparators
from privacyidea.models import Realm
from tests.base import MyApiTestCase
from tests.test_lib_tokencontainer import MockSmartphone

from .api_container_common import (
    APIContainerTest,
    APIContainerAuthorization,
    SmartphoneRequests,
    UNSPECIFIC_ERROR_MESSAGES,
)


class APIContainerAuthorizationAdmin(APIContainerAuthorization):
    """
    Test the authorization of the API endpoints for admins.
        * allowed: admin has the required rights
        * denied: admin does not have the required rights
    """

    def test_01_admin_create_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_CREATE)
        result = self.request_assert_success('/container/init', {"type": "generic"}, self.at)
        self.assertGreater(len(result["result"]["value"]["container_serial"]), 0)
        delete_policy("policy")

    def test_02_admin_create_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION)
        self.request_denied_assert_403('/container/init', {"type": "Smartphone", "description": "test description!!"},
                                       self.at)
        delete_policy("policy")

    def test_03_admin_delete_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}", {}, self.at, method='DELETE')
        delete_policy("policy")

    def test_04_admin_delete_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_CREATE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}", {}, self.at, method='DELETE')
        delete_policy("policy")

    def test_05_admin_description_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION)
        # container of a user
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/description", {"description": "test"}, self.at,
                                    method='POST')
        # container without user
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/description", {"description": "test"}, self.at,
                                    method='POST')
        delete_policy("policy")

    def test_06_admin_description_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/description", {"description": "test"},
                                       self.at, method='POST')
        delete_policy("policy")

    def test_07_admin_state_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_STATE)
        # container of a user
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                    self.at, method='POST')
        # container without user
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                    self.at, method='POST')
        delete_policy("policy")

    def test_08_admin_state_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                       self.at, method='POST')
        delete_policy("policy")

    def test_09_admin_add_token_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ADD_TOKEN)
        # container of a user
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        result = self.request_assert_success(f"/container/{container_serial}/add", {"serial": token_serial}, self.at,
                                             method='POST')
        self.assertTrue(result["result"]["value"])

        # container without user
        container_serial = init_container({"type": "generic"})["container_serial"]
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        result = self.request_assert_success(f"/container/{container_serial}/add", {"serial": token_serial}, self.at,
                                             method='POST')
        self.assertTrue(result["result"]["value"])
        delete_policy("policy")

    def test_10_admin_add_token_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{container_serial}/add", {"serial": token_serial}, self.at,
                                       method='POST')
        delete_policy("policy")

    def test_11_admin_add_multiple_tokens_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ADD_TOKEN)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token2 = init_token({"type": "hotp", "genkey": True})
        serials = ",".join([token.get_serial(), token2.get_serial()])
        result = self.request_assert_success(f"/container/{container_serial}/addall",
                                             {"serial": serials}, self.at,
                                             method='POST')
        self.assertTrue(result["result"]["value"])
        self.assertTrue(result["result"]["value"][token.get_serial()])
        self.assertTrue(result["result"]["value"][token2.get_serial()])
        delete_policy("policy")

    def test_12_admin_add_multiple_tokens_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token2 = init_token({"type": "hotp", "genkey": True})
        serials = ",".join([token.get_serial(), token2.get_serial()])
        self.request_denied_assert_403(f"/container/{container_serial}/addall", {"serial": serials}, self.at,
                                       method='POST')
        delete_policy("policy")

    def test_13_admin_remove_token_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REMOVE_TOKEN)
        # container of a user
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        container = find_container_by_serial(container_serial)
        container.add_token(token)
        result = self.request_assert_success(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at,
                                             method='POST')
        self.assertTrue(result["result"]["value"])

        # container without user
        container_serial = init_container({"type": "generic"})["container_serial"]
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        container = find_container_by_serial(container_serial)
        container.add_token(token)
        result = self.request_assert_success(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at,
                                             method='POST')
        self.assertTrue(result["result"]["value"])

        delete_policy("policy")

    def test_14_admin_remove_token_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        container = find_container_by_serial(container_serial)
        container.add_token(token)
        self.request_denied_assert_403(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at,
                                       method='POST')
        delete_policy("policy")

    def test_15_admin_assign_user_allowed(self):
        self.setUp_user_realms()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER)
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/assign",
                                    {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_16_admin_assign_user_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE)
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_17_admin_remove_user_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_UNASSIGN_USER)
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/unassign",
                                    {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_18_admin_remove_user_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE)
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_19_admin_container_realms_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REALMS)
        # container of a user
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)

        # container without user
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)
        delete_policy("policy")

    def test_20_admin_container_realms_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/realms", {"realms": "realm1"}, self.at)
        delete_policy("policy")

    def test_21_admin_container_list_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_LIST)
        self.request_assert_success('/container/', {}, self.at, 'GET')
        delete_policy("policy")

    def test_22_admin_container_list_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE)
        self.request_denied_assert_403('/container/', {}, self.at, 'GET')
        delete_policy("policy")

    def test_23_admin_container_register_allowed(self):
        container_serial = self.create_container_for_user("smartphone")
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REGISTER)
        set_policy("container_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://test"})
        data = {"container_serial": container_serial}
        self.request_assert_success('/container/register/initialize', data, self.at, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")
        return container_serial

    def test_24_admin_container_register_denied(self):
        container_serial = self.create_container_for_user("smartphone")
        # Admin does not have CONTAINER_REGISTER rights
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_CREATE)
        set_policy("container_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://test"})
        data = {"container_serial": container_serial}
        self.request_denied_assert_403('/container/register/initialize', data, self.at, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")

    def test_25_admin_container_unregister_allowed(self):
        container_serial = self.test_23_admin_container_register_allowed()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_UNREGISTER)
        self.request_assert_success(f'/container/register/{container_serial}/terminate', {}, self.at, 'POST')
        delete_policy("policy")

    def test_26_admin_container_unregister_denied(self):
        container_serial = self.test_23_admin_container_register_allowed()
        # Admin does not have CONTAINER_UNREGISTER rights
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_CREATE)
        self.request_denied_assert_403(f'/container/register/{container_serial}/terminate', {}, self.at, 'POST')
        delete_policy("policy")

    def test_27_admin_container_rollover_allowed(self):
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key=RegistrationState.get_key(),
                                                                value=RegistrationState.REGISTERED.value,
                                                                info_type=PI_INTERNAL)])
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={PolicyAction.CONTAINER_ROLLOVER: True})
        set_policy("container_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://test"})
        data = {"container_serial": container_serial, "rollover": True}
        self.request_assert_success('/container/register/initialize', data, self.at, 'POST')

        delete_policy("policy")
        delete_policy("container_policy")

    def test_28_admin_container_rollover_denied(self):
        # Admin has no CONTAINER_ROLLOVER rights
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(RegistrationState.get_key(),
                                                                RegistrationState.REGISTERED.value,
                                                                info_type=PI_INTERNAL)])
        set_policy("container_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://test"})
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={PolicyAction.CONTAINER_REGISTER: True})
        data = {"container_serial": container_serial, "rollover": True}
        self.request_denied_assert_403('/container/register/initialize', data, self.at, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")

    def test_29_admin_container_template_create_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_TEMPLATE_CREATE)
        data = {"template_options": {}}
        template_name = "test"
        self.request_assert_success(f'/container/generic/template/{template_name}', data, self.at, 'POST')
        delete_policy("policy")
        return template_name

    def test_30_admin_container_template_create_denied(self):
        # Admin does not have CONTAINER_TEMPLATE_CREATE rights
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_CREATE)
        data = {"template_options": {}}
        self.request_denied_assert_403('/container/generic/template/test', data, self.at, 'POST')
        delete_policy("policy")

    def test_31_admin_container_template_delete_allowed(self):
        template_name = self.test_29_admin_container_template_create_allowed()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_TEMPLATE_DELETE)
        self.request_assert_success(f'/container/template/{template_name}', {}, self.at, 'DELETE')
        delete_policy("policy")

    def test_32_admin_container_template_delete_denied(self):
        template_name = self.test_29_admin_container_template_create_allowed()
        # Admin does not have CONTAINER_TEMPLATE_DELETE rights
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_CREATE)
        self.request_denied_assert_403(f'/container/template/{template_name}', {}, self.at, 'DELETE')
        delete_policy("policy")
        get_template_obj(template_name).delete()

    def test_33_admin_template_list_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_TEMPLATE_LIST)
        self.request_assert_success('/container/templates', {}, self.at, 'GET')
        delete_policy("policy")

    def test_34_admin_template_list_denied(self):
        # Admin does not have CONTAINER_TEMPLATE_LIST rights
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_CREATE)
        self.request_denied_assert_403('/container/templates', {}, self.at, 'GET')
        delete_policy("policy")

    def test_35_admin_compare_template_container_allowed(self):
        template_name = self.test_29_admin_container_template_create_allowed()
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={PolicyAction.CONTAINER_TEMPLATE_LIST: True, PolicyAction.CONTAINER_LIST: True})
        self.request_assert_success(f'/container/template/{template_name}/compare', {}, self.at, 'GET')
        delete_policy("policy")
        get_template_obj(template_name).delete()

    def test_36_admin_compare_template_container_denied(self):
        template_name = self.test_29_admin_container_template_create_allowed()
        # Admin does not have CONTAINER_TEMPLATE_LIST rights
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_CREATE)
        self.request_denied_assert_403(f'/container/template/{template_name}/compare', {}, self.at, 'GET')
        delete_policy("policy")
        get_template_obj(template_name).delete()

    def test_37_admin_create_container_with_template(self):
        # admin is allowed to create container and enroll HOTP, but not TOTP tokens
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={PolicyAction.CONTAINER_CREATE: True, "enrollHOTP": True})

        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {
                               "tokens": [{"type": "totp", "genkey": True, "user": True},
                                          {"type": "hotp", "genkey": True}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        request_params = json.dumps(
            {"type": "smartphone", "template": template_params, "user": "hans", "realm": self.realm1})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertEqual("hotp", tokens[0].get_type())
        container_template = container.template
        self.assertEqual(template_params["name"], container_template.name)

        template = get_template_obj(template_params["name"])
        template.delete()

        delete_policy("policy")

    def test_38_admin_set_container_info_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO)
        container_serial = self.create_container_for_user("smartphone")
        self.request_assert_success(f"/container/{container_serial}/info/test", {"value": "1234"}, self.at,
                                    method='POST')
        delete_policy("policy")

    def test_39_admin_set_container_info_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE)
        container_serial = self.create_container_for_user("smartphone")
        self.request_denied_assert_403(f"/container/{container_serial}/info/test", {"value": "1234"}, self.at,
                                       method='POST')
        delete_policy("policy")

        # Modify container info is allowed, but internal info can not be modified
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO)
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info(
            [TokenContainerInfoData(key="public_server_key", value="123456789", info_type=PI_INTERNAL)])
        self.request_denied_assert_403(f"/container/{container_serial}/info/public_server_key",
                                       {"value": "1234"}, self.at, method='POST')
        delete_policy("policy")

    def test_40_admin_delete_container_info_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO)
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key="test", value="1234")])
        self.request_assert_success(f"/container/{container_serial}/info/delete/test", {}, self.at,
                                    method="DELETE")
        delete_policy("policy")

    def test_41_admin_delete_container_info_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE)
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key="test", value="1234")])
        self.request_denied_assert_403(f"/container/{container_serial}/info/delete/test", {}, self.at,
                                       method="DELETE")
        delete_policy("policy")
