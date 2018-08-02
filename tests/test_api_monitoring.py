import json
from .base import MyTestCase
from privacyidea.lib.monitoringstats import write_stats
from privacyidea.lib.tokenclass import AUTH_DATE_FORMAT
import datetime


class APIMonitoringTestCase(MyTestCase):

    def test_01_get_stats(self):

        # create some statistics

        write_stats("key1", 1)
        write_stats("key2", "A")
        write_stats("key1", 2)
        ts = datetime.datetime.now().isoformat()

        write_stats("key2", "B")
        write_stats("key1", 3)
        write_stats("key2", "A")
        write_stats("key1", 4)

        # get available stats keys
        with self.app.test_request_context('/monitoring/',
                                           method='GET',
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue("key1" in result.get("value"))
            self.assertTrue("key2" in result.get("value"))

        # check values of key1
        with self.app.test_request_context('/monitoring/key1',
                                           method='GET',
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(len(result.get("value")), 4)
            self.assertEqual(result.get("value")[0][1], 1)
            self.assertEqual(result.get("value")[1][1], 2)
            self.assertEqual(result.get("value")[2][1], 3)
            self.assertEqual(result.get("value")[3][1], 4)

        # check values of key1, with a start value in the past
        with self.app.test_request_context('/monitoring/key1',
                                           data={"start": "2010-01-01 10:00+0200"},
                                           method='GET',
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(len(result.get("value")), 4)

        # End value in the past will return no data.
        with self.app.test_request_context('/monitoring/key1',
                                           data={"end": "2010-01-01"},
                                           method='GET',
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(len(result.get("value")), 0)

        # check with start timestamp after the 2nd value.
        # This should return the 3rd and 4th.
        with self.app.test_request_context('/monitoring/key1',
                                           data={"start": ts},
                                           method='GET',
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(len(result.get("value")), 2)
            self.assertEqual(result.get("value")[0][1], 3)
            self.assertEqual(result.get("value")[1][1], 4)

        # check the last value of key1
        with self.app.test_request_context('/monitoring/key1/last',
                                           method='GET',
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), 4)

    def test_02_delete_stats(self):

        ts = datetime.datetime.now()
        write_stats("key2", "B")

        # Now we delete some keys (the three old ones)
        with self.app.test_request_context('/monitoring/key2',
                                           method='DELETE',
                                           data={"start": "2010-01-01",
                                                 "end": ts.strftime(AUTH_DATE_FORMAT)},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            # Number of deleted values
            self.assertEqual(result.get("value"), 3)

        # ..and check if there is only one key left!
        with self.app.test_request_context('/monitoring/key2',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            # Number of remaining values
            self.assertEqual(len(result.get("value")), 1)
