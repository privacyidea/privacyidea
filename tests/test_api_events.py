from privacyidea.lib.container import init_container, add_token_to_container
from privacyidea.lib.event import set_event, delete_event
from privacyidea.lib.eventhandler.containerhandler import ContainerEventHandler
from privacyidea.lib.eventhandler.customuserattributeshandler import ACTION_TYPE, USER_TYPE
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.token import init_token, remove_token
from privacyidea.lib.user import User
from .base import MyApiTestCase, FakeFlaskG
from . import smtpmock
import mock
from privacyidea.lib.config import set_privacyidea_config

# TODO: this should be imported from lib.event when available
HANDLERS = ["UserNotification", "Token", "Federation", "Script", "Counter",
            "RequestMangler", "ResponseMangler", "Logging", "CustomUserAttributes"]


class APIEventsTestCase(MyApiTestCase):

    def test_00_api_errors(self):
        # check for auth error
        with self.app.test_request_context('/event/',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401, res)
            self.assertEqual(res.json['result']['error']['code'], 4033, res.json)

        # check for automatic redirect on missing trailing slash from flask
        with self.app.test_request_context('/event',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            # In test environment this can throw a 301
            self.assertTrue(res.status_code in [301, 308], res)
            self.assertIn('Location', res.headers, res)

        param = {
            "name": "Send an email",
            "event": "token_init",
            "action": "sendmail",
            "handlermodule": "UserNotification",
            "conditions": '{"blabla": "yes"}'
        }
        with self.app.test_request_context('/event',
                                           method='POST',
                                           data=param,
                                           headers={'Authorization': self.at}):
            # check for policy error with a restrictive admin policy
            set_policy(name="adm_disable_event", scope=SCOPE.ADMIN,
                       action="configwrite")
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403, res)
            self.assertEqual(res.json['result']['error']['code'], 303, res.json)
            delete_policy('adm_disable_event')

        # check fo resourceNotFound error
        with self.app.test_request_context('/event/enable/1234',
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404, res)
            self.assertEqual(res.json['result']['error']['code'], 601, res.json)
        # And check if the /event request writes a valid (failed) audit entry
        auditentry = self.find_most_recent_audit_entry(action='POST /event/enable/<eventid>')
        self.assertEqual(auditentry['action'], 'POST /event/enable/<eventid>', auditentry)
        self.assertEqual(auditentry['success'], 0, auditentry)

    def test_01_crud_events(self):
        # list empty events
        with self.app.test_request_context('/event/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value"), [])
            self.assertIn('signature', res.json, res.json)

        # Check if the /event request writes a valid audit entry
        auditentry = self.find_most_recent_audit_entry(action='GET /event/')
        self.assertEqual(auditentry['success'], 1, auditentry)

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
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), 1)

        # check the event
        with self.app.test_request_context('/event/',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
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
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), 1)

        # check the event
        with self.app.test_request_context('/event/',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
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
            result = res.json.get("result")
            detail = res.json.get("detail")
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
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), 1)

        # list empty events
        with self.app.test_request_context('/event/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
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
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertGreaterEqual(result.get("value"), 1, result)
            ev1_id = result.get('value')

        # list event with options
        with self.app.test_request_context('/event/',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            event_list = result.get("value")
            self.assertEqual(len(event_list), 1)
            self.assertEqual(event_list[0].get("action"), "sendmail")
            self.assertEqual(event_list[0].get("event"), ["token_init"])
            self.assertEqual(event_list[0].get("options").get("2"), "value2")
            self.assertEqual(event_list[0].get("options").get("emailconfig"),
                             "themis")

        # delete event
        with self.app.test_request_context('/event/{0!s}'.format(ev1_id),
                                           method='DELETE',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), ev1_id)

        # list empty events
        with self.app.test_request_context('/event/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), [])

    def test_03_available_events(self):
        with self.app.test_request_context('/event/available',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertTrue("token_init" in result.get("value"))
            self.assertTrue("token_assign" in result.get("value"))
            self.assertTrue("token_unassign" in result.get("value"))

    def test_04_handler_modules(self):
        with self.app.test_request_context('/event/handlermodules',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            for h in HANDLERS:
                self.assertIn(h, result.get("value"), result)

    def test_05_get_handler_actions(self):
        with self.app.test_request_context('/event/actions/UserNotification',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue("sendmail" in result.get("value"))
            self.assertTrue("sendsms" in result.get("value"))
            detail = res.json.get("detail")

        with self.app.test_request_context('/event/actions/Token',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            set_random_pin = result.get("value").get("set random pin")
            # The valid OTP PIN length is returned as list
            self.assertTrue(type(set_random_pin.get("length").get("value")), "list")

    def test_05_get_handler_conditions(self):
        with self.app.test_request_context('/event/conditions/UserNotification',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue("logged_in_user" in result.get("value"))
            self.assertTrue("result_value" in result.get("value"))
            detail = res.json.get("detail")

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
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertGreaterEqual(result.get("value"), 1, result)
            ev1_id = result.get('value')

        # list event with options
        with self.app.test_request_context('/event/',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            event_list = result.get("value")
            self.assertEqual(len(event_list), 1)
            self.assertEqual(event_list[0].get("active"), True)

        # disable event
        with self.app.test_request_context('/event/disable/{0!s}'.format(ev1_id),
                                           method='POST',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        with self.app.test_request_context('/event/',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            event_list = result.get("value")
            self.assertEqual(len(event_list), 1)
            self.assertEqual(event_list[0].get("active"), False)

        # Enable event
        with self.app.test_request_context('/event/enable/{0!s}'.format(ev1_id),
                                           method='POST',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        with self.app.test_request_context('/event/',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            event_list = result.get("value")
            self.assertEqual(len(event_list), 1)
            self.assertEqual(event_list[0].get("active"), True)

        # delete event
        with self.app.test_request_context('/event/{0!s}'.format(ev1_id),
                                           method='DELETE',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), ev1_id, result)

        # list empty events
        with self.app.test_request_context('/event/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), [])

    def test_07_positions(self):
        # test the available Positions

        with self.app.test_request_context('/event/positions/Token',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertGreaterEqual(result.get("value"), 1, result)
            ev1_id = result.get('value')

        # check the event
        with self.app.test_request_context('/event/{0!s}'.format(ev1_id),
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value")[0].get("position"), "post")

        # Update event with the position=pre
        param["id"] = ev1_id
        param["position"] = "pre"
        with self.app.test_request_context('/event',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), ev1_id, result)

        # check the event
        with self.app.test_request_context('/event/{0!s}'.format(ev1_id),
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value")[0].get("position"), "pre")

        # delete event
        with self.app.test_request_context('/event/{0!s}'.format(ev1_id),
                                           method='DELETE',
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), ev1_id, result)

        # list empty events
        with self.app.test_request_context('/event/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
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
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertGreaterEqual(result.get("value"), 1, result)

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
            result = res.json.get("result")
            detail = res.json.get("detail")
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
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertTrue(detail.get("serial").startswith("PIEM"))
            # This is a challenge response!
            self.assertTrue("transaction_id" in detail, detail)
            self.assertTrue("multi_challenge" in detail, detail)
            self.assertEqual(detail.get("message"), "Enter the OTP from the Email")

        # check user has a token
        with self.app.test_request_context('/token/',
                                           data={"user": "usernotoken",
                                                 "realm": self.realm2},
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value").get("count"), 1)
            self.assertEqual(result.get("value").get("tokens")[0].get("tokentype"), "email")

    def test_09_get_container_serial(self):
        # Get container serial from response
        payload = {"type": "Smartphone", "description": "test description!!"}
        request = self.app.test_request_context('/container/init',
                                                method='POST',
                                                data=payload,
                                                headers={'Authorization': self.at})
        with request:
            res = self.app.full_dispatch_request()

            c_handler = ContainerEventHandler()
            content = c_handler._get_response_content(res)
            container_serial = c_handler._get_container_serial(request.request, content)

            self.assertIsNotNone(container_serial)

        # Get container serial from request
        container_serial = init_container({"type": "Generic", "description": "test description!!"})
        payload = {"container_serial": container_serial, "states": ["active"]}
        request = self.app.test_request_context(f'/container/{container_serial}/states',
                                                method='POST',
                                                data=payload,
                                                headers={'Authorization': self.at})
        with request:
            res = self.app.full_dispatch_request()

            c_handler = ContainerEventHandler()
            container_serial_req = c_handler._get_container_serial(request.request, res)

            self.assertEqual(container_serial_req, container_serial)

        # Get container serial from token
        token_serial = "SPASS0001"
        init_token({"type": "spass", "serial": token_serial})
        add_token_to_container(container_serial, token_serial, user=User(), user_role="admin")

        payload = {"serial": token_serial}
        request = self.app.test_request_context('/token/enable',
                                                method='POST',
                                                data=payload,
                                                headers={'Authorization': self.at})
        with request:
            res = self.app.full_dispatch_request()
            g = FakeFlaskG()

            c_handler = ContainerEventHandler()
            container_serial_token = c_handler._get_container_serial_from_token(request.request, res, g)

            self.assertEqual(container_serial_token, container_serial)


class CustomUserAttributeHandlerTestCase(MyApiTestCase):
    def setUp(self):
        super(CustomUserAttributeHandlerTestCase, self).setUp()
        self.setUp_user_realms()

    def test_01_user_attribute_with_handler_tokenowner(self):
        user = User('cornelius', self.realm1)
        tok = init_token({'type': 'spass', 'pin': 'test'})
        self.assertNotIn('foo', user.attributes, user.attributes)

        # First try to delete a non-existing attribute
        eid = set_event("user_atts", event=["validate_check"],
                        action=ACTION_TYPE.DELETE_CUSTOM_USER_ATTRIBUTES,
                        handlermodule="CustomUserAttributes", conditions={},
                        options={'user': USER_TYPE.TOKENOWNER,
                                 'attrkey': 'foo'})

        # what happens if the token has no user
        with self.app.test_request_context('/validate/check',
                                           data={"serial": tok.token.serial,
                                                 "pass": 'test'},
                                           method='POST'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"), result)
            self.assertNotIn('foo', user.attributes, user.attributes)

        # now we attach the token to a user
        tok.add_user(user)
        with self.app.test_request_context('/validate/check',
                                           data={"user": 'cornelius',
                                                 "pass": 'test'},
                                           method='POST'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"), result)
            self.assertNotIn('foo', user.attributes, user.attributes)

        # update event to add an attribute
        eid = set_event("user_atts", event=["validate_check"], id=eid,
                        action=ACTION_TYPE.SET_CUSTOM_USER_ATTRIBUTES,
                        handlermodule="CustomUserAttributes", conditions={},
                        options={'user': USER_TYPE.TOKENOWNER,
                                 'attrkey': 'foo',
                                 'attrvalue': 'bar'})
        with self.app.test_request_context('/validate/check',
                                           data={"user": "cornelius",
                                                 "pass": 'test'},
                                           method='POST'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"), result)
            self.assertEqual('bar', user.attributes.get('foo'), user.attributes)

        # update event to update an attribute
        eid = set_event("user_atts", event=["validate_check"], id=eid,
                        action=ACTION_TYPE.SET_CUSTOM_USER_ATTRIBUTES,
                        handlermodule="CustomUserAttributes", conditions={},
                        options={'user': USER_TYPE.TOKENOWNER,
                                 'attrkey': 'foo',
                                 'attrvalue': 'baz'})
        with self.app.test_request_context('/validate/check',
                                           data={"user": "cornelius",
                                                 "pass": 'test'},
                                           method='POST'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"), result)
            self.assertEqual('baz', user.attributes.get('foo'), user.attributes)

        # now delete the added attribute
        eid = set_event("user_atts", event=["validate_check"], id=eid,
                        action=ACTION_TYPE.DELETE_CUSTOM_USER_ATTRIBUTES,
                        handlermodule="CustomUserAttributes", conditions={},
                        options={'user': USER_TYPE.TOKENOWNER,
                                 'attrkey': 'foo'})
        with self.app.test_request_context('/validate/check',
                                           data={"user": "cornelius",
                                                 "pass": 'test'},
                                           method='POST'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"), result)
            self.assertNotIn('foo', user.attributes, user.attributes)

        delete_event(eid)
        remove_token(tok.token.serial)

    def test_02_user_attribute_with_handler_logged_in_user(self):
        user = User('cornelius', realm=self.realm1)
        self.assertNotIn('foo', user.attributes, user.attributes)

        # get the auth-token for the user
        with self.app.test_request_context('/auth',
                                           data={"username": 'cornelius',
                                                 "password": 'test'},
                                           method='POST'):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            user_token = result.get("value").get("token")

        # try to delete a non-existing attribute
        eid = set_event("user_atts", event=["token_list"],
                        action=ACTION_TYPE.DELETE_CUSTOM_USER_ATTRIBUTES,
                        handlermodule="CustomUserAttributes", conditions={},
                        options={'user': USER_TYPE.LOGGED_IN_USER,
                                 'attrkey': 'foo'})
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': user_token}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertNotIn('foo', user.attributes, user.attributes)

        # delete an existing attribute
        user.set_attribute('foo', 'bar')
        self.assertIn('foo', user.attributes, user.attributes)
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': user_token}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertNotIn('foo', user.attributes, user.attributes)

        # add an attribute
        eid = set_event("user_atts", event=["token_list"], id=eid,
                        action=ACTION_TYPE.SET_CUSTOM_USER_ATTRIBUTES,
                        handlermodule="CustomUserAttributes", conditions={},
                        options={'user': USER_TYPE.LOGGED_IN_USER,
                                 'attrkey': 'foo',
                                 'attrvalue': 'bar'})
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': user_token}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertEqual('bar', user.attributes['foo'], user.attributes)

        # overwrite an attribute
        eid = set_event("user_atts", event=["token_list"], id=eid,
                        action=ACTION_TYPE.SET_CUSTOM_USER_ATTRIBUTES,
                        handlermodule="CustomUserAttributes", conditions={},
                        options={'user': USER_TYPE.LOGGED_IN_USER,
                                 'attrkey': 'foo',
                                 'attrvalue': 'baz'})
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': user_token}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertEqual('baz', user.attributes['foo'], user.attributes)

        delete_event(eid)
        user.delete_attribute('foo')


from privacyidea.lib.smtpserver import add_smtpserver
from . import smtpmock


class EventWrapperTestCase(MyApiTestCase):
    # Test the wrapper/decorator in lib/event.py
    # In other cases we test specific event handlers, but not the calling of the event handler
    # We do this here via an API call.
    serial = "myToken"

    def test_00_setup(self):
        # setup realms
        self.setUp_user_realms()

        r = add_smtpserver(identifier="myserver", server="1.2.3.4", tls=False)
        self.assertTrue(r > 0)

    @smtpmock.activate
    def test_01_sendmail_post(self):
        r = set_event("send email", "token_init", "UserNotification", "sendmail",
                      conditions={},
                      options={"emailconfig": "myserver",
                               "To": "email",
                               "To email": "pretzel@example.com",
                               "reply_to": "email",
                               "reply_to email": "privacyidea@example.com"})
        self.assertTrue(r > 0)

        smtpmock.setdata(response={"pretzel@example.com": (450, "Mailbox not available")},
                         support_tls=False)

        with mock.patch("logging.Logger.warning") as mock_log:
            with self.app.test_request_context('/token/init',
                                               data={"genkey": 1,
                                                     "serial": self.serial},
                                               headers={'Authorization': self.at},
                                               method='POST'):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertTrue(result.get("value"), result)
            # Check warning in log
            expected = "Failed to send a notification email to user {'email': ['pretzel@example.com']}"
            mock_log.assert_called_once_with(expected)
            msg = smtpmock.get_sent_message()
            self.assertIn('To: pretzel@example.com', msg)
        delete_event(r)

    @smtpmock.activate
    def test_02_sendmail_pre(self):
        r = set_event("send email", "token_init", "UserNotification", "sendmail",
                      conditions={},
                      position="pre",
                      options={"emailconfig": "myserver",
                               "To": "email",
                               "To email": "donut@example.com",
                               "reply_to": "email",
                               "reply_to email": "privacyidea@example.com"})
        self.assertTrue(r > 0)

        smtpmock.setdata(response={"donut@example.com": (450, "Mailbox not available")},
                         support_tls=False)

        with mock.patch("logging.Logger.warning") as mock_log:
            with self.app.test_request_context('/token/init',
                                               data={"genkey": 1,
                                                     "serial": self.serial},
                                               headers={'Authorization': self.at},
                                               method='POST'):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                self.assertTrue(result.get("value"), result)
            # Check warning in log
            expected = "Failed to send a notification email to user {'email': ['donut@example.com']}"
            mock_log.assert_called_once_with(expected)

            msg = smtpmock.get_sent_message()
            self.assertIn('To: donut@example.com', msg)
        delete_event(r)
