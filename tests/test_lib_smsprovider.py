__doc__ = """
This test file tests the modules:
 lib.smsprovider.httpsmsprovider
 lib.smsprovider.sipgateprovider
 lib.smsprovider.smtpsmsprovider
 lib.smsprovider.smppsmsprovider
 lib.smsprovider.scriptsmsprovider
"""

import os

import mock
import responses
from sqlalchemy import select

from privacyidea.lib.error import ConfigAdminError
from privacyidea.lib.smsprovider.FirebaseProvider import FirebaseConfig
from privacyidea.lib.smsprovider.HttpSMSProvider import HttpSMSProvider
from privacyidea.lib.smsprovider.SMSProvider import ISMSProvider
from privacyidea.lib.smsprovider.SMSProvider import (SMSError,
                                                     get_sms_provider_class,
                                                     set_smsgateway,
                                                     get_smsgateway,
                                                     delete_smsgateway,
                                                     delete_smsgateway_option,
                                                     delete_smsgateway_header,
                                                     delete_smsgateway_key_generic,
                                                     create_sms_instance,
                                                     _is_sensitive_key)
from privacyidea.lib.smsprovider.ScriptSMSProvider import ScriptSMSProvider, SCRIPT_WAIT
from privacyidea.lib.smsprovider.SipgateSMSProvider import SipgateSMSProvider
from privacyidea.lib.smsprovider.SipgateSMSProvider import URL
from privacyidea.lib.smsprovider.SmppSMSProvider import SmppSMSProvider
from privacyidea.lib.smsprovider.SmtpSMSProvider import SmtpSMSProvider
from privacyidea.lib.smtpserver import add_smtpserver
from privacyidea.models import SMSGatewayOption, db
from . import smppmock
from . import smtpmock
from .base import MyTestCase


