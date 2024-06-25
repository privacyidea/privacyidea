from privacyidea.lib.container import init_container, find_container_by_serial
from privacyidea.lib.policy import set_policy, SCOPE, ACTION, delete_policy
from privacyidea.lib.realm import set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.token import init_token
from privacyidea.lib.user import User
from privacyidea.models import TokenContainer
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
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_CREATE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}", {}, self.at_user, method='DELETE')
        delete_policy("policy")

    def test_05_user_description_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DESCRIPTION)
        container_serial = self.create_container_for_user()
        self.request_assert_200(f"/container/{container_serial}/description", {"description": "test"}, self.at_user,
                                method='POST')
        delete_policy("policy")

    def test_06_user_description_denied(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/description", {"description": "test"},
                                       self.at_user,
                                       method='POST')
        delete_policy("policy")

    def test_07_user_state_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_STATE)
        container_serial = self.create_container_for_user()
        self.request_assert_200(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                self.at_user,
                                method='POST')
        delete_policy("policy")

    def test_08_user_state_denied(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                       self.at_user,
                                       method='POST')
        delete_policy("policy")

    def test_09_user_add_token_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_ADD_TOKEN)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        json = self.request_assert_200(f"/container/{container_serial}/add", {"serial": token_serial}, self.at_user,
                                       method='POST')
        self.assertTrue(json["result"]["value"][token_serial])
        delete_policy("policy")

    def test_10_user_add_token_denied(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{container_serial}/add", {"serial": token_serial}, self.at_user,
                                       method='POST')
        delete_policy("policy")

    def test_11_user_remove_token_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_REMOVE_TOKEN)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        container = find_container_by_serial(container_serial)
        container.add_token(token)
        json = self.request_assert_200(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at_user,
                                       method='POST')
        self.assertTrue(json["result"]["value"][token_serial])
        delete_policy("policy")

    def test_12_user_remove_token_denied(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1"})
        token_serial = token.get_serial()
        container = find_container_by_serial(container_serial)
        container.add_token(token)
        self.request_denied_assert_403(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at_user,
                                       method='POST')
        delete_policy("policy")

    def test_13_user_assign_user_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_ASSIGN_USER)
        container_serial = self.create_container_for_user()
        self.request_assert_200(f"/container/{container_serial}/assign", {"realm": "realm1", "user": "root"},
                                self.at_user)
        delete_policy("policy")

    def test_14_user_assign_user_denied(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/assign", {"realm": "realm1", "user": "root"},
                                       self.at_user)
        delete_policy("policy")

    def test_15_user_remove_user_allowed(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_UNASSIGN_USER)
        container_serial = self.create_container_for_user()
        user = User(login="root", realm=self.realm1, resolver=self.resolvername1)
        container = find_container_by_serial(container_serial)
        container.add_user(user)
        self.request_assert_200(f"/container/{container_serial}/unassign", {"realm": "realm1", "user": "root"},
                                self.at_user)
        delete_policy("policy")

    def test_16_user_remove_user_denied(self):
        set_policy("policy", scope=SCOPE.USER, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        user = User(login="root", realm=self.realm1, resolver=self.resolvername1)
        container = find_container_by_serial(container_serial)
        container.add_user(user)
        self.request_denied_assert_403(f"/container/{container_serial}/unassign", {"realm": "realm1", "user": "root"},
                                       self.at_user)
        delete_policy("policy")

    def test_17_admin_create_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_CREATE)
        json = self.request_assert_200('/container/init', {"type": "generic"}, self.at)
        self.assertGreater(len(json["result"]["value"]["container_serial"]), 0)
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
        json = self.request_assert_200(f"/container/{container_serial}/add", {"serial": token_serial}, self.at,
                                       method='POST')
        self.assertTrue(json["result"]["value"][token_serial])
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
        json = self.request_assert_200(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at,
                                       method='POST')
        self.assertTrue(json["result"]["value"][token_serial])
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
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_ASSIGN_USER)
        container_serial = self.create_container_for_user()
        self.request_assert_200(f"/container/{container_serial}/assign",
                                {"realm": "realm1", "user": "root", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_30_admin_assign_user_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": "realm1", "user": "root", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_31_admin_remove_user_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_UNASSIGN_USER)
        container_serial = self.create_container_for_user()
        user = User(login="root", realm=self.realm1, resolver=self.resolvername1)
        container = find_container_by_serial(container_serial)
        container.add_user(user)
        self.request_assert_200(f"/container/{container_serial}/unassign",
                                {"realm": "realm1", "user": "root", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_32_admin_remove_user_denied(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=ACTION.CONTAINER_DELETE)
        container_serial = self.create_container_for_user()
        user = User(login="root", realm=self.realm1, resolver=self.resolvername1)
        container = find_container_by_serial(container_serial)
        container.add_user(user)
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


class APIContainer(MyApiTestCase):

    def test_00_init_delete_container(self):
        payload = {"type": "Smartphone", "description": "test description!!"}
        with self.app.test_request_context('/container/init',
                                           method='POST',
                                           data=payload,
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"])
            cserial = result["value"]["container_serial"]
            self.assertTrue(len(cserial) > 1)
        # Delete the container
        with self.app.test_request_context(f"container/{cserial}", method='DELETE', headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"])

    def test_01_init_container_fail(self):
        payload = {"type": "wrongType", "description": "test description!!"}
        with self.app.test_request_context('/container/init',
                                           method='POST',
                                           data=payload,
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            error = res.json["result"]["error"]
            error_code = error["code"]
            error_msg = error["message"]
            self.assertEqual(404, error_code)
            self.assertEqual("ERR404: Type 'wrongType' is not a valid type!", error_msg)
            self.assertFalse(res.json["result"]["status"])

    def test_04_get_all_containers_paginate(self):
        types = ["Smartphone", "generic", "Yubikey", "Smartphone", "generic", "Yubikey"]
        container_serials = []
        for t in types:
            serial = init_container({"type": t, "description": "test container"})
            container_serials.append(serial)

        # Filter for container serial
        with self.app.test_request_context('/container/',
                                           method='GET',
                                           data={"container_serial": container_serials[3], "pagesize": 15},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            containerdata = res.json["result"]["value"]
            self.assertEqual(containerdata["count"], 1)
            self.assertEqual(containerdata["containers"][0]["serial"], container_serials[3])

        # filter for type
        with self.app.test_request_context('/container/',
                                           method='GET',
                                           data={"type": "generic", "pagesize": 15},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            containerdata = res.json["result"]["value"]
            count = 0
            for container in containerdata["containers"]:
                self.assertEqual(container["type"], "generic")
                count += 1
            self.assertEqual(containerdata["count"], count)

        # Assign token
        tokens = []
        params = {"genkey": "1"}
        for i in range(3):
            t = init_token(params)
            tokens.append(t)
        token_serials = [t.get_serial() for t in tokens]

        for serial in container_serials[2:4]:
            container = find_container_by_serial(serial)
            for token in tokens:
                container.add_token(token)

        # Filter for token serial
        with self.app.test_request_context('/container/',
                                           method='GET',
                                           data={'token_serial': token_serials[1], "pagesize": 15},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            containerdata = res.json["result"]["value"]
            count = 0
            for container in containerdata["containers"]:
                self.assertTrue(container["serial"] in container_serials[2:4])
                count += 1
            self.assertEqual(containerdata["count"], count)

        # Assign user and realm
        self.setUp_user_realms()
        self.setUp_user_realm2()
        test_user = User(login="cornelius", realm=self.realm1)
        container = find_container_by_serial(container_serials[2])
        container.set_realms([self.realm2])
        container.add_user(test_user)

        # Test output
        with self.app.test_request_context('/container/',
                                           method='GET',
                                           data={"container_serial": container_serials[2], "pagesize": 15, "page": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            containerdata = res.json["result"]["value"]
            self.assertEqual(1, containerdata["count"])
            self.assertEqual(1, len(containerdata["containers"]))
            res_container = containerdata["containers"][0]
            self.assertEqual(3, len(res_container["tokens"]))
            self.assertEqual(1, len(res_container["users"]))
            self.assertEqual(test_user.login, res_container["users"][0]["user_name"])
            self.assertIn(self.realm1, res_container["realms"])

    def test_05_get_all_containers_paginate_wrong_arguments(self):
        TokenContainer.query.delete()
        types = ["Smartphone", "generic", "Yubikey", "Smartphone", "generic", "Yubikey"]
        container_serials = []
        for type in types:
            serial = init_container({"type": type, "description": "test container"})
            container_serials.append(serial)

        # Filter for container serial
        with self.app.test_request_context('/container/',
                                           method='GET',
                                           data={"container_serial": "wrong_serial", "pagesize": 15},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            containerdata = res.json["result"]["value"]
            self.assertEqual(0, containerdata["count"])

        # filter for type
        with self.app.test_request_context('/container/',
                                           method='GET',
                                           data={"type": "wrong_type", "pagesize": 15},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            containerdata = res.json["result"]["value"]
            self.assertEqual(0, containerdata["count"])

        # Assign token
        tokens = []
        params = {"genkey": "1"}
        for i in range(3):
            t = init_token(params)
            tokens.append(t)

        for serial in container_serials[2:4]:
            container = find_container_by_serial(serial)
            for token in tokens:
                container.add_token(token)

        # Filter for token serial
        with self.app.test_request_context('/container/',
                                           method='GET',
                                           data={"token_serial": "wrong_token_serial", "pagesize": 15},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            containerdata = res.json["result"]["value"]
            self.assertEqual(len(container_serials), containerdata["count"])

    def test_06_set_realms(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial = init_container({"type": "generic", "description": "test container"})
        payload = {"realms": self.realm1 + "," + self.realm2}

        # Set existing realms
        with self.app.test_request_context(f'/container/{container_serial}/realms',
                                           method='POST',
                                           data=payload,
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"])
            self.assertTrue(result["value"])
            self.assertTrue(result["value"]["deleted"])
            self.assertTrue(result["value"][self.realm1])
            self.assertTrue(result["value"][self.realm2])

        # Set non-existing realm
        payload = {"realms": "nonexistingrealm"}
        with self.app.test_request_context(f'/container/{container_serial}/realms',
                                           method='POST',
                                           data=payload,
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            result = res.json.get("result")
            self.assertFalse(result["value"]["nonexistingrealm"])

        # Set no realm shall remove all realms for the container
        payload = {"realms": ""}
        with self.app.test_request_context(f'/container/{container_serial}/realms',
                                           method='POST',
                                           data=payload,
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"])
            self.assertTrue(result["value"])
            self.assertTrue(result["value"]["deleted"])

        # Missing realm parameter
        with self.app.test_request_context(f'/container/{container_serial}/realms',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            error = res.json["result"]["error"]
            error_code = error["code"]
            error_msg = error["message"]
            self.assertEqual(905, error_code)
            self.assertEqual("ERR905: Missing parameter: 'realms'", error_msg)
            self.assertFalse(res.json["result"]["status"])

        # Clean up
        container = find_container_by_serial(container_serial)
        container.delete()

    """def test_03_token_in_container(self):
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": "tests/testdata/passwd"})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm1, [{'name': self.resolvername1}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)
        user_root = User(login="root", realm=self.realm1, resolver=self.resolvername1)
        user_statd = User(login="statd", realm=self.realm1, resolver=self.resolvername1)
        users = [user_root, user_statd]
        tokens = []
        params = {"genkey": "1"}
        for i in range(4):
            t = init_token(params, user=user_root if i % 2 == 0 else user_statd)
            tokens.append(t)
        token_serials = [t.get_serial() for t in tokens]
        params = {"type": "generic", "description": "testcontainer"}
        cserial = init_container(params)

        for u in users:
            payload = {"realm": "realm1", "user": u.login, "serial": cserial}
            with self.app.test_request_context('/container/assign',
                                               method='POST',
                                               data=payload,
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                j = res.json
                self.assertTrue(j["result"]["status"])
                self.assertTrue(j["result"]["value"])

        for serial in token_serials:
            payload = {"serial": serial}
            with self.app.test_request_context(f"/container/{cserial}/add",
                                               method='POST',
                                               data=payload,
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                self.assertTrue(j["result"]["status"])
                self.assertTrue(j["result"]["value"])

        with self.app.test_request_context('/container/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json = res.json
            print(json)
            self.assertTrue(json["result"]["status"])
            self.assertEqual(json["result"]["value"]["containers"][0]["type"], "generic")
            self.assertEqual(json["result"]["value"]["containers"][0]["description"], "testcontainer")
            self.assertTrue(len(json["result"]["value"]["containers"][0]["serial"]) > 0)

            users_res = json["result"]["value"]["containers"][0]["users"]
            for u in users_res:
                self.assertEqual(u["user_realm"], "realm1")

            tokens_res = json["result"]["value"][0]["tokens_paginated"]["tokens"]
            self.assertEqual(len(tokens_res), 4)
"""
