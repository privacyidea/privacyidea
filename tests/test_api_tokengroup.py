# -*- coding: utf-8 -*-

from .base import MyApiTestCase


class APITokengroupTestCase(MyApiTestCase):

    def test_01_set_get_delete_tokengroup(self):
        # Set tokengroup
        with self.app.test_request_context('/tokengroup/gruppe1',
                                           data={"description": "My Cool first group"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertGreaterEqual(value, 1)

        # get tokengroups
        with self.app.test_request_context('/tokengroup/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertIn("gruppe1", value)
            self.assertEqual(value["gruppe1"]["description"], "My Cool first group")

        # create a 2nd group
        with self.app.test_request_context('/tokengroup/gruppe2',
                                           data={"description": "2nd group"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertGreaterEqual(value, 1)

        # get all tokengroups
        with self.app.test_request_context('/tokengroup/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertEqual(len(value), 2)
            self.assertIn("gruppe1", value)
            self.assertIn("gruppe2", value)

        # Change the description of the first group
        with self.app.test_request_context('/tokengroup/gruppe1',
                                           data={"description": "1st group"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertGreaterEqual(value, 1)

        # get 1st group
        with self.app.test_request_context('/tokengroup/gruppe1',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertEqual(len(value), 1)
            self.assertEqual(value["gruppe1"]["description"], "1st group")

        # delete 1st group
        with self.app.test_request_context('/tokengroup/gruppe1',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertEqual(value, 1)

        # check, that only the 2nd group is available
        with self.app.test_request_context('/tokengroup/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertEqual(len(value), 1)
            self.assertNotIn("gruppe1", value)
            self.assertIn("gruppe2", value)

        # delete 2nd group
        with self.app.test_request_context('/tokengroup/gruppe2',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertEqual(value, 1)