class SMSTestCase(MyTestCase):

    def test_00_SMSError(self):
        err = SMSError(100, "Some Error")
        text = "{0!r}".format(err)
        self.assertTrue(text == "SMSError(error_id=100, description='Some "
                                "Error')", text)

        text = "{0!s}".format(err)
        self.assertTrue(text == "Some Error", text)

    def test_01_get_provider_class(self):
        _provider = get_sms_provider_class(
            "privacyidea.lib.smsprovider.SipgateSMSProvider",
            "SipgateSMSProvider")

        _provider = get_sms_provider_class(
            "privacyidea.lib.smsprovider.HttpSMSProvider",
            "HttpSMSProvider")

        _provider = get_sms_provider_class(
            "privacyidea.lib.smsprovider.SmtpSMSProvider",
            "SmtpSMSProvider")

        _provider = get_sms_provider_class(
            "privacyidea.lib.smsprovider.SmppSMSProvider",
            "SmppSMSProvider")

        # A non-existing module will raise an error
        self.assertRaises(Exception,
                          get_sms_provider_class,
                          "DoesNotExist",
                          "DoesNotExist")

        # Any other arbitrary class will raise an error, since it has not
        # submit_method
        self.assertRaises(Exception,
                          get_sms_provider_class,
                          "privacyidea.lib.smsprovider.SMSProvider",
                          "SMSError")

    def test_02_create_modify_delete_smsgateway_configuration(self):
        identifier = "myGW"
        provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider"
        id = set_smsgateway(identifier, provider_module, description="test",
                            options={"HTTP_METHOD": "POST",
                                     "URL": "example.com"},
                            headers={"Authorization": "QWERTZ",
                                     "BANANA": "will be eaten"})
        self.assertTrue(id > 0)

        # Check everything is stored correctly
        gw = get_smsgateway(id=id)
        my_gw = gw[0]
        self.assertEqual(my_gw.description, "test")
        self.assertEqual(provider_module, my_gw.providermodule)
        option_keys = {option.Key for option in my_gw.options}
        self.assertSetEqual({"HTTP_METHOD", "URL", "Authorization", "BANANA"}, option_keys)
        for option in my_gw.options:
            self.assertEqual(id, option.gateway_id)
            if option.Key == "HTTP_METHOD":
                self.assertEqual(option.Value, "POST")
                self.assertEqual(option.Type, "option")
            if option.Key == "URL":
                self.assertEqual(option.Value, "example.com")
                self.assertEqual(option.Type, "option")
            if option.Key == "Authorization":
                self.assertEqual(option.Value, "QWERTZ")
                self.assertEqual(option.Type, "header")
            if option.Key == "BANANA":
                self.assertEqual(option.Value, "will be eaten")
                self.assertEqual(option.Type, "header")

        # update the description
        set_smsgateway(identifier, provider_module,
                       description="This is a sensible description")
        gw = get_smsgateway(id=id)
        self.assertEqual(gw[0].description, "This is a sensible description")
        # All options are removed when updating the smsgateway without options
        self.assertEqual(0, len(gw[0].options.all()))

        # update some options
        set_smsgateway(identifier, provider_module,
                       options={"HTTP_METHOD": "POST",
                                "URL": "example.com",
                                "IDENTICAL_KEY": "new option"},
                       headers={"Authorization": "ValueChanged",
                                "IDENTICAL_KEY": "new header",
                                "URL": "URL_in_headers"})
        gw = get_smsgateway(id=id)
        self.assertEqual(len(gw[0].option_dict), 3)
        self.assertEqual(gw[0].option_dict.get("HTTP_METHOD"), "POST")
        self.assertEqual(gw[0].option_dict.get("URL"), "example.com")
        self.assertEqual(gw[0].option_dict.get("IDENTICAL_KEY"), "new option")
        self.assertEqual(gw[0].header_dict.get("Authorization"), "ValueChanged")
        self.assertEqual(gw[0].header_dict.get("BANANA"), None)
        self.assertEqual(gw[0].header_dict.get("IDENTICAL_KEY"), "new header")
        self.assertEqual(gw[0].header_dict.get("URL"), "URL_in_headers")
        self.assertIsNone(gw[0].description)

        # delete a single option
        r = delete_smsgateway_option(id, "URL")
        gw = get_smsgateway(id=id)
        self.assertEqual(len(gw[0].option_dict), 2)
        self.assertEqual(gw[0].option_dict.get("HTTP_METHOD"), "POST")
        self.assertEqual(gw[0].option_dict.get("URL"), None)
        self.assertEqual(gw[0].option_dict.get("IDENTICAL_KEY"), "new option")

        # delete a single header
        r = delete_smsgateway_header(id, "IDENTICAL_KEY")
        gw = get_smsgateway(id=id)
        self.assertEqual(gw[0].header_dict.get("IDENTICAL_KEY"), None)

        # delete a single header via generic function
        r = delete_smsgateway_key_generic(id, "URL", Type="header")
        gw = get_smsgateway(id=id)
        self.assertEqual(gw[0].header_dict.get("URL"), None)

        # finally delete the gateway definition
        r = delete_smsgateway(identifier)
        self.assertEqual(r, id)

        # check that there are no remaining options
        options = db.session.scalars(select(SMSGatewayOption)).all()
        for option in options:
            self.assertIsNotNone(option.gateway_id)
            self.assertNotEqual(r, option.gateway_id)

        # delete successful?
        gw = get_smsgateway()
        self.assertEqual(len(gw), 0)

    def test_03_create_instance_by_identifier(self):
        # SMS gateway definition
        identifier = "myGW"
        provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider" \
                          ".HttpSMSProvider"
        id = set_smsgateway(identifier, provider_module, description="test",
                            options={"HTTP_METHOD": "POST",
                                     "URL": "example.com"},
                            headers={"Authorization": "QWERTZ"})
        self.assertTrue(id > 0)

        sms = create_sms_instance(identifier)

        self.assertEqual(sms.smsgateway.option_dict.get("URL"), "example.com")
        self.assertEqual(sms.smsgateway.option_dict.get("HTTP_METHOD"),
                         "POST")
        self.assertEqual(sms.smsgateway.header_dict.get("Authorization"), "QWERTZ")
        self.assertEqual(sms.smsgateway.option_dict.get("Authorization"), None)

    def test_04_REGEXP(self):
        p = ISMSProvider._mangle_phone("+49 123/456-78", {"REGEXP": "/[+-/. ]//"})
        self.assertEqual("4912345678", p)

        # Replace + with 00
        p = ISMSProvider._mangle_phone("+49 123/456-78", {"REGEXP": r"/\+/00/"})
        self.assertEqual("0049 123/456-78", p)
        p = ISMSProvider._mangle_phone("+49 123/456-78", {"REGEXP": r"/[\+/]//"})
        self.assertEqual("49 123456-78", p)

        # An invalid regexp is caught and a log error is written. The same
        # phone number is returned
        p = ISMSProvider._mangle_phone("+49 123/456-78", {"REGEXP": r"/+/00/"})
        self.assertEqual("+49 123/456-78", p)

        # Only use leading numbers and not the rest
        p = ISMSProvider._mangle_phone("12345abcdef", {"REGEXP": r"/^([0-9]+).*/\1/"})
        self.assertEqual("12345", p)

        # Known limitation: The slash in the replace statement does not work!
        p = ISMSProvider._mangle_phone("12.34.56.78", {"REGEXP": r"/\./\//"})
        self.assertEqual("12.34.56.78", p)

    def test_05_export_censor_smsgateway(self):
        from privacyidea.lib.smsprovider.SMSProvider import (set_smsgateway,
                                                             export_smsgateway,
                                                             delete_smsgateway)
        from privacyidea.lib.crypto import CENSORED
        provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider"
        set_smsgateway("expgw", provider_module,
                       options={"PASSWORD": "smspw", "URL": "http://example.com"},
                       headers={"X-Secret": "headertoken", "X-Plain": "ok"})
        # secret-looking options/headers are censored, the rest is kept
        censored = export_smsgateway(censor=True)
        self.assertEqual(censored["expgw"]["options"]["PASSWORD"], CENSORED)
        self.assertEqual(censored["expgw"]["options"]["URL"], "http://example.com")
        self.assertEqual(censored["expgw"]["headers"]["X-Secret"], CENSORED)
        self.assertEqual(censored["expgw"]["headers"]["X-Plain"], "ok")
        # without censoring the values are returned as stored
        plain = export_smsgateway()
        self.assertEqual(plain["expgw"]["options"]["PASSWORD"], "smspw")
        delete_smsgateway("expgw")

    def test_06_export_censor_explicit_secret_option(self):
        # A value marked secret via secret_options / secret_headers is stored
        # encrypted even when its key name carries no PASSWORD/SECRET hint. Such
        # a value must still be censored on export - otherwise a "censored"
        # export leaks it in clear text.
        from privacyidea.lib.smsprovider.SMSProvider import (set_smsgateway,
                                                             export_smsgateway,
                                                             delete_smsgateway)
        from privacyidea.lib.crypto import CENSORED
        provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider"
        set_smsgateway("expgw2", provider_module,
                       options={"apitoken": "SUPERSECRET", "URL": "http://example.com"},
                       headers={"X-Auth": "headertoken", "X-Plain": "ok"},
                       secret_options={"apitoken"},
                       secret_headers={"X-Auth"})
        censored = export_smsgateway(censor=True)
        self.assertEqual(censored["expgw2"]["options"]["apitoken"], CENSORED)
        self.assertEqual(censored["expgw2"]["headers"]["X-Auth"], CENSORED)
        # non-secret values are still returned as stored
        self.assertEqual(censored["expgw2"]["options"]["URL"], "http://example.com")
        self.assertEqual(censored["expgw2"]["headers"]["X-Plain"], "ok")
        delete_smsgateway("expgw2")


