# -*- coding: utf-8 -*-

from .base import MyApiTestCase
from privacyidea.lib.policy import set_policy, SCOPE, ACTION, delete_policy, CONDITION_SECTION
from privacyidea.lib.token import remove_token


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
        with self.app.test_request_context('/policy/pol1',
                                           method='POST',
                                           data={"action": ACTION.NODETAILFAIL,
                                                 "client": "10.1.2.3",
                                                 "scope": SCOPE.AUTHZ,
                                                 "check_all_resolvers": "true",
                                                 "realm": "realm1",
                                                 "priority": 3},
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
                                               "realm": "realm1"},
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

        with self.app.test_request_context('/policy/polpinode',
                                           method='POST',
                                           data={"action": ACTION.NODETAILFAIL,
                                                 "client": "10.1.2.3",
                                                 "scope": SCOPE.AUTHZ,
                                                 "pinode": "Node1",
                                                 "priority": 1,
                                                 "realm": "realm1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            self.assertTrue("setPolicy polpinode" in result.get("value"),
                            result.get("value"))

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
        # set a policy with conditions
        with self.app.test_request_context('/policy/cond1',
                                   method='POST',
                                   json={"action": ACTION.NODETAILFAIL,
                                         "client": "10.1.2.3",
                                         "scope": SCOPE.AUTHZ,
                                         "realm": "realm1",
                                         "conditions": [
                                             ["userinfo", "groups", "contains", "group1", True],
                                             ["userinfo", "type", "equals", "secure", False],
                                             ["HTTP header", "Origin", "equals", "https://localhost", True]
                                         ]},
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
            self.assertIn(["userinfo", "groups", "contains", "group1", True], cond1["conditions"])
            self.assertIn(["userinfo", "type", "equals", "secure", False], cond1["conditions"])
            self.assertIn(["HTTP header", "Origin", "equals", "https://localhost", True], cond1["conditions"])

        # update the policy, but not its conditions
        with self.app.test_request_context('/policy/cond1',
                                   method='POST',
                                   json={"action": ACTION.NODETAILFAIL,
                                         "client": "10.1.2.3",
                                         "scope": SCOPE.AUTHZ,
                                         "realm": "realm2"},
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
            self.assertEqual(len(cond1["conditions"]), 3)
            # order of conditions is not guaranteed
            self.assertIn(["userinfo", "groups", "contains", "group1", True], cond1["conditions"])
            self.assertIn(["userinfo", "type", "equals", "secure", False], cond1["conditions"])
            self.assertIn(["HTTP header", "Origin", "equals", "https://localhost", True], cond1["conditions"])

        # update the policy conditions
        with self.app.test_request_context('/policy/cond1',
                                   method='POST',
                                   json={"action": ACTION.NODETAILFAIL,
                                         "client": "10.1.2.3",
                                         "scope": SCOPE.AUTHZ,
                                         "conditions": [["userinfo", "type", "equals", "secure", True]],
                                         "realm": "realm2"},
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
            self.assertIn(["userinfo", "type", "equals", "secure", True], cond1["conditions"])

        # test some invalid conditions
        # no 5-tuples
        with self.app.test_request_context('/policy/cond1',
                                   method='POST',
                                   json={"action": ACTION.NODETAILFAIL,
                                         "client": "10.1.2.3",
                                         "scope": SCOPE.AUTHZ,
                                         "conditions": [["userinfo", "type", "equals", "secure"]],
                                         "realm": "realm2"},
                                   headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)

        with self.app.test_request_context('/policy/cond1',
                                   method='POST',
                                   json={"action": ACTION.NODETAILFAIL,
                                         "client": "10.1.2.3",
                                         "scope": SCOPE.AUTHZ,
                                         "conditions": [["userinfo", "type", "equals", "secure", True, "extra"]],
                                         "realm": "realm2"},
                                   headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)

        # wrong types
        with self.app.test_request_context('/policy/cond1',
                                   method='POST',
                                   json={"action": ACTION.NODETAILFAIL,
                                         "client": "10.1.2.3",
                                         "scope": SCOPE.AUTHZ,
                                         "conditions": [["userinfo", "type", "equals", 123, False]],
                                         "realm": "realm2"},
                                   headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)

        with self.app.test_request_context('/policy/cond1',
                                   method='POST',
                                   json={"action": ACTION.NODETAILFAIL,
                                         "client": "10.1.2.3",
                                         "scope": SCOPE.AUTHZ,
                                         "conditions": [["userinfo", "type", "equals", "123", "true"]],
                                         "realm": "realm2"},
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
                                         "realm": "realm2"},
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
            self.assertEqual(cond1["realm"], ["realm2"])
            self.assertEqual(cond1["conditions"], [])

        # delete policy
        with self.app.test_request_context('/policy/cond1',
                                   method='DELETE',
                                   headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

    def test_03_set_adminuser_policy(self):
        # Set a policy for the user testadmin
        with self.app.test_request_context('/policy/pol1adminuser',
                                           method='POST',
                                           data={
                                               "action": "{0!s}, {1!s}".format(ACTION.POLICYDELETE,
                                               ACTION.POLICYREAD),
                                               "scope": SCOPE.ADMIN,
                                               "realm": "",
                                               "adminuser": "testadmin",
                                               "client": "10.1.2.3"},
                                           headers={
                                               'Authorization': self.at}):
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
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            status = result.get("status")
            self.assertTrue(status)

    def test_04_policy_defs(self):
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
                                               "conditions": [[CONDITION_SECTION.HTTP_REQUEST_HEADER,
                                                               "User-Agent", "broken",
                                                               "SpecialApp", True]],
                                               "scope": SCOPE.AUTHZ},
                                           headers={'PI-Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)
            data = res.json
            result = data.get("result")
            self.assertEqual(result['error'], {'code': 302, 'message': 'ERR302: Invalid client definition!'})

class APIPolicyConditionTestCase(MyApiTestCase):

    def test_01_check_httpheader_condition(self):
        self.setUp_user_realms()
        # enroll a simple pass token
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           json={"type": "spass", "pin": "1234",
                                                 "serial": "sp1", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"},
                                           headers={'PI-Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # test an auth request
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertTrue("detail" in result)
            self.assertEqual(result.get("detail").get("message"), "matching 1 tokens")

        # set a policy with conditions
        # Request from a certain user agent will not see the detail
        with self.app.test_request_context('/policy/cond1',
                                           method='POST',
                                           json={"action": ACTION.NODETAILSUCCESS,
                                                 "client": "10.1.2.3",
                                                 "realm": "realm1",
                                                 "conditions": [[CONDITION_SECTION.HTTP_REQUEST_HEADER,
                                                                 "User-Agent", "equals", "SpecialApp", True]],
                                                 "scope": SCOPE.AUTHZ},
                                           headers={'PI-Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # A request with another header will display the details
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           headers={"User-Agent": "somethingelse"},
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertTrue("detail" in result)
            self.assertEqual(result.get("detail").get("message"), "matching 1 tokens")

        # A request with the dedicated header will not display the details
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           headers={'User-Agent': 'SpecialApp'},
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertFalse("detail" in result)

        # A request without such a header
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           headers={"Another": "header"},
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json
            self.assertIn("Unknown HTTP header key referenced in condition of policy",
                          result["result"]["error"]["message"])
            self.assertIn("User-Agent", result["result"]["error"]["message"])

        # A request without such a specific header - always has a header
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json
            self.assertIn("Unknown HTTP header key referenced in condition of policy",
                          result["result"]["error"]["message"])
            self.assertIn("User-Agent", result["result"]["error"]["message"])

        # Test http header policy with broken matching
        # update the policy
        with self.app.test_request_context('/policy/cond1',
                                           method='POST',
                                           json={"action": ACTION.NODETAILSUCCESS,
                                                 "client": "10.1.2.3",
                                                 "realm": "realm1",
                                                 "conditions": [[CONDITION_SECTION.HTTP_REQUEST_HEADER,
                                                                 "User-Agent", "broken",
                                                                 "SpecialApp", True]],
                                                 "scope": SCOPE.AUTHZ},
                                           headers={'PI-Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
        # now test the policy
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           headers={"User-Agent": "SpecialApp"},
                                           json={"pass": "1234", "user": "cornelius",
                                                 "realm": "realm1", "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json
            self.assertIn("Invalid comparison in the HTTP header conditions of policy",
                          result["result"]["error"]["message"])

        # Also check for an unknown section
        # update the policy
        with self.app.test_request_context('/policy/cond1',
                                           method='POST',
                                           json={"action": ACTION.NODETAILSUCCESS,
                                                 "client": "10.1.2.3",
                                                 "realm": "realm1",
                                                 "conditions": [['blabla',
                                                                 "User-Agent", "equals",
                                                                 "SpecialApp", True]],
                                                 "scope": SCOPE.AUTHZ},
                                           headers={'PI-Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
        # now test the policy
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           headers={"User-Agent": "SpecialApp"},
                                           json={"pass": "1234", "user": "cornelius",
                                                 "realm": "realm1", "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json
            # The text can be "Policy u'cond1' has condition with unknown section"
            # or "Policy 'cond1' has condition with unknown section"
            # so we only match for a substring
            self.assertIn("has condition with unknown section",
                          result["result"]["error"]["message"], result)

        delete_policy("cond1")
        remove_token("sp1")

    def test_02_check_httpenvironment_condition(self):
        self.setUp_user_realms()
        # enroll a simple pass token
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           json={"type": "spass", "pin": "1234",
                                                 "serial": "sp1", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"},
                                           headers={'PI-Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # test an auth request
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertTrue("detail" in result)
            self.assertEqual(result.get("detail").get("message"), "matching 1 tokens")

        # set a policy with conditions
        # Request with a certain request method will not see the user details
        with self.app.test_request_context('/policy/cond1',
                                           method='POST',
                                           json={"action": ACTION.NODETAILSUCCESS,
                                                 "realm": "realm1",
                                                 "client": "10.1.2.3",
                                                 "conditions": [[CONDITION_SECTION.HTTP_ENVIRONMENT,
                                                                 "REQUEST_METHOD", "equals", "POST", True]],
                                                 "scope": SCOPE.AUTHZ},
                                           headers={'PI-Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # A GET request will contain the details!
        with self.app.test_request_context('/validate/check',
                                           method='GET',
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertTrue("detail" in result)
            self.assertEqual(result.get("detail").get("message"), "matching 1 tokens")

        # A POST request will NOT contain the details!
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json
            self.assertFalse("detail" in result)

        delete_policy("cond1")
        # Now we run a test with a non-existing environment key
        with self.app.test_request_context('/policy/cond1',
                                           method='POST',
                                           json={"action": ACTION.NODETAILSUCCESS,
                                                 "realm": "realm1",
                                                 "client": "10.1.2.3",
                                                 "conditions": [[CONDITION_SECTION.HTTP_ENVIRONMENT,
                                                                 "NON_EXISTING", "equals", "POST", True]],
                                                 "scope": SCOPE.AUTHZ},
                                           headers={'PI-Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           json={"pass": "1234", "user": "cornelius", "realm": "realm1",
                                                 "client": "10.1.2.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json
            self.assertIn("Unknown HTTP environment key referenced in condition of policy",
                          result["result"]["error"]["message"])
            self.assertIn("NON_EXISTING", result["result"]["error"]["message"])

        delete_policy("cond1")
        remove_token("sp1")
