import json
from .base import MyTestCase
from privacyidea.lib.clientapplication import save_clientapplication


class APIClienttypeTestCase(MyTestCase):

    def test_00_get_client(self):
        save_clientapplication("1.2.3.4", "PAM")
        save_clientapplication("1.2.3.4", "RADIUS")
        with self.app.test_request_context('/client/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data)
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertTrue("PAM" in json_response.get("result").get("value"))
            self.assertTrue("RADIUS" in json_response.get("result").get(
                "value"))

        # test the decorator
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "hans",
                                                 "pass": "dampf"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            # Some user... does not exist
            self.assertTrue(res.status_code == 400, res)

        with self.app.test_request_context('/client/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data)
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertTrue("PAM" in json_response.get("result").get("value"))
            self.assertTrue("RADIUS" in json_response.get("result").get(
                "value"))
            self.assertTrue("unknown" in json_response.get("result").get(
                "value"))
