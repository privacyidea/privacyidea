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


class APIContainerAuthorizationUser(APIContainerAuthorization):
    """
    Test the authorization of the API endpoints for users.
        * allowed: user has the required rights
        * denied: user does not have the required rights
                  user has the rights, but is not the owner of the container
    """

    def test_01_user_create_allowed(self):
        self.create_container_for_user()

    def test_02_user_create_denied(self):
        # Set a random policy so that user actions are defined
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DESCRIPTION)
        self.request_denied_assert_403('/container/init', {"type": "Smartphone", "description": "test description!!"},
                                       self.at_user)
        delete_policy("policy")

    def test_03_user_delete_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}", {}, self.at_user, method='DELETE')
        delete_policy("policy")

    def test_04_user_delete_denied(self):
        # User does not have 'delete' rights
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_CREATE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}", {}, self.at_user, method='DELETE')
        delete_policy("policy")

        # User is not the owner of the container
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DELETE)
        # another owner
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}", {}, self.at_user, method='DELETE')
        # no owner
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}", {}, self.at_user, method='DELETE')
        delete_policy("policy")

    def test_05_user_description_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DESCRIPTION)
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/description", {"description": "test"}, self.at_user,
                                    method='POST')
        delete_policy("policy")

    def test_06_user_description_denied(self):
        # User does not have 'description' rights
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/description", {"description": "test"},
                                       self.at_user,
                                       method='POST')
        delete_policy("policy")

        # User is not the owner of the container
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DESCRIPTION)
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/description", {"description": "test"},
                                       self.at_user, method='POST')

        # Container has no owner
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/description", {"description": "test"},
                                       self.at_user, method='POST')
        delete_policy("policy")

    def test_07_user_state_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_STATE)
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                    self.at_user,
                                    method='POST')
        delete_policy("policy")

    def test_08_user_state_denied(self):
        # User does not have 'state' rights
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                       self.at_user,
                                       method='POST')
        delete_policy("policy")

        # User is not the owner of the container
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_STATE)
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                       self.at_user, method='POST')

        # Container has no owner
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                       self.at_user, method='POST')
        delete_policy("policy")

    def test_09_user_add_token_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_ADD_TOKEN)
        container_serial = self.create_container_for_user()
        container = find_container_by_serial(container_serial)
        container_owner = container.get_users()[0]

        # add single token
        token = init_token({"genkey": "1"}, user=container_owner)
        token_serial = token.get_serial()
        result = self.request_assert_success(f"/container/{container_serial}/add", {"serial": token_serial},
                                             self.at_user,
                                             method='POST')
        self.assertTrue(result["result"]["value"])

        # add multiple tokens
        token2 = init_token({"genkey": "1"}, user=container_owner)
        token3 = init_token({"genkey": "1"}, user=container_owner)
        token_serials = ','.join([token2.get_serial(), token3.get_serial()])
        result = self.request_assert_success(f"/container/{container_serial}/addall", {"serial": token_serials},
                                             self.at_user,
                                             method='POST')
        self.assertTrue(result["result"]["value"][token2.get_serial()])
        self.assertTrue(result["result"]["value"][token3.get_serial()])

        delete_policy("policy")

    def test_10_user_add_token_denied(self):
        # Arrange
        container_serial = self.create_container_for_user()
        my_token = init_token({"genkey": "1"}, user=User("selfservice", self.realm1, self.resolvername1))
        my_token_serial = my_token.get_serial()

        # User does not have 'add' rights
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DELETE)
        self.request_denied_assert_403(f"/container/{container_serial}/add", {"serial": my_token_serial}, self.at_user,
                                       method='POST')
        delete_policy("policy")

        # User has 'add' rights but is not the owner of the token
        user = User(login="hans", realm=self.realm1, resolver=self.resolvername1)
        token = init_token({"genkey": "1"}, user=user)
        token_serial = token.get_serial()
        set_policy("policy", scope=SCOPE.USER,
                   action={PolicyAction.CONTAINER_ADD_TOKEN: True, PolicyAction.CONTAINER_REMOVE_TOKEN: True})
        self.request_denied_assert_403(f"/container/{container_serial}/add", {"serial": token_serial}, self.at_user,
                                       method='POST')

        # User has 'add' rights but is not the owner of the container
        another_container_serial = init_container({"type": "generic",
                                                   "user": user.login,
                                                   "realm": user.realm})["container_serial"]
        self.request_denied_assert_403(f"/container/{another_container_serial}/add", {"serial": my_token_serial},
                                       self.at_user,
                                       method='POST')

        # User has 'add' rights but the token is already in a container from another user
        add_token_to_container(another_container_serial, my_token_serial)
        self.request_denied_assert_403(f"/container/{container_serial}/add", {"serial": my_token_serial},
                                       self.at_user,
                                       method='POST')

        # Adding multiple tokens, user is only the owner of one token
        token2 = init_token({"genkey": "1"}, user=User("hans", self.realm1))
        token3 = init_token({"genkey": "1"}, user=User("selfservice", self.realm1))
        token4 = init_token({"genkey": "1"})
        token_serials = ','.join([token2.get_serial(), token3.get_serial(), token4.get_serial()])
        result = self.request_assert_success(f"/container/{container_serial}/addall", {"serial": token_serials},
                                             self.at_user,
                                             method='POST')
        self.assertFalse(result["result"]["value"][token2.get_serial()])
        self.assertTrue(result["result"]["value"][token3.get_serial()])
        self.assertFalse(result["result"]["value"][token4.get_serial()])

        delete_policy("policy")

    def test_11_user_remove_token_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_REMOVE_TOKEN)
        container_serial = self.create_container_for_user()
        container = find_container_by_serial(container_serial)

        # single token
        token = init_token({"genkey": "1"}, user=container.get_users()[0])
        token_serial = token.get_serial()
        container.add_token(token)

        result = self.request_assert_success(f"/container/{container_serial}/remove", {"serial": token_serial},
                                             self.at_user,
                                             method='POST')
        self.assertTrue(result["result"]["value"])

        # multiple tokens
        hotp = init_token({"type": "hotp", "genkey": True}, user=container.get_users()[0])
        container.add_token(hotp)
        totp = init_token({"type": "totp", "genkey": True}, user=container.get_users()[0])
        container.add_token(totp)
        serials = ','.join([hotp.get_serial(), totp.get_serial()])
        result = self.request_assert_success(f"/container/{container_serial}/removeall", {"serial": serials},
                                             self.at_user,
                                             method='POST')
        self.assertTrue(result["result"]["value"][hotp.get_serial()])
        self.assertTrue(result["result"]["value"][totp.get_serial()])
        delete_policy("policy")

    def test_12_user_remove_token_denied(self):
        # User does not have 'remove' rights
        container_serial = self.create_container_for_user()
        my_token = init_token({"genkey": "1"}, user=User("selfservice", self.realm1, self.resolvername1))
        my_token_serial = my_token.get_serial()
        add_token_to_container(container_serial, my_token_serial)
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DELETE)
        self.request_denied_assert_403(f"/container/{container_serial}/remove", {"serial": my_token_serial},
                                       self.at_user, method='POST')
        delete_policy("policy")

        # User has 'remove' rights but is not the owner of the token
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_REMOVE_TOKEN)
        user = User(login="hans", realm=self.realm1, resolver=self.resolvername1)
        token = init_token({"genkey": "1"}, user=user)
        token_serial = token.get_serial()
        add_token_to_container(container_serial, token_serial)
        self.request_denied_assert_403(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at_user,
                                       method='POST')

        # User has 'remove' rights but is not the owner of the token (token has no owner)
        unassign_token(token_serial)
        add_token_to_container(container_serial, token_serial)
        self.request_denied_assert_403(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at_user,
                                       method='POST')

        # User has 'remove' rights but is not the owner of the container
        another_container_serial = init_container({"type": "generic",
                                                   "user": "hans",
                                                   "realm": self.realm1})["container_serial"]
        add_token_to_container(another_container_serial, my_token_serial)
        self.request_denied_assert_403(f"/container/{another_container_serial}/remove", {"serial": my_token_serial},
                                       self.at_user, method='POST')

        # User has 'remove' rights but is not the owner of the container (container has no owner)
        find_container_by_serial(another_container_serial).remove_user(User("hans", self.realm1))
        add_token_to_container(another_container_serial, my_token_serial)
        self.request_denied_assert_403(f"/container/{another_container_serial}/remove", {"serial": my_token_serial},
                                       self.at_user, method='POST')

        # multiple tokens
        container = find_container_by_serial(container_serial)
        hotp = init_token({"type": "hotp", "genkey": True}, user=User("hans", self.realm1))
        container.add_token(hotp)
        totp = init_token({"type": "totp", "genkey": True}, user=container.get_users()[0])
        container.add_token(totp)
        spass = init_token({"type": "spass"})
        container.add_token(spass)
        serials = ','.join([hotp.get_serial(), totp.get_serial(), spass.get_serial()])
        result = self.request_assert_success(f"/container/{container_serial}/removeall", {"serial": serials},
                                             self.at_user,
                                             method='POST')
        self.assertFalse(result["result"]["value"][hotp.get_serial()])
        self.assertTrue(result["result"]["value"][totp.get_serial()])
        self.assertFalse(result["result"]["value"][spass.get_serial()])
        delete_policy("policy")

    def test_13_user_assign_user_allowed(self):
        # Note: This will not set the user root but the user selfservice, because the user attribute is changed in
        # before_request()
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_ASSIGN_USER)
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/assign", {"realm": "realm1", "user": "root"},
                                    self.at_user)
        delete_policy("policy")

    def test_14_user_assign_user_denied(self):
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": "realm1", "user": "selfservice"},
                                       self.at_user)
        delete_policy("policy")

    def test_15_user_remove_user_allowed(self):
        # User is allowed to unassign from its own container
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_UNASSIGN_USER)
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/unassign", {"realm": "realm1", "user": "root"},
                                    self.at_user)
        delete_policy("policy")

    def test_16_user_remove_user_denied(self):
        # User does not have 'unassign' rights
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": "realm1", "user": "selfservice"}, self.at_user)
        delete_policy("policy")

        # User is not allowed to unassign users from a container that is not his own
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_UNASSIGN_USER)
        container_serial = init_container({"type": "generic"})["container_serial"]
        user = User(login="hans", realm=self.realm1, resolver=self.resolvername1)
        assign_user(container_serial, user)
        self.request_denied_assert_403(f"/container/{container_serial}/unassign", {"realm": "realm1", "user": "root"},
                                       self.at_user)
        delete_policy("policy")

    def test_17_user_container_realms_denied(self):
        # Editing the container realms is an admin action and therefore only ever allowed for admins
        # But this returns a 401 from the @admin_required decorator
        container_serial = self.create_container_for_user()
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DELETE)

        with self.app.test_request_context(f"/container/{container_serial}/realms", method='POST',
                                           data={"realms": "realm1"}, headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)
        delete_policy("policy")

    def test_18_user_container_list_allowed(self):
        # Arrange
        self.setUp_user_realms()
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_LIST)

        # container with token from another user: reduce token info
        container_serial = init_container({"type": "generic"})["container_serial"]
        me = User("selfservice", self.realm1, self.resolvername1)
        assign_user(container_serial, me)

        my_token = init_token({"genkey": "1"}, user=me)
        my_token_serial = my_token.get_serial()
        add_token_to_container(container_serial, my_token_serial)

        user = User(login="hans", realm=self.realm1, resolver=self.resolvername1)
        another_token = init_token({"genkey": "1"}, user=user)
        token_serial = another_token.get_serial()
        add_token_to_container(container_serial, token_serial)

        # Act
        result = self.request_assert_success('/container/', {"container_serial": container_serial}, self.at_user, 'GET')

        # Assert
        tokens = result["result"]["value"]["containers"][0]["tokens"]
        # first token: all information
        self.assertEqual(my_token.get_serial(), tokens[0]["serial"])
        self.assertEqual("hotp", tokens[0]["tokentype"])
        # second token: only serial
        self.assertEqual(another_token.get_serial(), tokens[1]["serial"])
        self.assertEqual(1, len(tokens[1].keys()))
        self.assertNotIn("tokentype", tokens[1].keys())

        delete_policy("policy")

    def test_19_user_container_list_denied(self):
        # User does not have CONTAINER_LIST rights
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DELETE)
        self.request_denied_assert_403('/container/', {}, self.at_user, 'GET')

    def test_20_user_container_register_allowed(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial = self.create_container_for_user("smartphone")
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_REGISTER)
        # set two policies, but only one applicable for the realm of the user
        set_policy("another_container_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://random"},
                   realm=self.realm2)
        set_policy("container_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://test"},
                   realm=self.realm1)
        data = {"container_serial": container_serial}
        self.request_assert_success('/container/register/initialize', data, self.at_user, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")
        delete_policy("another_container_policy")
        return container_serial

    def test_21_user_container_register_denied(self):
        container_serial = self.create_container_for_user("smartphone")
        set_policy("container_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://test"})
        # User does not have CONTAINER_REGISTER rights
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_CREATE)
        data = {"container_serial": container_serial}
        self.request_denied_assert_403('/container/register/initialize', data, self.at_user, 'POST')
        delete_container_by_serial(container_serial)
        delete_policy("policy")

        # user is not the owner of the container
        another_container_serial = init_container({"type": "smartphone",
                                                   "user": "hans",
                                                   "realm": self.realm1})["container_serial"]
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_REGISTER)
        data = {"container_serial": another_container_serial}
        self.request_denied_assert_403('/container/register/initialize', data, self.at_user, 'POST')
        delete_container_by_serial(another_container_serial)
        delete_policy("policy")

        delete_policy("container_policy")

    def test_22_user_container_unregister_allowed(self):
        container_serial = self.test_20_user_container_register_allowed()
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_UNREGISTER)
        self.request_assert_success(f'/container/register/{container_serial}/terminate', {}, self.at_user, 'POST')
        delete_policy("policy")

    def test_23_user_container_unregister_denied(self):
        container_serial = self.test_20_user_container_register_allowed()
        # User does not have CONTAINER_UNREGISTER rights
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_CREATE)
        self.request_denied_assert_403(f'/container/register/{container_serial}/terminate', {}, self.at_user, 'POST')
        delete_policy("policy")

        # User has CONTAINER_UNREGISTER rights but is not the owner of the container
        another_container_serial = init_container({"type": "smartphone",
                                                   "user": "hans",
                                                   "realm": self.realm1})["container_serial"]
        set_policy("container_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://test"})
        data = {"container_serial": container_serial}
        self.request_assert_success('/container/register/initialize', data, self.at, 'POST')

        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_UNREGISTER)
        self.request_denied_assert_403(f'/container/register/{another_container_serial}/terminate', {}, self.at_user,
                                       'POST')
        delete_policy("policy")
        delete_policy("container_policy")

    def test_24_user_container_rollover_allowed(self):
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key=RegistrationState.get_key(),
                                                                value=RegistrationState.REGISTERED.value,
                                                                info_type=PI_INTERNAL)])
        set_policy("policy", scope=SCOPE.USER,
                   action={PolicyAction.CONTAINER_ROLLOVER: True})
        set_policy("container_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://test"})
        data = {"container_serial": container_serial, "rollover": True}
        self.request_assert_success('/container/register/initialize', data, self.at_user, 'POST')

        delete_policy("policy")
        delete_policy("container_policy")

    def test_25_user_container_rollover_denied(self):
        # User has no CONTAINER_ROLLOVER rights
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key=RegistrationState.get_key(),
                                                                value=RegistrationState.REGISTERED.value,
                                                                info_type=PI_INTERNAL)])
        set_policy("container_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://test"})
        set_policy("policy", scope=SCOPE.USER,
                   action={PolicyAction.CONTAINER_REGISTER: True})
        data = {"container_serial": container_serial, "rollover": True}
        self.request_denied_assert_403('/container/register/initialize', data, self.at_user, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")

    def test_26_user_container_template_create_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_TEMPLATE_CREATE)
        data = {"template_options": {}}
        template_name = "test"
        self.request_assert_success(f'/container/generic/template/{template_name}', data, self.at_user, 'POST')
        delete_policy("policy")
        return template_name

    def test_27_user_container_template_create_denied(self):
        # User does not have CONTAINER_TEMPLATE_CREATE rights
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_CREATE)
        data = {"template_options": {}}
        self.request_denied_assert_403('/container/generic/template/test', data, self.at_user, 'POST')
        delete_policy("policy")

    def test_28_user_container_template_delete_allowed(self):
        template_name = self.test_26_user_container_template_create_allowed()
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_TEMPLATE_DELETE)
        self.request_assert_success(f'/container/template/{template_name}', {}, self.at_user, 'DELETE')
        delete_policy("policy")

    def test_29_user_container_template_delete_denied(self):
        template_name = self.test_26_user_container_template_create_allowed()
        # User does not have CONTAINER_TEMPLATE_DELETE rights
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_CREATE)
        self.request_denied_assert_403(f'/container/template/{template_name}', {}, self.at_user, 'DELETE')
        get_template_obj(template_name).delete()
        delete_policy("policy")

    def test_30_user_template_list_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_TEMPLATE_LIST)
        self.request_assert_success('/container/templates', {}, self.at_user, 'GET')
        delete_policy("policy")

    def test_31_user_template_list_denied(self):
        # User does not have CONTAINER_TEMPLATE_LIST rights
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_CREATE)
        self.request_denied_assert_403('/container/templates', {}, self.at_user, 'GET')
        delete_policy("policy")

    def test_32_user_compare_template_container_allowed(self):
        template_name = "test"
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])
        set_policy("policy", scope=SCOPE.USER,
                   action={PolicyAction.CONTAINER_TEMPLATE_LIST: True, PolicyAction.CONTAINER_LIST: True})
        self.request_assert_success(f'/container/template/{template_name}/compare', {}, self.at_user, 'GET')

        # Test with containers the user might not be allowed to see
        # Create containers with template
        request_params = json.dumps({"type": "smartphone", "template": template_params})

        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')
        container_serial_no_user = result["result"]["value"]["container_serial"]

        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')
        container_serial_user = result["result"]["value"]["container_serial"]
        container_user = find_container_by_serial(container_serial_user)
        container_user.add_user(User("selfservice", self.realm1))

        result = self.request_assert_success(f'/container/template/{template_name}/compare', {}, self.at_user, 'GET')
        containers = result["result"]["value"].keys()
        self.assertIn(container_serial_user, containers)
        self.assertNotIn(container_serial_no_user, containers)

        # Compare specific container
        # container of the user
        result = self.request_assert_success(f'/container/template/{template_name}/compare',
                                             {"container_serial": container_serial_user}, self.at_user, 'GET')
        containers = result["result"]["value"].keys()
        self.assertIn(container_serial_user, containers)
        self.assertNotIn(container_serial_no_user, containers)
        # container without user
        result = self.request_assert_success(f'/container/template/{template_name}/compare',
                                             {"container_serial": container_serial_no_user}, self.at_user, 'GET')
        containers = result["result"]["value"].keys()
        self.assertNotIn(container_serial_user, containers)
        self.assertNotIn(container_serial_no_user, containers)

        delete_policy("policy")
        template = get_template_obj(template_name)
        template.delete()

    def test_33_user_compare_template_container_denied(self):
        template_name = self.test_26_user_container_template_create_allowed()
        # User does not have CONTAINER_TEMPLATE_LIST rights
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_CREATE)
        self.request_denied_assert_403(f'/container/template/{template_name}/compare', {}, self.at_user, 'GET')
        delete_policy("policy")

        template = get_template_obj(template_name)
        template.delete()

    def test_34_create_container_with_template(self):
        # user is allowed to create container and enroll HOTP and TOTP tokens, but not spass tokens
        set_policy("policy", scope=SCOPE.USER, action={PolicyAction.CONTAINER_CREATE: True, "enrollHOTP": True,
                                                       "enrollTOTP": True})

        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {
                               "tokens": [{"type": "totp", "genkey": True, "user": True},
                                          {"type": "hotp", "genkey": True, "user": False},
                                          {"type": "spass"}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        request_params = json.dumps({"type": "generic", "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at_user, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertSetEqual({"hotp", "totp"}, {token.get_tokentype() for token in tokens})
        # The user is assigned to both tokens because users are always assigned to tokens during enrollment
        for token in tokens:
            self.assertEqual("selfservice", token.user.login)
            self.assertEqual(self.realm1, token.user.realm)

        container_template = container.template
        self.assertEqual(template_params["name"], container_template.name)

        template = get_template_obj(template_params["name"])
        template.delete()

        delete_policy("policy")
