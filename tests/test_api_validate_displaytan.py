# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later


from privacyidea.lib.token import (remove_token)
from .base import MyApiTestCase



class DisplayTANTestCase(MyApiTestCase):

    def test_00_run_complete_workflow(self):
        # This is a standard workflow of a display TAN token.

        # Import OCRA Token file
        IMPORTFILE = "tests/testdata/ocra.csv"
        with self.app.test_request_context('/token/load/ocra.csv',
                                           method="POST",
                                           data={"type": "oathcsv",
                                                 "file": (IMPORTFILE,
                                                          "oath.csv")},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")['n_imported']
            self.assertTrue(value == 1, result)

        from privacyidea.lib.token import set_pin
        set_pin("ocra1234", "test")

        # Issue a challenge response
        challenge = "83507112  ~320,00~1399458665_G6HNVF"
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "ocra1234",
                                                 "pass": "test",
                                                 "hashchallenge": 1,
                                                 "challenge": challenge}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            hex_challenge = detail.get("attributes").get("challenge")
            self.assertEqual(hex_challenge, "7196501689c356046867728f4feb74458dcfd079")

        # Issue an authentication request
        otpvalue = "90065298"
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "ocra1234",
                                                 "pass": otpvalue,
                                                 "transaction_id":
                                                     transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)

        # The second request will fail
        otpvalue = "90065298"
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "ocra1234",
                                                 "pass": otpvalue,
                                                 "transaction_id":
                                                     transaction_id}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)

        # Get another challenge with a random nonce
        challenge = "83507112  ~320,00~"
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "ocra1234",
                                                 "pass": "test",
                                                 "hashchallenge": 1,
                                                 "addrandomchallenge": 20,
                                                 "challenge": challenge}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)
            detail = res.json.get("detail")
            transaction_id = detail.get("transaction_id")
            hex_challenge = detail.get("attributes").get("challenge")
            self.assertEqual(len(hex_challenge), 40)

        remove_token("ocra1234")
