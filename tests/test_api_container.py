import base64
from datetime import datetime, timezone
import json

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey

from privacyidea.lib.container import (init_container, find_container_by_serial, add_token_to_container, assign_user,
                                       add_container_realms, get_container_realms, create_container_template,
                                       get_template_obj)
from privacyidea.lib.containers.smartphone import SmartphoneOptions
from privacyidea.lib.containers.yubikey import YubikeyOptions
from privacyidea.lib.crypto import generate_keypair_ecc, ecc_key_pair_to_b64url_str, sign_ecc, decrypt_ecc, geturandom
from privacyidea.lib.policy import set_policy, SCOPE, ACTION, delete_policy
from privacyidea.lib.realm import set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.smsprovider.FirebaseProvider import FIREBASE_CONFIG
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
from privacyidea.lib.token import init_token, get_tokens_paginate, get_one_token
from privacyidea.lib.tokens.pushtoken import PUSH_ACTION
from privacyidea.lib.user import User
from tests.base import MyApiTestCase


class APIContainerAuthorization(MyApiTestCase):
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
                                           data=data,
                                           headers={'Authorization': auth_token}):
            res = self.app.full_dispatch_request()
            self.assertEqual(403, res.status_code, res.json)
            self.assertEqual(res.json["result"]["error"]["code"], 303)
            return res.json

    def request_assert_200(self, url, data: dict, auth_token, method='POST'):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data,
                                           headers={'Authorization': auth_token}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
            self.assertTrue(res.json["result"]["status"])
            return res.json

    def create_container_for_user(self):
        set_policy("user_container_create", scope=SCOPE.USER, action=ACTION.CONTAINER_CREATE)
        with self.app.test_request_context('/container/init',
                                           method='POST',
                                           data={"type": "generic"},
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
        container_serial = res.json["result"]["value"]["container_serial"]
        self.assertGreater(len(container_serial), 0)
        delete_policy("user_container_create")
        return container_serial

    def test_01_user_create_allowed(self):
        self.create_container_for_user()

    def test_02_user_create_denied(self):
        # Set a random policy so that user action are defined
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DESCRIPTION)
        self.request_denied_assert_403('/container/init', {"type": "Smartphone", "description": "test description!!"},
                                       self.at_user)
        delete_policy("policy")

    def test_03_user_delete_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_assert_200(f"/container/{container_serial}", {}, self.at_user, method='DELETE')
        delete_policy("policy")

    def test_04_user_delete_denied(self):
        # User does not have 'delete' rights
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_CREATE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}", {}, self.at_user, method='DELETE')
        delete_policy("policy")

        # User is not the owner of the container
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        container_serial, _ = init_container({"type": "generic", "user": "hans", "realm": self.realm1})
        self.request_denied_assert_403(f"/container/{container_serial}", {}, self.at_user, method='DELETE')
        delete_policy("policy")

    def test_05_user_description_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DESCRIPTION)
        container_serial = self.create_container_for_user()
        self.request_assert_200(f"/container/{container_serial}/description", {"description": "test"}, self.at_user,
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
        container_serial, _ = init_container({"type": "generic", "user": "hans", "realm": self.realm1})
        self.request_denied_assert_403(f"/container/{container_serial}/description", {"description": "test"},
                                       self.at_user, method='POST')
        delete_policy("policy")

    def test_07_user_state_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_STATE)
        container_serial = self.create_container_for_user()
        self.request_assert_200(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
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
        container_serial, _ = init_container({"type": "generic", "user": "hans", "realm": self.realm1})
        self.request_denied_assert_403(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                       self.at_user, method='POST')
        delete_policy("policy")

    def test_09_user_add_token_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_ADD_TOKEN)
        container_serial = self.create_container_for_user()
        container = find_container_by_serial(container_serial)
        container_owner = container.get_users()[0]
        token = init_token({"genkey": "1"}, user=container_owner)
        token_serial = token.get_serial()
        result = self.request_assert_200(f"/container/{container_serial}/add", {"serial": token_serial}, self.at_user,
                                         method='POST')
        self.assertTrue(result["result"]["value"])

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
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_ADD_TOKEN)
        self.request_denied_assert_403(f"/container/{container_serial}/add", {"serial": token_serial}, self.at_user,
                                       method='POST')

        # User has 'add' rights but is not the owner of the container
        another_container_serial, _ = init_container({"type": "generic", "user": user.login, "realm": user.realm})
        self.request_denied_assert_403(f"/container/{another_container_serial}/add", {"serial": my_token_serial},
                                       self.at_user,
                                       method='POST')

        # User has 'add' rights but the token is already in a container from another user
        add_token_to_container(another_container_serial, my_token_serial, user_role='admin')
        self.request_denied_assert_403(f"/container/{container_serial}/add", {"serial": my_token_serial},
                                       self.at_user,
                                       method='POST')
        delete_policy("policy")

    def test_11_user_remove_token_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_REMOVE_TOKEN)
        container_serial = self.create_container_for_user()
        container = find_container_by_serial(container_serial)
        token = init_token({"genkey": "1"}, user=container.get_users()[0])
        token_serial = token.get_serial()
        container.add_token(token)

        result = self.request_assert_200(f"/container/{container_serial}/remove", {"serial": token_serial},
                                         self.at_user,
                                         method='POST')
        self.assertTrue(result["result"]["value"])
        delete_policy("policy")

    def test_12_user_remove_token_denied(self):
        # User does not have 'remove' rights
        container_serial = self.create_container_for_user()
        my_token = init_token({"genkey": "1"}, user=User("selfservice", self.realm1, self.resolvername1))
        my_token_serial = my_token.get_serial()
        add_token_to_container(container_serial, my_token_serial, user_role='admin')
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        self.request_denied_assert_403(f"/container/{container_serial}/remove", {"serial": my_token_serial},
                                       self.at_user, method='POST')
        delete_policy("policy")

        # User has 'remove' rights but is not the owner of the token
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_REMOVE_TOKEN)
        user = User(login="hans", realm=self.realm1, resolver=self.resolvername1)
        token = init_token({"genkey": "1"}, user=user)
        token_serial = token.get_serial()
        add_token_to_container(container_serial, token_serial, user_role='admin')
        self.request_denied_assert_403(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at_user,
                                       method='POST')

        # User has 'remove' rights but is not the owner of the container
        another_container_serial, _ = init_container({"type": "generic", "user": "hans", "realm": self.realm1})
        add_token_to_container(another_container_serial, my_token_serial, user_role='admin')
        self.request_denied_assert_403(f"/container/{another_container_serial}/remove", {"serial": my_token_serial},
                                       self.at_user, method='POST')
        delete_policy("policy")

    def test_13_user_assign_user_allowed(self):
        # Note: This will not set the user root but the user selfservice, because the user attribute is changed in
        # before_request()
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_ASSIGN_USER)
        container_serial, _ = init_container({"type": "generic"})
        self.request_assert_200(f"/container/{container_serial}/assign", {"realm": "realm1", "user": "root"},
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
        self.request_assert_200(f"/container/{container_serial}/unassign", {"realm": "realm1", "user": "root"},
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
        container_serial, _ = init_container({"type": "generic"})
        user = User(login="hans", realm=self.realm1, resolver=self.resolvername1)
        assign_user(container_serial, user, user_role='admin')
        self.request_denied_assert_403(f"/container/{container_serial}/unassign", {"realm": "realm1", "user": "root"},
                                       self.at_user)
        delete_policy("policy")

    def test_17_admin_create_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE)
        result = self.request_assert_200('/container/init', {"type": "generic"}, self.at)
        self.assertGreater(len(result["result"]["value"]["container_serial"]), 0)
        delete_policy("policy")

    def test_18_admin_create_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DESCRIPTION)
        self.request_denied_assert_403('/container/init', {"type": "Smartphone", "description": "test description!!"},
                                       self.at)
        delete_policy("policy")

    def test_19_admin_delete_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_assert_200(f"/container/{container_serial}", {}, self.at, method='DELETE')
        delete_policy("policy")

    def test_20_admin_delete_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}", {}, self.at, method='DELETE')
        delete_policy("policy")

    def test_21_admin_description_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DESCRIPTION)
        container_serial = self.create_container_for_user()
        self.request_assert_200(f"/container/{container_serial}/description", {"description": "test"}, self.at,
                                method='POST')
        delete_policy("policy")

    def test_22_admin_description_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/description", {"description": "test"},
                                       self.at, method='POST')
        delete_policy("policy")

    def test_23_admin_state_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_STATE)
        container_serial = self.create_container_for_user()
        self.request_assert_200(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                self.at, method='POST')
        delete_policy("policy")

    def test_24_admin_state_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                       self.at, method='POST')
        delete_policy("policy")

    def test_25_admin_add_token_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ADD_TOKEN)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        result = self.request_assert_200(f"/container/{container_serial}/add", {"serial": token_serial}, self.at,
                                         method='POST')
        self.assertTrue(result["result"]["value"])
        delete_policy("policy")

    def test_26_admin_add_token_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{container_serial}/add", {"serial": token_serial}, self.at,
                                       method='POST')
        delete_policy("policy")

    def test_27_admin_remove_token_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REMOVE_TOKEN)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        container = find_container_by_serial(container_serial)
        container.add_token(token)
        result = self.request_assert_200(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at,
                                         method='POST')
        self.assertTrue(result["result"]["value"])
        delete_policy("policy")

    def test_28_admin_remove_token_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        container = find_container_by_serial(container_serial)
        container.add_token(token)
        self.request_denied_assert_403(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at,
                                       method='POST')
        delete_policy("policy")

    def test_29_admin_assign_user_allowed(self):
        self.setUp_user_realms()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ASSIGN_USER)
        container_serial, _ = init_container({"type": "generic"})
        self.request_assert_200(f"/container/{container_serial}/assign",
                                {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_30_admin_assign_user_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial, _ = init_container({"type": "generic"})
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_31_admin_remove_user_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_UNASSIGN_USER)
        container_serial, _ = init_container({"type": "generic", "user": "root", "realm": self.realm1})
        self.request_assert_200(f"/container/{container_serial}/unassign",
                                {"realm": "realm1", "user": "root", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_32_admin_remove_user_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial, _ = init_container({"type": "generic", "user": "root", "realm": self.realm1})
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": "realm1", "user": "root", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_33_user_container_realms_denied(self):
        # Editing the container realms is an admin action and therefore only ever allowed for admins
        # But this returns a 401 from the @admin_required decorator
        container_serial = self.create_container_for_user()
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)

        with self.app.test_request_context(f"/container/{container_serial}/realms", method='POST',
                                           data={"realms": "realm1"}, headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)
        delete_policy("policy")

    def test_34_admin_container_realms_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REALMS)
        container_serial = self.create_container_for_user()
        self.request_assert_200(f"/container/{container_serial}/realms", {"realms": "realm1"}, self.at)
        delete_policy("policy")

    def test_35_admin_container_realms_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/realms", {"realms": "realm1"}, self.at)
        delete_policy("policy")

    def test_36_admin_container_list_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_LIST)
        self.request_assert_200('/container/', {}, self.at, 'GET')
        delete_policy("policy")

    def test_37_admin_container_list_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        self.request_denied_assert_403('/container/', {}, self.at, 'GET')
        delete_policy("policy")

    def test_38_helpdesk_create_allowed(self):
        self.setUp_user_realms()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE, realm=self.realm1)
        result = self.request_assert_200('/container/init', {"type": "generic", "realm": self.realm1}, self.at)
        self.assertGreater(len(result["result"]["value"]["container_serial"]), 0)

        # If no realm is given, the container is created in the realm of the helpdesk user
        result = self.request_assert_200('/container/init', {"type": "generic"}, self.at)
        self.assertGreater(len(result["result"]["value"]["container_serial"]), 0)
        container_realms = get_container_realms(result["result"]["value"]["container_serial"])
        self.assertEqual(self.realm1, container_realms[0])
        delete_policy("policy")

    def test_39_helpdesk_create_denied(self):
        self.setUp_user_realm2()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE, realm=self.realm1)
        self.request_denied_assert_403('/container/init', {"type": "Smartphone", "realm": self.realm2},
                                       self.at)
        delete_policy("policy")

    def test_40_helpdesk_delete_allowed(self):
        self.setUp_user_realm2()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE, realm=[self.realm2, self.realm1])
        container_serial = self.create_container_for_user()
        self.request_assert_200(f"/container/{container_serial}", {}, self.at, method='DELETE')
        delete_policy("policy")

    def test_41_helpdesk_delete_denied(self):
        self.setUp_user_realm2()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE, realm=self.realm2)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}", {}, self.at, method='DELETE')
        delete_policy("policy")

    def test_42_helpdesk_description_allowed(self):
        self.setUp_user_realm2()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DESCRIPTION, realm=[self.realm1, self.realm2])
        container_serial, _ = init_container({"type": "generic", "realm": self.realm1})
        self.request_assert_200(f"/container/{container_serial}/description", {"description": "test"}, self.at,
                                method='POST')
        delete_policy("policy")

    def test_43_helpdesk_description_denied(self):
        self.setUp_user_realm2()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE, realm=self.realm2)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/description", {"description": "test"},
                                       self.at, method='POST')
        delete_policy("policy")

    def test_44_helpdesk_state_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_STATE, realm=self.realm1)
        container_serial = self.create_container_for_user()
        self.request_assert_200(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                self.at, method='POST')
        delete_policy("policy")

    def test_45_helpdesk_state_denied(self):
        self.setUp_user_realm2()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE, realm=self.realm2)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                       self.at, method='POST')
        delete_policy("policy")

    def test_46_helpdesk_add_token_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ADD_TOKEN, realm=self.realm1)
        container_serial = self.create_container_for_user()

        # Add single token
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()
        self.request_assert_200(f"/container/{container_serial}/add", {"serial": token_serial}, self.at,
                                method='POST')

        # add multiple tokens
        token2 = init_token({"genkey": "1", "realm": self.realm1})
        token3 = init_token({"genkey": "1", "realm": self.realm1})
        token_serials = ','.join([token2.get_serial(), token3.get_serial()])
        result = self.request_assert_200(f"/container/{container_serial}/addall", {"serial": token_serials}, self.at,
                                         method='POST')
        self.assertTrue(result["result"]["value"][token2.get_serial()])
        self.assertTrue(result["result"]["value"][token3.get_serial()])
        delete_policy("policy")

        # Add token to container during enrollment fails
        set_policy("policy", scope=SCOPE.ADMIN, action=[ACTION.CONTAINER_ADD_TOKEN, "enrollHOTP"], realm=self.realm1)
        result = self.request_assert_200("/token/init", {"type": "hotp", "realm": self.realm1, "genkey": 1,
                                                         "container_serial": container_serial}, self.at, method='POST')
        token_serial = result["detail"]["serial"]
        tokens = get_tokens_paginate(serial=token_serial)
        self.assertEqual(container_serial, tokens["tokens"][0]["container_serial"])

    def test_47_helpdesk_add_token_denied(self):
        self.setUp_user_realm2()
        # helpdesk of user realm realm2: container and token are both in realm1
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ADD_TOKEN, realm=self.realm2)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{container_serial}/add", {"serial": token_serial}, self.at,
                                       method='POST')
        delete_policy("policy")

        # helpdesk of userealm realm1: only token is in realm2
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ADD_TOKEN, realm=self.realm1)
        token = init_token({"genkey": "1", "realm": self.realm2})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{container_serial}/add", {"serial": token_serial}, self.at,
                                       method='POST')

        # same for adding multiple tokens
        token2 = init_token({"genkey": "1", "realm": self.realm2})
        token3 = init_token({"genkey": "1", "realm": self.realm1})
        token_serials = ','.join([token2.get_serial(), token3.get_serial()])
        result = self.request_assert_200(f"/container/{container_serial}/addall", {"serial": token_serials}, self.at,
                                         method='POST')
        self.assertFalse(result["result"]["value"][token2.get_serial()])
        self.assertTrue(result["result"]["value"][token3.get_serial()])

        delete_policy("policy")

        # Add token to container during enrollment fails
        set_policy("policy", scope=SCOPE.ADMIN, action=[ACTION.CONTAINER_ADD_TOKEN, "enrollHOTP"], realm=self.realm1)
        container_serial, _ = init_container({"type": "generic", "realm": self.realm2})
        result = self.request_assert_200("/token/init", {"type": "hotp", "realm": self.realm1, "genkey": 1,
                                                         "container_serial": container_serial}, self.at,
                                         method='POST')
        token_serial = result["detail"]["serial"]
        tokens = get_tokens_paginate(serial=token_serial)
        self.assertEqual("", tokens["tokens"][0]["container_serial"])

    def test_48_helpdesk_remove_token_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REMOVE_TOKEN, realm=self.realm1)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()

        # single token
        add_token_to_container(container_serial, token_serial, user_role='admin')
        result = self.request_assert_200(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at,
                                         method='POST')
        self.assertTrue(result["result"]["value"])

        # multiple tokens
        add_token_to_container(container_serial, token_serial, user_role='admin')
        token2 = init_token({"genkey": "1", "realm": self.realm1})
        add_token_to_container(container_serial, token2.get_serial(), user_role='admin')
        token_serials = ','.join([token_serial, token2.get_serial()])
        result = self.request_assert_200(f"/container/{container_serial}/removeall", {"serial": token_serials}, self.at,
                                         method='POST')
        self.assertTrue(result["result"]["value"][token_serial])
        self.assertTrue(result["result"]["value"][token2.get_serial()])
        delete_policy("policy")

    def test_49_helpdesk_remove_token_denied(self):
        self.setUp_user_realm2()

        # helpdesk of user realm realm2: container and token are both in realm1
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE, realm=self.realm2)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()
        add_token_to_container(container_serial, token_serial, user_role='admin')
        self.request_denied_assert_403(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at,
                                       method='POST')

        # helpdesk of userealm realm2: container in realm1 and token in realm 2
        token = init_token({"genkey": "1", "realm": self.realm2})
        token_serial = token.get_serial()
        add_token_to_container(container_serial, token_serial, user_role='admin')
        self.request_denied_assert_403(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at,
                                       method='POST')
        delete_policy("policy")

        # helpdesk of userealm realm1: container in realm1 and token in realm 2
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REMOVE_TOKEN, realm=self.realm1)
        self.request_denied_assert_403(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at,
                                       method='POST')

        # Same for multiple tokens
        token2 = init_token({"genkey": "1", "realm": self.realm2})
        add_token_to_container(container_serial, token2.get_serial(), user_role='admin')
        token3 = init_token({"genkey": "1", "realm": self.realm1})
        add_token_to_container(container_serial, token3.get_serial(), user_role='admin')
        token_serials = ','.join([token2.get_serial(), token3.get_serial()])
        result = self.request_assert_200(f"/container/{container_serial}/removeall", {"serial": token_serials}, self.at,
                                         method='POST')
        self.assertFalse(result["result"]["value"][token2.get_serial()])
        self.assertTrue(result["result"]["value"][token3.get_serial()])
        delete_policy("policy")

    def test_50_helpdesk_assign_user_allowed(self):
        # Allow to assign a user to a container without any realm
        self.setUp_user_realms()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ASSIGN_USER, realm=self.realm1)
        container_serial, _ = init_container({"type": "generic"})
        self.request_assert_200(f"/container/{container_serial}/assign",
                                {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_51_helpdesk_assign_user_denied(self):
        self.setUp_user_realm2()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE, realm=self.realm2)

        # helpdesk of user realm realm2: container in realm2, but user from realm1
        container_serial, _ = init_container({"type": "generic", "realm": self.realm2})
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)

        # helpdesk of user realm realm2: user from realm2, but container in realm1
        container_serial, _ = init_container({"type": "generic", "realm": self.realm1})
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": "realm2", "user": "root", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_52_helpdesk_remove_user_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_UNASSIGN_USER, realm=self.realm1)
        container_serial, _ = init_container({"type": "generic", "user": "hans", "realm": self.realm1})
        self.request_assert_200(f"/container/{container_serial}/unassign",
                                {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_53_helpdesk_remove_user_denied(self):
        self.setUp_user_realm2()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE, realm=self.realm2)
        container_serial, _ = init_container({"type": "generic", "user": "hans", "realm": self.realm1})
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)

        # container is additionally in realm2, but user is still from realm1
        add_container_realms(container_serial, ["realm2"], allowed_realms=None)
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_54_helpdesk_container_realms_allowed(self):
        self.setUp_user_realm2()
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REALMS, realm=[self.realm1, self.realm2])
        container_serial = self.create_container_for_user()
        self.request_assert_200(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)

        # Set realm for container without any realm
        container_serial, _ = init_container({"type": "generic"})
        self.request_assert_200(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)
        delete_policy("policy")

    def test_55_helpdesk_container_realms_denied(self):
        self.setUp_user_realm2()
        self.setUp_user_realm3()

        # helpdesk of user realm realm2: container in realm1
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REALMS, realm=self.realm2)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)

        # helpdesk of user realm realm2: container in realm1, set realm3
        self.request_denied_assert_403(f"/container/{container_serial}/realms", {"realms": "realm3"}, self.at)
        delete_policy("policy")

        # helpdesk of user realm realm1: container in realm1, set realm2
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_REALMS, realm=self.realm1)
        result = self.request_assert_200(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)
        self.assertFalse(result["result"]["value"]["realm2"])
        container = find_container_by_serial(container_serial)
        realms = [realm.name for realm in container.realms]
        self.assertEqual(1, len(realms))
        self.assertEqual("realm1", realms[0])

        # helpdesk of user realm realm1: container in realm1, set realm2 and realm1 (only realm1 allowed)
        result = self.request_assert_200(f"/container/{container_serial}/realms", {"realms": "realm2,realm1"}, self.at)
        self.assertFalse(result["result"]["value"]["realm2"])
        self.assertTrue(result["result"]["value"]["realm1"])

        # helpdesk of user realm realm1: container in realm1 and realm2, set realm1 (removes realm2 not allowed)
        add_container_realms(container_serial, ["realm1", "realm2"], allowed_realms=None)
        self.request_assert_200(f"/container/{container_serial}/realms", {"realms": "realm1"}, self.at)
        container = find_container_by_serial(container_serial)
        realms = [realm.name for realm in container.realms]
        self.assertEqual(2, len(realms))
        self.assertIn("realm1", realms)
        self.assertIn("realm2", realms)
        delete_policy("policy")

    def test_56_helpdesk_container_list_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_LIST, realm=self.realm1)
        self.request_assert_200('/container/', {}, self.at, 'GET')

        # container with token from another realm: reduce token info
        set_policy("policy2", scope=SCOPE.ADMIN, action=ACTION.TOKENLIST, realm=self.realm1)
        container_serial, _ = init_container({"type": "generic", "realm": self.realm1})
        token_1 = init_token({"genkey": 1, "realm": self.realm1})
        token_2 = init_token({"genkey": 1, "realm": self.realm2})
        add_token_to_container(container_serial, token_1.get_serial(), user_role='admin')
        add_token_to_container(container_serial, token_2.get_serial(), user_role='admin')
        result = self.request_assert_200('/container/', {"container_serial": container_serial}, self.at, 'GET')
        tokens = result["result"]["value"]["containers"][0]["tokens"]
        # first token: all information
        self.assertEqual(token_1.get_serial(), tokens[0]["serial"])
        self.assertEqual("hotp", tokens[0]["tokentype"])
        # second token: only serial
        self.assertEqual(token_2.get_serial(), tokens[1]["serial"])
        self.assertEqual(1, len(tokens[1].keys()))
        self.assertNotIn("tokentype", tokens[1].keys())

        delete_policy("policy")
        delete_policy("policy2")


