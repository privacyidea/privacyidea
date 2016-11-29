import json
from .base import MyTestCase


class APIEventsTestCase(MyTestCase):

    def test_01_crud_events(self):

        # list empty events
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), 1)

        # check the event
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), 1)

        # check the event
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
                result = json.loads(res.data).get("result")
                detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), 1)

        # list empty events
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), 1)

        # list event with options
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), 1)

        # list empty events
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), [])

    def test_03_available_events(self):
        with self.app.test_request_context('/event/available',
                                           method='GET',
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertTrue("token_init" in result.get("value"))
            self.assertTrue("token_assign" in result.get("value"))
            self.assertTrue("token_unassign" in result.get("value"))

    def test_04_handler_modules(self):
        with self.app.test_request_context('/event/handlermodules',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertTrue("UserNotification" in result.get("value"))

    def test_05_get_handler_actions(self):
        with self.app.test_request_context('/event/actions/UserNotification',
                                           method='GET',
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue("sendmail" in result.get("value"))
            self.assertTrue("sendsms" in result.get("value"))
            detail = json.loads(res.data).get("detail")

    def test_05_get_handler_conditions(self):
        with self.app.test_request_context('/event/conditions/UserNotification',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue("logged_in_user" in result.get("value"))
            self.assertTrue("result_value" in result.get("value"))
            detail = json.loads(res.data).get("detail")

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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), 1)

        # list event with options
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
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
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), 1)

        # list empty events
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), [])
