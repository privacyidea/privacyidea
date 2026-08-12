"""
Tests for exception handling in the event decorator (lib/event.py).

Verifies that:
- A failing handler does not crash the API call
- A failing handler is audited with success=False, and the audit entry names the exception class only
- A failing handler leaves no failed transaction behind
- Remaining handlers still execute after a prior handler fails
- An exception while evaluating the handler conditions propagates
- HandlerAbortError (intentional abort) propagates and is audited
- A handler configured with abort_on_error fails the request
- The Script handler raises HandlerAbortError when raise_error is set
"""
import os
from unittest.mock import patch, MagicMock

from flask import Request, Response
from werkzeug.test import EnvironBuilder

from privacyidea.lib.audit import getAudit
from privacyidea.lib.error import HandlerAbortError
from privacyidea.lib.event import event, set_event, EventConfiguration
from privacyidea.lib.user import User
from privacyidea.models import audit_column_length
from .base import MyTestCase, FakeFlaskG


class EventDecoratorExceptionHandlingTestCase(MyTestCase):
    """Test that the event decorator properly handles exceptions from handlers."""

    def setUp(self):
        super().setUp()
        self._event_ids = []
        self.g = FakeFlaskG()
        self.g.audit_object = getAudit(self.app.config)
        self.g.audit_object.audit_data = {
            "action": "POST /test/endpoint",
            "client": "127.0.0.1",
        }
        self.g.event_config = EventConfiguration()
        self.g.logged_in_user = {"username": "admin", "role": "admin", "realm": ""}

        builder = EnvironBuilder(method='POST', data={'serial': 'TEST01'}, headers={})
        self.req = Request(builder.get_environ())
        self.req.all_data = {"serial": "TEST01", "type": "hotp"}
        self.req.User = User()

    def tearDown(self):
        from privacyidea.lib.event import delete_event
        for eid in self._event_ids:
            delete_event(eid)
        super().tearDown()

    def _add_event(self, name, position="post", handlermodule="UserNotification",
                   action="sendmail", **kwargs):
        """Register an event handler and track it for cleanup."""
        kwargs.setdefault("conditions", {})
        kwargs.setdefault("options", {})
        eid = set_event(name, "token_init", handlermodule, action,
                        position=position, **kwargs)
        self._event_ids.append(eid)
        # The decorator reads the handler definitions from the event configuration, which is cached
        self.g.event_config = EventConfiguration()
        return eid

    def _make_decorated_fn(self):
        """Return a decorated API function that returns a successful response."""

        @event("token_init", self.req, self.g)
        def api_fn():
            return Response('{"result": {"value": true}}')

        return api_fn

    def _make_failing_handler(self, exc=None, condition_exc=None):
        """Create a mock handler that raises on do() or check_condition()."""
        mock_handler = MagicMock()
        mock_handler.run_details = ""
        if condition_exc:
            mock_handler.check_condition.side_effect = condition_exc
        else:
            mock_handler.check_condition.return_value = True
            mock_handler.do.side_effect = exc or Exception("handler failed")
        return mock_handler

    def test_post_handler_exception_does_not_crash_api_call(self):
        """A post-event handler that raises should not affect the API response."""
        self._add_event("failing_handler", position="post")
        api_fn = self._make_decorated_fn()

        with patch("privacyidea.lib.event.get_handler_object",
                   return_value=self._make_failing_handler(Exception("SMTP connection refused"))):
            result = api_fn()
            self.assertIn(b"true", result.data)

    def test_pre_handler_exception_does_not_crash_api_call(self):
        """A pre-event handler that raises should not prevent the API function from running."""
        self._add_event("failing_pre_handler", position="pre")

        api_was_called = []

        @event("token_init", self.req, self.g)
        def api_fn():
            api_was_called.append(True)
            return Response('{"result": {"value": true}}')

        with patch("privacyidea.lib.event.get_handler_object",
                   return_value=self._make_failing_handler(RuntimeError("pre handler blew up"))):
            result = api_fn()
            self.assertTrue(api_was_called)
            self.assertIn(b"true", result.data)

    def test_handler_abort_error_still_propagates(self):
        """HandlerAbortError (intentional abort) must NOT be swallowed."""
        self._add_event("aborting_handler", position="post")
        api_fn = self._make_decorated_fn()

        with patch("privacyidea.lib.event.get_handler_object",
                   return_value=self._make_failing_handler(HandlerAbortError("intentional"))):
            with self.assertRaises(HandlerAbortError):
                api_fn()

    def test_handler_abort_error_propagates_from_pre_event(self):
        """HandlerAbortError from a pre-event handler must propagate."""
        self._add_event("aborting_pre_handler", position="pre")
        api_fn = self._make_decorated_fn()

        with patch("privacyidea.lib.event.get_handler_object",
                   return_value=self._make_failing_handler(HandlerAbortError("pre-event abort"))):
            with self.assertRaises(HandlerAbortError):
                api_fn()

    def test_failing_handler_is_audited_with_success_false(self):
        """A handler failure should be recorded in the audit log with success=False."""
        self._add_event("audited_failure", position="post")
        api_fn = self._make_decorated_fn()

        with (patch("privacyidea.lib.event.get_handler_object",
                    return_value=self._make_failing_handler(ConnectionError("Mail server down"))),
              patch("privacyidea.lib.event.getAudit") as mock_get_audit):
            mock_audit_obj = MagicMock()
            mock_get_audit.return_value = mock_audit_obj

            api_fn()

            # Verify success=False was logged
            success_logged = any(
                call_args[0][0].get("success") is False
                for call_args in mock_audit_obj.log.call_args_list
                if call_args[0]
            )
            self.assertTrue(success_logged,
                            f"Expected success=False in audit log calls: "
                            f"{mock_audit_obj.log.call_args_list}")
            mock_audit_obj.finalize_log.assert_called()

    def test_remaining_handlers_run_after_failure(self):
        """If one handler fails, the remaining handlers should still execute."""
        self._add_event("handler_that_fails", position="post", ordering=1)
        self._add_event("handler_that_succeeds", position="post", ordering=2,
                        handlermodule="Logging", action="logit")
        api_fn = self._make_decorated_fn()

        second_handler_called = []

        def get_handler_by_name(handler_name):
            handler = MagicMock(run_details="")
            if handler_name == "UserNotification":
                handler.check_condition.return_value = True
                handler.do.side_effect = Exception("First handler fails")
            else:
                handler.check_condition.return_value = True
                handler.do.side_effect = lambda *a, **kw: second_handler_called.append(True) or True
            return handler

        with patch("privacyidea.lib.event.get_handler_object", side_effect=get_handler_by_name):
            api_fn()

        self.assertTrue(second_handler_called,
                        "Second handler should run even after first handler fails")

    def test_check_condition_exception_propagates(self):
        """An exception while evaluating the conditions must not be treated like an unmet condition."""
        self._add_event("condition_fails", position="post")
        api_fn = self._make_decorated_fn()

        with patch("privacyidea.lib.event.get_handler_object",
                   return_value=self._make_failing_handler(
                       condition_exc=KeyError("bad condition key"))):
            with self.assertRaises(KeyError):
                api_fn()

    def test_pre_event_check_condition_exception_propagates(self):
        """A pre-event handler whose condition evaluation raises must not silently skip the handler."""
        self._add_event("pre_condition_fails", position="pre")
        api_fn = self._make_decorated_fn()

        with patch("privacyidea.lib.event.get_handler_object",
                   return_value=self._make_failing_handler(
                       condition_exc=RuntimeError("resolver unreachable"))):
            with self.assertRaises(RuntimeError):
                api_fn()

    def test_audit_failure_in_except_block_does_not_crash(self):
        """If auditing the failure itself fails, log.error is called and request succeeds."""
        self._add_event("double_failure", position="post")
        api_fn = self._make_decorated_fn()

        with (patch("privacyidea.lib.event.get_handler_object",
                    return_value=self._make_failing_handler(RuntimeError("handler explodes"))),
              patch("privacyidea.lib.event.getAudit") as mock_get_audit,
              patch("privacyidea.lib.event.log") as mock_log):
            mock_audit_obj = MagicMock()
            mock_audit_obj.finalize_log.side_effect = RuntimeError("DB is down")
            mock_get_audit.return_value = mock_audit_obj

            result = api_fn()
            self.assertIn(b"true", result.data)

            error_calls = [str(c) for c in mock_log.error.call_args_list]
            self.assertTrue(
                any("Failed to audit handler failure" in c for c in error_calls),
                f"Expected 'Failed to audit handler failure' in log.error calls: {error_calls}"
            )

    def test_audit_failure_in_pre_event_except_block_logs_error(self):
        """If auditing a pre-event handler failure itself fails, log.error is called."""
        self._add_event("double_failure_pre", position="pre")
        api_fn = self._make_decorated_fn()

        with (patch("privacyidea.lib.event.get_handler_object",
                    return_value=self._make_failing_handler(RuntimeError("pre-handler explodes"))),
              patch("privacyidea.lib.event.getAudit") as mock_get_audit,
              patch("privacyidea.lib.event.log") as mock_log):
            mock_audit_obj = MagicMock()
            mock_audit_obj.finalize_log.side_effect = RuntimeError("audit DB is down")
            mock_get_audit.return_value = mock_audit_obj

            result = api_fn()
            self.assertIn(b"true", result.data)

            error_calls = [str(c) for c in mock_log.error.call_args_list]
            self.assertTrue(
                any("Failed to audit handler failure" in c for c in error_calls),
                f"Expected 'Failed to audit handler failure' in log.error calls: {error_calls}"
            )

    def test_handler_failure_rolls_back_the_session(self):
        """A handler that fails inside a transaction must not leave the session in a failed state."""
        self._add_event("failure_with_open_transaction", position="pre")
        api_fn = self._make_decorated_fn()

        with (patch("privacyidea.lib.event.get_handler_object",
                    return_value=self._make_failing_handler(RuntimeError("handler died mid-transaction"))),
              patch("privacyidea.lib.event.db") as mock_db):
            api_fn()
            mock_db.session.rollback.assert_called_once()

    def test_audited_failure_names_the_exception_class_only(self):
        """The audit entry of a failed handler must not carry the exception message."""
        self._add_event("leaky_exception", position="post")
        api_fn = self._make_decorated_fn()
        secret = "topsecret123456"

        with (patch("privacyidea.lib.event.get_handler_object",
                    return_value=self._make_failing_handler(
                        ConnectionError(f"failed to reach https://remote/validate/check?pass={secret}"))),
              patch("privacyidea.lib.event.getAudit") as mock_get_audit):
            mock_audit_obj = MagicMock()
            mock_get_audit.return_value = mock_audit_obj

            api_fn()

            logged_info = [call_args[0][0].get("info") for call_args in mock_audit_obj.log.call_args_list
                           if call_args[0] and "info" in call_args[0][0]]
            self.assertTrue(logged_info, f"Expected an info value in audit log calls: "
                                         f"{mock_audit_obj.log.call_args_list}")
            self.assertIn("ConnectionError", logged_info[-1])
            for info in logged_info:
                self.assertNotIn(secret, info)

    def test_audited_failure_info_fits_the_audit_column(self):
        """The info of a failed handler is bounded to the length of the audit column."""
        self._add_event("very_long_name", position="post")
        api_fn = self._make_decorated_fn()
        info_limit = audit_column_length.get("info")

        with (patch("privacyidea.lib.event.get_handler_object",
                    return_value=self._make_failing_handler(RuntimeError("x" * 4000))),
              patch("privacyidea.lib.event.getAudit") as mock_get_audit,
              patch.object(EventConfiguration, "get_handled_events",
                           return_value=[{"name": "N" * 4000, "handlermodule": "UserNotification",
                                          "action": "sendmail", "options": {}, "position": "post"}])):
            mock_audit_obj = MagicMock()
            mock_get_audit.return_value = mock_audit_obj

            api_fn()

            logged_info = [call_args[0][0].get("info") for call_args in mock_audit_obj.log.call_args_list
                           if call_args[0] and "info" in call_args[0][0]]
            self.assertEqual(info_limit, len(logged_info[-1]))

    def test_abort_on_error_fails_the_request(self):
        """A post-event handler marked abort_on_error must let its exception reach the client."""
        self._add_event("aborting_on_error", position="post", abort_on_error=True)
        api_fn = self._make_decorated_fn()

        with patch("privacyidea.lib.event.get_handler_object",
                   return_value=self._make_failing_handler(ConnectionError("remote is down"))):
            with self.assertRaises(ConnectionError):
                api_fn()

    def test_abort_on_error_fails_the_request_from_pre_event(self):
        """A pre-event handler marked abort_on_error must prevent the API function from running."""
        self._add_event("aborting_on_error_pre", position="pre", abort_on_error=True)

        api_was_called = []

        @event("token_init", self.req, self.g)
        def api_fn():
            api_was_called.append(True)
            return Response('{"result": {"value": true}}')

        with patch("privacyidea.lib.event.get_handler_object",
                   return_value=self._make_failing_handler(RuntimeError("mangling failed"))):
            with self.assertRaises(RuntimeError):
                api_fn()
        self.assertFalse(api_was_called)

    def test_abort_on_error_is_audited(self):
        """A handler that fails the request is audited like any other handler failure."""
        self._add_event("audited_abort_on_error", position="post", abort_on_error=True)
        api_fn = self._make_decorated_fn()

        with (patch("privacyidea.lib.event.get_handler_object",
                    return_value=self._make_failing_handler(ConnectionError("remote is down"))),
              patch("privacyidea.lib.event.getAudit") as mock_get_audit):
            mock_audit_obj = MagicMock()
            mock_get_audit.return_value = mock_audit_obj

            with self.assertRaises(ConnectionError):
                api_fn()

            success_logged = any(call_args[0][0].get("success") is False
                                 for call_args in mock_audit_obj.log.call_args_list if call_args[0])
            self.assertTrue(success_logged,
                            f"Expected success=False in audit log calls: {mock_audit_obj.log.call_args_list}")
            mock_audit_obj.finalize_log.assert_called()

    def test_abort_on_error_defaults_to_best_effort(self):
        """Without abort_on_error the request continues, which is what an existing binding gets."""
        self._add_event("best_effort_by_default", position="post")
        api_fn = self._make_decorated_fn()

        self.assertFalse(self.g.event_config.get_handled_events("token_init")[0].get("abort_on_error"))

        with patch("privacyidea.lib.event.get_handler_object",
                   return_value=self._make_failing_handler(ConnectionError("remote is down"))):
            result = api_fn()
            self.assertIn(b"true", result.data)

    def test_intentional_abort_is_audited(self):
        """An intentionally aborting handler finalizes its pending audit entry before propagating."""
        self._add_event("audited_abort", position="post")
        api_fn = self._make_decorated_fn()

        with (patch("privacyidea.lib.event.get_handler_object",
                    return_value=self._make_failing_handler(HandlerAbortError("intentional"))),
              patch("privacyidea.lib.event.getAudit") as mock_get_audit):
            mock_audit_obj = MagicMock()
            mock_get_audit.return_value = mock_audit_obj

            with self.assertRaises(HandlerAbortError):
                api_fn()

            success_logged = any(call_args[0][0].get("success") is False
                                 for call_args in mock_audit_obj.log.call_args_list if call_args[0])
            self.assertTrue(success_logged,
                            f"Expected success=False in audit log calls: {mock_audit_obj.log.call_args_list}")
            mock_audit_obj.finalize_log.assert_called()