class SmtpSMSTestCase(MyTestCase):
    missing_config = {"MAILSERVER": "localhost:25"}

    simple_config = {"MAILSERVER": "localhost:25",
                     "MAILTO": "recp@example.com",
                     "MAILSENDER": "pi@example.com"}

    wrong_config = {"MAILSERVER": "this.server.does.not.exist",
                    "MAILTO": "recp@example.com",
                    "MAILSENDER": "pi@example.com"}

    auth_config = {"MAILSERVER": "localhost:25",
                   "MAILTO": "recp@example.com",
                   "MAILSENDER": "pi@example.com",
                   "MAILUSER": "username",
                   "MAILPASSWORD": "sosecret"}

    identifier_config = {"MAILTO": "recp@example.com",
                         "IDENTIFIER": "myServer"}

    def setUp(self):
        self.missing_provider = SmtpSMSProvider()
        self.missing_provider.load_config(self.missing_config)

        self.simple_provider = SmtpSMSProvider()
        self.simple_provider.load_config(self.simple_config)

        self.wrong_provider = SmtpSMSProvider()
        self.wrong_provider.load_config(self.wrong_config)

        self.auth_provider = SmtpSMSProvider()
        self.auth_provider.load_config(self.auth_config)

        self.identifier_provider = SmtpSMSProvider()
        self.identifier_provider.load_config(self.identifier_config)

    def test_01_missing_config(self):
        self.assertRaises(SMSError, self.missing_provider.submit_message,
                          "1234356", "Hello")

    @smtpmock.activate
    def test_02_simple_config_success(self):
        smtpmock.setdata(response={"recp@example.com": (200, "OK")})
        r = self.simple_provider.submit_message("123456", "Hello")
        self.assertTrue(r)

    @smtpmock.activate
    def test_03_simple_config_fail(self):
        smtpmock.setdata(response={"recp@example.com": (550,
                                                        "mailbox unavailable")})
        self.assertRaises(SMSError, self.simple_provider.submit_message,
                          "123456", "Hello")

    def test_04_generic_exception(self):
        self.assertRaises(Exception, self.wrong_provider.submit_message,
                          "123456", "Hello")

    @smtpmock.activate
    def test_05_auth_config_success(self):
        smtpmock.setdata(response={"recp@example.com": (200, "OK")})
        r = self.auth_provider.submit_message("123456", "Hello")
        self.assertTrue(r)

    @smtpmock.activate
    def test_06_auth_config_fail(self):
        smtpmock.setdata(response={},
                         authenticated=False,
                         config=self.auth_config)
        self.assertRaises(SMSError, self.auth_provider.submit_message,
                          "123456", "Hello")

    @smtpmock.activate
    def test_07_identifier_config_success(self):
        r = add_smtpserver("myServer", "1.2.3.4", sender="mail@pi.org")
        self.assertTrue(r > 0)
        smtpmock.setdata(response={"recp@example.com": (200, "OK")})
        r = self.identifier_provider.submit_message("123456", "Halo")
        self.assertTrue(r)

    @smtpmock.activate
    def test_08_smsgateway_success(self):
        r = add_smtpserver("myServer", "1.2.3.4", sender="mail@pi.org")
        self.assertTrue(r > 0)
        smtpmock.setdata(response={"recp@example.com": (200, "OK")})

        identifier = "myMail"
        provider_module = "privacyidea.lib.smsprovider.SmtpSMSProvider" \
                          ".SmtpSMSProvider"
        id = set_smsgateway(identifier, provider_module, description="test",
                            options={"SMTPIDENTIFIER": "myServer",
                                     "MAILTO": "recp@example.com",
                                     "SUBJECT": "{phone}",
                                     "BODY": "{otp}"})
        self.assertTrue(id > 0)
        sms = create_sms_instance(identifier)
        with mock.patch("logging.Logger.debug") as log:
            r = sms.submit_message("123456", "Halo")
            self.assertTrue(r)
            log.assert_any_call("submitting message {0!r} to {1!s}".format("Halo", "123456"))

    @smtpmock.activate
    def test_09_send_sms_regexp_success(self):
        regexp_config = {"MAILSERVER": "localhost:25",
                         "MAILTO": "recp@example.com",
                         "MAILSENDER": "pi@example.com",
                         "MAILUSER": "username",
                         "MAILPASSWORD": "sosecret",
                         "REGEXP": "/[+-/. ]//"}

        self.regexp_provider = SmtpSMSProvider()
        self.regexp_provider.load_config(regexp_config)

        with mock.patch("logging.Logger.debug") as log:
            smtpmock.setdata(response={"recp@example.com": (200, "OK")})
            # Here we need to send the SMS
            r = self.regexp_provider.submit_message("+49 123/456-78", "Hello")
            self.assertTrue(r)
            log.assert_any_call("submitting message {0!r} to {1!s}".format("Hello", "4912345678"))


