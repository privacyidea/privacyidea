from datetime import datetime, timedelta

from privacyidea.lib.subscriptions import DASHBOARD_PLUGINS
from privacyidea.models import ClientApplication, Subscription, db
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

    def test_02_status_endpoint(self):
        # Seed a used+valid plugin and leave the rest unused.
        db.session.add(ClientApplication(
            ip="1.2.3.4",
            clienttype="privacyidea-keycloak/1.0 test/1",
            node="localnode",
            lastseen=datetime.now()))
        db.session.add(Subscription(
            application="privacyidea-keycloak",
            for_name="customer", for_email="c@x", for_phone="0",
            by_name="vendor", by_email="v@x",
            date_from=datetime.now() - timedelta(days=10),
            date_till=datetime.now() + timedelta(days=100),
            num_users=10, num_tokens=10, num_clients=10,
            level="Gold", signature="0"))
        db.session.commit()

        with self.app.test_request_context('/subscriptions/status',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            value = res.json.get("result").get("value")

        # First entry is always the server row, followed by DASHBOARD_PLUGINS in order.
        self.assertTrue(value[0].get("is_server"))
        self.assertEqual(value[0]["application"], "privacyidea")
        self.assertEqual([e["application"] for e in value[1:]], DASHBOARD_PLUGINS)
        by_app = {e["application"]: e for e in value[1:]}
        self.assertEqual(by_app["privacyidea-keycloak"]["subscription"], "valid")
        self.assertEqual(by_app["privacyidea-keycloak"]["usage"], "yes")
        # entraid-via-keycloak mirrors the keycloak subscription (same owning
        # application), so it is valid/used too even without its own client row.
        mirror_keycloak = {"privacyidea-keycloak", "entraid-via-keycloak"}
        for plugin in DASHBOARD_PLUGINS:
            if plugin in mirror_keycloak:
                self.assertEqual(by_app[plugin]["subscription"], "valid")
                self.assertEqual(by_app[plugin]["usage"], "yes")
            else:
                # No subscription and unused on a fresh test DB.
                self.assertEqual(by_app[plugin]["subscription"], "none")
                self.assertEqual(by_app[plugin]["usage"], "no")

