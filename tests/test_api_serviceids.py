from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.serviceid import set_serviceid, delete_serviceid
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
        """A self-service user needs the service IDs to enroll an application specific password token. Listing them
        follows the serviceid_list action of the user scope, while adding and deleting stays with the administrator."""
        set_serviceid("serviceC", "3rd service")
        self.addCleanup(delete_serviceid, "serviceC")
        self.setUp_user_realms()
        self.authenticate_selfservice_user()

        # Without any policy in the user scope, every action of the scope is allowed
        with self.app.test_request_context('/serviceid/',
                                           method='GET',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
            self.assertIn("serviceC", res.json['result']['value'])

        # A user scope that is configured without the action denies the listing
        set_policy("user_pol", scope=SCOPE.USER, action=PolicyAction.DISABLE)
        self.addCleanup(delete_policy, "user_pol")
        with self.app.test_request_context('/serviceid/',
                                           method='GET',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(403, res.status_code, res.json)
            self.assertIn(PolicyAction.SERVICEID_LIST, res.json['result']['error']['message'])

        # ...and granting the action allows it again
        set_policy("user_pol", scope=SCOPE.USER,
                   action=[PolicyAction.DISABLE, PolicyAction.SERVICEID_LIST])
        with self.app.test_request_context('/serviceid/',
                                           method='GET',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
            self.assertIn("serviceC", res.json['result']['value'])

        # The user is not allowed to create a new service ID
        with self.app.test_request_context('/serviceid/serviceD',
                                           data={"description": "4th service"},
                                           method='POST',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)

        # ...nor to delete an existing one
        with self.app.test_request_context('/serviceid/serviceC',
                                           method='DELETE',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)