class SipgateSMSTestCase(MyTestCase):
    url = URL
    config = {'USERNAME': "user",
              'PASSWORD': "password",
              'PROXY': "https://user:pw@1.2.3.4:8089"}

    def setUp(self):
        self.provider = SipgateSMSProvider()
        self.provider.load_config(self.config)

    @responses.activate
    def test_01_success(self):
        responses.add(responses.POST,
                      self.url)
        # Here we need to send the SMS
        r = self.provider.submit_message("123456", "Hello")
        self.assertTrue(r)

    @responses.activate
    def test_02_fail(self):
        responses.add(responses.POST,
                      self.url, status=402)
        # Here we need to send the SMS
        self.assertRaises(SMSError, self.provider.submit_message,
                          "123456", "Hello")

    @responses.activate
    def test_03_send_sms_regexp_success(self):
        config_regexp = {'USERNAME': "user",
                         'PASSWORD': "password",
                         'PROXY': "https://user:pw@1.2.3.4:8089",
                         "REGEXP": "/[+-/. ]//"}
        regexp_provider = SipgateSMSProvider()
        regexp_provider.load_config(config_regexp)
        responses.add(responses.POST,
                      self.url)
        # Here we need to send the SMS
        with mock.patch("logging.Logger.debug") as log:
            r = regexp_provider.submit_message("+49 123/456-78", "Hello")
            self.assertTrue(r)
            log.assert_any_call("submitting message {0!r} to {1!s}".format("Hello", "4912345678"))

    @responses.activate
    def test_08_smsgateway_success(self):
        responses.add(responses.POST,
                      self.url)
        identifier = "mySMS"
        provider_module = "privacyidea.lib.smsprovider.SipgateSMSProvider" \
                          ".SipgateSMSProvider"
        id = set_smsgateway(identifier, provider_module, description="test",
                            options=self.config)
        self.assertTrue(id > 0)
        sms = create_sms_instance(identifier)
        with mock.patch("logging.Logger.debug") as log:
            r = sms.submit_message("123456", "Hello")
            self.assertTrue(r)
            log.assert_any_call("submitting message {0!r} to {1!s}".format("Hello", "123456"))


class ScriptSMSTestCase(MyTestCase):
    directory = "{0!s}/tests/testdata/scripts/".format(os.getcwd())

    def test_01_fail_no_script(self):
        # The script does not exist
        identifier = "myScriptSMS"
        config = {"background": SCRIPT_WAIT,
                  "script": "sms-script-does-not-exist.sh"}
        provider_module = "privacyidea.lib.smsprovider.ScriptSMSProvider" \
                          ".ScriptSMSProvider"
        id = set_smsgateway(identifier, provider_module, description="test",
                            options=config)
        self.assertTrue(id > 0)
        sms = ScriptSMSProvider(smsgateway=get_smsgateway(identifier)[0], directory=self.directory)
        self.assertRaises(SMSError, sms.submit_message, "123456", "Hello")
        delete_smsgateway(identifier)

        # We bail out, if no smsgateway definition is given!
        sms = ScriptSMSProvider(directory=self.directory)
        self.assertRaises(SMSError, sms.submit_message, "123456", "Hello")

    def test_02_success(self):
        # the script runs successfully
        identifier = "myScriptSMS"
        config = {"background": SCRIPT_WAIT,
                  "script": "success.sh",
                  "REGEXP": "/[+-/. ]//"}
        provider_module = "privacyidea.lib.smsprovider.ScriptSMSProvider" \
                          ".ScriptSMSProvider"
        id = set_smsgateway(identifier, provider_module, description="test",
                            options=config)
        self.assertTrue(id > 0)
        sms = ScriptSMSProvider(smsgateway=get_smsgateway(identifier)[0], directory=self.directory)
        with mock.patch("logging.Logger.info") as log:
            r = sms.submit_message("+49 123/456-78", "Hello")
            self.assertTrue(r)
            log.assert_any_call("SMS delivered to 4912345678.")
        delete_smsgateway(identifier)

    def test_02_fail(self):
        # The script returns a failing rcode
        identifier = "myScriptSMS"
        config = {"background": SCRIPT_WAIT,
                  "script": "fail.sh"}
        provider_module = "privacyidea.lib.smsprovider.ScriptSMSProvider" \
                          ".ScriptSMSProvider"
        id = set_smsgateway(identifier, provider_module, description="test",
                            options=config)
        self.assertTrue(id > 0)
        sms = ScriptSMSProvider(smsgateway=get_smsgateway(identifier)[0], directory=self.directory)
        self.assertRaises(SMSError, sms.submit_message, "123456", "Hello")
        delete_smsgateway(identifier)

    def test_03_parameters(self):
        # check parameters
        params = ScriptSMSProvider.parameters()
        self.assertFalse(params.get("options_allowed"))
        self.assertIn("script", params.get("parameters"))
        self.assertIn("background", params.get("parameters"))


