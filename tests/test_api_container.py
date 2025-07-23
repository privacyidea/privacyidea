import base64
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import json

import passlib
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey

from privacyidea.lib.applications.offline import MachineApplication, REFILLTOKEN_LENGTH
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.container import (create_container_template, get_template_obj, delete_container_by_serial,
                                       get_container_realms, set_container_states, unregister)
from privacyidea.lib.containers.container_info import PI_INTERNAL, TokenContainerInfoData, RegistrationState
from privacyidea.lib.containers.container_states import ContainerStates
from privacyidea.lib.containers.smartphone import SmartphoneOptions
from privacyidea.lib.crypto import generate_keypair_ecc, decrypt_aes
from privacyidea.lib.container import (init_container, find_container_by_serial, add_token_to_container, assign_user,
                                       add_container_realms, remove_token_from_container)
from privacyidea.lib.machine import attach_token
from privacyidea.lib.policies.policy_conditions import ConditionSection, ConditionHandleMissingData
from privacyidea.lib.policy import set_policy, SCOPE, ACTION, delete_policy
from privacyidea.lib.privacyideaserver import add_privacyideaserver
from privacyidea.lib.realm import set_realm, set_default_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.serviceid import set_serviceid
from privacyidea.lib.smsprovider.FirebaseProvider import FirebaseConfig
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
from privacyidea.lib.token import (get_one_token, get_tokens_from_serial_or_user,
                                   get_tokeninfo, get_tokens)
from privacyidea.lib.tokens.papertoken import PAPERACTION
from privacyidea.lib.tokens.pushtoken import PUSH_ACTION
from privacyidea.lib.tokens.tantoken import TANACTION
from privacyidea.lib.token import init_token, get_tokens_paginate, unassign_token
from privacyidea.lib.user import User
from privacyidea.lib.utils.compare import PrimaryComparators
from tests.base import MyApiTestCase
from tests.test_lib_tokencontainer import MockSmartphone


class APIContainerTest(MyApiTestCase):
    FIREBASE_FILE = "tests/testdata/firebase-test.json"
    CLIENT_FILE = "tests/testdata/google-services.json"

    def clear_flask_g(self):
        if self.app_context.g:
            keys = [key for key in iter(self.app_context.g)]
            [self.app_context.g.pop(key) for key in keys]

    def request_assert_success(self, url, data: dict, auth_token, method='POST'):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
            self.assertTrue(res.json["result"]["status"])
        self.clear_flask_g()
        return res.json

    def request_assert_error(self, status_code, url, data: dict, auth_token, method='POST'):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(status_code, res.status_code, res.json)
            self.assertFalse(res.json["result"]["status"])
        self.clear_flask_g()
        return res.json

    def request_assert_405(self, url, data: dict, auth_token, method='POST'):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(405, res.status_code, res.json)
        self.clear_flask_g()
        return res.json

    def request_assert_404_no_result(self, url, data: dict, auth_token, method='POST'):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(404, res.status_code, res.json)
        self.clear_flask_g()


class APIContainerAuthorization(APIContainerTest):
    def setUp(self):
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

    def request_denied_assert_403(self, url, data: dict, auth_token, method='POST'):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(403, res.status_code, res.json)
            self.assertEqual(res.json["result"]["error"]["code"], 303)
        self.clear_flask_g()
        return res.json

    def create_container_for_user(self, ctype="generic"):
        set_policy("user_container_create", scope=SCOPE.USER, action=ACTION.CONTAINER_CREATE)
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
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DESCRIPTION)
        self.request_denied_assert_403('/container/init', {"type": "Smartphone", "description": "test description!!"},
                                       self.at_user)
        delete_policy("policy")

    def test_03_user_delete_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}", {}, self.at_user, method='DELETE')
        delete_policy("policy")

    def test_04_user_delete_denied(self):
        # User does not have 'delete' rights
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_CREATE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}", {}, self.at_user, method='DELETE')
        delete_policy("policy")

        # User is not the owner of the container
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        # another owner
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}", {}, self.at_user, method='DELETE')
        # no owner
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}", {}, self.at_user, method='DELETE')
        delete_policy("policy")

    def test_05_user_description_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DESCRIPTION)
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/description", {"description": "test"}, self.at_user,
                                    method='POST')
        delete_policy("policy")

    def test_06_user_description_denied(self):
        # User does not have 'description' rights
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/description", {"description": "test"},
                                       self.at_user,
                                       method='POST')
        delete_policy("policy")

        # User is not the owner of the container
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DESCRIPTION)
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/description", {"description": "test"},
                                       self.at_user, method='POST')

        # Container has no owner
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/description", {"description": "test"},
                                       self.at_user, method='POST')
        delete_policy("policy")

    def test_07_user_state_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_STATE)
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                    self.at_user,
                                    method='POST')
        delete_policy("policy")

    def test_08_user_state_denied(self):
        # User does not have 'state' rights
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                       self.at_user,
                                       method='POST')
        delete_policy("policy")

        # User is not the owner of the container
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_STATE)
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                       self.at_user, method='POST')

        # Container has no owner
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                       self.at_user, method='POST')
        delete_policy("policy")

    def test_09_user_add_token_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_ADD_TOKEN)
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
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        self.request_denied_assert_403(f"/container/{container_serial}/add", {"serial": my_token_serial}, self.at_user,
                                       method='POST')
        delete_policy("policy")

        # User has 'add' rights but is not the owner of the token
        user = User(login="hans", realm=self.realm1, resolver=self.resolvername1)
        token = init_token({"genkey": "1"}, user=user)
        token_serial = token.get_serial()
        set_policy("policy", scope=SCOPE.USER,
                   action={ACTION.CONTAINER_ADD_TOKEN: True, ACTION.CONTAINER_REMOVE_TOKEN: True})
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
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_REMOVE_TOKEN)
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
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        self.request_denied_assert_403(f"/container/{container_serial}/remove", {"serial": my_token_serial},
                                       self.at_user, method='POST')
        delete_policy("policy")

        # User has 'remove' rights but is not the owner of the token
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_REMOVE_TOKEN)
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
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_ASSIGN_USER)
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/assign", {"realm": "realm1", "user": "root"},
                                    self.at_user)
        delete_policy("policy")

    def test_14_user_assign_user_denied(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": "realm1", "user": "selfservice"},
                                       self.at_user)
        delete_policy("policy")

    def test_15_user_remove_user_allowed(self):
        # User is allowed to unassign from its own container
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_UNASSIGN_USER)
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/unassign", {"realm": "realm1", "user": "root"},
                                    self.at_user)
        delete_policy("policy")

    def test_16_user_remove_user_denied(self):
        # User does not have 'unassign' rights
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": "realm1", "user": "selfservice"}, self.at_user)
        delete_policy("policy")

        # User is not allowed to unassign users from a container that is not his own
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_UNASSIGN_USER)
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
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)

        with self.app.test_request_context(f"/container/{container_serial}/realms", method='POST',
                                           data={"realms": "realm1"}, headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)
        delete_policy("policy")

    def test_18_user_container_list_allowed(self):
        # Arrange
        self.setUp_user_realms()
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_LIST)

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
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        self.request_denied_assert_403('/container/', {}, self.at_user, 'GET')

    def test_20_user_container_register_allowed(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial = self.create_container_for_user("smartphone")
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_REGISTER)
        # set two policies, but only one applicable for the realm of the user
        set_policy("another_container_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://random"},
                   realm=self.realm2)
        set_policy("container_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://test"},
                   realm=self.realm1)
        data = {"container_serial": container_serial}
        self.request_assert_success('/container/register/initialize', data, self.at_user, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")
        delete_policy("another_container_policy")
        return container_serial

    def test_21_user_container_register_denied(self):
        container_serial = self.create_container_for_user("smartphone")
        set_policy("container_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://test"})
        # User does not have CONTAINER_REGISTER rights
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_CREATE)
        data = {"container_serial": container_serial}
        self.request_denied_assert_403('/container/register/initialize', data, self.at_user, 'POST')
        delete_container_by_serial(container_serial)
        delete_policy("policy")

        # user is not the owner of the container
        another_container_serial = init_container({"type": "smartphone",
                                                   "user": "hans",
                                                   "realm": self.realm1})["container_serial"]
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_REGISTER)
        data = {"container_serial": another_container_serial}
        self.request_denied_assert_403('/container/register/initialize', data, self.at_user, 'POST')
        delete_container_by_serial(another_container_serial)
        delete_policy("policy")

        delete_policy("container_policy")

    def test_22_user_container_unregister_allowed(self):
        container_serial = self.test_20_user_container_register_allowed()
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_UNREGISTER)
        self.request_assert_success(f'/container/register/{container_serial}/terminate', {}, self.at_user, 'POST')
        delete_policy("policy")

    def test_23_user_container_unregister_denied(self):
        container_serial = self.test_20_user_container_register_allowed()
        # User does not have CONTAINER_UNREGISTER rights
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_CREATE)
        self.request_denied_assert_403(f'/container/register/{container_serial}/terminate', {}, self.at_user, 'POST')
        delete_policy("policy")

        # User has CONTAINER_UNREGISTER rights but is not the owner of the container
        another_container_serial = init_container({"type": "smartphone",
                                                   "user": "hans",
                                                   "realm": self.realm1})["container_serial"]
        set_policy("container_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://test"})
        data = {"container_serial": container_serial}
        self.request_assert_success('/container/register/initialize', data, self.at, 'POST')

        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_UNREGISTER)
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
                   action={ACTION.CONTAINER_ROLLOVER: True})
        set_policy("container_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://test"})
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
        set_policy("container_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://test"})
        set_policy("policy", scope=SCOPE.USER,
                   action={ACTION.CONTAINER_REGISTER: True})
        data = {"container_serial": container_serial, "rollover": True}
        self.request_denied_assert_403('/container/register/initialize', data, self.at_user, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")

    def test_26_user_container_template_create_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_TEMPLATE_CREATE)
        data = {"template_options": {}}
        template_name = "test"
        self.request_assert_success(f'/container/generic/template/{template_name}', data, self.at_user, 'POST')
        delete_policy("policy")
        return template_name

    def test_27_user_container_template_create_denied(self):
        # User does not have CONTAINER_TEMPLATE_CREATE rights
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_CREATE)
        data = {"template_options": {}}
        self.request_denied_assert_403('/container/generic/template/test', data, self.at_user, 'POST')
        delete_policy("policy")

    def test_28_user_container_template_delete_allowed(self):
        template_name = self.test_26_user_container_template_create_allowed()
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_TEMPLATE_DELETE)
        self.request_assert_success(f'/container/template/{template_name}', {}, self.at_user, 'DELETE')
        delete_policy("policy")

    def test_29_user_container_template_delete_denied(self):
        template_name = self.test_26_user_container_template_create_allowed()
        # User does not have CONTAINER_TEMPLATE_DELETE rights
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_CREATE)
        self.request_denied_assert_403(f'/container/template/{template_name}', {}, self.at_user, 'DELETE')
        get_template_obj(template_name).delete()
        delete_policy("policy")

    def test_30_user_template_list_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_TEMPLATE_LIST)
        self.request_assert_success('/container/templates', {}, self.at_user, 'GET')
        delete_policy("policy")

    def test_31_user_template_list_denied(self):
        # User does not have CONTAINER_TEMPLATE_LIST rights
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_CREATE)
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
                   action={ACTION.CONTAINER_TEMPLATE_LIST: True, ACTION.CONTAINER_LIST: True})
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
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_CREATE)
        self.request_denied_assert_403(f'/container/template/{template_name}/compare', {}, self.at_user, 'GET')
        delete_policy("policy")

        template = get_template_obj(template_name)
        template.delete()

    def test_34_create_container_with_template(self):
        # user is allowed to create container and enroll HOTP and TOTP tokens, but not spass tokens
        set_policy("policy", scope=SCOPE.USER, action={ACTION.CONTAINER_CREATE: True, "enrollHOTP": True,
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


class APIContainerAuthorizationAdmin(APIContainerAuthorization):
    """
    Test the authorization of the API endpoints for admins.
        * allowed: admin has the required rights
        * denied: admin does not have the required rights
    """

    def test_01_admin_create_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE)
        result = self.request_assert_success('/container/init', {"type": "generic"}, self.at)
        self.assertGreater(len(result["result"]["value"]["container_serial"]), 0)
        delete_policy("policy")

    def test_02_admin_create_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DESCRIPTION)
        self.request_denied_assert_403('/container/init', {"type": "Smartphone", "description": "test description!!"},
                                       self.at)
        delete_policy("policy")

    def test_03_admin_delete_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}", {}, self.at, method='DELETE')
        delete_policy("policy")

    def test_04_admin_delete_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}", {}, self.at, method='DELETE')
        delete_policy("policy")

    def test_05_admin_description_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DESCRIPTION)
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
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/description", {"description": "test"},
                                       self.at, method='POST')
        delete_policy("policy")

    def test_07_admin_state_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_STATE)
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
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                       self.at, method='POST')
        delete_policy("policy")

    def test_09_admin_add_token_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ADD_TOKEN)
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
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{container_serial}/add", {"serial": token_serial}, self.at,
                                       method='POST')
        delete_policy("policy")

    def test_11_admin_add_multiple_tokens_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ADD_TOKEN)
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
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token2 = init_token({"type": "hotp", "genkey": True})
        serials = ",".join([token.get_serial(), token2.get_serial()])
        self.request_denied_assert_403(f"/container/{container_serial}/addall", {"serial": serials}, self.at,
                                       method='POST')
        delete_policy("policy")

    def test_13_admin_remove_token_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REMOVE_TOKEN)
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
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
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
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ASSIGN_USER)
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/assign",
                                    {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_16_admin_assign_user_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_17_admin_remove_user_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_UNASSIGN_USER)
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/unassign",
                                    {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_18_admin_remove_user_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_19_admin_container_realms_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REALMS)
        # container of a user
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)

        # container without user
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)
        delete_policy("policy")

    def test_20_admin_container_realms_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/realms", {"realms": "realm1"}, self.at)
        delete_policy("policy")

    def test_21_admin_container_list_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_LIST)
        self.request_assert_success('/container/', {}, self.at, 'GET')
        delete_policy("policy")

    def test_22_admin_container_list_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        self.request_denied_assert_403('/container/', {}, self.at, 'GET')
        delete_policy("policy")

    def test_23_admin_container_register_allowed(self):
        container_serial = self.create_container_for_user("smartphone")
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REGISTER)
        set_policy("container_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://test"})
        data = {"container_serial": container_serial}
        self.request_assert_success('/container/register/initialize', data, self.at, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")
        return container_serial

    def test_24_admin_container_register_denied(self):
        container_serial = self.create_container_for_user("smartphone")
        # Admin does not have CONTAINER_REGISTER rights
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE)
        set_policy("container_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://test"})
        data = {"container_serial": container_serial}
        self.request_denied_assert_403('/container/register/initialize', data, self.at, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")

    def test_25_admin_container_unregister_allowed(self):
        container_serial = self.test_23_admin_container_register_allowed()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_UNREGISTER)
        self.request_assert_success(f'/container/register/{container_serial}/terminate', {}, self.at, 'POST')
        delete_policy("policy")

    def test_26_admin_container_unregister_denied(self):
        container_serial = self.test_23_admin_container_register_allowed()
        # Admin does not have CONTAINER_UNREGISTER rights
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE)
        self.request_denied_assert_403(f'/container/register/{container_serial}/terminate', {}, self.at, 'POST')
        delete_policy("policy")

    def test_27_admin_container_rollover_allowed(self):
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key=RegistrationState.get_key(),
                                                                value=RegistrationState.REGISTERED.value,
                                                                info_type=PI_INTERNAL)])
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={ACTION.CONTAINER_ROLLOVER: True})
        set_policy("container_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://test"})
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
        set_policy("container_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://test"})
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={ACTION.CONTAINER_REGISTER: True})
        data = {"container_serial": container_serial, "rollover": True}
        self.request_denied_assert_403('/container/register/initialize', data, self.at, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")

    def test_29_admin_container_template_create_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_TEMPLATE_CREATE)
        data = {"template_options": {}}
        template_name = "test"
        self.request_assert_success(f'/container/generic/template/{template_name}', data, self.at, 'POST')
        delete_policy("policy")
        return template_name

    def test_30_admin_container_template_create_denied(self):
        # Admin does not have CONTAINER_TEMPLATE_CREATE rights
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE)
        data = {"template_options": {}}
        self.request_denied_assert_403('/container/generic/template/test', data, self.at, 'POST')
        delete_policy("policy")

    def test_31_admin_container_template_delete_allowed(self):
        template_name = self.test_29_admin_container_template_create_allowed()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_TEMPLATE_DELETE)
        self.request_assert_success(f'/container/template/{template_name}', {}, self.at, 'DELETE')
        delete_policy("policy")

    def test_32_admin_container_template_delete_denied(self):
        template_name = self.test_29_admin_container_template_create_allowed()
        # Admin does not have CONTAINER_TEMPLATE_DELETE rights
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE)
        self.request_denied_assert_403(f'/container/template/{template_name}', {}, self.at, 'DELETE')
        delete_policy("policy")
        get_template_obj(template_name).delete()

    def test_33_admin_template_list_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_TEMPLATE_LIST)
        self.request_assert_success('/container/templates', {}, self.at, 'GET')
        delete_policy("policy")

    def test_34_admin_template_list_denied(self):
        # Admin does not have CONTAINER_TEMPLATE_LIST rights
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE)
        self.request_denied_assert_403('/container/templates', {}, self.at, 'GET')
        delete_policy("policy")

    def test_35_admin_compare_template_container_allowed(self):
        template_name = self.test_29_admin_container_template_create_allowed()
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={ACTION.CONTAINER_TEMPLATE_LIST: True, ACTION.CONTAINER_LIST: True})
        self.request_assert_success(f'/container/template/{template_name}/compare', {}, self.at, 'GET')
        delete_policy("policy")
        get_template_obj(template_name).delete()

    def test_36_admin_compare_template_container_denied(self):
        template_name = self.test_29_admin_container_template_create_allowed()
        # Admin does not have CONTAINER_TEMPLATE_LIST rights
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE)
        self.request_denied_assert_403(f'/container/template/{template_name}/compare', {}, self.at, 'GET')
        delete_policy("policy")
        get_template_obj(template_name).delete()

    def test_37_admin_create_container_with_template(self):
        # admin is allowed to create container and enroll HOTP, but not TOTP tokens
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={ACTION.CONTAINER_CREATE: True, "enrollHOTP": True})

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
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO)
        container_serial = self.create_container_for_user("smartphone")
        self.request_assert_success(f"/container/{container_serial}/info/test", {"value": "1234"}, self.at,
                                    method='POST')
        delete_policy("policy")

    def test_39_admin_set_container_info_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user("smartphone")
        self.request_denied_assert_403(f"/container/{container_serial}/info/test", {"value": "1234"}, self.at,
                                       method='POST')
        delete_policy("policy")

        # Modify container info is allowed, but internal info can not be modified
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO)
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info(
            [TokenContainerInfoData(key="public_server_key", value="123456789", info_type=PI_INTERNAL)])
        self.request_denied_assert_403(f"/container/{container_serial}/info/public_server_key",
                                       {"value": "1234"}, self.at, method='POST')
        delete_policy("policy")

    def test_40_admin_delete_container_info_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO)
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key="test", value="1234")])
        self.request_assert_success(f"/container/{container_serial}/info/delete/test", {}, self.at,
                                    method="DELETE")
        delete_policy("policy")

    def test_41_admin_delete_container_info_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key="test", value="1234")])
        self.request_denied_assert_403(f"/container/{container_serial}/info/delete/test", {}, self.at,
                                       method="DELETE")
        delete_policy("policy")


