from .base import MyApiTestCase

SUB_FILE = "tests/testdata/test.sub"


class APISubscriptionsTestCase(MyApiTestCase):

    def test_01_crud_subscription(self):
        # Load Subscription file
        with self.app.test_request_context('/subscriptions/',
                                           method="POST",
                                           data={"file": (SUB_FILE,
                                                          "test.sub")},
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertTrue(value >= 1, result)

        # Get all subscriptions
        with self.app.test_request_context('/subscriptions/',
                                           method="GET",
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertEqual(len(value), 1)
            self.assertEqual(value[0].get("application"), "demo_application")

        # Get one subscription
        with self.app.test_request_context('/subscriptions/demo_application',
                                           method="GET",
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertEqual(len(value), 1)
            self.assertEqual(value[0].get("application"),
                             "demo_application")

        # Filtering by an unknown application returns an empty list.
        with self.app.test_request_context('/subscriptions/no_such_app',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            self.assertEqual([], res.json.get("result").get("value"))

        # delete subscriptions
        with self.app.test_request_context('/subscriptions/demo_application',
                                           method="DELETE",
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertEqual(value, 1)

        # Get one subscription
        with self.app.test_request_context('/subscriptions/demo_application',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertEqual(len(value), 0)