class HttpSMSTestCase(MyTestCase):
    post_url = "http://smsgateway.com/sms_send_api.cgi"
    config_post = {"URL": post_url,
                   "PARAMETER": {"from": "0170111111",
                                 "password": "yoursecret",
                                 "sender": "name",
                                 "account": "company_ltd"},
                   "SMS_TEXT_KEY": "text",
                   "SMS_PHONENUMBER_KEY": "destination",
                   "HTTP_Method": "POST",
                   "PROXY": "http://username:password@your-proxy:8080",
                   "RETURN_SUCCESS": "ID"
                   }

    config_regexp = {"URL": post_url,
                     "PARAMETER": {"from": "0170111111",
                                   "password": "yoursecret",
                                   "sender": "name",
                                   "account": "company_ltd"},
                     "SMS_TEXT_KEY": "text",
                     "SMS_PHONENUMBER_KEY": "destination",
                     "HTTP_Method": "POST",
                     "PROXY": "http://username:password@your-proxy:8080",
                     "RETURN_SUCCESS": "ID",
                     "REGEXP": "/[+-/. ]//"
                     }

    get_url = "http://api.clickatell.com/http/sendmsg"
    config_get = {"URL": get_url,
                  "PARAMETER": {"user": "username",
                                "password": "askme",
                                "api_id": "12980436"},
                  "SMS_TEXT_KEY": "text",
                  "SMS_PHONENUMBER_KEY": "to",
                  "HTTP_Method": "GET",
                  "PROXY": "http://user:pass@1.2.3.4:8080",
                  "RETURN_FAIL": "Failed"
                  }

    simple_url = "http://some.other.service"
    config_simple = {"URL": simple_url,
                     "PARAMETER": {"user": "username",
                                   "password": "askme",
                                   "api_id": "12980436"},
                     "SMS_TEXT_KEY": "text",
                     "SMS_PHONENUMBER_KEY": "to",
                     }

    missing_url = "http://some.missing.url"
    config_missing = {"PARAMETER": {"user": "username",
                                    "password": "askme",
                                    "api_id": "12980436"},
                      "SMS_TEXT_KEY": "text",
                      "SMS_PHONENUMBER_KEY": "to",
                      }

    basic_url = "https://fitz:sosecret@secret.gateway/some/path"
    config_basicauth = {"URL": basic_url,
                        "PARAMETER": {"user": "username",
                                      "password": "askme",
                                      "api_id": "12980436"},
                        "SMS_TEXT_KEY": "text",
                        "SMS_PHONENUMBER_KEY": "to",
                        }

    success_body = "ID 12345"
    fail_body = "Sent SMS Failed"

    def setUp(self):
        self.post_provider = HttpSMSProvider()
        self.post_provider.load_config(self.config_post)

        self.regexp_provider = HttpSMSProvider()
        self.regexp_provider.load_config(self.config_regexp)

        self.get_provider = HttpSMSProvider()
        self.get_provider.load_config(self.config_get)

        self.simple_provider = HttpSMSProvider()
        self.simple_provider.load_config(self.config_simple)

        self.auth_provider = HttpSMSProvider()
        self.auth_provider.load_config(self.config_basicauth)

        self.missing_provider = HttpSMSProvider()
        self.missing_provider.load_config(self.config_missing)

    @responses.activate
    def test_01_send_sms_post_success(self):
        responses.add(responses.POST,
                      self.post_url,
                      body=self.success_body)
        # Here we need to send the SMS
        r = self.post_provider.submit_message("123456", "Hello")
        self.assertTrue(r)

    @responses.activate
    def test_01_send_sms_regexp_success(self):
        responses.add(responses.POST,
                      self.post_url,
                      body=self.success_body)
        # Here we need to send the SMS
        with mock.patch("logging.Logger.debug") as log:
            r = self.regexp_provider.submit_message("+49 123/456-78", "Hello")
            self.assertTrue(r)
            log.assert_any_call("submitting message {0!r} to {1!s}".format("Hello", "4912345678"))

    @responses.activate
    def test_02_send_sms_post_fail(self):
        responses.add(responses.POST,
                      self.post_url,
                      body=self.fail_body)
        # Here we need to send the SMS
        self.assertRaises(SMSError, self.post_provider.submit_message,
                          "123456", "Hello")

    @responses.activate
    def test_03_send_sms_get_success(self):
        responses.add(responses.GET,
                      self.get_url,
                      body=self.success_body)
        # Here we need to send the SMS
        r = self.get_provider.submit_message("123456", "Hello")
        self.assertTrue(r)

    @responses.activate
    def test_04_send_sms_get_fail(self):
        responses.add(responses.GET,
                      self.get_url,
                      body=self.fail_body)
        # Here we need to send the SMS
        self.assertRaises(SMSError, self.get_provider.submit_message,
                          "123456", "Hello")

    @responses.activate
    def test_05_simple_service_success(self):
        responses.add(responses.GET,
                      self.simple_url,
                      status=200)
        r = self.simple_provider.submit_message("123456", "Hello")
        self.assertTrue(r)

    @responses.activate
    def test_06_simple_service_fail(self):
        responses.add(responses.GET,
                      self.simple_url,
                      body="noting",
                      status=401)
        self.assertRaises(SMSError, self.simple_provider.submit_message,
                          "123456", "Hello")

    @responses.activate
    def test_07_missing_fail(self):
        responses.add(responses.GET,
                      self.missing_url)
        self.assertRaises(SMSError, self.missing_provider.submit_message,
                          "123456", "Hello")

    @responses.activate
    def test_08_auth_success(self):
        responses.add(responses.GET,
                      self.basic_url)
        r = self.auth_provider.submit_message("123456", "Hello")
        self.assertTrue(r)

    @responses.activate
    def test_08_auth_fail(self):
        responses.add(responses.GET,
                      self.basic_url,
                      status=401)
        self.assertRaises(SMSError, self.missing_provider.submit_message,
                          "123456", "Hello")

    @responses.activate
    def test_10_new_smsgateway(self):
        identifier = "myGW"
        provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider" \
                          ".HttpSMSProvider"
        id = set_smsgateway(identifier, provider_module, description="test",
                            options={"HTTP_METHOD": "POST",
                                     "URL": "http://example.com",
                                     "SEND_DATA_AS_JSON": "no",
                                     "RETURN_SUCCESS": "ID",
                                     "text": "{otp}",
                                     "phone": "{phone}"},
                            headers={"Authorization": "QWERTZ"})
        self.assertTrue(id > 0)

        sms = create_sms_instance(identifier)

        responses.add(responses.POST,
                      "http://example.com",
                      body=self.success_body)
        # Here we need to send the SMS
        r = sms.submit_message("123456", "Hello")
        self.assertTrue(r)

        delete_smsgateway(identifier)

    @responses.activate
    def test_11_send_nonascii_sms_post_success(self):
        responses.add(responses.POST,
                      self.post_url,
                      body=self.success_body)
        # Here we need to send the SMS
        r = self.post_provider.submit_message("123456", "Hallöle Smørrebrød")
        self.assertTrue(r)

    @responses.activate
    def test_12_send_sms_post_success_as_json(self):
        identifier = "myGWJSON"
        provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider" \
                          ".HttpSMSProvider"
        id = set_smsgateway(identifier, provider_module, description="test",
                            options={"HTTP_METHOD": "POST",
                                     "URL": "http://some.other.service",
                                     "RETURN_SUCCESS": "ID",
                                     "SEND_DATA_AS_JSON": "yes",
                                     "text": "{otp}",
                                     "phone": "{phone}",
                                     "receiverlist": '[{"phone": "{phone}", "message": "{otp}"}]'},
                            headers={"Authorization": "QWERTZ"})
        self.assertTrue(id > 0)
        provider = create_sms_instance(identifier=identifier)

        # also check that the parameters are sent as json
        responses.add(responses.POST,
                      "http://some.other.service",
                      body=self.success_body)
        # Here we need to send the SMS
        with mock.patch("logging.Logger.debug") as mock_log:
            r = provider.submit_message("123456", 'Hello: 7')
            self.assertTrue(r)
            for x in mock_log.call_args_list:
                print(x[0][0])
            call = [x[0][0] for x in mock_log.call_args_list if x[0][0].startswith('passing JSON data')][0]
            # JSON data content is hidden for security
            self.assertIn('passing JSON data (content hidden for security)', call)
        delete_smsgateway(identifier)