class APIContainerAuthorizationHelpdesk(APIContainerAuthorization):
    """
    Test the authorization of the API endpoints for helpdesk admins.
        * allowed: helpdesk admin has the required rights on the realm / resolver / user of the container
        * denied: helpdesk admin does not have the required rights on the container
    """

    def test_01_helpdesk_create_allowed(self):
        self.setUp_user_realms()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE, realm=self.realm1)
        result = self.request_assert_success('/container/init', {"type": "generic", "realm": self.realm1}, self.at)
        self.assertGreater(len(result["result"]["value"]["container_serial"]), 0)
        delete_policy("policy")

    def test_02_helpdesk_create_denied(self):
        self.setUp_user_realm2()
        # policy for a realm
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE, realm=self.realm1)
        self.request_denied_assert_403('/container/init', {"type": "Smartphone", "realm": self.realm2},
                                       self.at)
        # create container for no realm is denied
        self.request_denied_assert_403('/container/init',
                                       {"type": "Smartphone"},
                                       self.at)
        delete_policy("policy")

        # policy for a resolver
        self.setUp_user_realm3()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE, resolver=self.resolvername1)
        self.request_denied_assert_403('/container/init',
                                       {"type": "Smartphone", "user": "corny", "realm": self.realm3},
                                       self.at)
        # create container for no user is denied
        self.request_denied_assert_403('/container/init',
                                       {"type": "Smartphone"},
                                       self.at)
        delete_policy("policy")

    def test_03_helpdesk_delete_allowed(self):
        self.setUp_user_realm2()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE, realm=[self.realm2, self.realm1])
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}", {}, self.at, method='DELETE')
        delete_policy("policy")

    def test_04_helpdesk_delete_denied(self):
        self.setUp_user_realm3()
        c_serial_user = self.create_container_for_user()
        c_serial_no_user = init_container({"type": "generic"})["container_serial"]

        # policy for a realm
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE, realm=self.realm3)
        # container of a user
        self.request_denied_assert_403(f"/container/{c_serial_user}", {}, self.at, method='DELETE')
        # container without user
        self.request_denied_assert_403(f"/container/{c_serial_no_user}", {}, self.at, method='DELETE')
        delete_policy("policy")

        # policy for a resolver
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE, resolver=self.resolvername3)
        # container of a user
        self.request_denied_assert_403(f"/container/{c_serial_user}", {}, self.at, method='DELETE')
        # container without user
        self.request_denied_assert_403(f"/container/{c_serial_no_user}", {}, self.at, method='DELETE')
        delete_policy("policy")

    def test_05_helpdesk_description_allowed(self):
        self.setUp_user_realm2()
        # policy for realms
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DESCRIPTION, realm=[self.realm1, self.realm2])
        self.request_assert_success(f"/container/{container_serial}/description", {"description": "test"}, self.at,
                                    method='POST')
        delete_policy("policy")
        # policy for resolver
        container_serial = self.create_container_for_user()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DESCRIPTION, resolver=self.resolvername1)
        self.request_assert_success(f"/container/{container_serial}/description", {"description": "test"}, self.at,
                                    method='POST')
        delete_policy("policy")
        # policy for user
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DESCRIPTION, user="selfservice",
                   realm=self.realm1, resolver=self.resolvername1)
        self.request_assert_success(f"/container/{container_serial}/description", {"description": "test"}, self.at,
                                    method='POST')
        delete_policy("policy")

    def test_06_helpdesk_description_denied(self):
        self.setUp_user_realm3()
        c_serial_user = self.create_container_for_user()
        c_serial_no_user = init_container({"type": "generic"})["container_serial"]

        # policy for a realm
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DESCRIPTION, realm=self.realm3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/description", {"description": "test"},
                                       self.at, method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/description", {"description": "test"},
                                       self.at, method='POST')
        delete_policy("policy")

        # policy for a resolver
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DESCRIPTION, resolver=self.resolvername3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/description", {"description": "test"},
                                       self.at, method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/description", {"description": "test"},
                                       self.at, method='POST')
        delete_policy("policy")

        # policy for a user
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DESCRIPTION, user="hans", realm=self.realm1,
                   resolver=self.resolvername1)
        self.request_denied_assert_403(f"/container/{c_serial_user}/description", {"description": "test"},
                                       self.at, method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/description", {"description": "test"},
                                       self.at, method='POST')
        delete_policy("policy")

    def test_07_helpdesk_state_allowed(self):
        container_serial = self.create_container_for_user()
        # policy for realm
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_STATE, realm=self.realm1)
        self.request_assert_success(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                    self.at, method='POST')
        delete_policy("policy")

        # policy for resolver
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_STATE, realm=self.realm1,
                   resolver=self.resolvername1)
        self.request_assert_success(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                    self.at, method='POST')
        delete_policy("policy")

    def test_08_helpdesk_state_denied(self):
        self.setUp_user_realm3()
        c_serial_user = self.create_container_for_user()
        c_serial_no_user = init_container({"type": "generic"})["container_serial"]

        # policy for realm
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_STATE, realm=self.realm3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/states", {"states": "active, damaged, lost"},
                                       self.at, method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/states", {"states": "active, damaged, lost"},
                                       self.at, method='POST')
        delete_policy("policy")

        # policy for resolver
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_STATE, resolver=self.resolvername3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/states", {"states": "active, damaged, lost"},
                                       self.at, method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/states", {"states": "active, damaged, lost"},
                                       self.at, method='POST')
        delete_policy("policy")

    def test_09_helpdesk_add_token_allowed(self):
        self.setUp_user_realm3()
        set_policy("policy_realm", scope=SCOPE.ADMIN,
                   action={ACTION.CONTAINER_ADD_TOKEN: True, ACTION.CONTAINER_REMOVE_TOKEN: True}, realm=self.realm1)
        set_policy("policy_resolver", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ADD_TOKEN, resolver=self.resolvername3)
        container_serial = self.create_container_for_user()

        # Add single token
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()
        self.request_assert_success(f"/container/{container_serial}/add", {"serial": token_serial}, self.at,
                                    method='POST')

        # Add token that is in another container
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()
        old_container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        add_token_to_container(old_container_serial, token_serial)
        self.request_assert_success(f"/container/{container_serial}/add", {"serial": token_serial}, self.at,
                                    method='POST')

        # add multiple tokens: one authorized with the realm, the other with the resolver
        token2 = init_token({"genkey": "1", "realm": self.realm1})
        token3 = init_token({"genkey": "1"}, user=User("corny", self.realm3))
        token_serials = ','.join([token2.get_serial(), token3.get_serial()])
        result = self.request_assert_success(f"/container/{container_serial}/addall", {"serial": token_serials},
                                             self.at,
                                             method='POST')
        self.assertTrue(result["result"]["value"][token2.get_serial()])
        self.assertTrue(result["result"]["value"][token3.get_serial()])
        delete_policy("policy_realm")
        delete_policy("policy_resolver")

        # Add token to container during enrollment allowed
        set_policy("policy", scope=SCOPE.ADMIN, action=[ACTION.CONTAINER_ADD_TOKEN, "enrollHOTP"], realm=self.realm1)
        result = self.request_assert_success("/token/init", {"type": "hotp", "realm": self.realm1, "genkey": 1,
                                                             "container_serial": container_serial}, self.at,
                                             method='POST')
        token_serial = result["detail"]["serial"]
        tokens = get_tokens_paginate(serial=token_serial)
        self.assertEqual(container_serial, tokens["tokens"][0]["container_serial"])
        delete_policy("policy")

    def test_10_helpdesk_add_token_denied(self):
        self.setUp_user_realm3()
        c_serial_user = self.create_container_for_user()
        c_serial_no_user = init_container({"type": "generic"})["container_serial"]

        # helpdesk of user realm realm3: container and token are both in realm1
        set_policy("policy_realm", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ADD_TOKEN, realm=self.realm3)
        set_policy("policy_resolver", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ADD_TOKEN, resolver=self.resolvername3)
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{c_serial_user}/add", {"serial": token_serial}, self.at,
                                       method='POST')

        # helpdesk of user realm realm3: only container is in realm1
        token = init_token({"genkey": "1", "realm": self.realm3})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{c_serial_user}/add", {"serial": token_serial}, self.at,
                                       method='POST')
        delete_policy("policy_realm")
        delete_policy("policy_resolver")

        # helpdesk of user realm realm1: only token is in realm3
        set_policy("policy_realm", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ADD_TOKEN, realm=self.realm1)
        set_policy("policy_resolver", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ADD_TOKEN, resolver=self.resolvername3)
        token = init_token({"genkey": "1", "realm": self.realm3})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{c_serial_user}/add", {"serial": token_serial}, self.at,
                                       method='POST')

        # Helpdesk is not allowed to remove token from old container
        token.set_realms([self.realm1])
        add_token_to_container(c_serial_no_user, token_serial)
        self.request_denied_assert_403(f"/container/{c_serial_user}/add", {"serial": token_serial}, self.at,
                                       method='POST')

        # Adding multiple tokens
        token2 = init_token({"genkey": "1"}, user=User("hans", self.realm1))
        token3 = init_token({"genkey": "1", "realm": self.realm1})
        token_no_user = init_token({"genkey": "1"})
        token_serials = ','.join(
            [token.get_serial(), token2.get_serial(), token_no_user.get_serial(), token3.get_serial()])
        # to authorized container
        result = self.request_assert_success(f"/container/{c_serial_user}/addall", {"serial": token_serials}, self.at,
                                             method='POST')
        self.assertFalse(result["result"]["value"][token.get_serial()])
        self.assertTrue(result["result"]["value"][token2.get_serial()])
        self.assertTrue(result["result"]["value"][token3.get_serial()])
        self.assertFalse(result["result"]["value"][token_no_user.get_serial()])
        # to not authorized container
        container = find_container_by_serial(c_serial_user)
        container.remove_user(User("selfservice", self.realm1))
        container.set_realms([self.realm3], add=False)
        self.request_denied_assert_403(f"/container/{c_serial_user}/addall", {"serial": token_serials}, self.at,
                                       method='POST')

        # helpdesk of user realm realm1: container has no owner, token in realm 1
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/add", {"serial": token_serial}, self.at,
                                       method='POST')

        # helpdesk of userealm realm1: container has no owner, token is in realm3
        token = init_token({"genkey": "1", "realm": self.realm3})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/add", {"serial": token_serial}, self.at,
                                       method='POST')

        # adding multiple tokens denied, since access on container is not allowed
        token2 = init_token({"genkey": "1", "realm": self.realm3})
        token3 = init_token({"genkey": "1", "realm": self.realm1})
        token_serials = ','.join([token2.get_serial(), token3.get_serial()])
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/addall", {"serial": token_serials}, self.at,
                                       method='POST')
        delete_policy("policy_realm")
        delete_policy("policy_resolver")

        # Add token to container during enrollment fails
        set_policy("policy", scope=SCOPE.ADMIN, action=[ACTION.CONTAINER_ADD_TOKEN, "enrollHOTP"], realm=self.realm1)
        container_serial = init_container({"type": "generic", "realm": self.realm2})["container_serial"]
        result = self.request_assert_success("/token/init", {"type": "hotp", "realm": self.realm1, "genkey": 1,
                                                             "container_serial": container_serial}, self.at,
                                             method='POST')
        token_serial = result["detail"]["serial"]
        tokens = get_tokens_paginate(serial=token_serial)
        self.assertEqual("", tokens["tokens"][0]["container_serial"])

    def test_11_helpdesk_remove_token_allowed(self):
        self.setUp_user_realm3()
        set_policy("policy_realm", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REMOVE_TOKEN, realm=self.realm1)
        set_policy("policy_resolver", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REMOVE_TOKEN,
                   resolver=self.resolvername3)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()

        # single token
        add_token_to_container(container_serial, token_serial)
        result = self.request_assert_success(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at,
                                             method='POST')
        self.assertTrue(result["result"]["value"])

        # multiple tokens
        add_token_to_container(container_serial, token_serial)
        token2 = init_token({"genkey": "1"}, user=User("corny", self.realm3))
        add_token_to_container(container_serial, token2.get_serial())
        token_serials = ','.join([token_serial, token2.get_serial()])
        result = self.request_assert_success(f"/container/{container_serial}/removeall", {"serial": token_serials},
                                             self.at,
                                             method='POST')
        self.assertTrue(result["result"]["value"][token_serial])
        self.assertTrue(result["result"]["value"][token2.get_serial()])
        delete_policy("policy_realm")
        delete_policy("policy_resolver")

    def test_12_helpdesk_remove_token_denied(self):
        self.setUp_user_realm2()
        c_serial_user = self.create_container_for_user()
        c_serial_no_user = init_container({"type": "generic"})["container_serial"]

        # helpdesk of user realm realm2
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REMOVE_TOKEN, realm=self.realm2)
        # container and token are both in realm1
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()
        add_token_to_container(c_serial_user, token_serial)
        self.request_denied_assert_403(f"/container/{c_serial_user}/remove", {"serial": token_serial}, self.at,
                                       method='POST')
        # container has no owner, token is in realm1
        remove_token_from_container(c_serial_user, token_serial)
        add_token_to_container(c_serial_no_user, token_serial)
        self.request_denied_assert_403(f"/container/{c_serial_user}/remove", {"serial": token_serial}, self.at,
                                       method='POST')
        # container in realm1 and token in realm 2
        token = init_token({"genkey": "1", "realm": self.realm2})
        token_serial = token.get_serial()
        add_token_to_container(c_serial_user, token_serial)
        self.request_denied_assert_403(f"/container/{c_serial_user}/remove", {"serial": token_serial}, self.at,
                                       method='POST')
        # container has no owner, token is in realm2
        remove_token_from_container(c_serial_user, token_serial)
        add_token_to_container(c_serial_no_user, token_serial)
        self.request_denied_assert_403(f"/container/{c_serial_user}/remove", {"serial": token_serial}, self.at,
                                       method='POST')
        delete_policy("policy")

        # helpdesk of userealm realm1: container in realm1 and token in realm 2
        set_policy("policy_realm", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REMOVE_TOKEN, realm=self.realm1)
        remove_token_from_container(c_serial_no_user, token_serial)
        add_token_to_container(c_serial_user, token_serial)
        self.request_denied_assert_403(f"/container/{c_serial_user}/remove", {"serial": token_serial}, self.at,
                                       method='POST')

        # multiple tokens
        self.setUp_user_realm3()
        set_policy("policy_resolver", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REMOVE_TOKEN,
                   resolver=self.resolvername3)
        token_no_user = init_token({"genkey": "1"})
        add_token_to_container(c_serial_user, token_no_user.get_serial())
        token_user = init_token({"genkey": "1"}, user=User("hans", self.realm2))
        add_token_to_container(c_serial_user, token_user.get_serial())
        token_serials = ','.join([token_no_user.get_serial(), token_user.get_serial()])
        result = self.request_assert_success(f"/container/{c_serial_user}/removeall", {"serial": token_serials},
                                             self.at,
                                             method='POST')
        self.assertFalse(result["result"]["value"][token_no_user.get_serial()])
        self.assertFalse(result["result"]["value"][token_user.get_serial()])
        delete_policy("policy_realm")
        delete_policy("policy_resolver")

    def test_13_helpdesk_assign_user_allowed(self):
        # Allow to assign a user to a container in the helpdesk realm
        self.setUp_user_realms()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ASSIGN_USER, realm=self.realm1)
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/assign",
                                    {"realm": self.realm1, "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

        # Allow to assign a user to a container without user and realm
        self.setUp_user_realm4_with_2_resolvers()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ASSIGN_USER, realm=self.realm4,
                   resolver=self.resolvername1)
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/assign",
                                    {"realm": self.realm4, "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_14_helpdesk_assign_user_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()

        # helpdesk of user realm realm3
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ASSIGN_USER, realm=self.realm3)

        # container in realm3, but new user from realm1
        container_serial = init_container({"type": "generic", "realm": self.realm3})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": self.realm1, "user": "hans", "resolver": self.resolvername1}, self.at)

        # container in realm1, new user from realm3
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": self.realm3, "user": "corny"}, self.at)
        delete_policy("policy")

        # helpdesk for resolver1
        self.setUp_user_realm4_with_2_resolvers()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ASSIGN_USER, realm=self.realm4,
                   resolver=self.resolvername1)
        # container without user, new user from resolver3
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": self.realm4, "user": "corny"}, self.at)
        # container in realm1, new user from resolver1
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": self.realm4, "user": "hans"}, self.at)
        delete_policy("policy")

    def test_15_helpdesk_remove_user_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_UNASSIGN_USER, realm=self.realm1)
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/unassign",
                                    {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

        # Policy for realm and resolver
        self.setUp_user_realm4_with_2_resolvers()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_UNASSIGN_USER, realm=self.realm4,
                   resolver=self.resolvername3)
        container_serial = init_container({"type": "generic",
                                           "user": "corny",
                                           "realm": self.realm4,
                                           "resolver": self.resolvername3})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/unassign",
                                    {"realm": self.realm4, "user": "corny", "resolver": self.resolvername3}, self.at)
        delete_policy("policy")

        # Helpdesk for resolver3
        self.setUp_user_realm4_with_2_resolvers()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_UNASSIGN_USER, resolver=self.resolvername1)
        # container is in realm1, user is from resolver1
        container_serial = init_container({"type": "generic",
                                           "user": "hans",
                                           "realm": self.realm1,
                                           "resolver": self.resolvername1})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/unassign",
                                    {"realm": self.realm1, "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_16_helpdesk_remove_user_denied(self):
        self.setUp_user_realm2()

        # Helpdesk for realm2
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_UNASSIGN_USER, realm=self.realm2)
        # container in realm1, user from realm1
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        # container is additionally in realm2, but user is still from realm1
        add_container_realms(container_serial, ["realm2"], allowed_realms=None)
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

        # Helpdesk for resolver3 in realm4
        self.setUp_user_realm4_with_2_resolvers()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_UNASSIGN_USER, realm=self.realm4,
                   resolver=self.resolvername3)
        # container and user in realm4, but user is from resolver1
        container_serial = init_container({"type": "generic",
                                           "user": "hans",
                                           "realm": self.realm4,
                                           "resolver": self.resolvername1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": self.realm4, "user": "hans", "resolver": self.resolvername1}, self.at)
        # container is in realm3, user is from resolver3 (correct resolver, but wrong realm)
        container_serial = init_container({"type": "generic",
                                           "user": "corny",
                                           "realm": self.realm3,
                                           "resolver": self.resolvername3})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": self.realm3, "user": "corny", "resolver": self.resolvername3}, self.at)
        delete_policy("policy")

    def test_17_helpdesk_container_realms_allowed(self):
        self.setUp_user_realm2()
        # Helpdesk for realm1 and realm2
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REALMS, realm=[self.realm1, self.realm2])
        # container in realm1, add realm2
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)
        delete_policy("policy")

        # Helpdesk for resolver1 in realm1 and realm2
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REALMS, realm=[self.realm1, self.realm2],
                   resolver=self.resolvername1)
        # container in realm1 and resolver1, add realm2
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)
        delete_policy("policy")

        # Helpdesk for resolver1 (is allowed to set all realms)
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REALMS, resolver=self.resolvername1)
        # container in realm1 and resolver1, add realm2
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": [self.realm1, self.realm2]},
                                    self.at)
        delete_policy("policy")

        # Helpdesk for realm1
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REALMS, realm=[self.realm1])
        # container in realm1, add realm2
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": [self.realm1, self.realm2]},
                                    self.at)
        self.assertSetEqual({self.realm1}, set(get_container_realms(container_serial)))
        delete_policy("policy")

    def test_18_helpdesk_container_realms_denied(self):
        self.setUp_user_realm2()
        self.setUp_user_realm3()

        # helpdesk of user realm realm2
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REALMS, realm=self.realm2)

        # container in realm1
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)

        # container in realm1, set realm3
        self.request_denied_assert_403(f"/container/{container_serial}/realms", {"realms": "realm3"}, self.at)
        delete_policy("policy")

        # Helpdesk for realm1
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REALMS, realm=self.realm1)

        # container in realm1, set realm2
        result = self.request_assert_success(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)
        self.assertFalse(result["result"]["value"]["realm2"])
        container = find_container_by_serial(container_serial)
        realms = [realm.name for realm in container.realms]
        self.assertEqual(1, len(realms))
        self.assertEqual("realm1", realms[0])

        # helpdesk of user realm realm1: container in realm1, set realm2 and realm1 (only realm1 allowed)
        result = self.request_assert_success(f"/container/{container_serial}/realms", {"realms": "realm2,realm1"},
                                             self.at)
        self.assertFalse(result["result"]["value"]["realm2"])
        self.assertTrue(result["result"]["value"]["realm1"])

        # container in realm1 and realm2, set realm1 (removes realm2 not allowed)
        add_container_realms(container_serial, ["realm1", "realm2"], allowed_realms=None)
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": "realm1"}, self.at)
        container = find_container_by_serial(container_serial)
        realms = [realm.name for realm in container.realms]
        self.assertEqual(2, len(realms))
        self.assertIn("realm1", realms)
        self.assertIn("realm2", realms)

        # container in no realm, set realm1
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/realms", {"realms": "realm1"}, self.at)
        delete_policy("policy")

        # Helpdesk for realm1 and realm4 and resolver3
        self.setUp_user_realm4_with_2_resolvers()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REALMS, realm=[self.realm4, self.realm1],
                   resolver=self.resolvername3)
        # container of realm4  with user from resolver1
        container_serial = init_container({"type": "generic",
                                           "realm": self.realm4,
                                           "resolver": self.resolvername1,
                                           "user": "hans"})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/realms", {"realms": "realm1"}, self.at)
        delete_policy("policy")

    def test_19_helpdesk_container_list_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_LIST, realm=self.realm1)
        self.request_assert_success('/container/', {}, self.at, 'GET')

        # container with token from another realm: reduce token info
        set_policy("policy2", scope=SCOPE.ADMIN, action=ACTION.TOKENLIST, realm=self.realm1)
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        token_1 = init_token({"genkey": 1, "realm": self.realm1})
        token_2 = init_token({"genkey": 1, "realm": self.realm2})
        add_token_to_container(container_serial, token_1.get_serial())
        add_token_to_container(container_serial, token_2.get_serial())
        result = self.request_assert_success('/container/', {"container_serial": container_serial}, self.at, 'GET')
        tokens = result["result"]["value"]["containers"][0]["tokens"]
        tokens_dict = {token["serial"]: token for token in tokens}
        # first token: all information
        self.assertEqual(token_1.get_serial(), tokens_dict[token_1.get_serial()]["serial"])
        self.assertEqual("hotp", tokens_dict[token_1.get_serial()]["tokentype"])
        # second token: only serial
        self.assertEqual(token_2.get_serial(), tokens_dict[token_2.get_serial()]["serial"])
        self.assertEqual(1, len(tokens_dict[token_2.get_serial()].keys()))
        self.assertNotIn("tokentype", tokens_dict[token_2.get_serial()].keys())

        delete_policy("policy")
        delete_policy("policy2")

    def test_20_helpdesk_container_register_allowed(self):
        container_serial = self.create_container_for_user("smartphone")
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REGISTER, realm=[self.realm2, self.realm1])
        set_policy("container_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://test"})
        data = {"container_serial": container_serial}
        self.request_assert_success('/container/register/initialize', data, self.at, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")
        return container_serial

    def test_21_helpdesk_container_register_denied(self):
        container_serial = self.create_container_for_user("smartphone")
        set_policy("container_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://test"})

        # Helpdesk does not have CONTAINER_REGISTER rights for the realm of the container
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REGISTER, realm=self.realm2)
        data = {"container_serial": container_serial}
        self.request_denied_assert_403('/container/register/initialize', data, self.at, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")

    def test_22_helpdesk_container_unregister_allowed(self):
        container_serial = self.test_20_helpdesk_container_register_allowed()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_UNREGISTER, realm=self.realm1)
        self.request_assert_success(f'/container/register/{container_serial}/terminate', {}, self.at, 'POST')
        delete_policy("policy")

    def test_23_helpdesk_container_unregister_denied(self):
        container_serial = self.test_20_helpdesk_container_register_allowed()
        # Admin does not have CONTAINER_UNREGISTER rights for the realm of the container (realm 1)
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_UNREGISTER, realm=self.realm2)
        self.request_denied_assert_403(f'/container/register/{container_serial}/terminate', {}, self.at, 'POST')
        delete_policy("policy")

    def test_24_helpdesk_container_rollover_allowed(self):
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key=RegistrationState.get_key(),
                                                                value=RegistrationState.REGISTERED.value,
                                                                info_type=PI_INTERNAL)])
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ROLLOVER, realm=self.realm1)
        set_policy("container_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://test"})
        data = {"container_serial": container_serial, "rollover": True}
        self.request_assert_success('/container/register/initialize', data, self.at, 'POST')

        delete_policy("policy")
        delete_policy("container_policy")

    def test_25_helpdesk_container_rollover_denied(self):
        # Helpdesk has no CONTAINER_ROLLOVER rights for the realm of the container
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key=RegistrationState.get_key(),
                                                                value=RegistrationState.REGISTERED.value,
                                                                info_type=PI_INTERNAL)])
        set_policy("container_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://test"})
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REGISTER, realm=self.realm2)
        data = {"container_serial": container_serial, "rollover": True}
        self.request_denied_assert_403('/container/register/initialize', data, self.at, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")

    def test_26_helpdesk_compare_template_container(self):
        template_name = "test"
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={ACTION.CONTAINER_TEMPLATE_LIST: True, ACTION.CONTAINER_LIST: True}, realm=self.realm1)
        set_policy("admin", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE)

        # Test with containers the user might not be allowed to see
        # Create containers with template
        request_params = json.dumps({"type": "smartphone", "template": template_params})

        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')
        container_serial_no_user = result["result"]["value"]["container_serial"]

        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')
        container_serial_user = result["result"]["value"]["container_serial"]
        container_user = find_container_by_serial(container_serial_user)
        container_user.add_user(User("selfservice", self.realm1))

        result = self.request_assert_success(f'/container/template/{template_name}/compare', {}, self.at, 'GET')
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
        delete_policy("admin")

        # Helpdesk has no container_list rights for the realm of the container
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={ACTION.CONTAINER_TEMPLATE_LIST: True, ACTION.CONTAINER_LIST: True}, realm=self.realm2)
        result = self.request_assert_success(f'/container/template/{template_name}/compare', {}, self.at, 'GET')
        containers = result["result"]["value"].keys()
        self.assertNotIn(container_serial_user, containers)
        self.assertNotIn(container_serial_no_user, containers)
        delete_policy("policy")

        get_template_obj("test").delete()

    def test_28_helpdesk_create_container_with_template_with_user(self):
        # admin is allowed to create container and enroll HOTP and TOTP tokens for realm 1
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={ACTION.CONTAINER_CREATE: True, "enrollHOTP": True, "enrollTOTP": True},
                   realm=self.realm1)

        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {
                               "tokens": [{"type": "totp", "genkey": True, "user": True},
                                          {"type": "hotp", "genkey": True},
                                          {"type": "spass"}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        request_params = json.dumps(
            {"type": "generic", "template": template_params, "user": "hans", "realm": self.realm1})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertSetEqual({"totp", "hotp"}, {token.get_type() for token in tokens})
        self.assertEqual(2, len(tokens))
        # check user of tokens
        for token in tokens:
            if token.get_tokentype() == "totp":
                self.assertEqual("hans", token.user.login)
                self.assertEqual(self.realm1, token.user.realm)
            elif token.get_tokentype() == "hotp":
                self.assertIsNone(token.user)
        container_template = container.template
        self.assertEqual(template_params["name"], container_template.name)

        template = get_template_obj(template_params["name"])
        template.delete()

        delete_policy("policy")

    def test_29_helpdesk_create_container_with_template_with_realm(self):
        # admin is allowed to create container and enroll HOTP and TOTP tokens for realm 1
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={ACTION.CONTAINER_CREATE: True, "enrollHOTP": True, "enrollTOTP": True},
                   realm=self.realm1)

        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {
                               "tokens": [{"type": "totp", "genkey": True, "user": True},
                                          {"type": "hotp", "genkey": True}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        request_params = json.dumps(
            {"type": "generic", "template": template_params, "realm": self.realm1})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertSetEqual({"totp", "hotp"}, {token.get_type() for token in tokens})
        self.assertEqual(2, len(tokens))
        # check realm of tokens
        for token in tokens:
            self.assertIsNone(token.user)
            realms = token.get_realms()
            if token.get_tokentype() == "totp":
                self.assertEqual(1, len(realms))
                self.assertEqual(self.realm1, realms[0])
            elif token.get_tokentype() == "hotp":
                self.assertEqual(0, len(realms))

        container_template = container.template
        self.assertEqual(template_params["name"], container_template.name)

        template = get_template_obj(template_params["name"])
        template.delete()

        delete_policy("policy")

    def test_30_helpdesk_set_container_info_allowed(self):
        self.setUp_user_realm2()
        # policy for realms
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO, realm=[self.realm1, self.realm2])
        self.request_assert_success(f"/container/{container_serial}/info/test", {"value": "1234"}, self.at,
                                    method='POST')
        delete_policy("policy")

        # policy for resolver
        container_serial = self.create_container_for_user()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO, resolver=self.resolvername1)
        self.request_assert_success(f"/container/{container_serial}/info/test", {"value": "1234"}, self.at,
                                    method='POST')
        delete_policy("policy")

        # policy for user
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO, user="selfservice",
                   realm=self.realm1, resolver=self.resolvername1)
        self.request_assert_success(f"/container/{container_serial}/info/test", {"value": "1234"}, self.at,
                                    method='POST')
        delete_policy("policy")

    def test_31_helpdesk_set_container_info_denied(self):
        self.setUp_user_realm3()
        c_serial_user = self.create_container_for_user()
        c_serial_no_user = init_container({"type": "generic"})["container_serial"]

        # policy for a realm
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO, realm=self.realm3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/info/test", {"value": "1234"}, self.at,
                                       method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/info/test", {"value": "1234"}, self.at,
                                       method='POST')
        delete_policy("policy")

        # policy for a resolver
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO, resolver=self.resolvername3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/info/test", {"value": "1234"}, self.at,
                                       method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/info/test", {"value": "1234"}, self.at,
                                       method='POST')
        delete_policy("policy")

        # policy for a user
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO, user="hans", realm=self.realm1,
                   resolver=self.resolvername1)
        self.request_denied_assert_403(f"/container/{c_serial_user}/info/test", {"value": "1234"}, self.at,
                                       method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/info/test", {"value": "1234"}, self.at,
                                       method='POST')
        delete_policy("policy")

    def test_32_helpdesk_delete_container_info_allowed(self):
        self.setUp_user_realm2()
        # policy for realms
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key="test", value="1234")])
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO, realm=[self.realm1, self.realm2])
        self.request_assert_success(f"/container/{container_serial}/info/delete/test", {}, self.at,
                                    method="DELETE")
        delete_policy("policy")

        # policy for resolver
        container_serial = self.create_container_for_user()
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key="test", value="1234")])
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO, resolver=self.resolvername1)
        self.request_assert_success(f"/container/{container_serial}/info/delete/test", {}, self.at,
                                    method="DELETE")
        delete_policy("policy")

        # policy for user
        container.update_container_info([TokenContainerInfoData(key="test", value="1234")])
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO, user="selfservice",
                   realm=self.realm1, resolver=self.resolvername1)
        self.request_assert_success(f"/container/{container_serial}/info/delete/test", {}, self.at,
                                    method="DELETE")
        delete_policy("policy")

    def test_33_helpdesk_delete_container_info_denied(self):
        self.setUp_user_realm3()
        c_serial_user = self.create_container_for_user()
        container_user = find_container_by_serial(c_serial_user)
        container_user.update_container_info([TokenContainerInfoData(key="test", value="1234")])
        c_serial_no_user = init_container({"type": "generic"})["container_serial"]
        container_no_user = find_container_by_serial(c_serial_no_user)
        container_no_user.update_container_info([TokenContainerInfoData(key="test", value="1234")])

        # policy for a realm
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO, realm=self.realm3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/info/delete/test", {}, self.at,
                                       method="DELETE")
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/info/delete/test", {}, self.at,
                                       method="DELETE")
        delete_policy("policy")

        # policy for a resolver
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO, resolver=self.resolvername3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/info/delete/test", {}, self.at,
                                       method="DELETE")
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/info/delete/test", {}, self.at,
                                       method="DELETE")
        delete_policy("policy")

        # policy for a user
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_INFO, user="hans", realm=self.realm1,
                   resolver=self.resolvername1)
        self.request_denied_assert_403(f"/container/{c_serial_user}/info/delete/test", {}, self.at,
                                       method="DELETE")
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/info/delete/test", {}, self.at,
                                       method="DELETE")
        delete_policy("policy")


