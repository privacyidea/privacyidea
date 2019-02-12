import json
from .base import MyApiTestCase
from . import smtpmock
from privacyidea.lib.config import set_privacyidea_config


class APIEventsTestCase(MyApiTestCase):

    def test_01_crud_events(self):

        # list empty events
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), [])

        # create an event configuration
        param = {
            "name": "Send an email",
            "event": "token_init",
            "action": "sendmail",
            "handlermodule": "UserNotification",
            "conditions": '{"blabla": "yes"}'
        }
        with self.app.test_request_context('/event',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), 1)

        # check the event
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value")[0].get("action"), "sendmail")
            self.assertEqual(result.get("value")[0].get("conditions"),
                             {"blabla": "yes"})

        # update event config
        param = {
            "name": "A new name",
            "event": "token_init",
            "action": "sendmail",
            "handlermodule": "UserNotification",
            "conditions": '{"always": "yes"}',
            "id": 1
        }
        with self.app.test_request_context('/event',
                                           data=param,
                                           method='POST',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), 1)

        # check the event
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value")[0].get("action"),
                             "sendmail")
            self.assertEqual(result.get("value")[0].get("conditions"),
                             {"always": "yes"})

        # get one single event
        with self.app.test_request_context('/event/1',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = json.loads(res.data.decode('utf8')).get("result")
                detail = json.loads(res.data.decode('utf8')).get("detail")
                self.assertEqual(result.get("value")[0].get("action"),
                                 "sendmail")
                self.assertEqual(result.get("value")[0].get("conditions"),
                                 {"always": "yes"})

        # delete event
        with self.app.test_request_context('/event/1',
                                           method='DELETE',
                                           headers={
                                               'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), 1)

        # list empty events
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), [])

    def test_02_test_options(self):

        # create an event configuration
        param = {
            "name": "Send an email via themis",
            "event": "token_init",
            "action": "sendmail",
            "handlermodule": "UserNotification",
            "conditions": '{"blabla": "yes"}',
            "option.emailconfig": "themis",
            "option.2": "value2"
        }
        with self.app.test_request_context('/event',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), 1)

        # list event with options
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            event_list = result.get("value")
            self.assertEqual(len(event_list), 1)
            self.assertEqual(event_list[0].get("action"), "sendmail")
            self.assertEqual(event_list[0].get("event"), ["token_init"])
            self.assertEqual(event_list[0].get("options").get("2"), "value2")
            self.assertEqual(event_list[0].get("options").get("emailconfig"),
                             "themis")

        # delete event
        with self.app.test_request_context('/event/1',
                                           method='DELETE',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), 1)

        # list empty events
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), [])

    def test_03_available_events(self):
        with self.app.test_request_context('/event/available',
                                           method='GET',
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertTrue("token_init" in result.get("value"))
            self.assertTrue("token_assign" in result.get("value"))
            self.assertTrue("token_unassign" in result.get("value"))

    def test_04_handler_modules(self):
        with self.app.test_request_context('/event/handlermodules',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertTrue("UserNotification" in result.get("value"))

    def test_05_get_handler_actions(self):
        with self.app.test_request_context('/event/actions/UserNotification',
                                           method='GET',
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue("sendmail" in result.get("value"))
            self.assertTrue("sendsms" in result.get("value"))
            detail = json.loads(res.data.decode('utf8')).get("detail")

    def test_05_get_handler_conditions(self):
        with self.app.test_request_context('/event/conditions/UserNotification',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue("logged_in_user" in result.get("value"))
            self.assertTrue("result_value" in result.get("value"))
            detail = json.loads(res.data.decode('utf8')).get("detail")

    def test_06_test_enable_disable(self):
        # create an event configuration
        param = {
            "name": "Send an email via themis",
            "event": "token_init",
            "action": "sendmail",
            "handlermodule": "UserNotification",
            "conditions": '{"blabla": "yes"}',
            "option.emailconfig": "themis",
            "option.2": "value2"
        }
        with self.app.test_request_context('/event',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), 1)

        # list event with options
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            event_list = result.get("value")
            self.assertEqual(len(event_list), 1)
            self.assertEqual(event_list[0].get("active"), True)

        # disable event
        with self.app.test_request_context('/event/disable/1',
                                           method='POST',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            event_list = result.get("value")
            self.assertEqual(len(event_list), 1)
            self.assertEqual(event_list[0].get("active"), False)

        # Enable event
        with self.app.test_request_context('/event/enable/1',
                                           method='POST',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            event_list = result.get("value")
            self.assertEqual(len(event_list), 1)
            self.assertEqual(event_list[0].get("active"), True)

        # delete event
        with self.app.test_request_context('/event/1',
                                           method='DELETE',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), 1)

        # list empty events
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), [])

    def test_07_positions(self):
        # test the available Positions

        with self.app.test_request_context('/event/positions/Token',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue("post" in result.get("value"), result.get("value"))
            self.assertTrue("pre" in result.get("value"), result.get("value"))

        # create an event configuration
        param = {
            "name": "Delete the token that was created :-)",
            "event": "token_init",
            "action": "delete",
            "handlermodule": "Token",
            "conditions": '{"blabla": "yes"}',
            "position": "post"
        }
        with self.app.test_request_context('/event',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), 1)

        # check the event
        with self.app.test_request_context('/event/1',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value")[0].get("position"), "post")

        # Update event with the position=pre
        param["id"] = 1
        param["position"] = "pre"
        with self.app.test_request_context('/event',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), 1)

        # check the event
        with self.app.test_request_context('/event/1',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value")[0].get("position"), "pre")

        # delete event
        with self.app.test_request_context('/event/1',
                                           method='DELETE',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), 1)

        # list empty events
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), [])

    @smtpmock.activate
    def test_08_create_token_for_user(self):
        smtpmock.setdata(response={"pi_tester@privacyidea.org": (200, 'OK')})
        transactionid = "123456098712"
        # send the email with the old configuration
        set_privacyidea_config("email.mailserver", "localhost")
        set_privacyidea_config("email.username", "user")
        set_privacyidea_config("email.username", "password")
        set_privacyidea_config("email.tls", True)
        # We create a token for a user, who has currently no token!
        # create an event configuration
        param = {
            "name": "Create Email Token for untokened user",
            "event": "validate_check",
            "action": "enroll",
            "handlermodule": "Token",
            "position": "pre",
            "conditions": '{"user_token_number": "0"}',
            "option.user": "true",
            "option.tokentype": "email",
            "option.dynamic_email": "1",
            "option.additional_params": "{'pin':'1234'}"
        }
        with self.app.test_request_context('/event',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value"), 1)

        self.setUp_user_realm2()
        # usernotoken, self.realm2
        # check that the user has no tokens
        with self.app.test_request_context('/token/',
                                           data={"user": "usernotoken",
                                                 "realm": self.realm2},
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value").get("tokens"), [])

        # user tries to authenticate. with the pin 1234.
        # He gets an email token enrolled and gets the transaction code in the response
        with self.app.test_request_context('/validate/check',
                                           data={"user": "usernotoken",
                                                 "realm": self.realm2,
                                                 "pass": "1234"},
                                           method="POST",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertFalse(result.get("value"))
            self.assertTrue(detail.get("serial").startswith("PIEM"))
            # This is a challenge response!
            self.assertTrue("transaction_id" in detail, detail)
            self.assertTrue("multi_challenge" in detail, detail)
            self.assertEqual(detail.get("message"), u"Enter the OTP from the Email:")

        # check user has a token
        with self.app.test_request_context('/token/',
                                           data={"user": "usernotoken",
                                                 "realm": self.realm2},
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertEqual(result.get("value").get("count"), 1)
            self.assertEqual(result.get("value").get("tokens")[0].get("tokentype"), u"email")