class SmppSMSTestCase(MyTestCase):
    config = {'SMSC_HOST': "192.168.1.1",
              'SMSC_PORT': "1234",
              'SYSTEM_ID': "privacyIDEA",
              'PASSWORD': "secret",
              'S_ADDR_TON': "0x5",
              'S_ADDR_NPI': "0x1",
              'S_ADDR': "privacyIDEA",
              'D_ADDR_TON': "0x5",
              'D_ADDR_NPI': "0x1"}

    provider_module = "privacyidea.lib.smsprovider.SmppSMSProvider" \
                      ".SmppSMSProvider"

    def setUp(self):
        # Use the gateway definition for configuring the provider
        identifier = "mySmppGW"
        id = set_smsgateway(identifier, self.provider_module, description="test",
                            options=self.config)
        self.assertTrue(id > 0)
        self.provider = create_sms_instance(identifier=identifier)
        self.assertEqual(type(self.provider), SmppSMSProvider)

    def test_00_config(self):
        r = SmppSMSProvider.parameters()
        self.assertEqual(r.get("options_allowed"), False)
        params = r.get("parameters")
        self.assertEqual(params.get("SMSC_HOST").get("required"), True)

    def test_00_errors(self):
        # No smsgateway defined
        s = SmppSMSProvider()
        self.assertRaises(SMSError, s.submit_message, "phone", "message")

        # No host defined
        set_smsgateway("missing_host", self.provider_module,
                       options={"SMSC_PORT": "1234"})
        p = create_sms_instance(identifier="missing_host")
        self.assertRaises(SMSError, p.submit_message, "phone", "message")
        delete_smsgateway("missing_host")

        # No port defined
        set_smsgateway("missing_port", self.provider_module,
                       options={"SMSC_HOST": "1.1.1.1"})
        p = create_sms_instance(identifier="missing_port")
        self.assertRaises(SMSError, p.submit_message, "phone", "message")
        delete_smsgateway("missing_port")

    @smppmock.activate
    def test_01_success(self):
        # Here we need to send the SMS
        smppmock.setdata(connection_success=True,
                         systemid="privacyIDEA",
                         password="secret")
        r = self.provider.submit_message("123456", "Hello")
        self.assertTrue(r)

    @smppmock.activate
    def test_02_fail_connection(self):
        smppmock.setdata(connection_success=False,
                         systemid="privacyIDEA",
                         password="secret")
        self.assertRaises(SMSError, self.provider.submit_message, "123456", "hello")

    @smppmock.activate
    def test_03_fail_wrong_credentials(self):
        smppmock.setdata(connection_success=True,
                         systemid="privacyIDEA",
                         password="wrong")
        self.assertRaises(SMSError, self.provider.submit_message, "123456", "hello")

    @smppmock.activate
    def test_04_send_sms_regexp_success(self):
        config_regexp = {'SMSC_HOST': "192.168.1.1",
                         'SMSC_PORT': "1234",
                         'SYSTEM_ID': "privacyIDEA",
                         'PASSWORD': "secret",
                         'S_ADDR_TON': "0x5",
                         'S_ADDR_NPI': "0x1",
                         'S_ADDR': "privacyIDEA",
                         'D_ADDR_TON': "0x5",
                         'D_ADDR_NPI': "0x1",
                         "REGEXP": "/[+-/. ]//"}

        identifier_regexp = "myregexpSmppGW"
        id_regexp = set_smsgateway(identifier_regexp, self.provider_module, description="test",
                                   options=config_regexp)
        self.assertTrue(id_regexp > 0)
        regexp_provider = create_sms_instance(identifier=identifier_regexp)
        self.assertEqual(type(regexp_provider), SmppSMSProvider)
        smppmock.setdata(connection_success=True,
                         systemid="privacyIDEA",
                         password="secret")
        # Here we need to send the SMS
        with mock.patch("logging.Logger.debug") as log:
            r = regexp_provider.submit_message("+49 123/456-78", "Hello")
            self.assertTrue(r)
            log.assert_any_call("submitting message {0!r} to {1!s}".format("Hello", "4912345678"))

        delete_smsgateway(identifier_regexp)