class ContainerPolicyConditions(APIContainerAuthorization):
    """
    This class tests that the endpoints work as expected for extended policy conditions.
    It does not cover all possible combinations, but some useful scenarios.
    """

    def test_01_create(self):
        # condition on container fails as the container does not yet exist
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE,
                   conditions=[(ConditionSection.CONTAINER, "type", PrimaryComparators.EQUALS, "generic", True)])
        self.request_assert_error(403, '/container/init', {"type": "generic"}, self.at, 'POST')
        delete_policy("policy")

    def test_02_delete(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE,
                   conditions=[(ConditionSection.CONTAINER, "type", PrimaryComparators.IN, "generic,smartphone", True)])

        # Delete smartphone is allowed
        container_serial = init_container({"type": "smartphone"})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}", {}, self.at, "DELETE")

        # Delete yubikey fails
        container_serial = init_container({"type": "yubikey"})["container_serial"]
        self.request_assert_error(403, f"/container/{container_serial}", {}, self.at, "DELETE")
        delete_policy("policy")
        delete_container_by_serial(container_serial)

    def test_03_assign_unassign(self):
        self.setUp_user_realms()
        # Only allowed to assign users with a phone number to smartphone containers and all users to other containers
        set_policy("assign", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ASSIGN_USER,
                   conditions=[(ConditionSection.CONTAINER, "type", PrimaryComparators.NOT_EQUALS, "smartphone", True)])
        set_policy("assign_smph", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ASSIGN_USER,
                   conditions=[(ConditionSection.USERINFO, "phone", PrimaryComparators.MATCHES, ".+", True,
                                ConditionHandleMissingData.IS_FALSE.value),
                               (ConditionSection.CONTAINER, "type", PrimaryComparators.EQUALS, "smartphone", True)])
        # Unassignment only allowed for not registered containers
        set_policy("unassign", scope=SCOPE.ADMIN,
                   action=ACTION.CONTAINER_UNASSIGN_USER,
                   conditions=[(ConditionSection.CONTAINER_INFO, "registration_state", PrimaryComparators.NOT_EQUALS,
                                "registered", True, ConditionHandleMissingData.IS_TRUE.value)])

        generic_serial = init_container({"type": "generic"})["container_serial"]
        smph_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smph_serial)

        # Assign user without phone to generic container is allowed
        self.request_assert_success(f"/container/{generic_serial}/assign",
                                    {"user": "selfservice", "realm": self.realm1}, self.at, "POST")

        # Assign user without phone to smartphone container fails
        self.request_assert_error(403, f"/container/{smph_serial}/assign",
                                  {"user": "selfservice", "realm": self.realm1}, self.at, "POST")
        # Assign user with phone to smartphone is allowed
        self.request_assert_success(f"/container/{smph_serial}/assign",
                                    {"user": "cornelius", "realm": self.realm1}, self.at, "POST")

        # Simulate registration
        smartphone.set_container_info({"registration_state": RegistrationState.REGISTERED.value})

        # Unassign user from (not registered) generic container is allowed
        self.request_assert_success(f"/container/{generic_serial}/unassign",
                                    {"user": "selfservice", "realm": self.realm1}, self.at, "POST")

        # Unassign user from registered smartphone is not allowed
        self.request_assert_error(403, f"/container/{smph_serial}/unassign",
                                  {"user": "cornelius", "realm": self.realm1}, self.at, "POST")

        delete_policy("assign")
        delete_policy("assign_smph")
        delete_policy("unassign")
        delete_container_by_serial(generic_serial)
        smartphone.delete()

    def test_04_list_containers(self):
        # extended policy conditions do not work for list containers as most often this involves multiple containers
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_LIST,
                   conditions=[(ConditionSection.CONTAINER, "type", PrimaryComparators.EQUALS, "generic", True)])
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_assert_error(403, "/container/", {}, self.at, "GET")
        self.request_assert_error(403, "/container/", {"type": "generic"}, self.at, "GET")
        self.request_assert_error(403, "/container/", {"container_serial": container_serial}, self.at, "GET")

        delete_policy("policy")
        delete_container_by_serial(container_serial)

    def test_05_add_token(self):
        # only tokens of a specific type and hashlib can be added to smartphones
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_ADD_TOKEN,
                   conditions=[(ConditionSection.CONTAINER, "type", PrimaryComparators.EQUALS, "smartphone", True),
                               (ConditionSection.TOKEN, "tokentype", PrimaryComparators.IN, "hotp,totp", True),
                               (ConditionSection.TOKENINFO, "hashlib", PrimaryComparators.EQUALS, "sha256", True,
                                ConditionHandleMissingData.IS_FALSE.value)])
        selfservice = User("selfservice", self.realm1)
        hotp_sha1 = init_token({"type": "hotp", "genkey": True, "hashlib": "sha1"}, selfservice)
        hotp_sha256 = init_token({"type": "hotp", "genkey": True, "hashlib": "sha256"}, selfservice)
        totp_sha1 = init_token({"type": "totp", "genkey": True, "hashlib": "sha1"}, selfservice)
        totp_sha256 = init_token({"type": "totp", "genkey": True, "hashlib": "sha256"}, selfservice)
        sms = init_token({"type": "sms", "phone": "12345689"}, selfservice)
        container_serial = init_container({"type": "smartphone", "user": "selfservice", "realm": self.realm1})[
            "container_serial"]

        # ---- Add single tokens ----
        # hotp and totp with sha256 are allowed
        self.request_assert_success(f"/container/{container_serial}/add", {"serial": hotp_sha256.get_serial()},
                                    self.at_user, "POST")
        self.request_assert_success(f"/container/{container_serial}/add", {"serial": totp_sha256.get_serial()},
                                    self.at_user, "POST")
        # hotp and totp with sha1 are not allowed
        self.request_assert_error(403, f"/container/{container_serial}/add", {"serial": hotp_sha1.get_serial()},
                                  self.at_user, "POST")
        self.request_assert_error(403, f"/container/{container_serial}/add", {"serial": totp_sha1.get_serial()},
                                  self.at_user, "POST")
        # sms also not allowed
        self.request_assert_error(403, f"/container/{container_serial}/add", {"serial": sms.get_serial()},
                                  self.at_user, "POST")

        # ---- Add all tokens ----
        remove_token_from_container(container_serial, hotp_sha256.get_serial())
        remove_token_from_container(container_serial, totp_sha256.get_serial())

        result = self.request_assert_success(f"/container/{container_serial}/addall",
                                             {"serial": f"{hotp_sha256.get_serial()},{hotp_sha1.get_serial()},"
                                                        f"{sms.get_serial()},{totp_sha256.get_serial()},"
                                                        f"{totp_sha1.get_serial()}"},
                                             self.at_user, "POST")
        self.assertTrue(result["result"]["value"][hotp_sha256.get_serial()])
        self.assertTrue(result["result"]["value"][totp_sha256.get_serial()])
        self.assertFalse(result["result"]["value"][hotp_sha1.get_serial()])
        self.assertFalse(result["result"]["value"][totp_sha1.get_serial()])
        self.assertFalse(result["result"]["value"][sms.get_serial()])

        delete_policy("policy")

        # ---- user info condition ----
        # user condition is applied to the token and container owner
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ADD_TOKEN,
                   conditions=[(ConditionSection.USERINFO, "phone", PrimaryComparators.MATCHES, ".+", True)])

        cornelius = User("cornelius", self.realm1)
        container = find_container_by_serial(container_serial)
        container.remove_user(selfservice)
        container.add_user(cornelius)

        # Add token of a user without phone number to a container with phone number fails
        self.request_assert_error(403, f"/container/{container_serial}/add", {"serial": hotp_sha1.get_serial()},
                                  self.at, "POST")

        # Both users (same user) have phone number works
        unassign_token(hotp_sha1.get_serial())
        hotp_sha1.add_user(cornelius)
        self.request_assert_success(f"/container/{container_serial}/add", {"serial": hotp_sha1.get_serial()},
                                    self.at, "POST")

        delete_policy("policy")
        hotp_sha1.delete_token()
        hotp_sha256.delete_token()
        totp_sha1.delete_token()
        totp_sha256.delete_token()
        sms.delete_token()
        delete_container_by_serial(container_serial)

    def test_06_set_realms(self):
        # Only allow to set the realms for disabled containers
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REALMS,
                   conditions=[(ConditionSection.CONTAINER, "states", PrimaryComparators.CONTAINS,
                                ContainerStates.DISABLED.value, True)])
        container_serial = init_container({"type": "generic"})["container_serial"]

        # set realms for active container fails
        self.request_assert_error(403, f"/container/{container_serial}/realms", {"realms": self.realm1}, self.at,
                                  "POST")

        # Set realms for disabled container is allowed
        set_container_states(container_serial, [ContainerStates.DISABLED.value])
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": self.realm1}, self.at, "POST")

        delete_policy("policy")
        delete_container_by_serial(container_serial)

    def test_07_register(self):
        # only allow registration if state != lost/damaged
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_REGISTER,
                   conditions=[(ConditionSection.CONTAINER, "states", PrimaryComparators.NOT_CONTAINS,
                                ContainerStates.LOST.value, True),
                               (ConditionSection.CONTAINER, "states", PrimaryComparators.NOT_CONTAINS,
                                ContainerStates.DAMAGED.value, True)
                               ])
        # users should register at different pi servers
        set_policy("registration", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/"},
                   conditions=[(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES,
                                ".*@localhost.localdomain", True, ConditionHandleMissingData.IS_FALSE.value)])
        set_policy("registration_external", scope=SCOPE.CONTAINER,
                   action={ACTION.PI_SERVER_URL: "https://pi-external.net/"},
                   conditions=[(ConditionSection.USERINFO, "email", PrimaryComparators.NOT_MATCHES,
                                ".*@localhost.localdomain", True, ConditionHandleMissingData.IS_TRUE.value)])
        container_serial = init_container({"type": "smartphone", "user": "selfservice", "realm": self.realm1})[
            "container_serial"]
        container = find_container_by_serial(container_serial)

        # Registration not allowed
        container.add_states([ContainerStates.LOST.value])
        self.request_assert_error(403, "container/register/initialize", {"container_serial": container_serial},
                                  self.at_user, "POST")

        # Registration allowed
        container.set_states([ContainerStates.ACTIVE.value])
        # external user
        result = self.request_assert_success("container/register/initialize", {"container_serial": container_serial},
                                             self.at_user, "POST")
        self.assertEqual("https://pi-external.net/", result["result"]["value"]["server_url"])
        # internal user
        unregister(container)
        container.remove_user(User("selfservice", self.realm1))
        container.add_user(User("cornelius", self.realm1))
        result = self.request_assert_success("container/register/initialize", {"container_serial": container_serial},
                                             self.at, "POST")
        self.assertEqual("https://pi.net/", result["result"]["value"]["server_url"])

        delete_policy("policy")
        delete_policy("registration")
        delete_policy("registration_external")
        container.delete()

    def test_08_server_rollover(self):
        # only allow server rollover if state == lost and user has a phone number
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ROLLOVER,
                   conditions=[
                       (ConditionSection.CONTAINER, "states", PrimaryComparators.CONTAINS, ContainerStates.LOST.value,
                        True),
                       (ConditionSection.USERINFO, "phone", PrimaryComparators.MATCHES, ".+", True,
                        ConditionHandleMissingData.IS_FALSE.value)])
        set_policy("registration", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/"})
        container_serial = init_container({"type": "smartphone", "user": "selfservice", "realm": self.realm1})[
            "container_serial"]
        container = find_container_by_serial(container_serial)

        # Register smartphone
        container.set_container_info(
            {"registration_state": RegistrationState.REGISTERED.value, "server_url": "https://pi.net/"})

        # Rollover fails
        self.request_assert_error(403, "container/register/initialize",
                                  {"container_serial": container_serial, "rollover": True}, self.at, "POST")

        # Change user: Rollover still fails
        container.remove_user(User("selfservice", self.realm1))
        container.add_user(User("cornelius", self.realm1))
        self.request_assert_error(403, "container/register/initialize",
                                  {"container_serial": container_serial, "rollover": True}, self.at, "POST")

        # Rollover success
        container.set_states([ContainerStates.LOST.value])
        data = {"container_serial": container_serial, "rollover": True}
        self.request_assert_success("container/register/initialize", data, self.at, "POST")

        delete_policy("policy")
        delete_policy("registration")
        container.delete()

    def test_09_register_finalize(self):
        # initially add tokens only allowed if container was not created from a template
        set_policy("registration", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/"})
        set_policy("initially_add_tokens", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   conditions=[(ConditionSection.CONTAINER, "template", PrimaryComparators.NOT_MATCHES, ".+", True)])
        container_serial = init_container({"type": "smartphone", "user": "selfservice", "realm": self.realm1})[
            "container_serial"]
        container = find_container_by_serial(container_serial)

        # --- container without template: initially add tokens allowed ---
        # Register init
        result = self.request_assert_success("container/register/initialize", {"container_serial": container_serial},
                                             self.at, "POST")
        init_response_data = result["result"]["value"]

        # Finalize
        mock_smph = MockSmartphone()
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", container_serial)
        result = self.request_assert_success("container/register/finalize",
                                             params,
                                             None, 'POST')
        self.assertTrue(result["result"]["value"]["policies"][ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER])

        # --- container with template: initially add tokens not allowed ---
        unregister(container)
        create_container_template(container.type, "test", {}, False)
        container.template = "test"
        # Register init
        result = self.request_assert_success("container/register/initialize", {"container_serial": container_serial},
                                             self.at, "POST")
        init_response_data = result["result"]["value"]

        # Finalize
        mock_smph = MockSmartphone()
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", container_serial)
        result = self.request_assert_success("container/register/finalize", params, None, "POST")
        self.assertFalse(result["result"]["value"]["policies"][ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER])

        delete_policy("registration")
        delete_policy("initially_add_tokens")
        container.delete()

    def test_10_synchronization(self):
        # initially add tokens only allowed for internal users (specific mail domain) + specific client
        set_policy("registration", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/"})
        set_policy("initially_add_tokens", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   conditions=[(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES,
                                ".+@localhost.localdomain", True, ConditionHandleMissingData.IS_FALSE.value)])
        container_serial = init_container({"type": "smartphone", "user": "selfservice", "realm": self.realm1})[
            "container_serial"]
        container = find_container_by_serial(container_serial)

        # Registration
        result = self.request_assert_success("container/register/initialize", {"container_serial": container_serial},
                                             self.at, "POST")
        init_response_data = result["result"]["value"]
        # Finalize
        mock_smph = MockSmartphone()
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", container_serial)
        self.request_assert_success("container/register/finalize", params, None, "POST")

        # Synchronize with external user
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        params = mock_smph.synchronize(result["result"]["value"], scope)
        result = self.request_assert_success("container/synchronize", params, None, "POST")
        self.assertFalse(result["result"]["value"]["policies"][ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER])

        # Synchronize with internal user
        container.remove_user(User("selfservice", self.realm1))
        container.add_user(User("cornelius", self.realm1))
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        params = mock_smph.synchronize(result["result"]["value"], scope)
        result = self.request_assert_success("container/synchronize", params, None, "POST")
        self.assertTrue(result["result"]["value"]["policies"][ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER])

        delete_policy("registration")
        delete_policy("initially_add_tokens")
        container.delete()

    def test_11_client_rollover(self):
        # Only allowed if state != lost && userinfo
        set_policy("registration", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/"})
        set_policy("rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                   conditions=[(ConditionSection.CONTAINER, "states", PrimaryComparators.NOT_CONTAINS,
                                ContainerStates.LOST.value, True),
                               (ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES,
                                ".+@localhost.localdomain",
                                True, ConditionHandleMissingData.IS_FALSE.value)])
        container_serial = init_container({"type": "smartphone", "user": "selfservice", "realm": self.realm1})[
            "container_serial"]
        container = find_container_by_serial(container_serial)

        # Registration
        result = self.request_assert_success("container/register/initialize", {"container_serial": container_serial},
                                             self.at, "POST")
        init_response_data = result["result"]["value"]
        mock_smph = MockSmartphone()
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", container_serial)
        self.request_assert_success("container/register/finalize", params, None, "POST")

        container.set_states([ContainerStates.LOST.value])

        # Client rollover: User and state not allowed
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": container_serial}, None,
                                             "POST")
        challenge_data = result["result"]["value"]
        rollover_scope = "https://pi.net/container/rollover"
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"],
                                             rollover_scope, mock_smph.container_serial)
        self.request_assert_error(403, "container/rollover", params, None, "POST")

        # Client rollover: User not allowed
        container.set_states([ContainerStates.ACTIVE.value])
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": container_serial}, None,
                                             "POST")
        challenge_data = result["result"]["value"]
        rollover_scope = "https://pi.net/container/rollover"
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"],
                                             rollover_scope, mock_smph.container_serial)
        self.request_assert_error(403, "container/rollover", params, None, "POST")

        # Client rollover: State not allowed
        container.remove_user(User("selfservice", self.realm1))
        container.add_user(User("cornelius", self.realm1))
        container.set_states([ContainerStates.LOST.value])
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": container_serial}, None,
                                             "POST")
        challenge_data = result["result"]["value"]
        rollover_scope = "https://pi.net/container/rollover"
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"],
                                             rollover_scope, mock_smph.container_serial)
        self.request_assert_error(403, "container/rollover", params, None, "POST")

        # Client rollover: Success
        container.set_states([ContainerStates.ACTIVE.value])
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": container_serial}, None,
                                             "POST")
        challenge_data = result["result"]["value"]
        rollover_scope = "https://pi.net/container/rollover"
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"],
                                             rollover_scope, mock_smph.container_serial)
        self.request_assert_success("container/rollover", params, None, "POST")

        delete_policy("registration")
        delete_policy("rollover")
        container.delete()


