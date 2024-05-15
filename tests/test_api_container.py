from privacyidea.lib.container import init_container
from privacyidea.lib.realm import set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.token import init_token
from privacyidea.lib.user import User
from tests.base import MyApiTestCase


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
            cserial = result["value"]["serial"]
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

    def test_03_token_in_container(self):
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
            self.assertTrue(json["result"]["status"])
            self.assertEqual(json["result"]["value"][0]["type"], "generic")
            self.assertEqual(json["result"]["value"][0]["description"], "testcontainer")
            self.assertTrue(len(json["result"]["value"][0]["serial"]) > 0)

            users_res = json["result"]["value"][0]["users"]
            for u in users_res:
                self.assertEqual(u["user_realm"], "realm1")

            tokens_res = json["result"]["value"][0]["tokens"]
            for token in tokens_res:
                # token are dicts of {"type": "serial"}
                self.assertTrue("hotp" in token)
                self.assertTrue(token["hotp"] in token_serials)
