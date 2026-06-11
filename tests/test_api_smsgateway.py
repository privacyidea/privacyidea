from .base import MyApiTestCase
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.crypto import CENSORED


class APISmsGatewayTestCase(MyApiTestCase):

    def test_01_crud_smsgateway(self):
        # list empty sms gateway definitions
        with self.app.test_request_context('/smsgateway/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), [])

        # check that we have an entry in the audit log
        audit_entry = self.find_most_recent_audit_entry(action="GET /smsgateway*")
        self.assertEqual(audit_entry['success'], 1, audit_entry)

        # create an sms gateway definition
        param = {
            "name": "myGW",
            "module": "privacyidea.lib.smsprovider.SMSProvider.ISMSProvider",
            "description": "myGateway",
            "option.URL": "http://example.com"
        }
        with self.app.test_request_context('/smsgateway',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), 1)

        # check the gateway
        with self.app.test_request_context('/smsgateway/',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            sms_gw = result.get("value")[0]
            self.assertEqual(sms_gw.get("description"), "myGateway")
            self.assertEqual(sms_gw.get("name"), "myGW")
            self.assertEqual(sms_gw.get("id"), 1)
            self.assertEqual(sms_gw.get("providermodule"),
                             "privacyidea.lib.smsprovider.SMSProvider.ISMSProvider")
            self.assertEqual(sms_gw.get("options").get("URL"),
                             "http://example.com")

        # update
        param = {
            "name": "myGW",
            "module": "privacyidea.lib.smsprovider.SMSProvider.ISMSProvider",
            "description": "new description",
            "id": 1
        }

        with self.app.test_request_context('/smsgateway',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), 1)

        # check the gateway
        with self.app.test_request_context('/smsgateway/1',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            sms_gw = result.get("value")[0]
            self.assertEqual(sms_gw.get("description"), "new description")

        # delete gateway
        with self.app.test_request_context('/smsgateway/myGW',
                                           method='DELETE',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), 1)

        # list empty gateways
        with self.app.test_request_context('/smsgateway/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), [])

    def test_02_test_options(self):
        # create an sms gateway configuration
        param = {
            "name": "myGW",
            "module": "privacyidea.lib.smsprovider.SMSProvider.ISMSProvider",
            "description": "myGateway",
            "option.URL": "http://example.com",
            "header.header1": "headervalue1"
        }
        with self.app.test_request_context('/smsgateway',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertGreaterEqual(result.get("value"), 1, result)
            smsgw_id = result.get("value")

        # add option
        param["option.HTTP_METHOD"] = "POST"
        # add header
        param["header.header2"] = "headervalue2"
        param["id"] = smsgw_id
        with self.app.test_request_context('/smsgateway',
                                           method='POST',
                                           data=param,
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # check options and headers
        with self.app.test_request_context('/smsgateway/',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            sms_gw = result.get("value")[0]
            self.assertEqual(sms_gw.get("options").get("URL"),
                             "http://example.com")
            self.assertEqual(sms_gw.get("options").get("HTTP_METHOD"), "POST")
            self.assertEqual(sms_gw.get("headers").get("header1"), "headervalue1")
            self.assertEqual(sms_gw.get("headers").get("header2"), "headervalue2")

        # delete option "URL"
        with self.app.test_request_context('/smsgateway/option/{0!s}/option.URL'.format(smsgw_id),
                                           method='DELETE',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # try to delete header "header1" at the wrong endpoint
        with self.app.test_request_context('/smsgateway/option/{0!s}/option.header1'.format(smsgw_id),
                                           method='DELETE',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 404, res)

        # delete header "header1"
        with self.app.test_request_context('/smsgateway/option/{0!s}/header.header1'.format(smsgw_id),
                                           method='DELETE',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # check options
        with self.app.test_request_context('/smsgateway/',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            sms_gw = result.get("value")[0]
            self.assertEqual(sms_gw.get("options").get("URL"), None)
            self.assertEqual(sms_gw.get("options").get("HTTP_METHOD"),
                             "POST")
            self.assertEqual(sms_gw.get("headers").get("header1"), None)
            self.assertEqual(sms_gw.get("headers").get("header2"), "headervalue2")

    def test_04_sms_provider_modules(self):
        with self.app.test_request_context('/smsgateway/providers',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json.get("result").get("value")
            self.assertEqual(len(value), 6)
            self.assertTrue('privacyidea.lib.smsprovider.HttpSMSProvider'
                            '.HttpSMSProvider' in value)
            self.assertTrue('privacyidea.lib.smsprovider.SmtpSMSProvider'
                            '.SmtpSMSProvider' in value)
            self.assertTrue('privacyidea.lib.smsprovider.SipgateSMSProvider'
                            '.SipgateSMSProvider' in value)
            self.assertTrue('privacyidea.lib.smsprovider.SmppSMSProvider'
                            '.SmppSMSProvider' in value)
            self.assertIn('privacyidea.lib.smsprovider.ScriptSMSProvider'
                          '.ScriptSMSProvider', value)
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

    def test_05_read_write_policies(self):
        set_policy(name="pol_read", scope=SCOPE.ADMIN,
                   action=PolicyAction.SMSGATEWAYREAD)
        # create an sms gateway configuration
        param = {
            "name": "myGW",
            "module": "privacyidea.lib.smsprovider.SMSProvider.ISMSProvider",
            "description": "myGateway",
            "option.URL": "http://example.com"
        }
        with self.app.test_request_context('/smsgateway',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 403, res)

        # Now we create a write policy, and we are allowed to write
        set_policy(name="pol_write", scope=SCOPE.ADMIN,
                   action=PolicyAction.SMSGATEWAYWRITE)
        with self.app.test_request_context('/smsgateway',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # delete the read policy
        delete_policy("pol_read")

        with self.app.test_request_context('/smsgateway/',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 403, res)

        # delete the write policy
        delete_policy("pol_write")

        # and delete sms gateway
        with self.app.test_request_context('/smsgateway/myGW',
                                           method='DELETE',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

    def test_06_password_censored_in_response(self):
        """GET /smsgateway/ must censor PASSWORD options in the response."""
        # Create a gateway with a PASSWORD option
        param = {
            "name": "mySecureGW",
            "module": "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider",
            "description": "gateway with password",
            "option.URL": "http://sms.example.com",
            "option.USERNAME": "apiuser",
            "option.PASSWORD": "supersecret123",
        }
        with self.app.test_request_context('/smsgateway',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # Verify the PASSWORD is censored in the GET response
        with self.app.test_request_context('/smsgateway/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            sms_gw = result.get("value")[0]
            # PASSWORD must be censored
            self.assertEqual(sms_gw.get("options").get("PASSWORD"), CENSORED)
            # Non-sensitive options must NOT be censored
            self.assertEqual(sms_gw.get("options").get("URL"), "http://sms.example.com")
            self.assertEqual(sms_gw.get("options").get("USERNAME"), "apiuser")

        # Clean up
        with self.app.test_request_context('/smsgateway/mySecureGW',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            self.app.full_dispatch_request()

    def test_07_password_not_overwritten_by_censored(self):
        """Saving a gateway with __CENSORED__ password must preserve the original password."""
        # Create a gateway with a PASSWORD option
        param = {
            "name": "myPreserveGW",
            "module": "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider",
            "description": "gateway for preserve test",
            "option.URL": "http://sms.example.com",
            "option.PASSWORD": "original_secret",
        }
        with self.app.test_request_context('/smsgateway',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            gw_id = res.json["result"]["value"]

        # Now update the gateway, sending CENSORED as the password (simulating UI re-save)
        param_update = {
            "name": "myPreserveGW",
            "module": "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider",
            "description": "updated description",
            "option.URL": "http://sms-new.example.com",
            "option.PASSWORD": CENSORED,
        }
        with self.app.test_request_context('/smsgateway',
                                           data=param_update,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # Verify the password is still functional (not literally __CENSORED__)
        # We check via the model directly since the API censors the response
        from privacyidea.lib.smsprovider.SMSProvider import get_smsgateway
        gw_list = get_smsgateway(identifier="myPreserveGW")
        gw = gw_list[0]
        # option_dict decrypts - should return original password
        self.assertEqual(gw.option_dict.get("PASSWORD"), "original_secret")
        # Other options should be updated
        self.assertEqual(gw.option_dict.get("URL"), "http://sms-new.example.com")

        # Clean up
        with self.app.test_request_context('/smsgateway/myPreserveGW',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            self.app.full_dispatch_request()
