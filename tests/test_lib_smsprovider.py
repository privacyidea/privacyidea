# -*- coding: utf-8 -*-
__doc__="""
This test file tests the modules:
 lib.smsprovider.httpsmsprovider
 lib.smsprovider.sipgateprovider
 lib.smsprovider.smtpsmsprovider
"""

from .base import MyTestCase
from privacyidea.lib.smsprovider.HttpSMSProvider import HttpSMSProvider
from privacyidea.lib.smsprovider.SipgateSMSProvider import SipgateSMSProvider
from privacyidea.lib.smsprovider.SipgateSMSProvider import URL
from privacyidea.lib.smsprovider.SmtpSMSProvider import SmtpSMSProvider
from privacyidea.lib.smsprovider.SMSProvider import (SMSError,
                                                     get_sms_provider_class)
from privacyidea.lib.smtpserver import add_smtpserver
import responses
import smtpmock


class SMSTestCase(MyTestCase):

    def test_00_SMSError(self):
        err = SMSError(100, "Some Error")
        text = "{0!r}".format(err)
        self.assertTrue(text == "SMSError(error_id=100, description='Some "
                                "Error')", text)

        text = "{0!s}".format(err)
        self.assertTrue(text == "Some Error", text)

    def test_01_get_provider_class(self):
        _provider =get_sms_provider_class(
            "privacyidea.lib.smsprovider.SipgateSMSProvider",
            "SipgateSMSProvider")

        _provider =get_sms_provider_class(
            "privacyidea.lib.smsprovider.HttpSMSProvider",
            "HttpSMSProvider")

        _provider =get_sms_provider_class(
            "privacyidea.lib.smsprovider.SmtpSMSProvider",
            "SmtpSMSProvider")

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
        self.assertRaises(r)

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
