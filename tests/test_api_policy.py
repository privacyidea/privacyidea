import logging
from testfixtures import LogCapture

from privacyidea.lib.error import ParameterError
from privacyidea.lib.policies.policy_conditions import ConditionSection, ConditionHandleMissingData
from privacyidea.lib.utils.compare import Comparators
from .base import MyApiTestCase
from privacyidea.lib.policy import (set_policy, SCOPE, ACTION, delete_policy, rename_policy)
from privacyidea.lib.token import init_token
from privacyidea.lib.user import User
from privacyidea.models import db, NodeName


class APIPolicyTestCase(MyApiTestCase):
    def test_00_get_policy(self):
        with self.app.test_request_context('/policy/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'], res.json)
            self.assertEqual(res.json["result"]["value"], [], res.json)

        # test the policy export
        # first without policies (this used to fail due to an index error)
        with self.app.test_request_context('/policy/export/pols.txt',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertEqual(res.mimetype, 'text/plain', res)
            self.assertEqual(res.content_length, 0, res)

        # test export with a given policy
        set_policy("hide_welcome", scope=SCOPE.WEBUI, action=ACTION.HIDE_WELCOME, client="10.1.2.3")
        with self.app.test_request_context('/policy/export/pols.txt',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertEqual(res.mimetype, 'text/plain', res)
            self.assertGreater(res.content_length, 0, res)
            self.assertIn(b'[hide_welcome]', res.data, res)
        delete_policy('hide_welcome')

    def test_01_set_policy(self):
        self.setUp_user_realms()
        with self.app.test_request_context('/policy/pol1',
                                           method='POST',
                                           data={"action": ACTION.NODETAILFAIL,
                                                 "client": "10.1.2.3",
                                                 "scope": SCOPE.AUTHZ,
                                                 "check_all_resolvers": "true",
                                                 "realm": self.realm1,
                                                 "priority": 3,
                                                 "description": "This is a test policy"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            self.assertTrue("setPolicy pol1" in result.get("value"),
                            result.get("value"))

        # get the policies and see if check_all_resolvers and priority are set
        with self.app.test_request_context('/policy/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'], res.json)
            value = res.json['result']['value']
            self.assertEqual(len(value), 1)
            pol1 = value[0]
            self.assertEqual(pol1.get("check_all_resolvers"), True)
            self.assertEqual(pol1.get("priority"), 3)
            self.assertEqual(pol1.get("description"), "This is a test policy", pol1)

        # get active policies
        with self.app.test_request_context('/policy/?active=true',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'], res.json)
            self.assertEqual(len(value), 1)
            pol1 = value[0]
            self.assertEqual(pol1.get("check_all_resolvers"), True)
            self.assertEqual(pol1.get("priority"), 3)

        # Update policy to check_all_resolvers = false and priority = 5
        with self.app.test_request_context('/policy/pol1',
                                           method='POST',
                                           data={
                                               "action": ACTION.NODETAILFAIL,
                                               "client": "10.1.2.3",
                                               "scope": SCOPE.AUTHZ,
                                               "check_all_resolvers": "false",
                                               "priority": 5,
                                               "realm": self.realm1},
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            self.assertTrue("setPolicy pol1" in result.get("value"),
                            result.get("value"))

        # get the policies and see if check_all_resolvers and priority are set
        with self.app.test_request_context('/policy/',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'], res.json)
            value = res.json['result']['value']
            self.assertEqual(len(value), 1)
            pol1 = value[0]
            self.assertEqual(pol1.get("check_all_resolvers"), False)
            self.assertEqual(pol1.get("priority"), 5)

        delete_policy("pol1")

        db.session.add(NodeName(id="8e4272a9-9037-40df-8aa3-976e4a04b5a8", name="Node1"))
        with self.app.test_request_context('/policy/polpinode',
                                           method='POST',
                                           data={"action": ACTION.NODETAILFAIL,
                                                 "client": "10.1.2.3",
                                                 "scope": SCOPE.AUTHZ,
                                                 "pinode": "Node1",
                                                 "priority": 1,
                                                 "realm": self.realm1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            self.assertTrue("setPolicy polpinode" in result.get("value"),
                            result.get("value"))
        NodeName.query.filter_by(name="Node1").first().delete()

        # get the policies and see if the pinode was set
        with self.app.test_request_context('/policy/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'], res.json)
            value = res.json['result']['value']
            self.assertEqual(len(value), 1)
            pol1 = value[0]
            self.assertEqual(pol1.get("pinode"), ["Node1"])

        delete_policy("polpinode")

    def test_02_set_policy_conditions(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()

        expected_conditions = [[ConditionSection.USERINFO, "groups", Comparators.CONTAINS, "group1", True,
                                ConditionHandleMissingData.RAISE_ERROR.value],
                               [ConditionSection.USERINFO, "type", Comparators.EQUALS, "secure", False,
                                ConditionHandleMissingData.RAISE_ERROR.value],
                               [ConditionSection.HTTP_REQUEST_HEADER, "Origin", Comparators.EQUALS,
                                "https://localhost", True, ConditionHandleMissingData.IS_TRUE.value]]

        # set a policy with conditions
        conditions = [[ConditionSection.USERINFO, "groups", Comparators.CONTAINS, "group1", True],
                      [ConditionSection.USERINFO, "type", Comparators.EQUALS, "secure", False, None],
                      [ConditionSection.HTTP_REQUEST_HEADER, "Origin", Comparators.EQUALS, "https://localhost",
                       True, ConditionHandleMissingData.IS_TRUE.value]]
        with self.app.test_request_context('/policy/cond1',
                                           method='POST',
                                           json={"action": ACTION.NODETAILFAIL,
                                                 "client": "10.1.2.3",
                                                 "scope": SCOPE.AUTHZ,
                                                 "realm": self.realm1,
                                                 "conditions": conditions},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # get the policy and check its conditions
        with self.app.test_request_context('/policy/cond1',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json['result']['status'], res.json)
            value = res.json['result']['value']
            cond1 = value[0]
            self.assertEqual(cond1["realm"], ["realm1"])
            self.assertEqual(len(cond1["conditions"]), 3)
            # order of conditions is not guaranteed
            for condition in expected_conditions:
                self.assertIn(condition, cond1["conditions"])

        # update the policy, but not its conditions
        with self.app.test_request_context('/policy/cond1',
                                           method='POST',
                                           json={"action": ACTION.NODETAILFAIL,
                                                 "client": "10.1.2.3",
                                                 "scope": SCOPE.AUTHZ,
                                                 "realm": self.realm2},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # get the policy and check its conditions
        with self.app.test_request_context('/policy/cond1',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json['result']['status'], res.json)
            value = res.json['result']['value']
            cond1 = value[0]
            self.assertEqual(cond1["realm"], [self.realm2])
            self.assertEqual(len(cond1["conditions"]), 3)
            # order of conditions is not guaranteed
            for condition in expected_conditions:
                self.assertIn(condition, cond1["conditions"])

        # update the policy conditions
        with self.app.test_request_context('/policy/cond1',
                                           method='POST',
                                           json={"action": ACTION.NODETAILFAIL,
                                                 "client": "10.1.2.3",
                                                 "scope": SCOPE.AUTHZ,
                                                 "conditions": [[ConditionSection.USERINFO, "type",
                                                                 Comparators.EQUALS, "secure", True]],
                                                 "realm": self.realm2},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # get the policy and check its conditions
        with self.app.test_request_context('/policy/cond1',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json['result']['status'], res.json)
            value = res.json['result']['value']
            cond1 = value[0]
            self.assertEqual(cond1["realm"], ["realm2"])
            self.assertEqual(len(cond1["conditions"]), 1)
            # order of conditions is not guaranteed
            self.assertIn([ConditionSection.USERINFO, "type", Comparators.EQUALS, "secure", True,
                           ConditionHandleMissingData.RAISE_ERROR.value], cond1["conditions"])

        # test some invalid conditions
        # no 5-/6-tuples
        with self.app.test_request_context('/policy/cond1',
                                           method='POST',
                                           json={"action": ACTION.NODETAILFAIL,
                                                 "client": "10.1.2.3",
                                                 "scope": SCOPE.AUTHZ,
                                                 "conditions": [[ConditionSection.USERINFO, "type",
                                                                 Comparators.EQUALS, "secure"]],
                                                 "realm": "realm2"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)

        with self.app.test_request_context('/policy/cond1',
                                           method='POST',
                                           json={"action": ACTION.NODETAILFAIL,
                                                 "client": "10.1.2.3",
                                                 "scope": SCOPE.AUTHZ,
                                                 "conditions": [[ConditionSection.USERINFO, "type", Comparators.EQUALS,
                                                                 "secure", True,
                                                                 ConditionHandleMissingData.RAISE_ERROR.value,
                                                                 "extra"]],
                                                 "realm": self.realm2},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)

        # wrong types
        with self.app.test_request_context('/policy/cond1',
                                           method='POST',
                                           json={"action": ACTION.NODETAILFAIL,
                                                 "client": "10.1.2.3",
                                                 "scope": SCOPE.AUTHZ,
                                                 "conditions": [[ConditionSection.USERINFO, "type", Comparators.EQUALS,
                                                                 123, False]],
                                                 "realm": self.realm2},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)

        with self.app.test_request_context('/policy/cond1',
                                           method='POST',
                                           json={"action": ACTION.NODETAILFAIL,
                                                 "client": "10.1.2.3",
                                                 "scope": SCOPE.AUTHZ,
                                                 "conditions": [[ConditionSection.USERINFO, "type", Comparators.EQUALS,
                                                                 "123", "true"]],
                                                 "realm": self.realm2},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)

        # reset conditions
        with self.app.test_request_context('/policy/cond1',
                                           method='POST',
                                           json={"action": ACTION.NODETAILFAIL,
                                                 "client": "10.1.2.3",
                                                 "scope": SCOPE.AUTHZ,
                                                 "conditions": [],
                                                 "realm": self.realm2},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        with self.app.test_request_context('/policy/cond1',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json['result']['status'], res.json)
            value = res.json['result']['value']
            cond1 = value[0]
            self.assertEqual(cond1["realm"], [self.realm2])
            self.assertEqual(cond1["conditions"], [])

        # delete policy
        with self.app.test_request_context('/policy/cond1',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

    def test_03_set_adminuser_policy(self):
        self.setUp_user_realms()
        # Set an invalid admin realm throws ParameterError
        with self.app.test_request_context("/policy/pol1adminuser", method="POST",
                                           data={"action": f"{ACTION.POLICYDELETE}, {ACTION.POLICYREAD}",
                                                 "scope": SCOPE.ADMIN,
                                                 "realm": "",
                                                 "adminrealm": "test",
                                                 "client": "10.1.2.3"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code)
            self.assertEqual(905, res.json["result"]["error"]["code"])

        # Set a user realm as admin realm fails
        with self.app.test_request_context("/policy/pol1adminuser", method="POST",
                                           data={"action": f"{ACTION.POLICYDELETE}, {ACTION.POLICYREAD}",
                                                 "scope": SCOPE.ADMIN,
                                                 "realm": "",
                                                 "adminrealm": self.realm1,
                                                 "client": "10.1.2.3"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code)
            self.assertEqual(905, res.json["result"]["error"]["code"])

        # Set a correct admin realm
        with self.app.test_request_context('/policy/pol1adminuser',
                                           method='POST',
                                           data={"action": f"{ACTION.POLICYDELETE}, {ACTION.POLICYREAD}",
                                                 "scope": SCOPE.ADMIN,
                                                 "realm": "",
                                                 "adminrealm": "adminrealm",
                                                 "client": "10.1.2.3"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
        delete_policy("pol1adminuser")

        # Set a policy for the user testadmin
        with self.app.test_request_context('/policy/pol1adminuser',
                                           method='POST',
                                           data={"action": f"{ACTION.POLICYDELETE}, {ACTION.POLICYREAD}",
                                                 "scope": SCOPE.ADMIN,
                                                 "realm": "",
                                                 "adminuser": "testadmin",
                                                 "client": "10.1.2.3"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            self.assertTrue("setPolicy pol1adminuser" in result.get("value"),
                            result.get("value"))

        # Get the policies
        with self.app.test_request_context('/policy/',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            policies = result.get("value")
            self.assertEqual(1, len(policies))
            self.assertEqual("pol1adminuser", policies[0].get("name"))

        # The admin is not allowed to enroll a token!
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"genkey": 1},
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            # Forbidden
            self.assertTrue(res.status_code == 403, res)
            data = res.json
            result = data.get("result")
            status = result.get("status")
            self.assertFalse(status)
            message = result.get("error").get("message")
            self.assertEqual(message, "Admin actions are defined, but you are not allowed to enroll this token type!")

        # Delete the policy
        with self.app.test_request_context('/policy/pol1adminuser',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            status = result.get("status")
            self.assertTrue(status)

    def test_04_policy_defs(self):
        db.session.add(NodeName(id="8e4272a9-9037-40df-8aa3-976e4a04b5a9", name="Node1"))
        db.session.add(NodeName(id="d1d7fde6-330f-4c12-88f3-58a1752594bf", name="Node2"))
        db.session.commit()
        with self.app.test_request_context('/policy/defs/conditions',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            status = result.get("status")
            self.assertTrue(status)
            value = result.get("value")
            self.assertIn("comparators", value)
            self.assertIn("sections", value)

        with self.app.test_request_context('/policy/defs/pinodes',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            status = result.get("status")
            self.assertTrue(status)
            value = result.get("value")
            self.assertIn("Node1", value)
            self.assertIn("Node2", value)

    def test_05_invalid_client(self):
        with self.app.test_request_context('/policy/condFalse',
                                           method='POST',
                                           json={
                                               "client": "10.1.2.3.4",
                                               "action": ACTION.NODETAILSUCCESS,
                                               "realm": "realm1",
                                               "conditions": [[ConditionSection.HTTP_REQUEST_HEADER, "User-Agent",
                                                               "broken", "SpecialApp", True]],
                                               "scope": SCOPE.AUTHZ},
                                           headers={'PI-Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)
            data = res.json
            result = data.get("result")
            self.assertEqual(result['error'], {'code': 302, 'message': 'ERR302: Invalid client definition!'})

    def test_02_rename_policy(self):
        # create a policy pol_old
        with self.app.test_request_context(
                '/policy/pol_old',
                method='POST',
                json={
                    "action": ACTION.NODETAILFAIL,
                    "client": "10.1.2.3",
                    "scope": SCOPE.AUTHZ,
                    "realm": "realm1"},
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)

        # rename pol_old to pol_new
        with self.app.test_request_context(
                '/policy/rename/pol_old',
                method='POST',
                json={"newname": "pol_new"},
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            self.assertTrue(res.json["result"]["status"], res.json)

        # verify the list now contains only pol_new
        with self.app.test_request_context(
                '/policy/',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            policies = res.json["result"]["value"]
            self.assertEqual(len(policies), 1, policies)
            self.assertEqual(policies[0]["name"], "pol_new", policies)

        # verify GET /policy/pol_new works
        with self.app.test_request_context(
                '/policy/pol_new',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            self.assertTrue(res.json["result"]["status"], res.json)

        # verify GET /policy/pol_old returns 404
        with self.app.test_request_context(
                '/policy/pol_old',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertIn(res.status_code, (200, 404), res)
            if res.status_code == 200:
                self.assertEqual(res.json["result"]["value"], [], res.json)

        # renaming a non‐existent policy should raise ParameterError
        with self.assertRaises(ParameterError) as cm1:
            rename_policy("no_such", "newname")
        self.assertIn("Policy 'no_such' does not exist!", str(cm1.exception))

        with self.app.test_request_context(
                '/policy/rename/no_such',
                method='POST',
                json={"newname": "newname"},
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)
            self.assertIn("does not exist",
                          res.json["result"]["error"]["message"])
            self.assertEqual(905, res.json["result"]["error"]["code"])

        # renaming to a name that already exists should raise ParameterError
        with self.app.test_request_context(
                "/policy/pol_a",
                method="POST",
                json={
                    "action": ACTION.NODETAILFAIL,
                    "client": "10.1.2.3",
                    "scope": SCOPE.AUTHZ,
                    "realm": "realm1"},
                headers={"Authorization": self.at}):
            self.app.full_dispatch_request()

        with self.app.test_request_context(
                "/policy/pol_b",
                method="POST",
                json={
                    "action": ACTION.NODETAILFAIL,
                    "client": "10.1.2.3",
                    "scope": SCOPE.AUTHZ,
                    "realm": "realm1"},
                headers={"Authorization": self.at}):
            self.app.full_dispatch_request()

        with self.assertRaises(ParameterError) as cm2:
            rename_policy("pol_a", "pol_b")
        self.assertIn("Policy 'pol_b' already exists!", str(cm2.exception))

        with self.app.test_request_context(
                "/policy/rename/pol_a",
                method="POST",
                json={"newname": "pol_b"},
                headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()

            self.assertEqual(res.status_code, 400)
            self.assertEqual(res.json["result"]["error"]["code"], 905)
            self.assertIn("already exists",
                          res.json["result"]["error"]["message"])

        # clean up
        delete_policy("pol_new")
        delete_policy("pol_a")
        delete_policy("pol_b")

class APIPolicyConditionTestCase(MyApiTestCase):

    def setUp(self):
        self.setUp_user_realms()
        # create a spass token
        init_token({"type": "spass", "pin": "1234", "serial": "sp1"}, user=User("cornelius", self.realm1))

    def test_01_check_httpheader_condition_success(self):
        # set a policy with conditions
        # Request from a certain user agent will not see the detail
        set_policy("policy", scope=SCOPE.AUTHZ, action=ACTION.NODETAILSUCCESS, client="10.1.2.3",
                   realm=self.realm1, conditions=[(ConditionSection.HTTP_REQUEST_HEADER, "User-Agent",
                                                   Comparators.EQUALS, "SpecialApp", True,
                                                   ConditionHandleMissingData.RAISE_ERROR.value)])

        # A request with another header will display the details
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           headers={"User-Agent": "somethingelse"},
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertTrue("detail" in result)
            self.assertEqual(result.get("detail").get("message"), "matching 1 tokens")

        # A request with the dedicated header will not display the details
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           headers={"User-Agent": "SpecialApp"},
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertFalse("detail" in result)

        delete_policy("policy")

    def test_02_check_httpheader_condition_missing_data(self):
        # ---- Raises error for missing data ----
        set_policy("policy", scope=SCOPE.AUTHZ, action=ACTION.NODETAILSUCCESS, client="10.1.2.3",
                   realm=self.realm1, conditions=[(ConditionSection.HTTP_REQUEST_HEADER, "User-Agent",
                                                   Comparators.EQUALS, "SpecialApp", True,
                                                   ConditionHandleMissingData.RAISE_ERROR.value)])
        # A request without such a header
        with LogCapture(level=logging.ERROR) as lc:
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               headers={"Another": "header"},
                                               json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                     "client": "10.1.2.3"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 403)
                result = res.json
                self.assertIn("Unknown HTTP Request header key 'User-Agent' referenced in condition of policy "
                              "'policy'!", result["result"]["error"]["message"])
                # Make sure the missing key is described in the error log
                lc.check_present(("privacyidea.lib.policies.policy_conditions", "ERROR",
                                  "Unknown HTTP Request header key 'User-Agent' referenced in condition of policy "
                                  "'policy'."))

        # A request without such a specific header - always has a header
        with LogCapture(level=logging.ERROR) as lc:
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                     "client": "10.1.2.3"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 403)
                result = res.json
                self.assertIn("Unknown HTTP Request header key 'User-Agent' referenced in condition of policy '"
                              "policy'!", result["result"]["error"]["message"])
                # Make sure the missing key is described in the error log
                lc.check_present(("privacyidea.lib.policies.policy_conditions", "ERROR",
                                  "Unknown HTTP Request header key 'User-Agent' "
                                  "referenced in condition of policy 'policy'."))

        # ---- Policy match for missing data ----
        # Define policy shall match if header or key is not present
        set_policy("policy", scope=SCOPE.AUTHZ, action=ACTION.NODETAILSUCCESS, client="10.1.2.3",
                   realm=self.realm1, conditions=[(ConditionSection.HTTP_REQUEST_HEADER, "User-Agent", "equals",
                                                   "SpecialApp", True, ConditionHandleMissingData.IS_TRUE.value)])

        # A request without such a header: policy matches, details not included
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           headers={"Another": "header"},
                                           json={"pass": "1234", "user": "cornelius", "realm": self.realm1,
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertFalse("detail" in result)

        # A request without such a specific header - always has a header: policy matches, details not included
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           json={"pass": "1234", "user": "cornelius", "realm": self.realm1,
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertFalse("detail" in result)

        # ---- Policy not match for missing data ----
        # Define policy shall not match if header or key is not present
        set_policy("policy", scope=SCOPE.AUTHZ, action=ACTION.NODETAILSUCCESS, client="10.1.2.3",
                   realm=self.realm1, conditions=[(ConditionSection.HTTP_REQUEST_HEADER, "User-Agent", "equals",
                                                   "SpecialApp", True, ConditionHandleMissingData.IS_FALSE.value)])

        # A request without such a header: policy not matches, details are included
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           headers={"Another": "header"},
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertTrue("detail" in result)
            self.assertEqual(result.get("detail").get("message"), "matching 1 tokens")

        # A request without such a specific header - always has a header: policy not matches, details are included
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertTrue("detail" in result)
            self.assertEqual(result.get("detail").get("message"), "matching 1 tokens")

        delete_policy("policy")

    def test_03_check_httpheader_condition_invalid(self):
        # Error for invalid comparator
        set_policy("policy", scope=SCOPE.AUTHZ, action=ACTION.NODETAILSUCCESS, client="10.1.2.3",
                   realm=self.realm1, conditions=[(ConditionSection.HTTP_REQUEST_HEADER, "User-Agent",
                                                   Comparators.CONTAINS, "SpecialApp", True,
                                                   ConditionHandleMissingData.RAISE_ERROR.value)])

        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           headers={"User-Agent": "SpecialApp"},
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json
            self.assertIn("Invalid comparison in the HTTP Request header conditions of policy",
                          result["result"]["error"]["message"])

        delete_policy("policy")

    def test_04_check_http_environment_condition_success(self):
        # test an auth request
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertTrue("detail" in result)
            self.assertEqual(result.get("detail").get("message"), "matching 1 tokens")

        # set a policy with conditions
        set_policy("policy", scope=SCOPE.AUTHZ, action=ACTION.NODETAILSUCCESS, realm=self.realm1,
                   client="10.1.2.3", conditions=[(ConditionSection.HTTP_ENVIRONMENT, "REQUEST_METHOD",
                                                   Comparators.EQUALS, "POST", True)])

        # A GET request will contain the details!
        with self.app.test_request_context("/validate/check",
                                           method="GET",
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertTrue("detail" in result)
            self.assertEqual(result.get("detail").get("message"), "matching 1 tokens")

        # A POST request will NOT contain the details!
        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertFalse("detail" in result)

        delete_policy("policy")

        # Now we run a test with a non-existing environment key
        with self.app.test_request_context('/policy/cond1',
                                           method='POST',
                                           json={"action": ACTION.NODETAILSUCCESS,
                                                 "realm": "realm1",
                                                 "client": "10.1.2.3",
                                                 "conditions": [[ConditionSection.HTTP_ENVIRONMENT, "NON_EXISTING",
                                                                 Comparators.EQUALS, "POST", True]],
                                                 "scope": SCOPE.AUTHZ},
                                           headers={'PI-Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        with LogCapture(level=logging.ERROR) as lc:
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                     "client": "10.1.2.3"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 403)
                result = res.json
                self.assertIn("Unknown HTTP Environment key 'NON_EXISTING' referenced in condition of policy "
                              "'cond1'!",
                              result["result"]["error"]["message"])
                # Make sure the missing key is described in the error log
                lc.check_present(("privacyidea.lib.policies.policy_conditions", "ERROR",
                                  "Unknown HTTP Environment key 'NON_EXISTING' referenced in condition of policy "
                                  "'cond1'."))

        delete_policy("cond1")

    def test_05_check_http_environment_condition_missing_data(self):
        # Raise Error
        set_policy("policy", scope=SCOPE.AUTHZ, action=ACTION.NODETAILSUCCESS, realm=self.realm1,
                   client="10.1.2.3", conditions=[(ConditionSection.HTTP_ENVIRONMENT, "NON_EXISTING",
                                                   Comparators.EQUALS, "POST", True,
                                                   ConditionHandleMissingData.RAISE_ERROR.value)])

        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json
            self.assertEqual("Unknown HTTP Environment key 'NON_EXISTING' referenced in condition of policy 'policy'!",
                             result["result"]["error"]["message"])

        # Policy matches (condition is true)
        set_policy("policy", scope=SCOPE.AUTHZ, action=ACTION.NODETAILSUCCESS, realm=self.realm1,
                   client="10.1.2.3", conditions=[(ConditionSection.HTTP_ENVIRONMENT, "NON_EXISTING",
                                                   Comparators.EQUALS, "POST", True,
                                                   ConditionHandleMissingData.IS_TRUE.value)])

        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertFalse("detail" in result)

        # Policy not matches (condition is false)
        set_policy("policy", scope=SCOPE.AUTHZ, action=ACTION.NODETAILSUCCESS, realm=self.realm1,
                   client="10.1.2.3", conditions=[(ConditionSection.HTTP_ENVIRONMENT, "NON_EXISTING",
                                                   Comparators.EQUALS, "POST", True,
                                                   ConditionHandleMissingData.IS_FALSE.value)])

        with self.app.test_request_context("/validate/check",
                                           method="POST",
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertTrue("detail" in result)
            self.assertEqual(result.get("detail").get("message"), "matching 1 tokens")

        delete_policy("policy")
