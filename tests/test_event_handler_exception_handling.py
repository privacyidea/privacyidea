"""
Tests for exception handling in the event decorator (lib/event.py).

Verifies that:
- A failing handler does not crash the API call
- A failing handler is audited with success=False
- Remaining handlers still execute after a prior handler fails
- HandlerAbortError (intentional abort) still propagates
- The Script handler raises HandlerAbortError when raise_error is set
"""
import unittest
from unittest import mock
from unittest.mock import patch, MagicMock

from flask import Request, Response
from werkzeug.test import EnvironBuilder

from privacyidea.lib.audit import getAudit
from privacyidea.lib.error import HandlerAbortError
from privacyidea.lib.event import event, set_event, EventConfiguration
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib.user import User
from .base import MyTestCase, FakeFlaskG


class EventDecoratorExceptionHandlingTestCase(MyTestCase):
    """Test that the event decorator properly handles exceptions from handlers."""

    def _setup_g_with_event_config(self):
        """Create a FakeFlaskG with a working audit object and event config."""
        g = FakeFlaskG()
        g.audit_object = getAudit(self.app.config)
        g.audit_object.audit_data = {
            "action": "POST /test/endpoint",
            "client": "127.0.0.1",
        }
        g.event_config = EventConfiguration()
        g.logged_in_user = {"username": "admin", "role": "admin", "realm": ""}
        return g

    def _make_request(self):
        """Create a minimal fake request."""
        builder = EnvironBuilder(method='POST', data={'serial': 'TEST01'}, headers={})
        req = Request(builder.get_environ())
        req.all_data = {"serial": "TEST01", "type": "hotp"}
        req.User = User()
        return req

    def test_post_handler_exception_does_not_crash_api_call(self):
        """A post-event handler that raises should not affect the API response."""
        # Set up a post-event handler that will raise
        eid = set_event("failing_handler", "token_init", "UserNotification", "sendmail",
                        conditions={}, options={"emailconfig": "nonexistent"},
                        position="post")

        g = self._setup_g_with_event_config()
        req = self._make_request()

        @event("token_init", req, g)
        def my_api_function():
            return Response('{"result": {"value": true}}')

        # Patch the handler's check_condition to return True,
        # and do() to raise an exception
        with patch("privacyidea.lib.event.get_handler_object") as mock_get_handler:
            mock_handler = MagicMock()
            mock_handler.check_condition.return_value = True
            mock_handler.do.side_effect = Exception("SMTP connection refused")
            mock_handler.run_details = ""
            mock_get_handler.return_value = mock_handler

            # This should NOT raise
            result = my_api_function()
            self.assertIn(b"true", result.data)

        # Cleanup
        from privacyidea.lib.event import delete_event
        delete_event(eid)

    def test_pre_handler_exception_does_not_crash_api_call(self):
        """A pre-event handler that raises should not prevent the API function from running."""
        eid = set_event("failing_pre_handler", "token_init", "UserNotification", "sendmail",
                        conditions={}, options={"emailconfig": "nonexistent"},
                        position="pre")

        g = self._setup_g_with_event_config()
        req = self._make_request()

        api_was_called = []

        @event("token_init", req, g)
        def my_api_function():
            api_was_called.append(True)
            return Response('{"result": {"value": true}}')

        with patch("privacyidea.lib.event.get_handler_object") as mock_get_handler:
            mock_handler = MagicMock()
            mock_handler.check_condition.side_effect = RuntimeError("condition check blew up")
            mock_handler.run_details = ""
            mock_get_handler.return_value = mock_handler

            result = my_api_function()
            # The API function should still have been called
            self.assertTrue(api_was_called)
            self.assertIn(b"true", result.data)

        from privacyidea.lib.event import delete_event
        delete_event(eid)

    def test_handler_abort_error_still_propagates(self):
        """HandlerAbortError (intentional abort) must NOT be swallowed."""
        eid = set_event("aborting_handler", "token_init", "Script", "run_script",
                        conditions={}, options={"raise_error": True},
                        position="post")

        g = self._setup_g_with_event_config()
        req = self._make_request()

        @event("token_init", req, g)
        def my_api_function():
            return Response('{"result": {"value": true}}')

        with patch("privacyidea.lib.event.get_handler_object") as mock_get_handler:
            mock_handler = MagicMock()
            mock_handler.check_condition.return_value = True
            mock_handler.do.side_effect = HandlerAbortError("Script failed intentionally")
            mock_handler.run_details = ""
            mock_get_handler.return_value = mock_handler

            # HandlerAbortError should propagate
            with self.assertRaises(HandlerAbortError):
                my_api_function()

        from privacyidea.lib.event import delete_event
        delete_event(eid)

    def test_handler_abort_error_propagates_from_pre_event(self):
        """HandlerAbortError from a pre-event handler must propagate."""
        eid = set_event("aborting_pre_handler", "token_init", "Script", "run_script",
                        conditions={}, options={"raise_error": True},
                        position="pre")

        g = self._setup_g_with_event_config()
        req = self._make_request()

        @event("token_init", req, g)
        def my_api_function():
            return Response('{"result": {"value": true}}')

        with patch("privacyidea.lib.event.get_handler_object") as mock_get_handler:
            mock_handler = MagicMock()
            mock_handler.check_condition.return_value = True
            mock_handler.do.side_effect = HandlerAbortError("Pre-event abort")
            mock_handler.run_details = ""
            mock_get_handler.return_value = mock_handler

            with self.assertRaises(HandlerAbortError):
                my_api_function()

        from privacyidea.lib.event import delete_event
        delete_event(eid)

    def test_failing_handler_is_audited_with_success_false(self):
        """A handler failure should be recorded in the audit log with success=False."""
        eid = set_event("audited_failure", "token_init", "UserNotification", "sendmail",
                        conditions={}, options={"emailconfig": "broken"},
                        position="post")

        g = self._setup_g_with_event_config()
        req = self._make_request()

        @event("token_init", req, g)
        def my_api_function():
            return Response('{"result": {"value": true}}')

        with patch("privacyidea.lib.event.get_handler_object") as mock_get_handler, \
                patch("privacyidea.lib.event.getAudit") as mock_get_audit:
            mock_handler = MagicMock()
            mock_handler.check_condition.return_value = True
            mock_handler.do.side_effect = ConnectionError("Mail server down")
            mock_handler.run_details = ""
            mock_get_handler.return_value = mock_handler

            # Set up the audit mock
            mock_audit_obj = MagicMock()
            mock_get_audit.return_value = mock_audit_obj

            result = my_api_function()

            # The audit object should have been called with success=False
            audit_log_calls = mock_audit_obj.log.call_args_list
            # Find the call that sets success=False
            success_logged = any(
                call_args[0][0].get("success") is False
                for call_args in audit_log_calls
                if call_args[0]  # positional args exist
            )
            self.assertTrue(success_logged,
                            f"Expected success=False in audit log calls: {audit_log_calls}")

            # finalize_log should have been called
            mock_audit_obj.finalize_log.assert_called()

        from privacyidea.lib.event import delete_event
        delete_event(eid)

    def test_remaining_handlers_run_after_failure(self):
        """If one handler fails, the remaining handlers should still execute."""
        eid1 = set_event("handler_that_fails", "token_init", "UserNotification", "sendmail",
                         conditions={}, options={"emailconfig": "broken"},
                         ordering=1, position="post")
        eid2 = set_event("handler_that_succeeds", "token_init", "Logging", "logit",
                         conditions={}, options={},
                         ordering=2, position="post")

        g = self._setup_g_with_event_config()
        req = self._make_request()

        @event("token_init", req, g)
        def my_api_function():
            return Response('{"result": {"value": true}}')

        handler_call_count = []

        def mock_get_handler_side_effect(handler_name):
            mock_handler = MagicMock()
            mock_handler.run_details = ""
            if handler_name == "UserNotification":
                mock_handler.check_condition.return_value = True
                mock_handler.do.side_effect = Exception("First handler fails")
            elif handler_name == "Logging":
                mock_handler.check_condition.return_value = True
                mock_handler.do.return_value = True
                mock_handler.do.side_effect = lambda *a, **kw: handler_call_count.append("Logging") or True
            else:
                mock_handler.check_condition.return_value = False
            return mock_handler

        with patch("privacyidea.lib.event.get_handler_object",
                   side_effect=mock_get_handler_side_effect):
            result = my_api_function()

        # The second handler should have been called despite the first one failing
        self.assertIn("Logging", handler_call_count,
                      "Second handler should run even after first handler fails")

        from privacyidea.lib.event import delete_event
        delete_event(eid1)
        delete_event(eid2)

    def test_check_condition_exception_is_caught(self):
        """An exception in check_condition() should be caught, not just in do()."""
        eid = set_event("condition_fails", "token_init", "UserNotification", "sendmail",
                        conditions={}, options={},
                        position="post")

        g = self._setup_g_with_event_config()
        req = self._make_request()

        @event("token_init", req, g)
        def my_api_function():
            return Response('{"result": {"value": true}}')

        with patch("privacyidea.lib.event.get_handler_object") as mock_get_handler:
            mock_handler = MagicMock()
            mock_handler.check_condition.side_effect = KeyError("bad condition key")
            mock_handler.run_details = ""
            mock_get_handler.return_value = mock_handler

            # Should not raise
            result = my_api_function()
            self.assertIn(b"true", result.data)

        from privacyidea.lib.event import delete_event
        delete_event(eid)

    def test_audit_failure_in_except_block_does_not_crash(self):
        """If auditing the failure itself fails, the request still succeeds."""
        eid = set_event("double_failure", "token_init", "UserNotification", "sendmail",
                        conditions={}, options={},
                        position="post")

        g = self._setup_g_with_event_config()
        req = self._make_request()

        @event("token_init", req, g)
        def my_api_function():
            return Response('{"result": {"value": true}}')

        with patch("privacyidea.lib.event.get_handler_object") as mock_get_handler, \
                patch("privacyidea.lib.event.getAudit") as mock_get_audit:
            mock_handler = MagicMock()
            mock_handler.check_condition.return_value = True
            mock_handler.do.side_effect = RuntimeError("handler explodes")
            mock_handler.run_details = ""
            mock_get_handler.return_value = mock_handler

            # Make the audit object itself raise when we try to log the failure
            mock_audit_obj = MagicMock()
            mock_audit_obj.log.side_effect = RuntimeError("DB is down")
            mock_get_audit.return_value = mock_audit_obj

            # Should still not raise - the outer except catches the audit failure
            result = my_api_function()
            self.assertIn(b"true", result.data)

        from privacyidea.lib.event import delete_event
        delete_event(eid)


