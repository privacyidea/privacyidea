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

    def test_02_selfservice_user_can_list_but_not_modify(self):
        # A self-service user needs to be able to list service IDs to enroll
        # an application specific password token, but must not be able to
        # add or delete one.
        with self.app.test_request_context('/serviceid/serviceC',
                                           data={"description": "3rd service"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        self.setUp_user_realms()
        self.authenticate_selfservice_user()

        # The user can list the service IDs
        with self.app.test_request_context('/serviceid/',
                                           method='GET',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertIn("serviceC", value)

        # ...but is not allowed to create a new service ID
        with self.app.test_request_context('/serviceid/serviceD',
                                           data={"description": "4th service"},
                                           method='POST',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        # ...nor to delete an existing one
        with self.app.test_request_context('/serviceid/serviceC',
                                           method='DELETE',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        # clean up
        with self.app.test_request_context('/serviceid/serviceC',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