class FirebaseProviderTestCase(MyTestCase):

    def test_set_configuration_success(self):
        valid_file = "tests/testdata/firebase-test.json"
        valid_config = {FirebaseConfig.JSON_CONFIG: valid_file}
        fb_id = set_smsgateway("test",
                               'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                               "", valid_config)
        self.assertGreater(fb_id, 0)
        delete_smsgateway("test")

    def test_set_configuration_fail(self):

        try:
            # Invalid file path
            invalid_config = {FirebaseConfig.JSON_CONFIG: "non-existing-file.json"}
            with self.assertRaises(ConfigAdminError) as context:
                set_smsgateway("test",
                               'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                               "", invalid_config)
            self.assertEqual("The JSON config file could not be found.", str(context.exception.message))

            # json config completely missing
            with self.assertRaises(ConfigAdminError) as context:
                set_smsgateway("test",
                               'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                               "", {})
            self.assertEqual("No JSON config file provided.", str(context.exception.message))

            # non-json file provided
            invalid_config = {FirebaseConfig.JSON_CONFIG: "tests/testdata/passwd"}
            with self.assertRaises(ConfigAdminError) as context:
                set_smsgateway("test",
                               'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider',
                               "", invalid_config)
            self.assertEqual("The config file has an invalid JSON format.", str(context.exception.message))
        finally:
            # Ensure no invalid gateway configuration with identifier "test" remains.
            try:
                delete_smsgateway("test")
            except Exception:
                # Ignore cleanup errors; gateway may not have been created.
                pass


class SendSmsIdentifierMetricsTestCase(MyTestCase):
    """Cover the metric-recording wrapper in ``send_sms_identifier``.

    The function builds the provider via ``create_sms_instance`` and then
    times / counts the call to ``submit_message``. We patch the factory so
    these tests don't need a real gateway in the database.
    """

    def setUp(self):
        from privacyidea.models import db as _db
        from privacyidea.models.metric_aggregate import MetricAggregate
        _db.session.query(MetricAggregate).delete()
        _db.session.commit()

    def _read_counter(self, result):
        from privacyidea.lib.metrics import get_metrics
        rows = get_metrics(name="sms_send_total")
        match = [r for r in rows if r["labels"].get("result") == result
                 and r["labels"].get("gateway") == "gw1"]
        return sum(r["count"] for r in match)

    def test_success_records_ok_counter(self):
        from privacyidea.lib.smsprovider import SMSProvider as smsmod
        fake = mock.MagicMock()
        fake.submit_message.return_value = True
        with mock.patch.object(smsmod, "create_sms_instance", return_value=fake):
            self.assertTrue(smsmod.send_sms_identifier("gw1", "+1555", "hello"))
        self.assertEqual(self._read_counter("ok"), 1)
        self.assertEqual(self._read_counter("failed"), 0)

    def test_returning_false_records_failed_counter(self):
        # ISMSProvider.submit_message is documented as boolean-returning, so a
        # provider that returns False (without raising) must still increment the
        # failed counter, not ok.
        from privacyidea.lib.smsprovider import SMSProvider as smsmod
        fake = mock.MagicMock()
        fake.submit_message.return_value = False
        with mock.patch.object(smsmod, "create_sms_instance", return_value=fake):
            self.assertFalse(smsmod.send_sms_identifier("gw1", "+1555", "hello"))
        self.assertEqual(self._read_counter("failed"), 1)
        self.assertEqual(self._read_counter("ok"), 0)

    def test_exception_records_failed_counter_and_reraises(self):
        # The path codecov flagged: the provider raises, we record duration +
        # failed counter, then re-raise so the caller still sees the error.
        from privacyidea.lib.smsprovider import SMSProvider as smsmod
        fake = mock.MagicMock()
        fake.submit_message.side_effect = SMSError(500, "gateway is down")
        with mock.patch.object(smsmod, "create_sms_instance", return_value=fake):
            with self.assertRaises(SMSError):
                smsmod.send_sms_identifier("gw1", "+1555", "hello")
        self.assertEqual(self._read_counter("failed"), 1)
        self.assertEqual(self._read_counter("ok"), 0)
        # And the duration histogram must have been written too (count of 1).
        from privacyidea.lib.metrics import get_metrics
        durations = get_metrics(name="sms_send_duration_seconds")
        durations = [d for d in durations if d["labels"].get("gateway") == "gw1"]
        self.assertEqual(len(durations), 1)
        self.assertEqual(durations[0]["count"], 1)


class SMSGatewayOptionEncryptionTestCase(MyTestCase):
    """Test that sensitive SMS gateway options are encrypted in the database."""

    def test_01_sensitive_key_detection(self):
        """_is_sensitive_key correctly identifies sensitive option keys."""
        self.assertTrue(_is_sensitive_key("PASSWORD"))
        self.assertTrue(_is_sensitive_key("password"))
        self.assertTrue(_is_sensitive_key("MAILPASSWORD"))
        self.assertTrue(_is_sensitive_key("MY_SECRET"))
        self.assertTrue(_is_sensitive_key("secret"))
        self.assertTrue(_is_sensitive_key("API_SECRET_KEY"))
        # Non-sensitive keys
        self.assertFalse(_is_sensitive_key("URL"))
        self.assertFalse(_is_sensitive_key("HTTP_METHOD"))
        self.assertFalse(_is_sensitive_key("USERNAME"))
        self.assertFalse(_is_sensitive_key("TIMEOUT"))

    def test_02_password_option_encrypted_in_db(self):
        """PASSWORD option values are stored encrypted in the DB but readable via option_dict."""
        identifier = "test_encrypt_gw"
        provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider"
        plaintext_password = "my_super_secret_password"

        gw_id = set_smsgateway(identifier, provider_module,
                               description="encryption test",
                               options={"URL": "https://example.com/sms",
                                        "HTTP_METHOD": "POST",
                                        "PASSWORD": plaintext_password,
                                        "USERNAME": "testuser"})
        self.assertTrue(gw_id > 0)

        # Verify the raw DB value is NOT the plaintext password
        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw_id, Key="PASSWORD", Type="option")
        option = db.session.execute(stmt).scalar_one()
        self.assertNotEqual(option.Value, plaintext_password,
                            "PASSWORD should be stored encrypted, not as plaintext!")
        self.assertIn(":", option.Value)
        self.assertTrue(option.Encrypted, "Encrypted flag should be True for sensitive options")

        # Verify the decrypted value via option_dict matches the original
        gw = get_smsgateway(id=gw_id)[0]
        self.assertEqual(gw.option_dict.get("PASSWORD"), plaintext_password)

        # Verify non-sensitive values are stored as-is
        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw_id, Key="URL", Type="option")
        option = db.session.execute(stmt).scalar_one()
        self.assertEqual(option.Value, "https://example.com/sms")
        self.assertFalse(option.Encrypted)

        # Verify USERNAME (not sensitive) is stored in plaintext
        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw_id, Key="USERNAME", Type="option")
        option = db.session.execute(stmt).scalar_one()
        self.assertEqual(option.Value, "testuser")
        self.assertFalse(option.Encrypted)

        # Clean up
        delete_smsgateway(identifier)

    def test_03_secret_option_encrypted_in_db(self):
        """Options with SECRET in the key name are also encrypted."""
        identifier = "test_secret_gw"
        provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider"
        api_secret = "abc123secret456"

        gw_id = set_smsgateway(identifier, provider_module,
                               description="secret test",
                               options={"URL": "https://example.com/sms",
                                        "HTTP_METHOD": "POST",
                                        "API_SECRET": api_secret})

        # Verify raw DB value is encrypted
        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw_id, Key="API_SECRET", Type="option")
        option = db.session.execute(stmt).scalar_one()
        self.assertNotEqual(option.Value, api_secret)
        self.assertIn(":", option.Value)
        self.assertTrue(option.Encrypted)

        # Verify decrypted value is correct
        gw = get_smsgateway(id=gw_id)[0]
        self.assertEqual(gw.option_dict.get("API_SECRET"), api_secret)

        # Clean up
        delete_smsgateway(identifier)

    def test_04_sensitive_header_encrypted_in_db(self):
        """Headers with sensitive key names are also encrypted."""
        identifier = "test_header_gw"
        provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider"
        secret_header_value = "Bearer token12345"

        gw_id = set_smsgateway(identifier, provider_module,
                               description="header test",
                               options={"URL": "https://example.com/sms",
                                        "HTTP_METHOD": "POST"},
                               headers={"X-API-SECRET": secret_header_value,
                                        "Content-Type": "application/json"})

        # Verify the sensitive header is encrypted in DB
        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw_id, Key="X-API-SECRET", Type="header")
        option = db.session.execute(stmt).scalar_one()
        self.assertNotEqual(option.Value, secret_header_value)
        self.assertIn(":", option.Value)
        self.assertTrue(option.Encrypted)

        # Verify non-sensitive header is stored in plaintext
        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw_id, Key="Content-Type", Type="header")
        option = db.session.execute(stmt).scalar_one()
        self.assertEqual(option.Value, "application/json")
        self.assertFalse(option.Encrypted)

        # Verify decrypted header value is correct
        gw = get_smsgateway(id=gw_id)[0]
        self.assertEqual(gw.header_dict.get("X-API-SECRET"), secret_header_value)
        self.assertEqual(gw.header_dict.get("Content-Type"), "application/json")

        # Clean up
        delete_smsgateway(identifier)

    def test_05_update_encrypted_option(self):
        """Updating a sensitive option re-encrypts with the new value."""
        identifier = "test_update_gw"
        provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider"
        old_password = "old_password_123"
        new_password = "new_password_456"

        gw_id = set_smsgateway(identifier, provider_module,
                               options={"URL": "https://example.com",
                                        "HTTP_METHOD": "POST",
                                        "PASSWORD": old_password})

        gw = get_smsgateway(id=gw_id)[0]
        self.assertEqual(gw.option_dict.get("PASSWORD"), old_password)

        # Update the password
        set_smsgateway(identifier, provider_module,
                       options={"URL": "https://example.com",
                                "HTTP_METHOD": "POST",
                                "PASSWORD": new_password})

        gw = get_smsgateway(id=gw_id)[0]
        self.assertEqual(gw.option_dict.get("PASSWORD"), new_password)

        # Verify raw DB value is encrypted
        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw_id, Key="PASSWORD", Type="option")
        option = db.session.execute(stmt).scalar_one()
        self.assertNotEqual(option.Value, new_password)
        self.assertIn(":", option.Value)
        self.assertTrue(option.Encrypted)

        # Clean up
        delete_smsgateway(identifier)

    def test_06_censored_password_not_overwritten(self):
        """Sending CENSORED placeholder keeps the existing encrypted password unchanged."""
        from privacyidea.lib.crypto import CENSORED

        identifier = "test_censored_gw"
        provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider"
        real_password = "the_real_password"

        gw_id = set_smsgateway(identifier, provider_module,
                               options={"URL": "https://example.com",
                                        "HTTP_METHOD": "POST",
                                        "PASSWORD": real_password})

        # Get the encrypted value from DB
        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw_id, Key="PASSWORD", Type="option")
        option = db.session.execute(stmt).scalar_one()
        encrypted_value_before = option.Value

        # Update with CENSORED - should keep existing value
        set_smsgateway(identifier, provider_module,
                       options={"URL": "https://example.com",
                                "HTTP_METHOD": "POST",
                                "PASSWORD": CENSORED})

        db.session.expire_all()
        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw_id, Key="PASSWORD", Type="option")
        option = db.session.execute(stmt).scalar_one()
        self.assertEqual(option.Value, encrypted_value_before)

        gw = get_smsgateway(id=gw_id)[0]
        self.assertEqual(gw.option_dict.get("PASSWORD"), real_password)

        # Clean up
        delete_smsgateway(identifier)

    def test_07_empty_password_not_encrypted(self):
        """An empty string password is stored as-is (not encrypted)."""
        identifier = "test_empty_pw_gw"
        provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider"

        gw_id = set_smsgateway(identifier, provider_module,
                               options={"URL": "https://example.com",
                                        "HTTP_METHOD": "POST",
                                        "PASSWORD": ""})

        stmt = select(SMSGatewayOption).filter_by(gateway_id=gw_id, Key="PASSWORD", Type="option")
        option = db.session.execute(stmt).scalar_one()
        self.assertEqual(option.Value, "")
        self.assertFalse(option.Encrypted)

        # Clean up
        delete_smsgateway(identifier)