class APIContainer(APIContainerTest):

    def test_00_init_delete_container_success(self):
        # Init container
        payload = {"type": "Smartphone", "description": "test description!!"}
        res = self.request_assert_success('/container/init', payload, self.at, 'POST')
        cserial = res["result"]["value"]["container_serial"]
        self.assertTrue(len(cserial) > 1)

        # Check creation date is set
        container = find_container_by_serial(cserial)
        self.assertIn("creation_date", list(container.get_container_info_dict().keys()))

        # Delete the container
        result = self.request_assert_success(f"container/{cserial}", {}, self.at, 'DELETE')
        self.assertTrue(result["result"]["value"])

    def test_01_init_container_fail(self):
        # Init with non-existing type
        payload = {"type": "wrongType", "description": "test description!!"}
        result = self.request_assert_error(400, '/container/init', payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(404, error["code"])
        self.assertEqual("ERR404: Type 'wrongType' is not a valid type!", error["message"])

        # Init without type
        result = self.request_assert_error(400, '/container/init', {}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(404, error["code"])
        self.assertEqual("ERR404: Type parameter is required!", error["message"])

        # Init without auth token
        payload = {"type": "Smartphone", "description": "test description!!"}
        result = self.request_assert_error(401, '/container/init',
                                           payload, None, 'POST')
        error = result["result"]["error"]
        self.assertEqual(4033, error["code"])
        self.assertEqual("Authentication failure. Missing Authorization header.", error["message"])

    def test_02_delete_container_fail(self):
        # Delete non-existing container
        result = self.request_assert_error(404, '/container/wrong_serial',
                                           {}, self.at, 'DELETE')
        error = result["result"]["error"]
        self.assertEqual(601, error["code"])
        self.assertEqual("Unable to find container with serial wrong_serial.", error["message"])

        # Call without serial
        self.request_assert_405('/container/', {}, self.at, 'DELETE')

    def test_03_assign_user_fail(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]

        # Assign without realm
        payload = {"user": "hans"}
        result = self.request_assert_error(400, f'/container/{container_serial}/assign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(904, error["code"])
        self.assertEqual("ERR904: The user can not be found in any resolver in this realm!", error["message"])

        # Assign user with non-existing realm
        payload = {"user": "hans", "realm": "non_existing"}
        result = self.request_assert_error(400, f'/container/{container_serial}/assign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(904, error["code"])
        self.assertEqual("ERR904: The user can not be found in any resolver in this realm!", error["message"])

        # Assign without user
        self.setUp_user_realm2()
        payload = {"realm": self.realm2}
        result = self.request_assert_error(400, f'/container/{container_serial}/assign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing parameter: 'user'", error["message"])

        delete_container_by_serial(container_serial)

    def test_04_assign_multiple_users_fails(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.setUp_user_realms()
        payload = {"user": "hans", "realm": self.realm1}

        # Assign with user and realm
        result = self.request_assert_success(f'/container/{container_serial}/assign', payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        # Assign another user fails
        payload = {"user": "cornelius", "realm": self.realm1}
        result = self.request_assert_error(400, f'/container/{container_serial}/assign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(301, error["code"])
        self.assertEqual("ERR301: This container is already assigned to another user.", error["message"])

        delete_container_by_serial(container_serial)

    def test_05_assign_unassign_user_success(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.setUp_user_realms()
        payload = {"user": "hans", "realm": self.realm1}

        # Assign with user and realm
        result = self.request_assert_success(f'/container/{container_serial}/assign', payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        # Unassign
        result = self.request_assert_success(f'/container/{container_serial}/unassign',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        delete_container_by_serial(container_serial)

    def test_06_assign_without_realm(self):
        # If no realm is passed the default realm is set in before_request
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.setUp_user_realm2()
        self.setUp_user_realm3()
        payload = {"user": "hans"}

        # Assign
        result = self.request_assert_success(f'/container/{container_serial}/assign',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])
        # Used default realm is correct
        container = find_container_by_serial(container_serial)
        owner = container.get_users()[0]
        self.assertTrue(owner.login == "hans")
        self.assertTrue(owner.realm == self.realm2)

        # Assign without realm where default realm is not correct
        container_serial = init_container({"type": "generic"})["container_serial"]
        payload = {"user": "root"}
        result = self.request_assert_error(400, f'/container/{container_serial}/assign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(904, error["code"])
        self.assertEqual("ERR904: The user can not be found in any resolver in this realm!", error["message"])

        container.delete()

    def test_07a_unassign_success(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm3()
        set_default_realm(self.realm1)
        user = User("hans", self.realm1)
        container_serial = init_container({"type": "generic", "user": user.login, "realm": user.realm})[
            "container_serial"]
        container = find_container_by_serial(container_serial)

        # Unassign only with username works if user is in default realm
        payload = {"user": "hans"}
        result = self.request_assert_success(f'/container/{container_serial}/unassign', payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # username + realm
        container.add_user(user)
        payload = {"user": user.login, "realm": user.realm}
        result = self.request_assert_success(f'/container/{container_serial}/unassign', payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # username + resolver
        container.add_user(user)
        payload = {"user": user.login, "resolver": user.resolver}
        result = self.request_assert_success(f'/container/{container_serial}/unassign', payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # uid
        container.add_user(user)
        payload = {"user_id": user.uid}
        result = self.request_assert_success(f'/container/{container_serial}/unassign', payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # uid + realm + resolver
        container.add_user(user)
        payload = {"user_id": user.uid, "realm": user.realm, "resolver": user.resolver}
        result = self.request_assert_success(f'/container/{container_serial}/unassign', payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        container.delete()

    def test_07b_unassign_fail(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm3()
        set_default_realm(self.realm1)
        user = User("corny", self.realm3)
        container_serial = init_container({"type": "generic", "user": user.login, "realm": user.realm})[
            "container_serial"]

        # Missing input parameters
        # No parameters
        result = self.request_assert_error(400, f'/container/{container_serial}/unassign', {}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing one of the following parameters: ['user', 'user_id']", error["message"])

        # Only username, realm / resolver / uid missing (if user is not in defrealm)
        payload = {"user": user.login}
        result = self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(904, error["code"])
        self.assertEqual("ERR904: The user can not be found in any resolver in this realm!", error["message"])
        # If no default realm exists, another error is raised
        set_default_realm()
        result = self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing parameter 'realm', 'resolver', and/or 'user_id'", error["message"])

        # Only realm: user / user_id missing
        payload = {"realm": self.realm3}
        result = self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing one of the following parameters: ['user', 'user_id']", error["message"])

        # Unassign user with non-existing realm
        payload = {"user": user.login, "realm": "non_existing"}
        result = self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(904, error["code"])
        self.assertEqual("ERR904: The user can not be found in any resolver in this realm!", error["message"])

        # Unassign not assigned user
        payload = {"user": "hans", "realm": self.realm1}
        result = self.request_assert_success(f'/container/{container_serial}/unassign',
                                             payload, self.at, 'POST')
        self.assertFalse(result["result"]["value"])

        delete_container_by_serial(container_serial)

    def test_07c_unassign_non_existing_user(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm3()
        set_default_realm(self.realm1)
        invalid_user = User("invalid", self.realm1, self.resolvername1, "123")
        container_serial = init_container({"type": "generic"})["container_serial"]
        container = find_container_by_serial(container_serial)
        container.add_user(invalid_user)
        self.assertEqual(1, len(container.get_users()))

        # --- Fail ---
        # Only with username and realm
        payload = {"user": "invalid", "realm": self.realm1}
        result = self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(904, error["code"])
        self.assertEqual("ERR904: The user can not be found in any resolver in this realm!", error["message"])

        # Remove non-existing not assigned user
        payload = {"user": "another_invalid", "realm": self.realm1, "user_id": "987"}
        result = self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(904, error["code"])
        self.assertEqual("ERR904: The user can not be found in any resolver in this realm!", error["message"])

        # --- Success ---
        # Only with user_id should work as long as the container can only have one user
        payload = {"user_id": invalid_user.uid}
        result = self.request_assert_success(f'/container/{container_serial}/unassign',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # With user_id and resolver success
        container.add_user(invalid_user)
        payload = {"user_id": invalid_user.uid, "resolver": invalid_user.resolver}
        result = self.request_assert_success(f'/container/{container_serial}/unassign',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # Provide realm and user_id should work
        container.add_user(invalid_user)
        payload = {"realm": invalid_user.realm, "user_id": invalid_user.uid}
        result = self.request_assert_success(f'/container/{container_serial}/unassign',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # Provide everything
        container.add_user(invalid_user)
        payload = {"user": invalid_user.login, "realm": invalid_user.realm, "resolver": invalid_user.resolver,
                   "user_id": invalid_user.uid}
        result = self.request_assert_success(f'/container/{container_serial}/unassign',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        container.delete()

    def test_08_set_realms_success(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial = init_container({"type": "generic"})["container_serial"]

        # Set existing realms
        payload = {"realms": self.realm1 + "," + self.realm2}
        result = self.request_assert_success(f'/container/{container_serial}/realms', payload, self.at, 'POST')
        result = result["result"]
        self.assertTrue(result["value"])
        self.assertTrue(result["value"]["deleted"])
        self.assertTrue(result["value"][self.realm1])
        self.assertTrue(result["value"][self.realm2])

        # Set no realm shall remove all realms for the container
        payload = {"realms": ""}
        result = self.request_assert_success(f'/container/{container_serial}/realms', payload, self.at, 'POST')
        result = result["result"]
        self.assertTrue(result["value"])
        self.assertTrue(result["value"]["deleted"])
        self.assertNotIn(self.realm1, result["value"].keys())
        self.assertNotIn(self.realm2, result["value"].keys())

        delete_container_by_serial(container_serial)

        # Automatically add the user realms
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        payload = {"realms": self.realm2}
        result = self.request_assert_success(f'/container/{container_serial}/realms', payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"][self.realm1])
        self.assertTrue(result["result"]["value"][self.realm2])

        delete_container_by_serial(container_serial)

    def test_09_set_realms_fail(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial = init_container({"type": "generic"})["container_serial"]

        # Missing realm parameter
        result = self.request_assert_error(400, f'/container/{container_serial}/realms',
                                           {}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing parameter: 'realms'", error["message"])

        # Set non-existing realm
        payload = {"realms": "nonexistingrealm"}
        result = self.request_assert_success(f'/container/{container_serial}/realms', payload, self.at, 'POST')
        result = result.get("result")
        self.assertFalse(result["value"]["nonexistingrealm"])

        # Missing container serial
        self.request_assert_405('/container/realms', {"realms": [self.realm1]}, self.at, 'POST')

        delete_container_by_serial(container_serial)

    def test_10_set_description_success(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]

        # Set description
        payload = {"description": "new description"}
        result = self.request_assert_success(f'/container/{container_serial}/description',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        # Set empty description
        payload = {"description": ""}
        result = self.request_assert_success(f'/container/{container_serial}/description',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        delete_container_by_serial(container_serial)

    def test_11_set_description_fail(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]

        # Missing description parameter
        result = self.request_assert_error(400, f'/container/{container_serial}/description',
                                           {}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing parameter: 'description'", error["message"])

        # Description parameter is None
        result = self.request_assert_error(400, f'/container/{container_serial}/description',
                                           {"description": None}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing parameter: 'description'", error["message"])

        # Missing container serial
        self.request_assert_405('/container/description', {"description": "new description"},
                                self.at, 'POST')

        delete_container_by_serial(container_serial)

    def test_12_set_states_success(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]

        # Set states
        payload = {"states": "active,damaged,lost"}
        result = self.request_assert_success(f'/container/{container_serial}/states',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])
        self.assertTrue(result["result"]["value"]["active"])
        self.assertTrue(result["result"]["value"]["damaged"])
        self.assertTrue(result["result"]["value"]["lost"])

        delete_container_by_serial(container_serial)

    def test_13_set_states_fail(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]

        # Missing states parameter
        result = self.request_assert_error(400, f'/container/{container_serial}/states',
                                           {}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing parameter: 'states'", error["message"])

        # Missing container serial
        self.request_assert_405('/container/states', {"states": "active,damaged,lost"},
                                self.at, 'POST')

        # Set exclusive states
        payload = {"states": "active,disabled"}
        result = self.request_assert_error(400, f'/container/{container_serial}/states',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: The state list ['active', 'disabled'] contains exclusive states!", error["message"])

        delete_container_by_serial(container_serial)

    def test_14_set_container_info_success(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]

        # Set info
        self.request_assert_success(f'/container/{container_serial}/info/key1',
                                    {"value": "value1"}, self.at, 'POST')

        delete_container_by_serial(container_serial)

    def test_15_set_container_info_fail(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]

        # Missing value parameter
        result = self.request_assert_error(400, f'/container/{container_serial}/info/key1',
                                           {}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing parameter: 'value'", error["message"])

        # Missing container serial
        self.request_assert_404_no_result('/container/info/key1', {"value": "value1"}, self.at, 'POST')

        # Missing key
        self.request_assert_404_no_result(f'/container/{container_serial}/info/',
                                          {"value": "value1"}, self.at, 'POST')

        delete_container_by_serial(container_serial)

    def test_16_add_remove_token_success(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]
        hotp_01 = init_token({"genkey": "1"})
        hotp_01_serial = hotp_01.get_serial()
        hotp_02 = init_token({"genkey": "1"})
        hotp_02_serial = hotp_02.get_serial()
        hotp_03 = init_token({"genkey": "1"})
        hotp_03_serial = hotp_03.get_serial()

        # Add single token
        result = self.request_assert_success(f'/container/{container_serial}/add',
                                             {"serial": hotp_01_serial}, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        # Remove single token
        result = self.request_assert_success(f'/container/{container_serial}/remove',
                                             {"serial": hotp_01_serial}, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        # Add multiple tokens
        result = self.request_assert_success(f'/container/{container_serial}/addall',
                                             {"serial": f"{hotp_01_serial},{hotp_02_serial},{hotp_03_serial}"},
                                             self.at, 'POST')
        self.assertTrue(result["result"]["value"][hotp_01_serial])
        self.assertTrue(result["result"]["value"][hotp_02_serial])
        self.assertTrue(result["result"]["value"][hotp_03_serial])

        # Remove multiple tokens with spaces in list
        result = self.request_assert_success(f'/container/{container_serial}/removeall',
                                             {"serial": f"{hotp_01_serial}, {hotp_02_serial}, {hotp_03_serial}"},
                                             self.at, 'POST')
        self.assertTrue(result["result"]["value"][hotp_01_serial])
        self.assertTrue(result["result"]["value"][hotp_02_serial])
        self.assertTrue(result["result"]["value"][hotp_03_serial])

        # Add multiple tokens with spaces in list
        result = self.request_assert_success(f'/container/{container_serial}/addall',
                                             {"serial": f"{hotp_01_serial}, {hotp_02_serial}, {hotp_03_serial}"},
                                             self.at, 'POST')
        self.assertTrue(result["result"]["value"][hotp_01_serial])
        self.assertTrue(result["result"]["value"][hotp_02_serial])
        self.assertTrue(result["result"]["value"][hotp_03_serial])

        # Remove multiple tokens
        result = self.request_assert_success(f'/container/{container_serial}/removeall',
                                             {"serial": f"{hotp_01_serial},{hotp_02_serial},{hotp_03_serial}"},
                                             self.at, 'POST')
        self.assertTrue(result["result"]["value"][hotp_01_serial])
        self.assertTrue(result["result"]["value"][hotp_02_serial])
        self.assertTrue(result["result"]["value"][hotp_03_serial])

        delete_container_by_serial(container_serial)

    def test_17_add_token_fail(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]
        hotp_01 = init_token({"genkey": "1"})
        hotp_01_serial = hotp_01.get_serial()

        # Add token without serial
        result = self.request_assert_error(400, f'/container/{container_serial}/add',
                                           {}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing parameter: 'serial'", error["message"])

        # Add token without container serial
        self.request_assert_405('/container/add', {"serial": hotp_01_serial}, self.at, 'POST')

        delete_container_by_serial(container_serial)

    def test_18_remove_token_fail(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]
        hotp_01 = init_token({"genkey": "1"})
        hotp_01_serial = hotp_01.get_serial()
        add_token_to_container(container_serial, hotp_01_serial)

        # Remove token without serial
        result = self.request_assert_error(400, f'/container/{container_serial}/remove',
                                           {}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing parameter: 'serial'", error["message"])

        # Remove token without container serial
        self.request_assert_405('/container/remove', {"serial": hotp_01_serial}, self.at, 'POST')

        delete_container_by_serial(container_serial)

    def test_19_get_state_types(self):
        result = self.request_assert_success('/container/statetypes', {}, self.at, 'GET')
        self.assertTrue(result["result"]["value"])
        self.assertIn("active", result["result"]["value"].keys())
        self.assertIn("disabled", result["result"]["value"]["active"])
        self.assertIn("lost", result["result"]["value"].keys())

    def test_20_get_types(self):
        result = self.request_assert_success('/container/types', {}, self.at, 'GET')
        self.assertTrue(result["result"]["value"])
        # Check that all container types are included
        self.assertIn("smartphone", result["result"]["value"])
        self.assertIn("generic", result["result"]["value"])
        self.assertIn("yubikey", result["result"]["value"])
        # Check that all properties are set
        self.assertIn("description", result["result"]["value"]["generic"])
        self.assertIn("token_types", result["result"]["value"]["generic"])

    def test_21_get_all_containers_paginate(self):
        # Arrange
        self.setUp_user_realms()
        # Create containers
        types = ["Smartphone", "generic", "Yubikey", "Smartphone", "generic", "Yubikey"]
        container_serials = []
        for t in types:
            serial = init_container({"type": t, "description": "test container"})["container_serial"]
            container_serials.append(serial)
        # Add token to container 1
        container = find_container_by_serial(container_serials[1])
        token = init_token({"genkey": "1"}, user=User("shadow", self.realm1))
        token_serial = token.get_serial()
        add_token_to_container(container_serials[1], token_serial)
        # Assign user to container 1
        self.setUp_user_realms()
        user_hans = User(login="hans", realm=self.realm1)
        container.add_user(user_hans)
        # Add second realm
        self.setUp_user_realm2()
        container.set_realms([self.realm2], add=True)
        # Add info
        container.update_container_info([TokenContainerInfoData(key="key1", value="value1")])

        # Filter for type
        result = self.request_assert_success('/container/',
                                             {"type": "generic", "pagesize": 15},
                                             self.at, 'GET')
        for container in result["result"]["value"]["containers"]:
            self.assertEqual(container["type"], "generic")

        # Filter for assigned containers
        result = self.request_assert_success('/container/',
                                             {"assigned": True, "pagesize": 15},
                                             self.at, 'GET')
        self.assertEqual(1, result["result"]["value"]["count"])

        # filter for realm the admin is not allowed to manage
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_LIST, realm=self.realm1)
        result = self.request_assert_success('/container/',
                                             {"container_realm": self.realm2, "pagesize": 15},
                                             self.at, 'GET')
        self.assertEqual(0, result["result"]["value"]["count"])
        delete_policy("policy")

        # Filter for token serial
        result = self.request_assert_success('/container/',
                                             {"token_serial": token_serial, "pagesize": 15},
                                             self.at, 'GET')
        self.assertTrue(container_serials[1], result["result"]["value"]["containers"][0]["serial"])
        self.assertEqual(result["result"]["value"]["count"], 1)

        # Set hide_container_info_policy
        set_policy("hide_info", scope=SCOPE.ADMIN,
                   action=f"{ACTION.HIDE_CONTAINER_INFO}=encrypt_algorithm device,{ACTION.CONTAINER_LIST}")
        container3 = find_container_by_serial(container_serials[3])
        container3.set_container_info({"encrypt_algorithm": "AES", "encrypt_mode": "GCM", "device": "ABC1234",
                                       RegistrationState.get_key(): RegistrationState.REGISTERED.value})
        # Filter for container serial
        result = self.request_assert_success('/container/',
                                             {"container_serial": container_serials[3], "pagesize": 15},
                                             self.at, 'GET')
        result_container = result["result"]["value"]["containers"][0]
        self.assertTrue(container_serials[3], result_container["serial"])
        self.assertSetEqual({"encrypt_mode", RegistrationState.get_key(), "creation_date"},
                            set(result_container["info"].keys()))
        # Get all containers
        result = self.request_assert_success('/container/', {"pagesize": 15}, self.at, 'GET')
        result_containers = result["result"]["value"]["containers"]
        for container in result_containers:
            info_keys = container["info"].keys()
            self.assertNotIn("encrypt_algorithm", info_keys)
            self.assertNotIn("device", info_keys)
        delete_policy("hide_info")

        # Test output
        result = self.request_assert_success('/container/',
                                             {"container_serial": container_serials[1], "pagesize": 15, "page": 1},
                                             self.at, 'GET')
        containerdata = result["result"]["value"]
        # Pagination
        self.assertEqual(1, containerdata["count"])
        self.assertIn("prev", containerdata.keys())
        self.assertIn("next", containerdata.keys())
        self.assertIn("current", containerdata.keys())
        self.assertEqual(1, len(containerdata["containers"]))
        # Container data
        res_container = containerdata["containers"][0]
        self.assertEqual("generic", res_container["type"])
        self.assertEqual(container_serials[1], res_container["serial"])
        self.assertEqual("test container", res_container["description"])
        self.assertIn("last_authentication", res_container.keys())
        self.assertIn("last_synchronization", res_container.keys())
        self.assertIn("active", res_container["states"])
        # Tokens
        self.assertEqual(1, len(res_container["tokens"]))
        # User
        self.assertEqual(1, len(res_container["users"]))
        self.assertEqual(user_hans.login, res_container["users"][0]["user_name"])
        self.assertEqual(user_hans.realm, res_container["users"][0]["user_realm"])
        self.assertEqual(user_hans.resolver, res_container["users"][0]["user_resolver"])
        self.assertEqual(user_hans.uid, res_container["users"][0]["user_id"])
        # Realms
        self.assertIn(self.realm1, res_container["realms"])
        self.assertIn(self.realm2, res_container["realms"])
        # Info
        self.assertIn("key1", res_container["info"].keys())
        self.assertEqual("value1", res_container["info"]["key1"])

    def test_22_get_all_containers_paginate_invalid_params(self):
        init_container({"type": "generic", "description": "test container"})

        # Filter for non-existing type
        result = self.request_assert_success('/container/',
                                             {"type": "non-existing", "pagesize": 15},
                                             self.at, 'GET')
        self.assertEqual(0, result["result"]["value"]["count"])

        # Filter for non existing token serial
        result = self.request_assert_success('/container/',
                                             {"token_serial": "non-existing", "pagesize": 15},
                                             self.at, 'GET')
        self.assertEqual(result["result"]["value"]["count"], 0)

    def test_23_delete_container_info_success(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key="test", value="1234")])

        # Delete info
        self.request_assert_success(f"/container/{container_serial}/info/delete/test",
                                    {}, self.at, "DELETE")

    def test_24_delete_container_info_fail(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key="test", value="1234"),
                                         TokenContainerInfoData(key="internal_test", value="abcd",
                                                                info_type=PI_INTERNAL)])

        # Try to delete internal key
        result = self.request_assert_success(f"/container/{container_serial}/info/delete/internal_test",
                                             {}, self.at, "DELETE")
        self.assertFalse(result["result"]["value"])

    def test_25_broken_user_resolver(self):
        # Arrange
        self.setUp_user_realms()
        container_serial = init_container({"type": "generic",
                                           "description": "test container",
                                           "user": "hans",
                                           "realm": self.realm1})["container_serial"]
        # Get all containers with assigned user
        result = self.request_assert_success('/container/', {}, self.at, 'GET')
        # Get the current container
        container = [x for x in result["result"]["value"]["containers"] if x["serial"] == container_serial][0]
        self.assertEqual(container["users"][0]["user_name"], "hans", result["result"])
        # Break the resolver
        save_resolver({"resolver": self.resolvername1,
                       "type": "passwdresolver",
                       "fileName": "/unknown/file"})
        # And check the container again
        result = self.request_assert_success('/container/', {}, self.at, 'GET')
        container = [x for x in result["result"]["value"]["containers"] if x["serial"] == container_serial][0]
        self.assertEqual(container["users"][0]["user_name"], "**resolver error**", result["result"])


@dataclass
class SmartphoneRequests:
    mock_smph: MockSmartphone = MockSmartphone()
    response: dict = None


class APIContainerSynchronization(APIContainerTest):

    @classmethod
    def create_smartphone_for_user_and_realm(cls, user: User = None, realm_list: list = None):
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smartphone_serial)
        if user:
            smartphone.add_user(user)
        if realm_list:
            smartphone.set_realms(realm_list, add=True)
        return smartphone

    def register_smartphone_success(self, smartphone_serial=None):
        set_policy("policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/",
                                                            ACTION.CONTAINER_REGISTRATION_TTL: 24,
                                                            ACTION.CONTAINER_CHALLENGE_TTL: 1,
                                                            ACTION.CONTAINER_SSL_VERIFY: "True"}, priority=2)
        if not smartphone_serial:
            smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        data = {"container_serial": smartphone_serial,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}

        # Initialize
        result = self.request_assert_success('container/register/initialize',
                                             data,
                                             self.at, 'POST')
        # Check if the response contains the expected values
        init_response_data = result["result"]["value"]
        self.assertIn("container_url", init_response_data)
        self.assertIn("nonce", init_response_data)
        self.assertIn("time_stamp", init_response_data)
        self.assertIn("key_algorithm", init_response_data)
        self.assertIn("hash_algorithm", init_response_data)
        self.assertIn("ssl_verify", init_response_data)
        self.assertIn("ttl", init_response_data)
        self.assertIn("passphrase_prompt", init_response_data)
        self.assertIn("server_url", init_response_data)
        # Check if the url contains all relevant data
        qr_url = init_response_data["container_url"]["value"]
        self.assertIn(f"pia://container/{smartphone_serial}", qr_url)
        self.assertIn("issuer=privacyIDEA", qr_url)
        self.assertIn("ttl=24", qr_url)
        self.assertIn("ssl_verify=True", qr_url)
        self.assertIn("nonce=", qr_url)
        self.assertIn("time=", qr_url)
        self.assertIn("url=https%3A//pi.net/", qr_url)
        self.assertIn(f"serial={smartphone_serial}", qr_url)
        self.assertIn("key_algorithm=", qr_url)
        self.assertIn("hash_algorithm", qr_url)
        self.assertIn("passphrase=Enter%20your%20passphrase", qr_url)

        # check challenge
        challenges = get_challenges(serial=smartphone_serial)
        challenge = challenges[0] if len(challenges) == 1 else None
        self.assertIsNotNone(challenge)
        self.assertEqual(init_response_data["nonce"], challenge.challenge)
        # timestamp: we need to add the timezone for the challenge timestamp
        creation_time = datetime.fromisoformat(init_response_data["time_stamp"])
        self.assertEqual(creation_time, challenge.timestamp.replace(tzinfo=timezone.utc))
        time_delta_challenge = (challenge.expiration - challenge.timestamp).total_seconds()
        self.assertAlmostEqual(24 * 60, time_delta_challenge, 0)
        challenge_data = json.loads(challenge.data)
        self.assertEqual("https://pi.net/container/register/finalize", challenge_data["scope"])

        # Finalize
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", smartphone_serial,
                                             "top_secret")
        result = self.request_assert_success('container/register/finalize',
                                             params,
                                             None, 'POST')

        # Check if the response contains the expected values
        self.assertIn("policies", result["result"]["value"])

        delete_policy("policy")

        return SmartphoneRequests(mock_smph, result)

    def create_offline_token(self, serial, otps):
        # authenticate online initially
        token = get_tokens(serial=serial)[0]
        res = token.check_otp(otps[2])  # count = 2
        self.assertEqual(2, res)
        # check intermediate counter value
        self.assertEqual(3, token.token.count)

        attach_token(serial, "offline", machine_id=0, )

        auth_item = MachineApplication.get_authentication_item("hotp", serial)
        refilltoken = auth_item.get("refilltoken")
        self.assertEqual(len(refilltoken), REFILLTOKEN_LENGTH * 2)
        self.assertTrue(passlib.hash.pbkdf2_sha512.verify(otps[3],  # count = 3
                                                          auth_item.get("response").get(3)))
        self.assertTrue(passlib.hash.pbkdf2_sha512.verify(otps[8],  # count = 8
                                                          auth_item.get("response").get(8)))
        # The token now contains the refill token information:
        self.assertEqual(refilltoken, token.get_tokeninfo("refilltoken"))
        self.assertEqual(103, token.token.count)

    def test_01_register_smartphone_success(self):
        set_policy("client_policy", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER, priority=1)

        result = self.register_smartphone_success()

        # Check if the response contains the expected values
        self.assertIn("policies", result.response["result"]["value"])
        policies = result.response["result"]["value"]["policies"]
        self.assertTrue(policies[ACTION.CONTAINER_CLIENT_ROLLOVER])
        self.assertFalse(policies[ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertFalse(policies[ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        self.assertFalse(policies[ACTION.DISABLE_CLIENT_TOKEN_DELETION])

        delete_policy("client_policy")

    def test_02_register_smartphone_of_user(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        set_policy("another_policy", scope=SCOPE.CONTAINER,
                   action={ACTION.PI_SERVER_URL: "https://another-pi.net/", ACTION.CONTAINER_REGISTRATION_TTL: 24},
                   realm=self.realm2)
        set_policy("low_prio_policy", scope=SCOPE.CONTAINER,
                   action={ACTION.PI_SERVER_URL: "https://pi-low_prio.net/", ACTION.CONTAINER_REGISTRATION_TTL: 24},
                   realm=self.realm1, priority=2)
        set_policy("policy", scope=SCOPE.CONTAINER,
                   action={ACTION.PI_SERVER_URL: "https://pi.net/", ACTION.CONTAINER_REGISTRATION_TTL: 24},
                   realm=self.realm1, priority=1)
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        data = {"container_serial": smartphone_serial,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}

        # Initialize
        result = self.request_assert_success('container/register/initialize',
                                             data,
                                             self.at, 'POST')
        init_response_data = result["result"]["value"]
        # Check if the url contains all relevant data
        qr_url = init_response_data["container_url"]["value"]
        self.assertIn("url=https%3A//pi.net/", qr_url)

        # Finalize
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", smartphone_serial,
                                             "top_secret")

        self.request_assert_success('container/register/finalize',
                                    params,
                                    None, 'POST')

        delete_policy("policy")
        delete_policy("another_policy")
        delete_policy("low_prio_policy")

    def test_03_register_init_fail(self):
        # Policy with server url not defined
        container_serial = init_container({"type": "smartphone"})["container_serial"]
        result = self.request_assert_error(403, 'container/register/initialize',
                                           {"container_serial": container_serial}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(303, error["code"])

        # conflicting server url policies
        self.setUp_user_realms()
        self.setUp_user_realm2()
        set_policy("another_policy", scope=SCOPE.CONTAINER,
                   action={ACTION.PI_SERVER_URL: "https://another-pi.net/", ACTION.CONTAINER_REGISTRATION_TTL: 24},
                   realm=self.realm2, priority=1)
        set_policy("policy", scope=SCOPE.CONTAINER,
                   action={ACTION.PI_SERVER_URL: "https://pi.net/", ACTION.CONTAINER_REGISTRATION_TTL: 24},
                   realm=self.realm1, priority=1)
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        data = {"container_serial": smartphone_serial,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}

        result = self.request_assert_error(403, 'container/register/initialize',
                                           data,
                                           self.at, 'POST')
        self.assertEqual(303, result["result"]["error"]["code"])
        delete_policy("another_policy")
        delete_container_by_serial(smartphone_serial)

        # Missing container serial
        result = self.request_assert_error(400, 'container/register/initialize',
                                           {}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing parameter: 'container_serial'", error["message"])

        # Invalid container serial
        result = self.request_assert_error(404, 'container/register/initialize',
                                           {"container_serial": "invalid_serial"}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(601, error["code"])  # ResourceNotFound

        delete_policy("policy")

    def test_04_register_finalize_wrong_params(self):
        # Missing container serial
        result = self.request_assert_error(400, 'container/register/finalize',
                                           {"device_brand": "LG", "device_model": "ABC123"}, None, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing parameter: 'container_serial'", error["message"])

        # Invalid container serial
        result = self.request_assert_error(404, 'container/register/finalize',
                                           {"container_serial": "invalid_serial", "device_brand": "LG",
                                            "device_model": "ABC123"},
                                           None, 'POST')
        error = result["result"]["error"]
        self.assertEqual(601, error["code"])  # ResourceNotFound

    def test_05_register_finalize_invalid_challenge(self):
        # Invalid challenge
        set_policy("policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/",
                                                            ACTION.CONTAINER_REGISTRATION_TTL: 24})
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        data = {"container_serial": smartphone_serial,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}
        # Initialize
        result = self.request_assert_success('container/register/initialize',
                                             data,
                                             self.at, 'POST')
        init_response_data = result["result"]["value"]
        # Finalize with invalid nonce
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        params = mock_smph.register_finalize("xxxxx", init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", smartphone_serial,
                                             "top_secret")

        result = self.request_assert_error(400, 'container/register/finalize', params,
                                           None, 'POST')
        self.assertEqual(3002, result["result"]["error"]["code"])

    def test_06_register_twice_fails(self):
        # register container successfully
        set_policy("policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/",
                                                            ACTION.CONTAINER_REGISTRATION_TTL: 24})
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        data = {"container_serial": smartphone_serial,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}

        # Initialize
        result = self.request_assert_success('container/register/initialize',
                                             data,
                                             self.at, 'POST')
        init_response_data = result["result"]["value"]

        # Finalize
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", smartphone_serial,
                                             "top_secret")

        self.request_assert_success('container/register/finalize',
                                    params, None, 'POST')

        # try register second time with same data
        self.request_assert_error(400, 'container/register/finalize',
                                  params, None, 'POST')

        # try to reinit registration
        result = self.request_assert_error(400, 'container/register/initialize',
                                           data, self.at, 'POST')
        self.assertEqual(3000, result["result"]["error"]["code"])

        delete_policy("policy")

    def test_07_register_terminate_server_success(self):
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        # Terminate
        self.request_assert_success(f'container/register/{mock_smph.container_serial}/terminate',
                                    {},
                                    self.at, 'POST')

    def test_08_register_terminate_fail(self):
        # Invalid container serial
        result = self.request_assert_error(404, "container/register/invalidSerial/terminate",
                                           {}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(601, error["code"])  # ResourceNotFound

    def test_09_challenge_success(self):
        set_policy("challenge_ttl", scope="container", action={ACTION.CONTAINER_CHALLENGE_TTL: 3}, priority=1)

        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph

        # Init
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success('container/challenge',
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             'POST')

        result_entries = result["result"]["value"].keys()
        self.assertIn("nonce", result_entries)
        self.assertIn("time_stamp", result_entries)
        self.assertIn("enc_key_algorithm", result_entries)

        # check challenge
        challenge_list = get_challenges(serial=mock_smph.container_serial)
        self.assertEqual(1, len(challenge_list))
        challenge = challenge_list[0]
        result = result["result"]["value"]
        self.assertEqual(result["nonce"], challenge.challenge)
        # we need to set the timezone since the database can not store it
        challenge_timestamp = challenge.timestamp.replace(tzinfo=timezone.utc)
        self.assertEqual(datetime.fromisoformat(result["time_stamp"]), challenge_timestamp)
        challenge_data = json.loads(challenge.data)
        self.assertEqual(scope, challenge_data["scope"])
        # expiration date: created a few microseconds after the creation date
        expiration_date = datetime.fromisoformat(result["time_stamp"]) + timedelta(seconds=180)
        time_delta = (expiration_date - challenge.expiration.replace(tzinfo=timezone.utc)).total_seconds()
        self.assertLessEqual(abs(time_delta), 1)

        delete_policy("challenge_ttl")

    def test_10_challenge_fail(self):
        # container does not exists
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_error(404, "container/challenge",
                                           {"scope": scope, "container_serial": "random"}, None, "POST")
        self.assertEqual(601, result["result"]["error"]["code"])

        # container is not registered
        smph_serial = init_container({"type": "smartphone"})["container_serial"]
        scope = "container/synchronize"
        result = self.request_assert_error(400, "container/challenge",
                                           {"scope": scope, "container_serial": smph_serial}, None, "POST")
        self.assertEqual(3001, result["result"]["error"]["code"])

        # Missing serial
        result = self.request_assert_error(400, "container/challenge",
                                           {"scope": scope}, None, "POST")
        self.assertEqual(905, result["result"]["error"]["code"])

    def register_terminate_client_success(self, smartphone_serial=None):
        # Registration
        registration = self.register_smartphone_success(smartphone_serial)
        mock_smph = registration.mock_smph

        # Challenge
        scope = "https://pi.net/container/register/terminate/client"
        result = self.request_assert_success('container/challenge',
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             'POST')

        params = mock_smph.register_terminate(result["result"]["value"], scope)

        # Terminate
        res = self.request_assert_success('container/register/terminate/client',
                                          params,
                                          None, 'POST')
        self.assertTrue(res["result"]["value"]["success"])

    def test_11_register_terminate_client_no_user_success(self):
        # Policy for a specific realm
        self.setUp_user_realms()
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=self.realm1)
        self.register_terminate_client_success()
        delete_policy("client_unregister")

        # Policy with no actions defined
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action={}, realm=self.realm1)
        self.register_terminate_client_success()
        delete_policy("client_unregister")

    def test_12_register_terminate_client_realm_and_user_success(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()
        user = User("hans", self.realm1)

        # No policy
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.register_terminate_client_success(smartphone.serial)

        # Policy for another realm
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=[self.realm3])
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.register_terminate_client_success(smartphone.serial)
        delete_policy("client_unregister")

        # Policy for another user in this realm
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=[self.realm2], user="hans")
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.register_terminate_client_success(smartphone.serial)
        delete_policy("client_unregister")

    def test_13_register_terminate_client_realm_success(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        smartphone = self.create_smartphone_for_user_and_realm(realm_list=[self.realm2])

        # No policy
        self.register_terminate_client_success(smartphone.serial)

        # Policy for another realm
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=self.realm1)
        self.register_terminate_client_success(smartphone.serial)
        delete_policy("client_unregister")

        # Policy for a specific user in this realm
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   user="hans", realm=self.realm2)
        self.register_terminate_client_success(smartphone.serial)
        delete_policy("client_unregister")
        smartphone.delete()

    def register_terminate_client_denied(self, smartphone_serial=None):
        # Registration
        registration = self.register_smartphone_success(smartphone_serial)
        mock_smph = registration.mock_smph

        # Challenge
        scope = "https://pi.net/container/register/terminate/client"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        params = mock_smph.register_terminate(result["result"]["value"], scope)

        # Terminate
        res = self.request_assert_error(403, "container/register/terminate/client",
                                        params,
                                        None, 'POST')
        self.assertEqual(303, res["result"]["error"]["code"])

    def test_14_register_terminate_client_no_user_denied(self):
        # Generic policy
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER)
        self.register_terminate_client_denied()
        delete_policy("client_unregister")

    def test_15_register_terminate_client_with_user_and_realms_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        user = User("hans", self.realm1)

        # Generic policy
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER)
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.register_terminate_client_denied(smartphone.serial)
        delete_policy("client_unregister")

        # Policy for the users realm
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=self.realm1)
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.register_terminate_client_denied(smartphone.serial)
        delete_policy("client_unregister")

        # Policy for the other realm
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=self.realm2)
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.register_terminate_client_denied(smartphone.serial)
        delete_policy("client_unregister")

        # Policy for the user
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=self.realm1, user="hans")
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.register_terminate_client_denied(smartphone.serial)
        delete_policy("client_unregister")

    def test_18_register_terminate_client_missing_param(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        result = registration.response

        self.assertFalse(result["result"]["value"]["policies"][ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER])

        # Challenge
        scope = "https://pi.net/container/register/terminate/client"
        self.request_assert_success('container/challenge',
                                    {"scope": scope, "container_serial": mock_smph.container_serial}, None, 'POST')

        # Terminate without signature
        result = self.request_assert_error(400,
                                           "container/register/terminate/client",
                                           {"container_serial": mock_smph.container_serial}, None, 'POST')
        self.assertEqual(905, result["result"]["error"]["code"])

        # Terminate without container serial
        result = self.request_assert_error(400,
                                           "container/register/terminate/client",
                                           {"signature": "123"}, None, 'POST')
        self.assertEqual(905, result["result"]["error"]["code"])

    def test_19_register_terminate_client_invalid_serial(self):
        # container does not exists
        result = self.request_assert_error(404,
                                           "container/register/terminate/client",
                                           {"container_serial": "random"},
                                           self.at, "POST")
        self.assertEqual(601, result["result"]["error"]["code"])

        # Missing serial
        result = self.request_assert_error(400,
                                           "container/register/terminate/client",
                                           {},
                                           self.at, "POST")
        self.assertEqual(905, result["result"]["error"]["code"])

    def test_20_register_terminate_client_invalid_challenge(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph

        # Challenge
        scope = "https://pi.net/container/register/terminate/client"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             'POST')
        # mock with another serial
        correct_serial = mock_smph.container_serial
        mock_smph.container_serial = "random123"
        params = mock_smph.register_terminate(result["result"]["value"], scope)
        params["container_serial"] = correct_serial

        # Terminate
        result = self.request_assert_error(400, "container/register/terminate/client",
                                           params, self.at, 'POST')
        self.assertEqual(3002, result["result"]["error"]["code"])

    def test_21_register_terminate_client_not_registered(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph

        # Challenge
        scope = "https://pi.net/container/register/terminate/client"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        # server terminates
        self.request_assert_success(f"container/register/{mock_smph.container_serial}/terminate",
                                    {},
                                    self.at, 'POST')

        # client tries to terminate
        params = mock_smph.register_terminate(result["result"]["value"], scope)
        result = self.request_assert_error(400, "container/register/terminate/client",
                                           params, self.at, "POST")
        self.assertEqual(3001, result["result"]["error"]["code"])

    def test_22_register_generic_fail(self):
        set_policy("policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/",
                                                            ACTION.CONTAINER_REGISTRATION_TTL: 24})
        generic_serial = init_container({"type": "generic"})["container_serial"]
        data = {"container_serial": generic_serial,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}

        # Initialize
        self.request_assert_error(501, 'container/register/initialize',
                                  data,
                                  self.at, 'POST')

        # Finalize
        data = {"container_serial": generic_serial}
        self.request_assert_error(501, 'container/register/finalize',
                                  data,
                                  None, 'POST')

        # Terminate
        self.request_assert_error(501, f'container/register/{generic_serial}/terminate',
                                  {}, self.at, 'POST')

        delete_policy('policy')

    def test_23_register_yubikey_fail(self):
        set_policy("policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/",
                                                            ACTION.CONTAINER_REGISTRATION_TTL: 24})
        yubi_serial = init_container({"type": "yubikey"})["container_serial"]
        data = {"container_serial": yubi_serial,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}

        # Initialize
        self.request_assert_error(501, 'container/register/initialize',
                                  data,
                                  self.at, 'POST')

        # Finalize
        data = {"container_serial": yubi_serial}
        self.request_assert_error(501, 'container/register/finalize',
                                  data,
                                  None, 'POST')

        # Terminate
        self.request_assert_error(501, f'container/register/{yubi_serial}/terminate',
                                  {}, self.at, 'POST')

    def test_24_synchronize_success(self):
        # client rollover and deletable tokens are implicitly set to False
        set_policy("smartphone_config", scope=SCOPE.CONTAINER,
                   action={ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER: True,
                           ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER: True})
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        result = registration.response
        policies = result["result"]["value"]["policies"]
        self.assertTrue(policies[ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        self.assertTrue(policies[ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertFalse(policies[ACTION.DISABLE_CLIENT_TOKEN_DELETION])
        self.assertFalse(policies[ACTION.CONTAINER_CLIENT_ROLLOVER])

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Sync
        sync_time = datetime.now(timezone.utc)
        result = self.request_assert_success("container/synchronize",
                                             params, None, "POST")
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)
        self.assertIn("policies", result_entries)
        policies = result["result"]["value"]["policies"]
        self.assertTrue(policies[ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        self.assertFalse(policies[ACTION.CONTAINER_CLIENT_ROLLOVER])
        self.assertTrue(policies[ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertFalse(policies[ACTION.DISABLE_CLIENT_TOKEN_DELETION])

        # check last synchronization timestamp
        smartphone = find_container_by_serial(mock_smph.container_serial)
        last_sync = smartphone.last_synchronization
        time_diff = abs((sync_time - last_sync).total_seconds())
        self.assertLessEqual(time_diff, 1)

        delete_policy("smartphone_config")

    def test_25_synchronize_invalid_params(self):
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]

        # missing signature
        params = {"public_enc_key_client": "123", "container_serial": smartphone_serial}
        result = self.request_assert_error(400, "container/synchronize",
                                           params, None, "POST")
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])

        # missing serial
        params = {"public_enc_key_client": "123", "signature": "0001"}
        result = self.request_assert_error(400, "container/synchronize",
                                           params, None, "POST")
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])

    def test_26_synchronize_invalid_container(self):
        # container does not exists
        params = {"public_enc_key_client": "123", "signature": "abcd", "container_serial": "random"}
        result = self.request_assert_error(404, "container/synchronize",
                                           params, None, 'POST')
        error = result["result"]["error"]
        self.assertEqual(601, error["code"])

    def test_27_synchronize_container_not_registered(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Server unregister
        self.request_assert_success(f"container/register/{mock_smph.container_serial}/terminate", {},
                                    self.at, "POST")

        # Sync
        result = self.request_assert_error(400, "container/synchronize",
                                           params, None, "POST")
        self.assertEqual(3001, result["result"]["error"]["code"])

    def test_28_synchronize_invalid_challenge(self):
        # invalid challenge
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        # create challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        # mock client with invalid scope (wrong serial)
        params = mock_smph.synchronize(result["result"]["value"], "https://pi.net/container/register/initialize")
        result = self.request_assert_error(400, "container/synchronize",
                                           params, None, 'POST')
        error = result["result"]["error"]
        self.assertEqual(3002, error["code"])

    def test_29_synchronize_man_in_the_middle(self):
        # client register successfully
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        # client creates challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             'POST')
        # mock client
        params = mock_smph.synchronize(result["result"]["value"], scope)
        # man in the middle fetches client request and inserts its own public encryption key
        enc_evil = generate_keypair_ecc("x25519")
        params["public_enc_key_client"] = base64.urlsafe_b64encode(enc_evil.public_key.public_bytes_raw()).decode(
            'utf-8')

        # man in the middle sends modified request to the server
        # Fails due to invalid signature (client signed the public encryption key which is now different)
        result = self.request_assert_error(400, "container/synchronize",
                                           params, None, 'POST')
        error = result["result"]["error"]
        self.assertEqual(3002, error["code"])

    def test_30_synchronize_smartphone_with_push_fb(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # tokens
        push_fb = init_token({"genkey": "1", "type": "push"})
        smartphone.add_token(push_fb)

        # Firebase config
        fb_config = {FirebaseConfig.REGISTRATION_URL: "http://test/ttype/push",
                     FirebaseConfig.JSON_CONFIG: self.FIREBASE_FILE,
                     FirebaseConfig.TTL: 10}
        set_smsgateway("fb1", 'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider', "myFB",
                       fb_config)
        set_policy("push", scope=SCOPE.ENROLL, action={PUSH_ACTION.FIREBASE_CONFIG: "fb1",
                                                       PUSH_ACTION.REGISTRATION_URL: "http://test/ttype/push"})

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial},
                                             None, "POST")

        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Finalize
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        tokens = tokens_dict["add"]
        self.assertEqual(1, len(tokens))
        self.assertIn("otpauth://pipush/", tokens[0])

        delete_policy("push")

    def test_31_synchronize_smartphone_with_push_poll_only(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # tokens
        push_fb = init_token({"genkey": "1", "type": "push"})
        smartphone.add_token(push_fb)

        # policies: push config is spread over multiple policies
        set_policy("push_1", scope=SCOPE.ENROLL, action={PUSH_ACTION.FIREBASE_CONFIG: "poll only"})
        set_policy("push_2", scope=SCOPE.ENROLL, action={PUSH_ACTION.REGISTRATION_URL: "http://test/ttype/push"})

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Finalize
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        tokens = tokens_dict["add"]
        self.assertEqual(1, len(tokens))
        self.assertIn("otpauth://pipush/", tokens[0])

        delete_policy("push_1")
        delete_policy("push_2")

    def test_32_synchronize_smartphone_with_new_tokens(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # tokens
        hotp = init_token({"genkey": "1", "type": "hotp", "otplen": 8, "hashlib": "sha256"})
        smartphone.add_token(hotp)
        totp = init_token({"genkey": "1", "type": "totp", "otplen": 8, "hashlib": "sha256", "timeStep": 60})
        smartphone.add_token(totp)
        sms = init_token({"type": "sms", "phone": "0123456789"})
        smartphone.add_token(sms)
        daypassword = init_token({"genkey": "1", "type": "daypassword", "hashlib": "sha256", "timeStep": 60})
        smartphone.add_token(daypassword)

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Finalize
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')

        # check result
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        tokens = tokens_dict["add"]
        # sms is skipped for synchronization
        self.assertEqual(3, len(tokens))

        # check token properties
        # new tokens are rolled over: enrollment settings need to be the same and not reset to defaults
        hotp_dict = hotp.get_as_dict()
        self.assertEqual(8, hotp_dict["otplen"])
        self.assertEqual("sha256", hotp_dict["info"]["hashlib"])
        totp_dict = totp.get_as_dict()
        self.assertEqual(8, totp_dict["otplen"])
        self.assertEqual("sha256", totp_dict["info"]["hashlib"])
        self.assertEqual("60", totp_dict["info"]["timeStep"])
        sms_dict = sms.get_as_dict()
        self.assertEqual("0123456789", sms_dict["info"]["phone"])
        daypw_dict = daypassword.get_as_dict()
        self.assertEqual("sha256", daypw_dict["info"]["hashlib"])
        self.assertEqual("60", daypw_dict["info"]["timeStep"])

    def test_33_synchronize_smartphone_missing_token_enroll_policies(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # tokens
        push_fb = init_token({"genkey": "1", "type": "push"})
        smartphone.add_token(push_fb)
        hotp = init_token({"genkey": "1", "type": "hotp"})
        smartphone.add_token(hotp)

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Finalize with missing push config
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        tokens = tokens_dict["add"]
        # Only hotp token to be added
        self.assertEqual(1, len(tokens))
        self.assertIn("otpauth://hotp/", tokens[0])

    def test_34_synchronize_smartphone_token_policies(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # Add tokens
        totp = init_token({"genkey": True, "type": "totp"})
        smartphone.add_token(totp)
        daypassword = init_token({"genkey": True, "type": "daypassword"})
        smartphone.add_token(daypassword)
        sms = init_token({"type": "sms", "phone": "0123456789"})
        smartphone.add_token(sms)

        # set label, issuer and require pin policies
        self.setUp_user_realms()
        self.setUp_user_realm2()
        set_policy('token_enroll_realm2', scope=SCOPE.ENROLL,
                   action={ACTION.TOKENLABEL: '{user}',
                           ACTION.TOKENISSUER: '{realm}',
                           'hotp_' + ACTION.FORCE_APP_PIN: True}, realm=self.realm2)
        set_policy('token_enroll_realm1', scope=SCOPE.ENROLL,
                   action={ACTION.TOKENLABEL: '{user}',
                           ACTION.TOKENISSUER: '{realm}',
                           'hotp_' + ACTION.FORCE_APP_PIN: True}, realm=self.realm1)

        # Get initial enroll url
        hotp_params = {"type": "hotp",
                       "genkey": True,
                       "realm": self.realm1,
                       "user": "hans"}
        result = self.request_assert_success("/token/init", hotp_params, self.at, "POST")
        initial_enroll_url = result["detail"]["googleurl"]["value"]
        self.assertIn("pin=True", initial_enroll_url)
        self.assertIn(f"issuer={self.realm1}", initial_enroll_url)
        self.assertIn("hans", initial_enroll_url)
        hotp = get_one_token(serial=result["detail"]["serial"])
        smartphone.add_token(hotp)

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Finalize
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        tokens = tokens_dict["add"]
        # totp, daypassword and hotp token to be added (sms token can not be enrolled in the app)
        self.assertEqual(3, len(tokens))
        # check hotp enroll url
        for token in tokens:
            if "hotp" in token:
                hotp_enroll_url = token
                break
        self.assertNotEqual(initial_enroll_url, hotp_enroll_url)
        self.assertIn("pin=True", hotp_enroll_url)
        self.assertIn(f"issuer={self.realm1}", hotp_enroll_url)
        self.assertIn("hans", hotp_enroll_url)

        delete_policy('token_enroll_realm1')
        delete_policy('token_enroll_realm2')

    def test_35_generic_sync_fail(self):
        generic_serial = init_container({"type": "generic"})["container_serial"]

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_error(400, "container/challenge",
                                           {"scope": scope, "container_serial": generic_serial}, None, 'POST')
        self.assertEqual(3001, result["result"]["error"]["code"])

    def test_36_yubi_sync_fail(self):
        generic_serial = init_container({"type": "generic"})["container_serial"]

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_error(400, "container/challenge",
                                           {"scope": scope, "container_serial": generic_serial}, None, "POST")
        self.assertEqual(3001, result["result"]["error"]["code"])

    def setup_rollover(self, smartphone_serial=None):
        # Registration
        registration = self.register_smartphone_success(smartphone_serial)
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)
        # tokens
        hotp = init_token({"genkey": "1", "type": "hotp"})
        smartphone.add_token(hotp)

        # Challenge for init rollover
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        challenge_data = result["result"]["value"]

        # Mock old smartphone
        rollover_scope = "https://pi.net/container/rollover"
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"],
                                             rollover_scope, mock_smph.container_serial)
        params.update({"passphrase_prompt": "Enter your phone number.", "passphrase_response": "123456789"})

        return params

    def client_rollover_success(self, smartphone_serial=None):
        set_policy("register_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/",
                                                                     ACTION.CONTAINER_REGISTRATION_TTL: 24},
                   priority=3)
        # Register, create challenge for rollover and mock smartphone for rollover
        smartphone_params = self.setup_rollover(smartphone_serial)
        smartphone_serial = smartphone_params['container_serial']

        # Init rollover
        result = self.request_assert_success("container/rollover",
                                             smartphone_params, None, 'POST')

        init_response_data = result["result"]["value"]
        self.assertIn("container_url", init_response_data)
        self.assertIn("nonce", init_response_data)
        self.assertIn("time_stamp", init_response_data)
        self.assertIn("key_algorithm", init_response_data)
        self.assertIn("hash_algorithm", init_response_data)
        self.assertIn("ssl_verify", init_response_data)
        self.assertIn("ttl", init_response_data)
        self.assertIn("passphrase_prompt", init_response_data)
        # Check if the url contains all relevant data
        qr_url = init_response_data["container_url"]["value"]
        self.assertIn(f"pia://container/{smartphone_serial}", qr_url)
        self.assertIn("issuer=privacyIDEA", qr_url)
        self.assertIn("ttl=24", qr_url)
        self.assertIn("nonce=", qr_url)
        self.assertIn("time=", qr_url)
        self.assertIn("url=https%3A//pi.net/", qr_url)
        self.assertIn(f"serial={smartphone_serial}", qr_url)
        self.assertIn("key_algorithm=", qr_url)
        self.assertIn("hash_algorithm", qr_url)
        self.assertIn("passphrase=Enter%20your%20phone%20number.", qr_url)
        # New smartphone finalizes rollover
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", smartphone_serial,
                                             smartphone_params["passphrase_response"])

        # Finalize rollover (finalize registration)
        self.request_assert_success('container/register/finalize',
                                    params, None, 'POST')

        delete_policy("register_policy")

    def client_rollover_denied(self, smartphone_serial=None):
        set_policy("register_policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/",
                                                                     ACTION.CONTAINER_REGISTRATION_TTL: 24}, priority=1)
        # Register, create challenge for rollover and mock smartphone for rollover
        smartphone_params = self.setup_rollover(smartphone_serial)
        smartphone_serial = smartphone_params['container_serial']

        # Init rollover
        result = self.request_assert_error(403, "container/rollover", smartphone_params,
                                           None, "POST")
        self.assertEqual(303, result["result"]["error"]["code"])

        delete_policy("register_policy")

    def test_37_rollover_client_no_user_success(self):
        # Rollover with generic policy
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER)
        self.client_rollover_success()
        delete_policy("policy_rollover")

    def test_38_rollover_client_no_user_denied(self):
        # No rollover right
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER)
        self.client_rollover_denied()
        delete_policy("policy_rollover")

        # Rollover with policy for a specific realm
        self.setUp_user_realms()
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER, realm=self.realm1)
        self.client_rollover_denied()
        delete_policy("policy_rollover")

    def test_39_rollover_client_realm_success(self):
        self.setUp_user_realms()

        # Rollover with generic policy
        smartphone_serial = init_container({"type": "smartphone", "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER)
        self.client_rollover_success(smartphone_serial)
        delete_policy("policy_rollover")

        # Rollover with policy for realm
        smartphone_serial = init_container({"type": "smartphone", "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm1)
        self.client_rollover_success(smartphone_serial)
        delete_policy("policy_rollover")

    def test_40_rollover_client_realm_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()

        # Rollover with policy for a user
        smartphone_serial = init_container({"type": "smartphone", "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                   user="hans", realm=self.realm1)
        self.client_rollover_denied(smartphone_serial)
        delete_policy("policy_rollover")

        # Rollover with policy for another realm
        smartphone_serial = init_container({"type": "smartphone", "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm2)
        self.client_rollover_denied(smartphone_serial)
        delete_policy("policy_rollover")

        # Rollover action not allowed
        smartphone_serial = init_container({"type": "smartphone", "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=self.realm1)
        self.client_rollover_denied(smartphone_serial)
        delete_policy("policy_rollover")

    def test_41_rollover_client_user_success(self):
        self.setUp_user_realms()

        # Rollover with generic policy
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER)
        self.client_rollover_success(smartphone_serial)
        delete_policy("policy_rollover")

        # Rollover with policy for user realm
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm1)
        self.client_rollover_success(smartphone_serial)
        delete_policy("policy_rollover")

        # Rollover with policy for the user
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm1, user="hans")
        self.client_rollover_success(smartphone_serial)
        delete_policy("policy_rollover")

    def test_42_rollover_client_user_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()

        # Rollover with no rollover rights
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER)
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        self.client_rollover_denied(smartphone_serial)
        delete_policy("policy_rollover")

        # Rollover with policy only for another realm
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm2)
        self.client_rollover_denied(smartphone_serial)
        delete_policy("policy_rollover")

        # Rollover with policy only for another user of the same realm
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm2, user="root")
        self.client_rollover_denied(smartphone_serial)
        delete_policy("policy_rollover")

    def test_43_rollover_client_user_and_realm_success(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        user = User("hans", self.realm1)

        # Rollover with policy for the user realm
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm1)
        self.client_rollover_success(smartphone.serial)
        delete_policy("policy_rollover")

        # Rollover with policy for the other realm
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm2)
        self.client_rollover_success(smartphone.serial)
        delete_policy("policy_rollover")

        # Rollover with policy for the user
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm1, user="hans")
        self.client_rollover_success(smartphone.serial)
        delete_policy("policy_rollover")

    def test_44_rollover_client_user_and_realm_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()
        user = User("hans", self.realm1)

        # Rollover with policy only for another realm
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm3)
        self.client_rollover_denied(smartphone.serial)
        delete_policy("policy_rollover")

        # Rollover with policy only for another user
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm2, user="hans")
        self.client_rollover_denied(smartphone.serial)
        delete_policy("policy_rollover")

    def test_45_rollover_client_container_not_registered(self):
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER)
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smartphone_serial)
        # tokens
        hotp = init_token({"genkey": "1", "type": "hotp"})
        smartphone.add_token(hotp)

        set_policy("policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/",
                                                            ACTION.CONTAINER_REGISTRATION_TTL: 36})

        # Challenge for init rollover
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_error(400, "container/challenge",
                                           {"scope": scope, "container_serial": smartphone_serial}, None, "POST")
        self.assertEqual(3001, result["result"]["error"]["code"])

        # Init rollover
        result = self.request_assert_error(400, "container/rollover",
                                           {"container_serial": smartphone_serial},
                                           None, 'POST')
        self.assertEqual(3001, result["result"]["error"]["code"])

        delete_policy("policy")
        delete_policy("policy_rollover")

    def test_46_rollover_client_init_invalid_challenge(self):
        # Registration
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER)
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        result = registration.response
        policies = result["result"]["value"]["policies"]
        self.assertFalse(policies[ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        self.assertFalse(policies[ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertFalse(policies[ACTION.DISABLE_CLIENT_TOKEN_DELETION])
        self.assertTrue(policies[ACTION.CONTAINER_CLIENT_ROLLOVER])

        smartphone = find_container_by_serial(mock_smph.container_serial)
        # tokens
        hotp = init_token({"genkey": "1", "type": "hotp"})
        smartphone.add_token(hotp)

        set_policy("policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/",
                                                            ACTION.CONTAINER_REGISTRATION_TTL: 36})

        # Challenge for init rollover
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        challenge_data = result["result"]["value"]

        # Mock smartphone with invalid nonce
        rollover_scope = "https://pi.net/container/rollover"
        params = mock_smph.register_finalize("123456789", challenge_data["time_stamp"],
                                             rollover_scope)

        # Init rollover
        result = self.request_assert_error(400, "container/rollover",
                                           params,
                                           None, 'POST')
        self.assertEqual(3002, result["result"]["error"]["code"])

        delete_policy("policy")
        delete_policy("policy_rollover")

    def test_47_rollover_client_finalize_invalid_challenge(self):
        # Registration
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER)
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        result = registration.response
        policies = result["result"]["value"]["policies"]
        self.assertFalse(policies[ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        self.assertFalse(policies[ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertFalse(policies[ACTION.DISABLE_CLIENT_TOKEN_DELETION])
        self.assertTrue(policies[ACTION.CONTAINER_CLIENT_ROLLOVER])

        smartphone = find_container_by_serial(mock_smph.container_serial)
        # tokens
        hotp = init_token({"genkey": "1", "type": "hotp"})
        smartphone.add_token(hotp)

        set_policy("policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/",
                                                            ACTION.CONTAINER_REGISTRATION_TTL: 36})

        # Challenge for init rollover
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        challenge_data = result["result"]["value"]

        # Mock smartphone
        rollover_scope = "https://pi.net/container/rollover"
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"],
                                             rollover_scope)
        passphrase = "top_secret"
        params.update({"passphrase_prompt": "Enter your passphrase", "passphrase_response": passphrase})

        # Init rollover
        result = self.request_assert_success("container/rollover",
                                             params,
                                             None, 'POST')
        rollover_data = result["result"]["value"]

        # Invalid Nonce
        # Mock smartphone
        params = mock_smph.register_finalize("123456789", rollover_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", passphrase=passphrase)

        # Finalize rollover (finalize registration)
        result = self.request_assert_error(400, 'container/register/finalize',
                                           params,
                                           None, 'POST')
        self.assertEqual(3002, result["result"]["error"]["code"])

        # Invalid time stamp
        # Mock smartphone
        params = mock_smph.register_finalize(rollover_data["nonce"], "2021-01-01T00:00:00+00:00",
                                             "https://pi.net/container/register/finalize", passphrase=passphrase)

        # Finalize rollover (finalize registration)
        result = self.request_assert_error(400, 'container/register/finalize',
                                           params,
                                           None, 'POST')
        self.assertEqual(3002, result["result"]["error"]["code"])

        # Invalid passphrase
        # Mock smartphone
        params = mock_smph.register_finalize(rollover_data["nonce"], rollover_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", passphrase="test1234")

        # Finalize rollover (finalize registration)
        result = self.request_assert_error(400, 'container/register/finalize',
                                           params,
                                           None, 'POST')
        self.assertEqual(3002, result["result"]["error"]["code"])

        delete_policy("policy")
        delete_policy("policy_rollover")

    def test_48_rollover_client_missing_serial(self):
        set_policy("policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/",
                                                            ACTION.CONTAINER_REGISTRATION_TTL: 36,
                                                            ACTION.CONTAINER_CLIENT_ROLLOVER: True})

        result = self.request_assert_error(400, "container/rollover", {}, None, 'POST')
        self.assertEqual(905, result["result"]["error"]["code"])

        delete_policy("policy")

    def test_49_client_self_rollover(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # token
        self.setUp_user_realms()
        hotp_params = {"type": "hotp",
                       "genkey": True,
                       "realm": self.realm1,
                       "user": "hans"}
        result = self.request_assert_success("/token/init", hotp_params, self.at, "POST")
        initial_enroll_url = result["detail"]["googleurl"]["value"]
        hotp = get_one_token(serial=result["detail"]["serial"])
        smartphone.add_token(hotp)

        set_policy("policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://new-pi.net/",
                                                            ACTION.CONTAINER_REGISTRATION_TTL: 36})

        # Challenge for init rollover
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        # Rollover init
        data = {"container_serial": mock_smph.container_serial, "rollover": True,
                "passphrase_prompt": "Enter your phone number.", "passphrase_response": "123456789"}
        result = self.request_assert_success("container/register/initialize", data, self.at, 'POST')

        init_response_data = result["result"]["value"]
        self.assertIn("container_url", init_response_data)
        self.assertIn("nonce", init_response_data)
        self.assertIn("time_stamp", init_response_data)
        self.assertIn("key_algorithm", init_response_data)
        self.assertIn("hash_algorithm", init_response_data)
        self.assertIn("ssl_verify", init_response_data)
        self.assertIn("ttl", init_response_data)
        self.assertIn("passphrase_prompt", init_response_data)
        # Check if the url contains all relevant data
        qr_url = init_response_data["container_url"]["value"]
        self.assertIn(f"pia://container/{mock_smph.container_serial}", qr_url)
        self.assertIn("issuer=privacyIDEA", qr_url)
        self.assertIn("ttl=36", qr_url)
        self.assertIn("nonce=", qr_url)
        self.assertIn("time=", qr_url)
        self.assertIn("url=https%3A//new-pi.net/", qr_url)
        self.assertIn(f"serial={mock_smph.container_serial}", qr_url)
        self.assertIn("key_algorithm=", qr_url)
        self.assertIn("hash_algorithm", qr_url)
        self.assertIn("passphrase=Enter%20your%20phone%20number.", qr_url)

        # smartphone finalizes rollover
        params = mock_smph.register_finalize(scope="https://new-pi.net/container/register/finalize",
                                             nonce=init_response_data["nonce"],
                                             registration_time=init_response_data["time_stamp"],
                                             passphrase="123456789")
        self.request_assert_success('container/register/finalize',
                                    params,
                                    None, 'POST')
        self.assertEqual(RegistrationState.ROLLOVER_COMPLETED, smartphone.registration_state)

        # Challenge for Sync
        scope = "https://new-pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        mock_smph.container = {"serial": mock_smph.container_serial, "type": "smartphone",
                               "tokens": [{"serial": hotp.get_serial(), "type": "HOTP", "label": hotp.get_serial(),
                                           "issuer": "privacIDEA", "pin": False, "algorithm": "SHA1", "digits": 6}]}
        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Sync
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        token_diff = container_dict_server["tokens"]
        self.assertEqual(1, len(token_diff["add"]))
        self.assertNotEqual(initial_enroll_url, token_diff["add"][0])
        self.assertEqual(0, len(token_diff["update"]))

        # smartphone got new token secrets: rollover completed
        self.assertEqual(RegistrationState.REGISTERED, smartphone.registration_state)

        delete_policy("policy")

    def test_50_sync_with_rollover_challenge_fails(self):
        # Registration
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=ACTION.CONTAINER_CLIENT_ROLLOVER)
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        result = registration.response
        policies = result["result"]["value"]["policies"]
        self.assertFalse(policies[ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        self.assertFalse(policies[ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertFalse(policies[ACTION.DISABLE_CLIENT_TOKEN_DELETION])
        self.assertTrue(policies[ACTION.CONTAINER_CLIENT_ROLLOVER])

        smartphone = find_container_by_serial(mock_smph.container_serial)
        # tokens
        hotp = init_token({"genkey": "1", "type": "hotp"})
        smartphone.add_token(hotp)

        set_policy("policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/",
                                                            ACTION.CONTAINER_REGISTRATION_TTL: 36})

        # Challenge for init rollover
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        # create signature for rollover endpoint
        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Call sync endpoint with rollover signature
        result = self.request_assert_error(400, "container/synchronize",
                                           params, None, 'POST')
        self.assertEqual(3002, result["result"]["error"]["code"])

        delete_policy("policy")
        delete_policy("policy_rollover")

    def test_51_rollover_server_success(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # tokens
        self.setUp_user_realms()

        push = init_token({"genkey": "1", "type": "push", PUSH_ACTION.FIREBASE_CONFIG: "poll only"})
        self.assertEqual("poll only", push.get_tokeninfo()[PUSH_ACTION.FIREBASE_CONFIG])
        smartphone.add_token(push)

        hotp_params = {"type": "hotp",
                       "genkey": True,
                       "realm": self.realm1,
                       "user": "hans",
                       "hashlib": "sha256"}
        result = self.request_assert_success("/token/init", hotp_params, self.at, "POST")
        initial_enroll_url = result["detail"]["googleurl"]["value"]
        hotp = get_one_token(serial=result["detail"]["serial"])
        self.assertEqual("sha256", hotp.hashlib)
        smartphone.add_token(hotp)

        totp = init_token({"genkey": True, "type": "totp", "otplen": 8, "hashlib": "sha256", "timeStep": 60})
        self.assertEqual("sha256", totp.hashlib)
        self.assertEqual(60, totp.timestep)
        smartphone.add_token(totp)
        daypassword = init_token({"genkey": True, "type": "daypassword", "hashlib": "sha256", "timeStep": 30})
        self.assertEqual("sha256", daypassword.hashlib)
        self.assertEqual(30, daypassword.timestep)
        smartphone.add_token(daypassword)

        # Offline token
        offline_hotp = init_token({"genkey": "1", "type": "hotp"})
        offline_hotp_otps = offline_hotp.get_multi_otp(100)[2]["otp"]
        smartphone.add_token(offline_hotp)
        self.create_offline_token(offline_hotp.get_serial(), offline_hotp_otps)

        set_policy("policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://new-pi.net/",
                                                            ACTION.CONTAINER_REGISTRATION_TTL: 36})
        # Firebase config
        fb_config = {FirebaseConfig.REGISTRATION_URL: "http://test/ttype/push",
                     FirebaseConfig.JSON_CONFIG: self.FIREBASE_FILE,
                     FirebaseConfig.TTL: 10}
        set_smsgateway("firebase", 'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider', "myFB",
                       fb_config)
        set_policy("push", scope=SCOPE.ENROLL, action={PUSH_ACTION.FIREBASE_CONFIG: "firebase",
                                                       PUSH_ACTION.REGISTRATION_URL: "http://test/ttype/push"})

        # Rollover init
        data = {"container_serial": mock_smph.container_serial, "rollover": True,
                "passphrase_prompt": "Enter your phone number.", "passphrase_response": "123456789"}
        result = self.request_assert_success("container/register/initialize", data, self.at, "POST")

        init_response_data = result["result"]["value"]
        self.assertIn("container_url", init_response_data)
        self.assertIn("nonce", init_response_data)
        self.assertIn("time_stamp", init_response_data)
        self.assertIn("key_algorithm", init_response_data)
        self.assertIn("hash_algorithm", init_response_data)
        self.assertIn("ssl_verify", init_response_data)
        self.assertIn("ttl", init_response_data)
        self.assertIn("passphrase_prompt", init_response_data)
        # Check if the url contains all relevant data
        qr_url = init_response_data["container_url"]["value"]
        self.assertIn(f"pia://container/{mock_smph.container_serial}", qr_url)
        self.assertIn("issuer=privacyIDEA", qr_url)
        self.assertIn("ttl=36", qr_url)
        self.assertIn("nonce=", qr_url)
        self.assertIn("time=", qr_url)
        self.assertIn("url=https%3A//new-pi.net/", qr_url)
        self.assertIn(f"serial={mock_smph.container_serial}", qr_url)
        self.assertIn("key_algorithm=", qr_url)
        self.assertIn("hash_algorithm", qr_url)
        self.assertIn("passphrase=Enter%20your%20phone%20number.", qr_url)

        # New smartphone finalizes rollover
        new_mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        params = new_mock_smph.register_finalize(scope="https://new-pi.net/container/register/finalize",
                                                 nonce=init_response_data["nonce"],
                                                 registration_time=init_response_data["time_stamp"],
                                                 passphrase="123456789", serial=mock_smph.container_serial)

        self.request_assert_success('container/register/finalize',
                                    params,
                                    None, 'POST')
        self.assertEqual(RegistrationState.ROLLOVER_COMPLETED, smartphone.registration_state)

        # Try to sync with old smartphone
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        params = mock_smph.synchronize(result["result"]["value"], scope)
        result = self.request_assert_error(400, "container/synchronize",
                                           params, None, 'POST')
        self.assertEqual(3002, result["result"]["error"]["code"])
        self.assertEqual(RegistrationState.ROLLOVER_COMPLETED, smartphone.registration_state)

        # Sync with new smartphone
        scope = "https://new-pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": new_mock_smph.container_serial}, None,
                                             "POST")

        new_mock_smph.container = {"serial": new_mock_smph.container_serial, "type": "smartphone",
                                   "tokens": [{"serial": hotp.get_serial(), "type": "HOTP", "label": hotp.get_serial(),
                                               "issuer": "privacIDEA", "pin": False, "algorithm": "SHA1", "digits": 6}]}
        params = new_mock_smph.synchronize(result["result"]["value"], scope)
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = new_mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        token_diff = container_dict_server["tokens"]
        # only online hotp token is included, for the push token the config is missing and offline tokens can not be
        # synchronized
        self.assertEqual(4, len(token_diff["add"]))
        new_hotp_enroll_url = [enroll_url for enroll_url in token_diff["add"] if hotp.get_serial() in enroll_url][0]
        self.assertNotEqual(initial_enroll_url, new_hotp_enroll_url)
        self.assertIn(offline_hotp.get_serial(), token_diff["offline"])
        self.assertEqual(103, offline_hotp.token.count)

        # check tokens
        self.assertEqual("sha256", hotp.hashlib)
        self.assertEqual("sha256", totp.hashlib)
        self.assertEqual(60, totp.timestep)
        self.assertEqual("sha256", daypassword.hashlib)
        self.assertEqual(30, daypassword.timestep)
        # due to new policy push token config changed to firebase
        self.assertEqual("firebase", push.get_tokeninfo()[PUSH_ACTION.FIREBASE_CONFIG])

        # smartphone got new token secrets: rollover completed
        self.assertEqual(RegistrationState.REGISTERED, smartphone.registration_state)

        delete_policy("policy")

    def test_52_rollover_server_not_completed(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # token
        hotp = init_token({"genkey": "1", "type": "hotp"})
        hotp_secret = hotp.token.get_otpkey().getKey().decode("utf-8")
        smartphone.add_token(hotp)

        set_policy("policy", scope=SCOPE.CONTAINER, action={ACTION.PI_SERVER_URL: "https://pi.net/",
                                                            ACTION.CONTAINER_REGISTRATION_TTL: 36})

        # Rollover init
        data = {"container_serial": mock_smph.container_serial, "rollover": True,
                "passphrase_prompt": "Enter your phone number.", "passphrase_response": "123456789"}
        self.request_assert_success("container/register/initialize", data, self.at, "POST")

        # register/finalize missing

        # Sync with old smartphone still working
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        mock_smph.container = {"serial": mock_smph.container_serial, "type": "smartphone",
                               "tokens": [{"serial": hotp.get_serial(), "type": "HOTP"}]}
        params = mock_smph.synchronize(result["result"]["value"], scope)

        self.request_assert_success("container/synchronize", params, None, 'POST')
        # check that token is not rolled over
        new_hotp_secret = hotp.token.get_otpkey().getKey().decode("utf-8")
        self.assertEqual(hotp_secret, new_hotp_secret)

        delete_policy("policy")

    def sync_with_initial_token_transfer_allowed(self, smartphone_serial=None):
        registration = self.register_smartphone_success(smartphone_serial)
        mock_smph = registration.mock_smph
        smartphone_serial = mock_smph.container_serial

        # Create Tokens
        hotp_token = init_token({"genkey": True, "type": "hotp"})
        _, _, otp_dict = hotp_token.get_multi_otp(2)
        hotp_otps = list(otp_dict["otp"].values())
        spass_token = init_token({"type": "spass"})
        totp = init_token({"genkey": True, "type": "totp"})
        daypassword = init_token({"genkey": True, "type": "daypassword"})

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": smartphone_serial}, None, 'POST')

        mock_smph.container = {"serial": smartphone_serial, "type": "smartphone",
                               "tokens": [{"serial": totp.get_serial()}, {"serial": daypassword.get_serial()},
                                          {"otp": hotp_otps, "type": "hotp"}, {"serial": spass_token.get_serial()},
                                          {"serial": "123456"}]}
        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Initial Sync
        sync_time = datetime.now(timezone.utc)
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)
        self.assertIn("policies", result_entries)
        self.assertTrue(result["result"]["value"]["policies"][ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER])

        # check last synchronization timestamp
        smartphone = find_container_by_serial(smartphone_serial)
        last_sync = smartphone.last_synchronization
        time_diff = abs((sync_time - last_sync).total_seconds())
        self.assertLessEqual(time_diff, 1)

        # check tokens of container
        smartphone_tokens = smartphone.get_tokens()
        self.assertEqual(3, len(smartphone_tokens))
        token_serials = [token.get_serial() for token in smartphone_tokens]
        self.assertIn(totp.get_serial(), token_serials)
        self.assertIn(daypassword.get_serial(), token_serials)
        self.assertIn(hotp_token.get_serial(), token_serials)

        # Second Sync
        new_hotp = init_token({"genkey": True, "type": "hotp"})

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": smartphone_serial}, None,
                                             "POST")

        mock_smph.container = {"serial": smartphone_serial, "type": "smartphone",
                               "tokens": [{"serial": totp.get_serial()}, {"serial": daypassword.get_serial()},
                                          {"otp": hotp_otps, "type": "hotp"}, {"serial": spass_token.get_serial()},
                                          {"serial": "123456"}, {"serial": new_hotp.get_serial()}]}
        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Sync
        self.request_assert_success("container/synchronize",
                                    params, None, 'POST')

        # check tokens of container: new hotp shall not be in the container
        smartphone_tokens = smartphone.get_tokens()
        self.assertEqual(3, len(smartphone_tokens))
        token_serials = [token.get_serial() for token in smartphone_tokens]
        self.assertIn(totp.get_serial(), token_serials)
        self.assertIn(daypassword.get_serial(), token_serials)
        self.assertIn(hotp_token.get_serial(), token_serials)
        self.assertNotIn(new_hotp.get_serial(), token_serials)

    def sync_with_initial_token_transfer_denied(self, smartphone_serial=None):
        registration = self.register_smartphone_success(smartphone_serial)
        mock_smph = registration.mock_smph
        smartphone_serial = mock_smph.container_serial

        # Create Tokens
        hotp_token = init_token({"genkey": True, "type": "hotp"})
        _, _, otp_dict = hotp_token.get_multi_otp(2)
        hotp_otps = list(otp_dict["otp"].values())
        spass_token = init_token({"type": "spass"})
        totp = init_token({"genkey": True, "type": "totp"})
        daypassword = init_token({"genkey": True, "type": "daypassword"})

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": smartphone_serial}, None, "POST")

        mock_smph.container = {"serial": smartphone_serial, "type": "smartphone",
                               "tokens": [{"serial": totp.get_serial()}, {"serial": daypassword.get_serial()},
                                          {"otp": hotp_otps, "type": "hotp"}, {"serial": spass_token.get_serial()},
                                          {"serial": "123456"}]}
        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Initial Sync
        sync_time = datetime.now(timezone.utc)
        result = self.request_assert_success("container/synchronize",
                                             params, None, "POST")
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)
        self.assertIn("policies", result_entries)
        self.assertFalse(result["result"]["value"]["policies"][ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER])

        # check last synchronization timestamp
        smartphone = find_container_by_serial(smartphone_serial)
        last_sync = smartphone.last_synchronization
        time_diff = abs((sync_time - last_sync).total_seconds())
        self.assertLessEqual(time_diff, 1)

        # check tokens of container
        smartphone_tokens = smartphone.get_tokens()
        self.assertEqual(0, len(smartphone_tokens))

    def test_53_synchronize_initial_token_transfer_no_user_success(self):
        # Generic policy
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER)
        self.sync_with_initial_token_transfer_allowed()
        delete_policy("transfer_policy")

    def test_54_synchronize_initial_token_transfer_no_user_denied(self):
        # No policy
        self.sync_with_initial_token_transfer_denied()

        # Policy for a specific realm
        self.setUp_user_realms()
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm1)
        self.sync_with_initial_token_transfer_denied()
        delete_policy("transfer_policy")

    def test_55_synchronize_initial_token_transfer_user_success(self):
        self.setUp_user_realms()

        # Generic policy
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER)
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        self.sync_with_initial_token_transfer_allowed(smartphone_serial)
        delete_policy("transfer_policy")

        # Policy for the users realm
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm1)
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        self.sync_with_initial_token_transfer_allowed(smartphone_serial)
        delete_policy("transfer_policy")

        # Policy for the user
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm1, user="hans")
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        self.sync_with_initial_token_transfer_allowed(smartphone_serial)
        delete_policy("transfer_policy")

        # Policy for the resolver
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   resolver=self.resolvername1)
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        self.sync_with_initial_token_transfer_allowed(smartphone_serial)
        delete_policy("transfer_policy")

    def test_56_synchronize_initial_token_transfer_user_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()

        # No policy
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        self.sync_with_initial_token_transfer_denied(smartphone_serial)

        # Policy for another realm
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm2)
        self.sync_with_initial_token_transfer_denied(smartphone_serial)
        delete_policy("transfer_policy")

        # Policy for another user
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm1, user="root")
        self.sync_with_initial_token_transfer_denied(smartphone_serial)
        delete_policy("transfer_policy")

    def test_57_synchronize_initial_token_transfer_user_realm_success(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        user = User("hans", self.realm1)

        # Policy for the users realm
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm1)
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.sync_with_initial_token_transfer_allowed(smartphone.serial)
        delete_policy("transfer_policy")

        # Policy for the other realm
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm2)
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.sync_with_initial_token_transfer_allowed(smartphone.serial)
        delete_policy("transfer_policy")

        # Policy for the user
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm1, user="hans")
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.sync_with_initial_token_transfer_allowed(smartphone.serial)
        delete_policy("transfer_policy")

    def test_58_synchronize_initial_token_transfer_user_realm_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()
        user = User("hans", self.realm1)

        # Policy for another realm
        smartphone = self.create_smartphone_for_user_and_realm(user, self.realm2)
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm3)
        self.sync_with_initial_token_transfer_denied(smartphone.serial)
        delete_policy("transfer_policy")

        # Policy for another user
        smartphone = self.create_smartphone_for_user_and_realm(user, self.realm2)
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm2, user="root")
        self.sync_with_initial_token_transfer_denied(smartphone.serial)
        delete_policy("transfer_policy")

    def test_59_synchronize_smartphone_with_offline_tokens(self):
        # Registration
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER)
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # tokens
        server_token = init_token({"genkey": "1", "type": "hotp", "otplen": 8, "hashlib": "sha256"})
        server_token_otps = server_token.get_multi_otp(100)[2]["otp"]
        client_token_no_serial = init_token({"genkey": "1", "type": "hotp"})
        client_token_no_serial_otps = client_token_no_serial.get_multi_otp(100)[2]["otp"]
        client_token_with_serial = init_token({"genkey": "1", "type": "hotp"})
        client_token_with_serial_otps = client_token_with_serial.get_multi_otp(100)[2]["otp"]
        shared_token = init_token({"genkey": "1", "type": "hotp"})
        shared_token_otps = shared_token.get_multi_otp(100)[2]["otp"]
        shared_token_no_serial = init_token({"genkey": "1", "type": "hotp"})
        shared_token_no_serial_otps = shared_token_no_serial.get_multi_otp(100)[2]["otp"]
        online_token = init_token({"genkey": "1", "type": "hotp"})

        smartphone.add_token(server_token)
        smartphone.add_token(shared_token)
        smartphone.add_token(shared_token_no_serial)
        smartphone.add_token(online_token)

        # Create offline token
        self.create_offline_token(server_token.get_serial(), server_token_otps)
        self.create_offline_token(client_token_no_serial.get_serial(), client_token_no_serial_otps)
        self.create_offline_token(client_token_with_serial.get_serial(), client_token_with_serial_otps)
        self.create_offline_token(shared_token.get_serial(), shared_token_otps)
        self.create_offline_token(shared_token_no_serial.get_serial(), shared_token_no_serial_otps)

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        mock_smph.container = {
            "tokens": [{"tokentype": "HOTP", "otp": list(client_token_no_serial_otps.values())[2:4], "counter": "2"},
                       {"tokentype": "HOTP", "serial": client_token_with_serial.get_serial()},
                       {"tokentype": "HOTP", "serial": shared_token.get_serial()},
                       {"tokentype": "HOTP", "otp": list(shared_token_no_serial_otps.values())[2:4], "counter": "2"},
                       {"tokentype": "HOTP", "serial": online_token.get_serial()}]}
        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Finalize
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        # the token only on the server can not be added to the client since the server does not know the offline counter
        add_tokens = tokens_dict["add"]
        self.assertEqual(0, len(add_tokens))
        self.assertEqual(103, server_token.token.count)

        update_tokens = {token["serial"]: token for token in tokens_dict["update"]}
        update_tokens_serials = update_tokens.keys()
        # the token from the client with serial is added to the container with unchanged counter
        self.assertIn(client_token_with_serial.get_serial(), update_tokens_serials)
        self.assertEqual(103, client_token_with_serial.token.count)
        self.assertTrue(update_tokens[client_token_with_serial.get_serial()]["offline"])
        # the shared token stays unchanged (counter = 103)
        self.assertIn(shared_token.get_serial(), update_tokens_serials)
        self.assertEqual(103, shared_token.token.count)
        self.assertTrue(update_tokens[shared_token.get_serial()]["offline"])
        # The token from the client without serial is added to the server and the counter is unchanged
        self.assertIn(client_token_no_serial.get_serial(), update_tokens_serials)
        self.assertEqual(103, client_token_no_serial.token.count)
        self.assertTrue(update_tokens[client_token_no_serial.get_serial()]["offline"])
        # Shared token: otp values could be mapped to serial
        self.assertIn(shared_token_no_serial.get_serial(), update_tokens_serials)
        self.assertEqual(103, shared_token_no_serial.token.count)
        self.assertTrue(update_tokens[shared_token_no_serial.get_serial()]["offline"])
        # Online token
        self.assertIn(online_token.get_serial(), update_tokens_serials)
        self.assertFalse(update_tokens[online_token.get_serial()]["offline"])
        self.assertEqual(5, len(update_tokens_serials))

        delete_policy("transfer_policy")

    def test_60_rollover_and_synchronize_with_offline_tokens(self):
        # Registration
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER)
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)
        smartphone.update_container_info([TokenContainerInfoData(key=RegistrationState.get_key(),
                                                                 value=RegistrationState.ROLLOVER_COMPLETED.value,
                                                                 info_type=PI_INTERNAL)])

        # tokens
        server_token = init_token({"genkey": "1", "type": "hotp", "otplen": 8, "hashlib": "sha256"})
        server_token_otps = server_token.get_multi_otp(100)[2]["otp"]
        client_token_no_serial = init_token({"genkey": "1", "type": "hotp"})
        client_token_no_serial_otps = client_token_no_serial.get_multi_otp(100)[2]["otp"]
        client_token_with_serial = init_token({"genkey": "1", "type": "hotp"})
        client_token_with_serial_otps = client_token_with_serial.get_multi_otp(100)[2]["otp"]
        shared_token = init_token({"genkey": "1", "type": "hotp"})
        shared_token_otps = shared_token.get_multi_otp(100)[2]["otp"]
        shared_token_no_serial = init_token({"genkey": "1", "type": "hotp"})
        shared_token_no_serial_otps = shared_token_no_serial.get_multi_otp(100)[2]["otp"]
        online_token = init_token({"genkey": "1", "type": "hotp"})

        smartphone.add_token(server_token)
        smartphone.add_token(shared_token)
        smartphone.add_token(shared_token_no_serial)
        smartphone.add_token(online_token)

        # Create offline token
        self.create_offline_token(server_token.get_serial(), server_token_otps)
        self.create_offline_token(client_token_no_serial.get_serial(), client_token_no_serial_otps)
        self.create_offline_token(client_token_with_serial.get_serial(), client_token_with_serial_otps)
        self.create_offline_token(shared_token.get_serial(), shared_token_otps)
        self.create_offline_token(shared_token_no_serial.get_serial(), shared_token_no_serial_otps)

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        mock_smph.container = {
            "tokens": [{"tokentype": "HOTP", "otp": list(client_token_no_serial_otps.values())[2:4], "counter": "2"},
                       {"tokentype": "HOTP", "serial": client_token_with_serial.get_serial()},
                       {"tokentype": "HOTP", "serial": shared_token.get_serial()},
                       {"tokentype": "HOTP", "otp": list(shared_token_no_serial_otps.values())[2:4], "counter": "2"},
                       {"tokentype": "HOTP", "serial": online_token.get_serial()}]}
        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Finalize
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        # Only the online token is rolled over and hence in the add list with the new token secret
        add_tokens = tokens_dict["add"]
        self.assertEqual(1, len(add_tokens))
        self.assertIn(online_token.get_serial(), add_tokens[0])

        # the token only on the server can not be added to the client since the server does not know the offline counter
        offline_tokens = tokens_dict["offline"]
        self.assertIn(server_token.get_serial(), offline_tokens)
        self.assertEqual(103, server_token.token.count)

        update_tokens = {token["serial"]: token for token in tokens_dict["update"]}
        update_tokens_serials = update_tokens.keys()
        # the token from the client with serial is added to the container with unchanged counter
        self.assertIn(client_token_with_serial.get_serial(), update_tokens_serials)
        self.assertEqual(103, client_token_with_serial.token.count)
        self.assertTrue(update_tokens[client_token_with_serial.get_serial()]["offline"])
        # the shared token stays unchanged (counter = 103)
        self.assertIn(shared_token.get_serial(), update_tokens_serials)
        self.assertEqual(103, shared_token.token.count)
        self.assertTrue(update_tokens[shared_token.get_serial()]["offline"])
        # The token from the client without serial is added to the server and the counter is unchanged
        self.assertIn(client_token_no_serial.get_serial(), update_tokens_serials)
        self.assertEqual(103, client_token_no_serial.token.count)
        self.assertTrue(update_tokens[client_token_no_serial.get_serial()]["offline"])
        # Shared token: otp values could be mapped to serial
        self.assertIn(shared_token_no_serial.get_serial(), update_tokens_serials)
        self.assertEqual(103, shared_token_no_serial.token.count)
        self.assertTrue(update_tokens[shared_token_no_serial.get_serial()]["offline"])
        self.assertEqual(4, len(update_tokens_serials))

        delete_policy("transfer_policy")


class APIContainerTemplate(APIContainerTest):

    def test_01_create_delete_template_success(self):
        template_name = "test"
        # Create template without tokens
        data = json.dumps({"template_options": {"tokens": []}, "default": True})
        result = self.request_assert_success(f'/container/smartphone/template/{template_name}',
                                             data, self.at, 'POST')
        self.assertGreater(result["result"]["value"]["template_id"], 0)

        # Delete template
        result = self.request_assert_success(f'/container/template/{template_name}',
                                             {}, self.at, 'DELETE')
        self.assertTrue(result["result"]["value"])

    def test_02_create_template_fail(self):
        # Create template without name
        self.request_assert_404_no_result('/container/smartphone/template',
                                          {}, self.at, 'POST')

    def test_03_delete_template_fail(self):
        # Delete non existing template
        template_name = "random"
        self.request_assert_405(f'container/template/{template_name}',
                                {}, None, 'POST')

    def test_04_update_template_options_success(self):
        # Create a template
        template_name = "test"
        template_id = create_container_template(container_type="generic",
                                                template_name=template_name,
                                                options={"tokens": [{"type": "hotp"}]})

        # Update options
        params = json.dumps({"template_options": {
            "tokens": [{"type": "hotp", "genkey": True}, {"type": "totp", "genkey": True, "hashlib": "sha256"}]}})

        result = self.request_assert_success(f'/container/generic/template/{template_name}',
                                             params, self.at, 'POST')
        self.assertEqual(template_id, result["result"]["value"]["template_id"])

        template = get_template_obj(template_name)
        template.delete()

    def test_05_update_template_options_fail(self):
        # Create a template
        template_name = "test"
        create_container_template(container_type="generic",
                                  template_name=template_name,
                                  options={"tokens": [{"type": "hotp"}]})

        # Update with wrong options type
        params = json.dumps({"template_options": json.dumps({
            "tokens": [{"type": "hotp", "genkey": True}, {"type": "totp", "genkey": True, "hashlib": "sha256"}]})})

        result = self.request_assert_error(400, f'/container/generic/template/{template_name}',
                                           params, self.at, 'POST')
        self.assertEqual(905, result["result"]["error"]["code"])

        template = get_template_obj(template_name)
        template.delete()

    def test_06_create_container_with_template_success(self):
        # Create a template
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        def check_result(result):
            container_serial = result["result"]["value"]["container_serial"]
            container = find_container_by_serial(container_serial)
            tokens = container.get_tokens()
            self.assertEqual(1, len(tokens))
            self.assertEqual("hotp", tokens[0].get_type())
            # result contains enroll info for one token
            self.assertEqual(1, len(result["result"]["value"]["tokens"]))
            container_template = container.template
            self.assertEqual(template_params["name"], container_template.name)

        # create container by passing the complete template dictionary
        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')
        check_result(result)

        # create container by passing only the template name
        result = self.request_assert_success('/container/init',
                                             {"type": "smartphone", "template_name": template_params["name"]},
                                             self.at, 'POST')
        check_result(result)

        template = get_template_obj(template_params["name"])
        template.delete()

    def test_07_create_container_with_template_no_tokens(self):
        # Create a template with no tokens
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        def check_result(result):
            container_serial = result["result"]["value"]["container_serial"]
            container = find_container_by_serial(container_serial)
            tokens = container.get_tokens()
            self.assertEqual(0, len(tokens))
            self.assertIsNone(result["result"]["value"].get("tokens"))
            self.assertEqual(template_params["name"], container.template.name)

        # with template dict
        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success("/container/init", request_params, self.at, "POST")
        check_result(result)

        # with template from db
        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success("/container/init",
                                             {"type": "smartphone", "template_name": template_params["name"]},
                                             self.at, "POST")
        check_result(result)

        template = get_template_obj(template_params["name"])
        template.delete()

        # Create a template without template options
        template_params = {"name": "test",
                           "container_type": "smartphone"}

        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(0, len(tokens))

    def test_08_create_container_with_template_missing_policies(self):
        # Create a template with hotp and push
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {
                               "tokens": [{"type": "hotp", "genkey": True}, {"type": "push", "genkey": True}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        def check_result(result):
            # only hotp token is created, push require policy that is not set
            container_serial = result["result"]["value"]["container_serial"]
            container = find_container_by_serial(container_serial)
            tokens = container.get_tokens()
            self.assertEqual(1, len(tokens))

        # Create a container from the template dict
        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')
        check_result(result)

        # Create a container from the db template
        result = self.request_assert_success("/container/init",
                                             {"type": "smartphone", "template_name": template_params["name"]}, self.at,
                                             "POST")
        check_result(result)

        template = get_template_obj(template_params["name"])
        template.delete()

    def test_09_create_container_with_template_all_tokens_success(self):
        self.setUp_user_realm3()
        # Policies
        set_policy("push", scope=SCOPE.ENROLL, action={PUSH_ACTION.FIREBASE_CONFIG: "poll only",
                                                       PUSH_ACTION.REGISTRATION_URL: "http://test/ttype/push",
                                                       ACTION.TOKENISSUER: "{realm}",
                                                       ACTION.TOKENLABEL: "serial_{serial}"})
        set_policy("admin", SCOPE.ADMIN, action={ACTION.CONTAINER_CREATE: True,
                                                 "enrollHOTP": True, "enrollREMOTE": True, "enrollDAYPASSWORD": True,
                                                 "enrollSPASS": True, "enrollTOTP": True, "enroll4EYES": True,
                                                 "enrollPAPER": True, "enrollTAN": True, "enrollPUSH": True,
                                                 "enrollINDEXEDSECRET": True,
                                                 "enrollAPPLSPEC": True, "enrollREGISTRATION": True, "enrollSMS": True,
                                                 "enrollEMAIL": True, "enrollTIQR": True,
                                                 "indexedsecret_force_attribute": "username",
                                                 "hotp_hashlib": "sha256"})
        set_policy("pw_length", scope=SCOPE.ENROLL, action={ACTION.REGISTRATIONCODE_LENGTH: 12})

        # privacyIDEA server for the remote token
        pi_server_id = add_privacyideaserver(identifier="myserver",
                                             url="https://pi/pi",
                                             description="Hallo")
        # service id for applspec
        service_id = set_serviceid("test", "This is an awesome test service id")

        # Create a template with all token types allowed for the generic container template
        tokens_dict = [
            {"type": "hotp", "genkey": True, "user": True},
            {"type": "remote", "remote.server_id": pi_server_id, "remote.serial": "1234"},
            {"type": "daypassword", "genkey": True}, {"type": "spass"},
            {"type": "totp", "genkey": True},
            {"type": "4eyes", "4eyes": {self.realm3: {"count": 2, "selected": True}}},
            {"type": "paper"}, {"type": "tan"}, {"type": "push", "genkey": True, "user": True},
            {"type": "indexedsecret", "user": True},
            {"type": "applspec", "genkey": True, "service_id": service_id},
            {"type": "registration"}, {"type": "sms", "dynamic_phone": True, "genkey": True, "user": True},
            {"type": "email", "dynamic_email": True, "genkey": True, "user": True}, {"type": "tiqr", "user": True}
        ]
        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {"tokens": tokens_dict}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        def check_result(result):
            # check tokens that were created
            container_serial = result["result"]["value"]["container_serial"]
            container = find_container_by_serial(container_serial)
            tokens = container.get_tokens()
            self.assertEqual(15, len(tokens))
            self.assertEqual(15, len(result["result"]["value"]["tokens"]))

            # check tokens and init details
            owner = User(login="cornelius", realm=self.realm3)
            init_details = result["result"]["value"]["tokens"]
            for token in tokens:
                token_type = token.get_type()

                # check user assignment
                if token_type in ["hotp", "indexedsecret", "push", "sms", "email", "tiqr"]:
                    self.assertEqual(owner, token.user)
                    if token_type == "hotp":
                        # check default hashlib
                        self.assertEqual("sha256", token.hashlib)
                else:
                    self.assertIsNone(token.user)

                # check init details
                if token_type in ["hotp", "totp", "daypassword"]:
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("googleurl"), dict))
                elif token_type in ["paper", "tan"]:
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("otps"), dict))
                elif token_type == "push":
                    serial = token.get_serial()
                    push_url = init_details[serial].get("pushurl")
                    self.assertTrue(isinstance(push_url, dict))
                    self.assertIn(f"issuer={self.realm3}", push_url["value"])
                    self.assertIn(f"serial_{serial}", push_url["value"])
                elif token_type == "applspec":
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("password"), str))
                elif token_type == "registration":
                    self.assertEqual(12, len(init_details[token.get_serial()]["registrationcode"]))
                elif token_type == "tiqr":
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("tiqrenroll"), dict))

            [token.delete_token() for token in tokens]
            container.delete()

        # Create a container from the template dict
        request_params = json.dumps(
            {"type": "generic", "template": template_params, "user": "cornelius", "realm": self.realm3})
        result = self.request_assert_success("/container/init", request_params, self.at, "POST")
        check_result(result)

        # Create a container from the template name
        result = self.request_assert_success("/container/init",
                                             {"type": "generic", "template_name": template_params["name"],
                                              "user": "cornelius", "realm": self.realm3}, self.at, "POST")
        check_result(result)

        template = get_template_obj(template_params["name"])
        template.delete()

        delete_policy("push")
        delete_policy("admin")
        delete_policy("pw_length")

    def test_10_create_container_with_template_some_tokens_fail(self):
        # tokens that require policies fail: push
        # tokens that require user fail: tiqr
        # Policies
        set_policy("admin", SCOPE.ADMIN, action={ACTION.CONTAINER_CREATE: True,
                                                 "enrollHOTP": True, "enrollREMOTE": True, "enrollDAYPASSWORD": True,
                                                 "enrollSPASS": True, "enrollTOTP": True, "enroll4EYES": True,
                                                 "enrollPAPER": True, "enrollTAN": True, "enrollPUSH": True,
                                                 "enrollINDEXEDSECRET": True,
                                                 "enrollAPPLSPEC": True, "enrollREGISTRATION": True, "enrollSMS": True,
                                                 "enrollEMAIL": True, "enrollTIQR": True,
                                                 "indexedsecret_force_attribute": "username",
                                                 "hotp_hashlib": "sha256"})
        set_policy("pw_length", scope=SCOPE.ENROLL, action={ACTION.REGISTRATIONCODE_LENGTH: 12})

        # privacyIDEA server for the remote token
        pi_server_id = add_privacyideaserver(identifier="myserver",
                                             url="https://pi/pi",
                                             description="Hallo")
        # service id for applspec
        service_id = set_serviceid("test", "This is an awesome test service id")

        # Create a template with all token types allowed for the generic container template
        tokens_dict = [
            {"type": "hotp", "genkey": True, "user": True},
            {"type": "remote", "remote.server_id": pi_server_id, "remote.serial": "1234"},
            {"type": "daypassword", "genkey": True}, {"type": "spass"},
            {"type": "totp", "genkey": True},
            {"type": "4eyes", "4eyes": {self.realm3: {"count": 2, "selected": True}}},
            {"type": "paper"}, {"type": "tan"}, {"type": "push", "genkey": True, "user": True},
            {"type": "indexedsecret", "user": True},
            {"type": "applspec", "genkey": True, "service_id": service_id},
            {"type": "registration"}, {"type": "sms", "dynamic_phone": True, "genkey": True, "user": True},
            {"type": "email", "dynamic_email": True, "genkey": True, "user": True}, {"type": "tiqr", "user": True}
        ]
        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {"tokens": tokens_dict}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        def check_result(result):
            # check tokens that were created
            container_serial = result["result"]["value"]["container_serial"]
            container = find_container_by_serial(container_serial)
            tokens = container.get_tokens()
            all_token_types = [token.get_type() for token in tokens]
            self.assertNotIn("push", all_token_types)
            self.assertNotIn("tiqr", all_token_types)
            self.assertEqual(13, len(tokens))
            self.assertEqual(13, len(result["result"]["value"]["tokens"]))

            # check tokens and init details
            init_details = result["result"]["value"]["tokens"]
            for token in tokens:
                token_type = token.get_type()

                # check user assignment
                self.assertIsNone(token.user)

                if token_type == "hotp":
                    # check default hashlib
                    self.assertEqual("sha256", token.hashlib)

                # check init details
                if token_type in ["hotp", "totp", "daypassword"]:
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("googleurl"), dict))
                elif token_type in ["paper", "tan"]:
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("otps"), dict))
                elif token_type == "applspec":
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("password"), str))
                elif token_type == "registration":
                    self.assertEqual(12, len(init_details[token.get_serial()]["registrationcode"]))
                elif token_type == "tiqr":
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("tiqrenroll"), dict))

            [token.delete_token() for token in tokens]
            container.delete()

        # Create a container from the template dict
        self.setUp_user_realm3()
        request_params = json.dumps(
            {"type": "generic", "template": template_params})
        result = self.request_assert_success("/container/init", request_params, self.at, "POST")
        check_result(result)

        # Create container from the db template
        result = self.request_assert_success("/container/init",
                                             {"type": "generic", "template_name": template_params["name"]}, self.at,
                                             "POST")
        check_result(result)

        template = get_template_obj(template_params["name"])
        template.delete()

        delete_policy("admin")
        delete_policy("pw_length")

    def test_11_create_container_with_template_max_token_policies(self):
        # Limit number of tokens per user and type
        set_policy("max_token", scope=SCOPE.ENROLL, action={ACTION.MAXTOKENUSER: 6,
                                                            TANACTION.TANTOKEN_COUNT: 2,
                                                            PAPERACTION.PAPERTOKEN_COUNT: 2,
                                                            ACTION.MAXTOKENREALM: 7})
        self.setUp_user_realms()
        hans = User(login="hans", realm=self.realm1)

        # Create tokens for hans
        init_token({"type": "paper"}, user=hans)
        init_token({"type": "tan"}, user=hans)

        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {
                               "tokens": [{"type": "hotp", "genkey": True, "user": True},
                                          {"type": "paper", "user": True},
                                          {"type": "tan", "user": True}]}}
        request_params = json.dumps({"type": "generic", "user": "hans", "realm": self.realm1,
                                     "template": template_params})

        # second paper and tan tokens for hans can be created with the template
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(3, len(tokens))
        token_types = [token.get_type() for token in tokens]
        self.assertEqual(set(["hotp", "paper", "tan"]), set(token_types))

        # third paper and tan tokens for hans can NOT be created
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container1 = find_container_by_serial(container_serial)
        tokens = container1.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertEqual("hotp", tokens[0].get_type())

        # Can not create any type of token: hans already has 6 tokens
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container2 = find_container_by_serial(container_serial)
        tokens = container2.get_tokens()
        self.assertEqual(0, len(tokens))

        # create tokens for another user in this realm: only one token created
        request_params = json.dumps({"type": "generic", "user": "selfservice", "realm": self.realm1,
                                     "template": template_params})

        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))

        delete_policy("max_token")
        container1.delete()
        container2.delete()
        user_tokens = get_tokens_from_serial_or_user(serial=None, user=hans)
        [token.delete_token() for token in user_tokens]

    def test_12_create_container_with_template_otp_pin(self):
        # Set otp pin policy
        set_policy("otp_pin", scope=SCOPE.ADMIN, action={ACTION.OTPPINMAXLEN: 6, ACTION.OTPPINMINLEN: 2})
        set_policy("encrypt", scope=SCOPE.ENROLL, action=ACTION.ENCRYPTPIN)
        # Set admin policies
        set_policy("admin", scope=SCOPE.ADMIN,
                   action={ACTION.CONTAINER_CREATE: True, "enrollHOTP": True})
        set_policy("enrollPIN", SCOPE.ADMIN, action=ACTION.ENROLLPIN)
        set_policy("change_pin", SCOPE.ENROLL, action={ACTION.CHANGE_PIN_FIRST_USE: True})

        # correct pin
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True, "pin": "1234"}]}}
        request_params = json.dumps({"type": "smartphone", "user": "hans", "realm": self.realm1,
                                     "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertNotEqual(-1, tokens[0].token.get_pin())
        self.assertIsNotNone(get_tokeninfo(tokens[0].get_serial(), "next_pin_change"))
        delete_policy("change_pin")

        # pin too short
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True, "pin": "1"}]}}
        request_params = json.dumps({"type": "smartphone", "user": "hans", "realm": self.realm1,
                                     "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(0, len(tokens))

        # Not allowed to set the pin
        delete_policy("otp_pin")
        delete_policy("enrollPIN")
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True, "pin": "1234"}]}}
        request_params = json.dumps({"type": "smartphone", "user": "hans", "realm": self.realm1,
                                     "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertEqual("hotp", tokens[0].get_type())
        self.assertEqual(-1, tokens[0].token.get_pin())

        # random pin
        set_policy("random_pin", scope=SCOPE.ENROLL, action={ACTION.OTPPINRANDOM: 8})
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True}]}}
        request_params = json.dumps({"type": "smartphone", "user": "hans", "realm": self.realm1,
                                     "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertNotEqual(-1, tokens[0].token.get_pin())

        delete_policy("random_pin")
        delete_policy("encrypt")
        delete_policy("admin")

    def test_13_create_container_with_template_verify_enrollment(self):
        # Policies
        set_policy("enrollment", scope=SCOPE.ENROLL,
                   action={ACTION.VERIFY_ENROLLMENT: "hotp totp paper tan indexedsecret"})

        # tokens
        tokens_dict = [
            {"type": "hotp", "genkey": True}, {"type": "totp", "genkey": True},
            {"type": "paper"}, {"type": "tan"}, {"type": "indexedsecret"},
        ]
        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {"tokens": tokens_dict}}
        request_params = json.dumps({"type": "generic", "user": "hans", "realm": self.realm1,
                                     "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(5, len(tokens))
        token_results = result["result"]["value"]["tokens"]
        for token in tokens:
            self.assertTrue("verify", token.rollout_state)
            self.assertEqual("verify", token_results[token.get_serial()]["rollout_state"])
            self.assertTrue(isinstance(token_results[token.get_serial()]["verify"], dict))

        # cleanup
        [token.delete_token() for token in tokens]
        delete_policy("enrollment")

    def test_14_create_container_with_template_2_step_enrollment(self):
        # Policies
        set_policy("enrollment", scope=SCOPE.ADMIN,
                   action={"hotp_2step": "allow", ACTION.CONTAINER_CREATE: True, "enrollHOTP": True,
                           "enrollTOTP": True})

        # tokens
        hotp_serial = "OATH0001"
        totp_serial = "TOTP0001"
        tokens_dict = [{"type": "hotp", "genkey": True, "2stepinit": True, "serial": hotp_serial},
                       {"type": "totp", "genkey": True, "serial": totp_serial}]
        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {"tokens": tokens_dict}}
        request_params = json.dumps({"type": "generic", "user": "hans", "realm": self.realm1,
                                     "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')

        # check result
        token_result = result["result"]["value"]["tokens"]
        hotp_result_keys = list(token_result[hotp_serial].keys())
        self.assertIn("2step_salt", hotp_result_keys)
        self.assertIn("2step_output", hotp_result_keys)
        self.assertIn("2step_difficulty", hotp_result_keys)
        totp_result_keys = list(token_result[totp_serial].keys())
        self.assertNotIn("2step_salt", totp_result_keys)
        self.assertNotIn("2step_output", totp_result_keys)
        self.assertNotIn("2step_difficulty", totp_result_keys)

        # check tokens
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        for token in tokens:
            if token.get_type() == "hotp":
                self.assertEqual("clientwait", token.rollout_state)
            else:
                self.assertEqual("", token.rollout_state)

        # cleanup
        [token.delete_token() for token in tokens]
        delete_policy("enrollment")

    def test_15_get_template(self):
        create_container_template(container_type="smartphone",
                                  template_name="test1",
                                  options={})
        create_container_template(container_type="generic",
                                  template_name="test2",
                                  options={})
        create_container_template(container_type="smartphone",
                                  template_name="test3",
                                  options={})

        query_params = {"container_type": "smartphone", "pagesize": 15, "page": 1}
        result = self.request_assert_success('/container/templates', query_params, self.at, 'GET')
        self.assertEqual(2, result["result"]["value"]["count"])
        self.assertEqual(1, result["result"]["value"]["current"])
        self.assertEqual(2, len(result["result"]["value"]["templates"]))

    def test_16_compare_template_with_containers(self):
        template_options = {"options": {SmartphoneOptions.KEY_ALGORITHM: "secp384r1"},
                            "tokens": [{"type": "hotp", "genkey": True}, {"type": "daypassword", "genkey": True}]}
        create_container_template(container_type="smartphone", template_name="test", options=template_options)

        # create container with template
        request_params = json.dumps({"type": "smartphone",
                                     "template": {"name": "test", "container_type": "smartphone",
                                                  "template_options": template_options}})
        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')
        equal_cserial = result["result"]["value"]["container_serial"]

        # Create container with tokens and link with template
        cserial = init_container({"type": "smartphone"})["container_serial"]
        container = find_container_by_serial(cserial)
        container.template = "test"

        hotp = init_token({"type": "hotp", "genkey": True})
        totp1 = init_token({"type": "totp", "genkey": True})
        totp2 = init_token({"type": "totp", "genkey": True})
        container.add_token(hotp)
        container.add_token(totp1)
        container.add_token(totp2)

        # Compare template with all containers
        result = self.request_assert_success("/container/template/test/compare", {}, self.at, "GET")
        # Check result for equal container
        container_diff = result["result"]["value"][equal_cserial]
        token_diff = container_diff["tokens"]
        self.assertEqual(0, len(token_diff["missing"]))
        self.assertEqual(0, len(token_diff["additional"]))
        self.assertTrue(token_diff["equal"])
        # Check result for unequal container
        container_diff = result["result"]["value"][cserial]
        token_diff = container_diff["tokens"]
        self.assertSetEqual({"daypassword"}, set(token_diff["missing"]))
        self.assertSetEqual({"totp", "totp"}, set(token_diff["additional"]))
        self.assertFalse(token_diff["equal"])

        # Compare template with specific container
        result = self.request_assert_success("/container/template/test/compare", {"container_serial": cserial},
                                             self.at, "GET")
        # Check result for unequal container
        container_diff = result["result"]["value"][cserial]
        token_diff = container_diff["tokens"]
        self.assertSetEqual({"daypassword"}, set(token_diff["missing"]))
        self.assertSetEqual({"totp", "totp"}, set(token_diff["additional"]))
        self.assertFalse(token_diff["equal"])
        self.assertNotIn(equal_cserial, result["result"]["value"].keys())

        # Clean up
        container.delete()
        hotp.delete_token()
        totp1.delete_token()
        totp2.delete_token()
        get_template_obj("test").delete()

    def test_17_get_template_token_types(self):
        result = self.request_assert_success('/container/template/tokentypes', {}, self.at, 'GET')
        self.assertEqual(3, len(result["result"]["value"]))
        template_token_types = result["result"]["value"]
        template_container_types = template_token_types.keys()

        self.assertIn("generic", template_container_types)
        self.assertIn("smartphone", template_container_types)
        self.assertIn("yubikey", template_container_types)

        self.assertTrue(isinstance(template_token_types["generic"]["description"], str))
        self.assertTrue(isinstance(template_token_types["generic"]["token_types"], list))