class APIContainer(MyApiTestCase):
    FIREBASE_FILE = "tests/testdata/firebase-test.json"
    CLIENT_FILE = "tests/testdata/google-services.json"

    def request_assert_success(self, url, data: dict, auth_token, method='POST'):
        headers = {'Authorization': auth_token} if auth_token else {}
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data,
                                           headers=headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
            self.assertTrue(res.json["result"]["status"])
            return res.json

    def request_assert_error(self, status_code, url, data: dict, auth_token, method='POST'):
        headers = {'Authorization': auth_token} if auth_token else {}
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data,
                                           headers=headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(status_code, res.status_code, res.json)
            self.assertFalse(res.json["result"]["status"])
            return res.json

    def request_assert_405(self, url, data: dict, auth_token, method='POST'):
        headers = {'Authorization': auth_token} if auth_token else {}
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data,
                                           headers=headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(405, res.status_code, res.json)
            return res.json

    def request_assert_404_no_result(self, url, data: dict, auth_token, method='POST'):
        headers = {'Authorization': auth_token} if auth_token else {}
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data,
                                           headers=headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(404, res.status_code, res.json)

    def test_00_init_delete_container_success(self):
        # Init container
        payload = {"type": "Smartphone", "description": "test description!!"}
        res = self.request_assert_success('/container/init', payload, self.at, 'POST')
        cserial = res["result"]["value"]["container_serial"]
        self.assertTrue(len(cserial) > 1)

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
        result = self.request_assert_error(401, '/container/init', payload, None, 'POST')
        error = result["result"]["error"]
        self.assertEqual(4033, error["code"])
        self.assertEqual("Authentication failure. Missing Authorization header.", error["message"])

    def test_02_delete_container_fail(self):
        # Delete non-existing container
        result = self.request_assert_error(404, '/container/wrong_serial', {}, self.at, 'DELETE')
        error = result["result"]["error"]
        self.assertEqual(601, error["code"])
        self.assertEqual("Unable to find container with serial wrong_serial.", error["message"])

        # Call without serial
        self.request_assert_405('/container/', {}, self.at, 'DELETE')

    def test_03_assign_user_fail(self):
        # Arrange
        container_serial, _ = init_container({"type": "generic"})

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

    def test_04_assign_multiple_users_fails(self):
        # Arrange
        container_serial, _ = init_container({"type": "generic"})
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

    def test_05_assign_unassign_user_success(self):
        # Arrange
        container_serial, _ = init_container({"type": "generic"})
        self.setUp_user_realms()
        payload = {"user": "hans", "realm": self.realm1}

        # Assign with user and realm
        result = self.request_assert_success(f'/container/{container_serial}/assign', payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        # Unassign
        result = self.request_assert_success(f'/container/{container_serial}/unassign',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

    def test_06_assign_without_realm(self):
        # If no realm is passed the default realm is set in before_request
        # Arrange
        container_serial, _ = init_container({"type": "generic"})
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
        container_serial, _ = init_container({"type": "generic"})
        payload = {"user": "root"}
        result = self.request_assert_error(400, f'/container/{container_serial}/assign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(904, error["code"])
        self.assertEqual("ERR904: The user can not be found in any resolver in this realm!", error["message"])

    def test_07_unassign_fail(self):
        # Arrange
        container_serial, _ = init_container({"type": "generic"})

        # Unassign without realm
        payload = {"user": "root"}
        result = self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(904, error["code"])
        self.assertEqual("ERR904: The user can not be found in any resolver in this realm!", error["message"])

        # Unassign user with non-existing realm
        payload = {"user": "hans", "realm": "non_existing"}
        result = self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(904, error["code"])
        self.assertEqual("ERR904: The user can not be found in any resolver in this realm!", error["message"])

        # Unassign without user
        self.setUp_user_realm2()
        payload = {"realm": self.realm2}
        result = self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                           payload, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing parameter: 'user'", error["message"])

        # Unassign not assigned user
        payload = {"user": "cornelius", "realm": self.realm2}
        result = self.request_assert_success(f'/container/{container_serial}/unassign',
                                             payload, self.at, 'POST')
        self.assertFalse(result["result"]["value"])

    def test_08_set_realms_success(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial, _ = init_container({"type": "generic"})

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

        # Automatically add the user realms
        container_serial, _ = init_container({"type": "generic", "user": "hans", "realm": self.realm1})
        payload = {"realms": self.realm2}
        result = self.request_assert_success(f'/container/{container_serial}/realms', payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"][self.realm1])
        self.assertTrue(result["result"]["value"][self.realm2])

    def test_09_set_realms_fail(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial, _ = init_container({"type": "generic"})

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

    def test_10_set_description_success(self):
        # Arrange
        container_serial, _ = init_container({"type": "generic", "description": "test container"})

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

    def test_11_set_description_fail(self):
        # Arrange
        container_serial, _ = init_container({"type": "generic", "description": "test container"})

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

    def test_12_set_states_success(self):
        # Arrange
        container_serial, _ = init_container({"type": "generic", "description": "test container"})

        # Set states
        payload = {"states": "active,damaged,lost"}
        result = self.request_assert_success(f'/container/{container_serial}/states',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])
        self.assertTrue(result["result"]["value"]["active"])
        self.assertTrue(result["result"]["value"]["damaged"])
        self.assertTrue(result["result"]["value"]["lost"])

    def test_13_set_states_fail(self):
        # Arrange
        container_serial, _ = init_container({"type": "generic", "description": "test container"})

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

    def test_14_set_container_info_success(self):
        # Arrange
        container_serial, _ = init_container({"type": "generic", "description": "test container"})

        # Set info
        self.request_assert_success(f'/container/{container_serial}/info/key1',
                                    {"value": "value1"}, self.at, 'POST')

    def test_15_set_container_info_fail(self):
        # Arrange
        container_serial, _ = init_container({"type": "generic"})

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

    def test_17_add_remove_token_success(self):
        # Arrange
        container_serial, _ = init_container({"type": "generic"})
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

    def test_18_add_token_fail(self):
        # Arrange
        container_serial, _ = init_container({"type": "generic"})
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

    def test_19_remove_token_fail(self):
        # Arrange
        container_serial, _ = init_container({"type": "generic"})
        hotp_01 = init_token({"genkey": "1"})
        hotp_01_serial = hotp_01.get_serial()
        add_token_to_container(container_serial, hotp_01_serial, user_role="admin")

        # Remove token without serial
        result = self.request_assert_error(400, f'/container/{container_serial}/remove',
                                           {}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing parameter: 'serial'", error["message"])

        # Remove token without container serial
        self.request_assert_405('/container/remove', {"serial": hotp_01_serial}, self.at, 'POST')

    def test_20_get_state_types(self):
        result = self.request_assert_success('/container/statetypes', {}, self.at, 'GET')
        self.assertTrue(result["result"]["value"])
        self.assertIn("active", result["result"]["value"].keys())
        self.assertIn("disabled", result["result"]["value"]["active"])
        self.assertIn("lost", result["result"]["value"].keys())

    def test_21_get_types(self):
        result = self.request_assert_success('/container/types', {}, self.at, 'GET')
        self.assertTrue(result["result"]["value"])
        # Check that all container types are included
        self.assertIn("smartphone", result["result"]["value"])
        self.assertIn("generic", result["result"]["value"])
        self.assertIn("yubikey", result["result"]["value"])
        # Check that all properties are set
        self.assertIn("description", result["result"]["value"]["generic"])
        self.assertIn("token_types", result["result"]["value"]["generic"])

    def test_22_get_all_containers_paginate(self):
        # Arrange
        # Create containers
        types = ["Smartphone", "generic", "Yubikey", "Smartphone", "generic", "Yubikey"]
        container_serials = []
        for t in types:
            serial, _ = init_container({"type": t, "description": "test container"})
            container_serials.append(serial)
        # Add token to container 1
        container = find_container_by_serial(container_serials[1])
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        add_token_to_container(container_serials[1], token_serial, user_role="admin")
        # Assign user to container 1
        self.setUp_user_realms()
        user_hans = User(login="hans", realm=self.realm1)
        container.add_user(user_hans)
        # Add second realm
        self.setUp_user_realm2()
        container.set_realms([self.realm2], add=True)
        # Add info
        container.add_container_info("key1", "value1")

        # Filter for type
        result = self.request_assert_success('/container/',
                                             {"type": "generic", "pagesize": 15},
                                             self.at, 'GET')
        for container in result["result"]["value"]["containers"]:
            self.assertEqual(container["type"], "generic")

        # Filter for token serial
        result = self.request_assert_success('/container/',
                                             {"token_serial": token_serial, "pagesize": 15},
                                             self.at, 'GET')
        self.assertTrue(container_serials[1], result["result"]["value"]["containers"][0]["serial"])
        self.assertEqual(result["result"]["value"]["count"], 1)

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

    def test_23_get_all_containers_paginate_invalid_params(self):
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

    def mock_smartphone_register_params(self, nonce, registration_time, registration_url, serial, passphrase=None):
        message = f"{nonce}|{registration_time}|{registration_url}|{serial}"
        if passphrase:
            message += f"|{passphrase}"

        public_key_smph, private_key_smph = generate_keypair_ecc("secp384r1")
        pub_key_smph_str, _ = ecc_key_pair_to_b64url_str(public_key=public_key_smph)

        signature, hash_algorithm = sign_ecc(message.encode("utf-8"), private_key_smph, "sha256")

        params = {"signature": base64.b64encode(signature), "public_client_key": pub_key_smph_str,
                  "passphrase": passphrase,
                  "message": message, "container_serial": serial}

        return params, private_key_smph

    def test_24_register_smartphone_success(self):
        set_policy("policy", scope=SCOPE.ENROLL, action={ACTION.PI_SERVER_URL: "http://localhost/",
                                                         ACTION.CONTAINER_REGISTRATION_TTL: 24})
        smartphone_serial, _ = init_container({"type": "smartphone"})
        data = {"container_serial": smartphone_serial,
                "passphrase_ad": False,
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
        # Check if the url contains all relevant data
        qr_url = init_response_data["container_url"]["value"]
        self.assertIn(f"pia://container/{smartphone_serial}", qr_url)
        self.assertIn("issuer=privacyIDEA", qr_url)
        self.assertIn("ttl=24", qr_url)
        self.assertIn("nonce=", qr_url)
        self.assertIn("time=", qr_url)
        self.assertIn("url=http://localhost/container/register/finalize", qr_url)
        self.assertIn(f"serial={smartphone_serial}", qr_url)
        self.assertIn("key_algorithm=", qr_url)
        self.assertIn("hash_algorithm", qr_url)
        self.assertIn("passphrase=Enter%20your%20passphrase", qr_url)

        # Finalize
        params, priv_key_sig_smph = self.mock_smartphone_register_params(serial=smartphone_serial,
                                                                         registration_url="http://localhost/container/register/finalize",
                                                                         nonce=init_response_data["nonce"],
                                                                         registration_time=init_response_data[
                                                                             "time_stamp"],
                                                                         passphrase="top_secret")
        result = self.request_assert_success('container/register/finalize',
                                             params,
                                             None, 'POST')

        # Check if the response contains the expected values
        self.assertIn("public_server_key", result["result"]["value"])
        sync_url = f"http://localhost/container/sync/{smartphone_serial}/init"
        self.assertEqual(sync_url, result["result"]["value"]["container_sync_url"])

        delete_policy("policy")

        return smartphone_serial, priv_key_sig_smph

    def test_25_register_terminate_success(self):
        smartphone_serial, _ = self.test_24_register_smartphone_success()
        # Terminate
        self.request_assert_success(f'container/register/{smartphone_serial}/terminate',
                                    {},
                                    self.at, 'DELETE')

    def test_25_register_terminate_client_success(self):
        smartphone_serial, priv_key_client = self.test_24_register_smartphone_success()
        nonce = geturandom(20, hex=True)
        time = datetime.now(timezone.utc).isoformat()
        message = f"nonce|time"
        signature = sign_ecc(message.encode("utf-8"), priv_key_client, "sha256")

        # Terminate
        data = {"message": message, "signature": signature}
        self.request_assert_success(f'container/register/{smartphone_serial}/terminate/client',
                                    data,
                                    self.at, 'DELETE')

    def test_26_register_init_fail(self):
        # Policy with server url not defined
        container_serial, _ = init_container({"type": "smartphone"})
        result = self.request_assert_error(403, 'container/register/initialize',
                                           {"container_serial": container_serial}, self.at, 'POST')
        error = result["result"]["error"]
        self.assertEqual(303, error["code"])

        # Define policy with server url
        set_policy("policy", scope=SCOPE.ENROLL, action={ACTION.PI_SERVER_URL: "http://localhost/"})

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

    def test_27_register_finalize_fail(self):
        # Policy with server url disabled defined
        set_policy("policy", scope=SCOPE.ENROLL, action={ACTION.PI_SERVER_URL: "http://localhost/"}, active=False)
        container_serial, _ = init_container({"type": "smartphone"})
        result = self.request_assert_error(403, 'container/register/finalize',
                                           {"container_serial": container_serial}, None, 'POST')
        error = result["result"]["error"]
        self.assertEqual(303, error["code"])

        set_policy("policy", scope=SCOPE.ENROLL, action={ACTION.PI_SERVER_URL: "http://localhost/"}, active=True)

        # Missing container serial
        result = self.request_assert_error(400, 'container/register/finalize',
                                           {}, None, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])
        self.assertEqual("ERR905: Missing parameter: 'container_serial'", error["message"])

        # Invalid container serial
        result = self.request_assert_error(404, 'container/register/finalize',
                                           {"container_serial": "invalid_serial"}, None, 'POST')
        error = result["result"]["error"]
        self.assertEqual(601, error["code"])  # ResourceNotFound

        delete_policy("policy")

    def test_27_register_twice_fails(self):
        # register container successfully
        set_policy("policy", scope=SCOPE.ENROLL, action={ACTION.PI_SERVER_URL: "http://test/",
                                                         ACTION.CONTAINER_REGISTRATION_TTL: 24})
        smartphone_serial, _ = init_container({"type": "smartphone"})
        data = {"container_serial": smartphone_serial,
                "passphrase_ad": False,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}

        # Initialize
        result = self.request_assert_success('container/register/initialize',
                                             data,
                                             self.at, 'POST')
        init_response_data = result["result"]["value"]

        # Finalize
        params, priv_key_sig_smph = self.mock_smartphone_register_params(serial=smartphone_serial,
                                                                         registration_url="http://test/container/register/finalize",
                                                                         nonce=init_response_data["nonce"],
                                                                         registration_time=init_response_data[
                                                                             "time_stamp"],
                                                                         passphrase="top_secret")
        self.request_assert_success('container/register/finalize',
                                    params,
                                    None, 'POST')

        # try register second time with same data
        self.request_assert_error(400, 'container/register/finalize',
                                  params,
                                  None, 'POST')

        delete_policy("policy")

    def test_28_register_terminate_fail(self):
        set_policy("policy", scope=SCOPE.ENROLL, action={ACTION.PI_SERVER_URL: "http://localhost/"})

        # Invalid container serial
        result = self.request_assert_error(404, f'container/register/invalidSerial/terminate',
                                           {}, self.at, 'DELETE')
        error = result["result"]["error"]
        self.assertEqual(601, error["code"])  # ResourceNotFound

        delete_policy("policy")

    def mock_smartphone_sync(self, params, serial, private_key_sig_smph):
        nonce = params["nonce"]
        time_stamp = params["time_stamp"]
        scope = params["container_sync_url"]

        public_key_enc_smph, private_enc_key_smph = generate_keypair_ecc("x25519")
        pub_key_enc_smph_str = base64.urlsafe_b64encode(public_key_enc_smph.public_bytes_raw()).decode('utf-8')

        container_dict = json.dumps({"serial": serial, "type": "smartphone"})

        message = f"{nonce}|{time_stamp}|{serial}|{scope}|{pub_key_enc_smph_str}|{container_dict}"
        signature, hash_algorithm = sign_ecc(message.encode("utf-8"), private_key_sig_smph, "sha256")

        params = {"signature": base64.b64encode(signature), "public_enc_key_client": pub_key_enc_smph_str,
                  "container_dict_client": container_dict}
        return params, private_enc_key_smph

    def test_29_sync_init_success(self):
        set_policy("policy", scope=SCOPE.ENROLL, action={ACTION.PI_SERVER_URL: "http://localhost/"})
        smartphone_serial, _ = init_container({"type": "smartphone"})

        result = self.request_assert_success(f'container/sync/{smartphone_serial}/init',
                                             {}, None, 'GET')
        result_entries = result["result"]["value"].keys()
        self.assertIn("nonce", result_entries)
        self.assertIn("time_stamp", result_entries)
        self.assertIn("key_algorithm", result_entries)
        self.assertIn("container_sync_url", result_entries)

        delete_policy("policy")

    def test_30_sync_finalize_success(self):
        # Registration
        smartphone_serial, priv_key_smph = self.test_24_register_smartphone_success()

        set_policy("policy", scope=SCOPE.ENROLL, action={ACTION.PI_SERVER_URL: "http://localhost/"})

        # Init
        result = self.request_assert_success(f'container/sync/{smartphone_serial}/init',
                                             {}, None, 'GET')

        params, _ = self.mock_smartphone_sync(result["result"]["value"], smartphone_serial, priv_key_smph)

        # Finalize
        result = self.request_assert_success(f'container/sync/{smartphone_serial}/finalize',
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("container_sync_url", result_entries)

        delete_policy("policy")

    def test_31_finalize_synchronize_smartphone_with_push_fb(self):
        # Registration
        smartphone_serial, priv_key_smph = self.test_24_register_smartphone_success()
        smartphone = find_container_by_serial(smartphone_serial)

        # tokens
        push_fb = init_token({"genkey": "1", "type": "push"})
        smartphone.add_token(push_fb)

        # Firebase config
        fb_config = {FIREBASE_CONFIG.REGISTRATION_URL: "http://test/ttype/push",
                     FIREBASE_CONFIG.JSON_CONFIG: self.FIREBASE_FILE,
                     FIREBASE_CONFIG.TTL: 10}
        set_smsgateway("fb1", 'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider', "myFB",
                       fb_config)
        set_policy("push", scope=SCOPE.ENROLL, action={PUSH_ACTION.FIREBASE_CONFIG: "fb1",
                                                       PUSH_ACTION.REGISTRATION_URL: "http://test/ttype/push"})

        set_policy("policy", scope=SCOPE.ENROLL, action={ACTION.PI_SERVER_URL: "http://test/"})

        # Init
        result = self.request_assert_success(f'container/sync/{smartphone_serial}/init',
                                             {}, None, 'GET')

        params, private_enc_key_smph = self.mock_smartphone_sync(result["result"]["value"], smartphone_serial,
                                                                 priv_key_smph)

        # Finalize
        result = self.request_assert_success(f'container/sync/{smartphone_serial}/finalize',
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("container_sync_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = private_enc_key_smph.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_ecc(container_dict_server_enc, shared_key, "AES",
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        tokens = tokens_dict["add"]
        self.assertEqual(1, len(tokens))
        self.assertIn("otpauth://pipush/", tokens[0])

        delete_policy("policy")
        delete_policy("push")

    def test_32_finalize_synchronize_smartphone_with_push_poll_only(self):
        # Registration
        smartphone_serial, priv_key_smph = self.test_24_register_smartphone_success()
        smartphone = find_container_by_serial(smartphone_serial)

        # tokens
        push_fb = init_token({"genkey": "1", "type": "push"})
        smartphone.add_token(push_fb)

        # policies: push config is spread over multiple policies
        set_policy("push_1", scope=SCOPE.ENROLL, action={PUSH_ACTION.FIREBASE_CONFIG: "poll only"})
        set_policy("push_2", scope=SCOPE.ENROLL, action={PUSH_ACTION.REGISTRATION_URL: "http://test/ttype/push"})

        set_policy("policy", scope=SCOPE.ENROLL, action={ACTION.PI_SERVER_URL: "http://test/"})

        # Init
        result = self.request_assert_success(f'container/sync/{smartphone_serial}/init',
                                             {}, None, 'GET')

        params, private_enc_key_smph = self.mock_smartphone_sync(result["result"]["value"], smartphone_serial,
                                                                 priv_key_smph)

        # Finalize
        result = self.request_assert_success(f'container/sync/{smartphone_serial}/finalize',
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("container_sync_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = private_enc_key_smph.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_ecc(container_dict_server_enc, shared_key, "AES",
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        tokens = tokens_dict["add"]
        self.assertEqual(1, len(tokens))
        self.assertIn("otpauth://pipush/", tokens[0])

        delete_policy("policy")
        delete_policy("push_1")
        delete_policy("push_2")

    def test_33_finalize_synchronize_smartphone_missing_token_enroll_policies(self):
        # Registration
        smartphone_serial, priv_key_smph = self.test_24_register_smartphone_success()
        smartphone = find_container_by_serial(smartphone_serial)

        # tokens
        push_fb = init_token({"genkey": "1", "type": "push"})
        smartphone.add_token(push_fb)
        hotp = init_token({"genkey": "1", "type": "hotp"})
        smartphone.add_token(hotp)

        # Init
        set_policy("policy", scope=SCOPE.ENROLL, action={ACTION.PI_SERVER_URL: "http://test/"})
        result = self.request_assert_success(f'container/sync/{smartphone_serial}/init',
                                             {}, None, 'GET')

        params, private_enc_key_smph = self.mock_smartphone_sync(result["result"]["value"], smartphone_serial,
                                                                 priv_key_smph)

        # Finalize with missing push config
        result = self.request_assert_success(f'container/sync/{smartphone_serial}/finalize',
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("container_sync_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = private_enc_key_smph.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_ecc(container_dict_server_enc, shared_key, "AES",
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        tokens = tokens_dict["add"]
        # Only hotp token to be added
        self.assertEqual(1, len(tokens))
        self.assertIn("otpauth://hotp/", tokens[0])

        delete_policy('policy')

    def test_34_finalize_synchronize_smartphone_token_policies(self):
        # Registration
        smartphone_serial, priv_key_smph = self.test_24_register_smartphone_success()
        smartphone = find_container_by_serial(smartphone_serial)

        # set label, issuer and require pin policies
        set_policy('token_enroll', scope=SCOPE.ENROLL,
                   action={ACTION.TOKENLABEL: '{user}',
                           ACTION.TOKENISSUER: '{realm}',
                           'hotp_' + ACTION.FORCE_APP_PIN: True})

        # Get initial enroll url
        self.setUp_user_realms()
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

        # Init
        set_policy("policy", scope=SCOPE.ENROLL, action={ACTION.PI_SERVER_URL: "http://test/"})
        result = self.request_assert_success(f'container/sync/{smartphone_serial}/init',
                                             {}, None, 'GET')

        params, private_enc_key_smph = self.mock_smartphone_sync(result["result"]["value"], smartphone_serial,
                                                                 priv_key_smph)

        # Finalize
        result = self.request_assert_success(f'container/sync/{smartphone_serial}/finalize',
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("container_sync_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = private_enc_key_smph.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_ecc(container_dict_server_enc, shared_key, "AES",
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        tokens = tokens_dict["add"]
        # Only hotp token to be added
        self.assertEqual(1, len(tokens))
        self.assertEqual(initial_enroll_url, tokens[0])

        delete_policy('policy')
        delete_policy('token_enroll')

    def test_35_sync_finalize_fail(self):
        smartphone_serial, _ = init_container({"type": "smartphone"})

        # missing policy
        result = self.request_assert_error(403, f'container/sync/{smartphone_serial}/finalize',
                                           {}, None, 'POST')
        error = result["result"]["error"]
        self.assertEqual(303, error["code"])

        set_policy("policy", scope=SCOPE.ENROLL, action={ACTION.PI_SERVER_URL: "http://localhost/"})

        # missing input parameters
        params = {"public_enc_key_client": "123"}
        result = self.request_assert_error(400, f'container/sync/{smartphone_serial}/finalize',
                                           params, None, 'POST')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])

        # missing registration
        public_key_smph, priv_key_smph = generate_keypair_ecc("secp384r1")
        smartphone_serial, _ = init_container({"type": "smartphone"})
        set_policy("policy", scope=SCOPE.ENROLL, action={ACTION.PI_SERVER_URL: "http://localhost/"})
        # Init
        result = self.request_assert_success(f'container/sync/{smartphone_serial}/init',
                                             {}, None, 'GET')
        params, _ = self.mock_smartphone_sync(result["result"]["value"], smartphone_serial, priv_key_smph)

        # Finalize
        result = self.request_assert_error(400, f'container/sync/{smartphone_serial}/finalize',
                                           params, None, 'POST')
        self.assertEqual(10, result["result"]["error"]["code"])

        delete_policy("policy")

    def test_36_get_class_options_all(self):
        result = self.request_assert_success('/container/classoptions', {}, self.at, 'GET')
        result = result["result"]["value"]

        self.assertIn("generic", result)

        self.assertIn("smartphone", result)
        smartphone_options = result["smartphone"]
        smartphone_required_keys = [SmartphoneOptions.KEY_ALGORITHM, SmartphoneOptions.ENCRYPT_KEY_ALGORITHM,
                                    SmartphoneOptions.HASH_ALGORITHM, SmartphoneOptions.ENCRYPT_ALGORITHM,
                                    SmartphoneOptions.ENCRYPT_MODE, SmartphoneOptions.FORCE_BIOMETRIC,
                                    SmartphoneOptions.ALLOW_ROLLOVER]
        for key in smartphone_required_keys:
            self.assertIn(key, smartphone_options)

        self.assertIn("yubikey", result)
        yubikey_options = result["yubikey"]
        self.assertIn(YubikeyOptions.PIN_POLICY, yubikey_options)

    def test_37_get_class_options_smartphone(self):
        result = self.request_assert_success('/container/classoptions', {"container_type": "smartphone"}, self.at,
                                             'GET')
        result = result["result"]["value"]

        self.assertNotIn("generic", result)
        self.assertNotIn("yubikey", result)

        self.assertIn("smartphone", result)
        smartphone_options = result["smartphone"]
        smartphone_required_keys = [SmartphoneOptions.KEY_ALGORITHM, SmartphoneOptions.ENCRYPT_KEY_ALGORITHM,
                                    SmartphoneOptions.HASH_ALGORITHM, SmartphoneOptions.ENCRYPT_ALGORITHM,
                                    SmartphoneOptions.ENCRYPT_MODE, SmartphoneOptions.FORCE_BIOMETRIC,
                                    SmartphoneOptions.ALLOW_ROLLOVER]
        for key in smartphone_required_keys:
            self.assertIn(key, smartphone_options)

    def test_38_get_class_options_invalid_type(self):
        result = self.request_assert_error(400, '/container/classoptions',
                                           {"container_type": "invalid"}, self.at,
                                           'GET')
        error = result["result"]["error"]
        self.assertEqual(905, error["code"])


class APIContainerTemplate(MyApiTestCase):

    def request_assert_success(self, url, data: dict, auth_token, method='POST'):
        headers = {'Authorization': auth_token} if auth_token else {}
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data,
                                           headers=headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
            self.assertTrue(res.json["result"]["status"])
            return res.json

    def request_assert_error(self, status_code, url, data: dict, auth_token, method='POST'):
        headers = {'Authorization': auth_token} if auth_token else {}
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data,
                                           headers=headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(status_code, res.status_code, res.json)
            self.assertFalse(res.json["result"]["status"])
            return res.json

    def request_assert_405(self, url, data: dict, auth_token, method='POST'):
        headers = {'Authorization': auth_token} if auth_token else {}
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data,
                                           headers=headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(405, res.status_code, res.json)
            return res.json

    def request_assert_404_no_result(self, url, data: dict, auth_token, method='POST'):
        headers = {'Authorization': auth_token} if auth_token else {}
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data,
                                           headers=headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(404, res.status_code, res.json)

    def test_01_create_delete_template_success(self):
        template_name = "test"
        # Create template without tokens
        data = json.dumps({"template_options": {"tokens": []}})
        result = self.request_assert_success(f'/container/smartphone/template/{template_name}',
                                             data, self.at, 'POST')
        self.assertGreater(result["result"]["value"], 0)

        # Delete template
        result = self.request_assert_success(f'/container/template/{template_name}',
                                             {}, self.at, 'DELETE')
        self.assertTrue(result["result"]["value"])

    def test_02_create_template_fail(self):
        # Create template without name
        self.request_assert_404_no_result(f'/container/smartphone/template',
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
        self.assertEqual(template_id, result["result"]["value"])

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

        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))
        container_template = container.template
        self.assertEqual(template_params["name"], container_template.name)

        template = get_template_obj(template_params["name"])
        template.delete()

    def test_07_create_container_with_template_no_tokens(self):
        # Create a template with no tokens
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {}}

        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(0, len(tokens))

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
        # Create a template
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        # Create a container from the template
        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))

    def test_09_create_container_with_template_push(self):
        # PUSH (poll-only)
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "push", "genkey": True}]}}

        set_policy("push_1", scope=SCOPE.ENROLL, action={PUSH_ACTION.FIREBASE_CONFIG: "poll only"})
        set_policy("push_2", scope=SCOPE.ENROLL, action={PUSH_ACTION.REGISTRATION_URL: "http://test/ttype/push"})

        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertEqual("push", tokens[0].get_type())

        delete_policy("push_1")
        delete_policy("push_2")

    def test_10_create_container_with_template_max_tokens(self):
        # Limit number of tokens per user
        set_policy("max_token", scope=SCOPE.ENROLL, action={ACTION.MAXTOKENUSER: 2})
        self.setUp_user_realms()
        hans = User(login="hans", realm=self.realm1)

        # First hotp token of hans
        init_token({"genkey": "1", "type": "hotp"}, user=hans)

        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True, "user": True}]}}
        request_params = json.dumps({"type": "smartphone", "user": "hans", "realm": self.realm1,
                                     "template": template_params})

        # second hotp token of hans can be created with the template
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertEqual("hotp", tokens[0].get_type())

        # third hotp token of hans can NOT be created
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(0, len(tokens))

        delete_policy("max_token")

    def test_11_create_container_with_template_otp_pin(self):
        # Set otp pin policy
        set_policy("otp_pin", scope=SCOPE.ADMIN, action={ACTION.OTPPINMAXLEN: 6, ACTION.OTPPINMINLEN: 2})
        # Set admin policies
        set_policy("admin", scope=SCOPE.ADMIN, action={ACTION.CONTAINER_CREATE: True, "enrollHOTP": True})

        # pin according to the policies
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

        delete_policy("otp_pin")
        delete_policy("admin")

    def test_12_get_template_options(self):
        result = self.request_assert_success('/container/template/options', {}, self.at, 'GET')
        list_keys = list(result["result"]["value"].keys())

        generic_keys = list(result["result"]["value"]["generic"].keys())
        self.assertIn("generic", list_keys)
        self.assertIn("tokens", generic_keys)
        self.assertIn("user_modifiable", generic_keys)

        smph_keys = list(result["result"]["value"]["smartphone"].keys())
        self.assertIn("smartphone", list_keys)
        self.assertIn("tokens", smph_keys)
        self.assertIn("user_modifiable", smph_keys)
        self.assertIn("allow_client_rollover", smph_keys)
        self.assertIn("force_biometric", smph_keys)

        yubikey_keys = list(result["result"]["value"]["yubikey"].keys())
        self.assertIn("yubikey", list_keys)
        self.assertIn("tokens", smph_keys)
        self.assertIn("user_modifiable", smph_keys)
        self.assertIn("pin_policy", yubikey_keys)