class ScriptHandlerAbortErrorTestCase(MyTestCase):
    """Test that ScriptEventHandler raises HandlerAbortError (not ServerError)."""

    def setUp(self):
        super().setUp()
        from privacyidea.lib.eventhandler.scripthandler import ScriptEventHandler, SCRIPT_WAIT
        self.ScriptEventHandler = ScriptEventHandler
        self.SCRIPT_WAIT = SCRIPT_WAIT

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

        self.base_options = {
            "g": g,
            "request": req,
            "response": resp,
            "handler_def": {
                "options": {
                    "background": SCRIPT_WAIT,
                    "raise_error": True,
                    "realm": "1",
                    "serial": "1",
                    "logged_in_user": "1",
                    "logged_in_role": "1",
                }
            },
        }
        self.app.config['PI_SCRIPT_HANDLER_DIRECTORY'] = os.path.join(
            os.getcwd(), "tests/testdata/scripts/")

    def _options_with(self, **overrides):
        """Return a copy of base_options with handler_def options overridden."""
        opts = dict(self.base_options)
        opts["handler_def"] = dict(opts["handler_def"])
        opts["handler_def"]["options"] = dict(opts["handler_def"]["options"], **overrides)
        return opts

    def test_script_handler_raises_handler_abort_error(self):
        """The Script handler with raise_error=True should raise HandlerAbortError."""
        handler = self.ScriptEventHandler()
        with self.assertRaises(HandlerAbortError):
            handler.do("fail.sh", options=self.base_options)

    def test_script_handler_popen_failure_with_raise_error(self):
        """When Popen itself raises and raise_error=True, HandlerAbortError is raised."""
        handler = self.ScriptEventHandler()
        with self.assertRaises(HandlerAbortError) as cm:
            handler.do("nonexistent_script.sh", options=self.base_options)
        self.assertIn("Failed to start script", str(cm.exception))

    def test_script_handler_popen_failure_without_raise_error(self):
        """When Popen itself raises but raise_error=False, exception is swallowed."""
        handler = self.ScriptEventHandler()
        options = self._options_with(raise_error=False)
        # Should NOT raise - exception is swallowed
        result = handler.do("nonexistent_script.sh", options=options)
        self.assertTrue(result)
