# -*- coding: utf-8 -*-

from .base import MyApiTestCase


class APIServiceIDTestCase(MyApiTestCase):

    def test_01_set_get_delete_serviceid(self):
        # Set serviceid
        with self.app.test_request_context('/serviceid/serviceA',
                                           data={"description": "My Cool first service"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertGreaterEqual(value, 1)

        # get services
        with self.app.test_request_context('/serviceid/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertIn("serviceA", value)
            self.assertEqual(value["serviceA"]["description"], "My Cool first service")

        # create a 2nd service
        with self.app.test_request_context('/serviceid/serviceB',
                                           data={"description": "2nd service"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertGreaterEqual(value, 1)

        # get all services
        with self.app.test_request_context('/serviceid/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertEqual(len(value), 2)
            self.assertIn("serviceA", value)
            self.assertIn("serviceB", value)

        # Change the description of the first group
        with self.app.test_request_context('/serviceid/serviceA',
                                           data={"description": "1st service"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertGreaterEqual(value, 1)

        # get 1st service
        with self.app.test_request_context('/serviceid/serviceA',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertEqual(len(value), 1)
            self.assertEqual(value["serviceA"]["description"], "1st service")

        # delete 1st service
        with self.app.test_request_context('/serviceid/serviceA',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertEqual(value, 1)

        # check, that only the 2nd service is available
        with self.app.test_request_context('/serviceid/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertEqual(len(value), 1)
            self.assertNotIn("serviceA", value)
            self.assertIn("serviceB", value)

        # delete 2nd service
        with self.app.test_request_context('/serviceid/serviceB',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertEqual(value, 1)
