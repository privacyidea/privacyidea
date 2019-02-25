# -*- coding: utf-8 -*-

import json
from .base import MyApiTestCase
from privacyidea.lib.policy import SCOPE, ACTION


class APIPolicyTestCase(MyApiTestCase):
    def test_00_get_policy(self):
        with self.app.test_request_context('/policy/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'], res.json)
            self.assertEquals(res.json["result"]["value"], [], res.json)

    def test_01_set_policy(self):
        with self.app.test_request_context('/policy/pol1',
                                           method='POST',
                                           data={"action": ACTION.NODETAILFAIL,
                                                 "scope": SCOPE.AUTHZ,
                                                 "check_all_resolvers": "true",
                                                 "realm": "realm1",
                                                 "priority": 3},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data.decode('utf8'))
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

        # Update policy to check_all_resolvers = false and priority = 5
        with self.app.test_request_context('/policy/pol1',
                                           method='POST',
                                           data={
                                               "action": ACTION.NODETAILFAIL,
                                               "scope": SCOPE.AUTHZ,
                                               "check_all_resolvers": "false",
                                               "priority": 5,
                                               "realm": "realm1"},
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data.decode('utf8'))
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
