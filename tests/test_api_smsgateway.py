import json
from .base import MyTestCase


class APISmsGatewayTestCase(MyTestCase):

    def test_01_crud_smsgateway(self):

        # list empty sms gateway definitions
        with self.app.test_request_context('/smsgateway',
                                           method='GET',
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), [])

        # create an sms gateway definition
        param = {
            "name": "myGW",
            "module": "privacyidea.lib.SMS",
            "description": "myGateway",
            "option.URL": "http://example.com"
        }
        with self.app.test_request_context('/smsgateway',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), 1)

        # check the gateway
        with self.app.test_request_context('/smsgateway',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            sms_gw = result.get("value")[0]
            self.assertEqual(sms_gw.get("description"), "myGateway")
            self.assertEqual(sms_gw.get("name"), "myGW")
            self.assertEqual(sms_gw.get("id"), 1)
            self.assertEqual(sms_gw.get("providermodule"),
                             "privacyidea.lib.SMS")
            self.assertEqual(sms_gw.get("options").get("URL"),
                             "http://example.com")

        # update
        param = {
            "name": "myGW",
            "module": "privacyidea.lib.SMS",
            "description": "new description",
            "id": 1
        }

        with self.app.test_request_context('/smsgateway',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), 1)

        # check the gateway
        with self.app.test_request_context('/smsgateway/1',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            sms_gw = result.get("value")[0]
            self.assertEqual(sms_gw.get("description"), "new description")


        # delete gateway
        with self.app.test_request_context('/smsgateway/myGW',
                                           method='DELETE',
                                           headers={
                                               'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), 1)

        # list empty gateways
        with self.app.test_request_context('/smsgateway',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), [])

    def test_02_test_options(self):

        # create an sms gateway configuration
        param = {
            "name": "myGW",
            "module": "privacyidea.lib.SMS",
            "description": "myGateway",
            "option.URL": "http://example.com"
        }
        with self.app.test_request_context('/smsgateway',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), 1)

        # add option
        param["option.HTTP_METHOD"] = "POST"
        param["id"] = 1
        with self.app.test_request_context('/smsgateway',
                                           method='POST',
                                           data=param,
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")

        # check options
        with self.app.test_request_context('/smsgateway',
                                           method='GET',
                                           headers={
                                                   'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            sms_gw = result.get("value")[0]
            self.assertEqual(sms_gw.get("options").get("URL"),
                             "http://example.com")
            self.assertEqual(sms_gw.get("options").get("HTTP_METHOD"), "POST")

        # delete option "URL"
        with self.app.test_request_context('/smsgateway/option/1/URL',
                                           method='DELETE',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")

        # check options
        with self.app.test_request_context('/smsgateway',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            sms_gw = result.get("value")[0]
            self.assertEqual(sms_gw.get("options").get("URL"), None)
            self.assertEqual(sms_gw.get("options").get("HTTP_METHOD"),
                             "POST")

    def test_04_sms_provider_modules(self):
        with self.app.test_request_context('/smsgateway/providers',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = json.loads(res.data).get("result").get("value")
            self.assertEqual(len(value), 4)
            self.assertTrue('privacyidea.lib.smsprovider.HttpSMSProvider'
                            '.HttpSMSProvider' in value)
            self.assertTrue('privacyidea.lib.smsprovider.SmtpSMSProvider'
                            '.SmtpSMSProvider' in value)
            self.assertTrue('privacyidea.lib.smsprovider.SipgateSMSProvider'
                            '.SipgateSMSProvider' in value)
            self.assertTrue('privacyidea.lib.smsprovider.SmppSMSProvider'
                            '.SmppSMSProvider' in value)
            http_parameters = value.get('privacyidea.lib.smsprovider.'
                                        'HttpSMSProvider.HttpSMSProvider')
            smtp_parameters = value.get('privacyidea.lib.smsprovider.'
                                        'SmtpSMSProvider.SmtpSMSProvider')
            sipgate_parameters = value.get('privacyidea.lib.smsprovider.'
                                        'SipgateSMSProvider.SipgateSMSProvider')
            smpp_parameters = value.get('privacyidea.lib.smsprovider.'
                                        'SmppSMSProvider.SmppSMSProvider')
            self.assertEqual(http_parameters.get("options_allowed"), True)
            self.assertEqual(smtp_parameters.get("options_allowed"), False)
            self.assertEqual(sipgate_parameters.get("options_allowed"), False)
            self.assertEqual(smpp_parameters.get("options_allowed"), False)
            self.assertTrue("URL" in http_parameters.get("parameters"))
            self.assertTrue("PROXY" in http_parameters.get("parameters"))
            self.assertTrue("HTTP_METHOD" in http_parameters.get("parameters"))