class ScriptHandlerAbortErrorTestCase(MyTestCase):
    """Test that ScriptEventHandler raises HandlerAbortError (not ServerError)."""

    def test_script_handler_raises_handler_abort_error(self):
        """The Script handler with raise_error=True should raise HandlerAbortError."""
        from privacyidea.lib.eventhandler.scripthandler import ScriptEventHandler, SCRIPT_WAIT
        import os

        g = FakeFlaskG()
        g.audit_object = getAudit(self.app.config)
        g.audit_object.audit_data = {}
        g.logged_in_user = {"username": "admin", "role": "admin", "realm": ""}

        builder = EnvironBuilder(method='POST', data={'serial': 'SPASS01'}, headers={})
        req = Request(builder.get_environ())
        req.all_data = {"serial": "SPASS01", "type": "spass"}
        req.User = User()
        resp = Response()
        resp.data = """{"result": {"value": true}}"""

        options = {"g": g,
                   "request": req,
                   "response": resp,
                   "handler_def": {
                       "options": {
                           "background": SCRIPT_WAIT,
                           "raise_error": True,
                           "realm": "1",
                           "serial": "1",
                           "logged_in_user": "1",
                           "logged_in_role": "1"}
                   }}

        script_name = "fail.sh"
        d = os.path.join(os.getcwd(), "tests/testdata/scripts/")
        self.app.config['PI_SCRIPT_HANDLER_DIRECTORY'] = d
        t_handler = ScriptEventHandler()

        # Should raise HandlerAbortError specifically (subclass of ServerError)
        with self.assertRaises(HandlerAbortError):
            t_handler.do(script_name, options=options)
