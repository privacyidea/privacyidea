# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
import io
from collections.abc import Mapping
import logging

import pytest

from .base import MyApiTestCase

from privacyidea.lib.log import is_sensitive_key, log_with, redact

# Values that must never reach the log. They are deliberately unusual strings so that a single
# substring check over the captured log output is enough to detect a leak.
TEST_PIN = "test-pin-9Xk2"
TEST_PASSWORD = "test-password-7Qz4"
TEST_SECRET = "test-secret-3Rv8"
ALL_TEST_SECRETS = [TEST_PIN, TEST_PASSWORD, TEST_SECRET]


def assert_not_logged(log_text: str, secret_values: list = None) -> None:
    """
    Assert that none of the secret test values appears anywhere in the captured log output.

    :param log_text: The captured log output
    :param secret_values: The values that must not appear, defaults to all of them
    """
    for secret in secret_values or ALL_TEST_SECRETS:
        assert secret not in log_text, f"{secret} was written to the log:\n{log_text}"


class TestRedact:
    """Tests for the value redaction that log_with applies to every decorated function."""

    def test_top_level_key(self):
        assert redact({"pin": TEST_PIN}) == {"pin": "HIDDEN"}

    def test_nested_key(self):
        data = {"outer": {"inner": {"password": TEST_PASSWORD}}}
        assert redact(data) == {"outer": {"inner": {"password": "HIDDEN"}}}

    def test_key_inside_list_and_tuple(self):
        data = {"tokens": [{"pin": TEST_PIN}], "pair": ({"secret": TEST_SECRET},)}
        redacted = redact(data)
        assert redacted["tokens"] == [{"pin": "HIDDEN"}]
        assert redacted["pair"] == ({"secret": "HIDDEN"},)

    def test_dotted_and_run_together_keys(self):
        # A key is matched as a whole, per "."/"_"/"-" segment, and by substring, so neither a
        # namespaced nor a run-together spelling has to be listed separately.
        data = {"radius.secret": TEST_SECRET, "motppin": TEST_PIN,
                "private_key_password": TEST_PASSWORD}
        assert redact(data) == {"radius.secret": "HIDDEN", "motppin": "HIDDEN",
                                "private_key_password": "HIDDEN"}

    def test_case_insensitive(self):
        assert redact({"BINDPW": TEST_PASSWORD, "PIN": TEST_PIN}) == {"BINDPW": "HIDDEN",
                                                                     "PIN": "HIDDEN"}

    def test_insensitive_keys_are_preserved(self):
        data = {"serial": "OATH0001", "type": "hotp", "count": 3, "user": None}
        assert redact(data) == data

    def test_original_is_not_modified(self):
        data = {"pin": TEST_PIN, "nested": {"password": TEST_PASSWORD}}
        redact(data)
        assert data == {"pin": TEST_PIN, "nested": {"password": TEST_PASSWORD}}

    def test_non_dict_values_are_returned_unchanged(self):
        assert redact("a string") == "a string"
        assert redact(42) == 42
        assert redact(None) is None

    def test_reference_cycle_terminates(self):
        data = {"pin": TEST_PIN}
        data["self"] = data
        redacted = redact(data)
        assert redacted["pin"] == "HIDDEN"
        assert redacted["self"] == "<recursion>"

    def test_deep_nesting_is_bounded(self):
        data = current = {}
        for _ in range(50):
            current["next"] = {}
            current = current["next"]
        current["pin"] = TEST_PIN
        # Terminates instead of raising RecursionError. The pin is below the depth limit and is
        # therefore not reached at all, so it cannot leak either.
        assert_not_logged(str(redact(data)))

    def test_uncopyable_object_does_not_hide_its_siblings(self):
        class Unpickleable:
            def __deepcopy__(self, memo):
                raise TypeError("cannot copy")

            def __repr__(self):
                return "<Unpickleable>"

        redacted = redact({"obj": Unpickleable(), "pin": TEST_PIN, "serial": "OATH0001"})
        assert redacted["pin"] == "HIDDEN"
        assert redacted["serial"] == "OATH0001"


class TestRedactionFailsClosed:
    """
    A failure while hiding must never fall back to the original value.

    Handing the original back looks harmless because no exception escapes, but the log line then
    renders the object through its repr and the secret is written out. Failing to hide something
    and logging it anyway is the one outcome that must not happen.
    """

    def test_mapping_whose_items_raises_is_not_returned(self):
        class ExplodingMapping(Mapping):
            def __getitem__(self, key):
                return TEST_PIN

            def __iter__(self):
                return iter(["pin"])

            def __len__(self):
                return 1

            def items(self):
                raise RuntimeError("cannot iterate")

            def __repr__(self):
                # What would end up in the log if the original were returned.
                return f"ExplodingMapping(pin={TEST_PIN!r})"

        redacted = redact(ExplodingMapping())
        assert redacted == "<redaction failed>"
        assert_not_logged(str(redacted))

    def test_nested_unwalkable_mapping_does_not_leak(self):
        class ExplodingMapping(Mapping):
            def __getitem__(self, key):
                return TEST_SECRET

            def __iter__(self):
                return iter(["secret"])

            def __len__(self):
                return 1

            def items(self):
                raise RuntimeError("cannot iterate")

            def __repr__(self):
                return f"ExplodingMapping(secret={TEST_SECRET!r})"

        redacted = redact({"serial": "OATH0001", "nested": ExplodingMapping()})
        assert redacted["serial"] == "OATH0001"
        assert_not_logged(str(redacted))

    def test_unreadable_signature_is_reported(self, monkeypatch, caplog):
        def exploding_signature(_func):
            raise ValueError("no signature for this callable")

        monkeypatch.setattr("privacyidea.lib.log.inspect.signature", exploding_signature)
        logger = logging.getLogger("privacyidea.redaction-test-signature")

        with caplog.at_level(logging.WARNING, logger="privacyidea.lib.log"):
            @log_with(logger)
            def check_user_pass(user, passw, options=None):
                return True

        assert "will not be hidden" in caplog.text
        # The decorator still works, it just cannot hide by parameter name any more.
        assert check_user_pass("alice", "some-value") is True


class TestNoOverHiding:
    """
    Names that must stay readable in the log.

    Hiding a value costs nothing in security terms and is therefore invisible to the leak tests,
    which only look for secrets that got through. These are the fields an admin reads while
    debugging, and every one of them is matched by a fragment of a sensitive name, so a change to
    the matching rules can silently swallow them.
    """

    @pytest.mark.parametrize("key", [
        "2stepinit",             # contains "pin" across the boundary of "step" and "init"
        "otpkeyformat",          # contains "otpkey" but names a format, not a key
        "encryptpin",            # a flag saying whether to encrypt, not a pin
        "radius.local_checkpin", # a flag selecting where the pin is checked
        "remote.local_checkpin",
        "credential_id",         # a public identifier
        "registered_credential_ids",
        "pinode",                # the node name
        "otplen",
        "serial",
        "tokentype",
        "rollout_state",
        "failcount",
        "ssl_verify",            # "verify" is only sensitive as a whole key
        "verify_tls",
        "push_ssl_verify",
    ])
    def test_key_is_not_hidden(self, key):
        assert not is_sensitive_key(key), f"{key} would be hidden from the log"

    @pytest.mark.parametrize("key", [
        "force_app_pin",          # a policy action governing a PIN, not holding one
        "otp_pin_minlength",
        "otp_pin_contents",
        "change_pin_every",
        "setpin",                 # the right to set a PIN
        "set_hsm_password",
        "passOnNoToken",
        "otp_valid",
        "password_hash_type",     # the name of an algorithm
        "daypassword.hashlib",
        "requestMapping",
        "webauthn_public_key_credential_algorithms",
    ])
    def test_policy_action_name_is_not_hidden(self, key):
        assert not is_sensitive_key(key), f"{key} would be hidden from the log"

    def test_a_flag_is_never_hidden_even_under_a_sensitive_name(self):
        # A key can be named after the credential it governs while holding only a switch.
        assert redact({"pin": True, "password": False, "otpkey": None}) == {
            "pin": True, "password": False, "otpkey": None}

    def test_a_credential_under_the_same_name_is_hidden(self):
        assert redact({"pin": TEST_PIN, "password": TEST_PASSWORD}) == {
            "pin": "HIDDEN", "password": "HIDDEN"}

    def test_sensitive_names_are_still_hidden(self):
        # The counterpart, so that widening the exceptions above cannot quietly disable hiding.
        for key in ["pin", "otppin", "userpin", "sopin", "motppin", "password", "BINDPW",
                    "radius.secret", "otpkey", "anOtpVal", "Authorization", "verify"]:
            assert is_sensitive_key(key), f"{key} would be logged"


class TestLogWithRedaction:
    """Tests for the argument hiding of the log_with decorator itself."""

    @pytest.fixture
    def logger(self, caplog):
        caplog.set_level(logging.DEBUG, logger="privacyidea.redaction-test")
        return logging.getLogger("privacyidea.redaction-test")

    def test_positional_dict_argument(self, logger, caplog):
        @log_with(logger)
        def init_token(param, user=None):
            return "token"

        init_token({"type": "hotp", "pin": TEST_PIN, "serial": "OATH0001"})
        assert_not_logged(caplog.text)
        assert "OATH0001" in caplog.text

    def test_keyword_dict_argument(self, logger, caplog):
        @log_with(logger)
        def init_token(param, user=None):
            return "token"

        # The same call by keyword. The hidden value does not depend on the position it arrives in.
        init_token(param={"type": "hotp", "pin": TEST_PIN})
        assert_not_logged(caplog.text)

    def test_bound_method_with_self(self, logger, caplog):
        class TokenClass:
            @log_with(logger)
            def update(self, param):
                return True

            def __repr__(self):
                return "<TokenClass>"

        TokenClass().update({"radius.secret": TEST_SECRET, "pin": TEST_PIN})
        assert_not_logged(caplog.text)

    def test_plain_string_argument_is_hidden_by_hide_args(self, logger, caplog):
        # A bare secret string carries no key name, so the denylist cannot see it and the
        # decorator has to name the parameter.
        @log_with(logger, hide_args=[1])
        def check_user_pass(user, passw, options=None):
            return True

        check_user_pass("alice", TEST_PASSWORD, options={})
        assert_not_logged(caplog.text)

    def test_secret_passed_by_keyword_is_hidden(self, logger, caplog):
        @log_with(logger)
        def check_user_pass(user, passw, options=None):
            return True

        check_user_pass("alice", passw=TEST_PASSWORD)
        assert_not_logged(caplog.text)

    def test_no_keyword_is_reported_as_hidden_unless_it_was_passed(self, caplog):
        # A log line that names a keyword as HIDDEN which the caller never sent looks redacted
        # while the value sits unhidden in the positional arguments next to it.
        logger = logging.getLogger("privacyidea.redaction-test-phantom")
        caplog.set_level(logging.DEBUG, logger="privacyidea.redaction-test-phantom")

        @log_with(logger)
        def check_user_pass(user, passw, options=None):
            return True

        check_user_pass("alice", "positional-secret")
        assert "'passw': 'HIDDEN'" not in caplog.text
        assert "keywords {}" in caplog.text

    def test_nothing_is_logged_below_debug(self, logger, caplog):
        @log_with(logger)
        def init_token(param):
            return "token"

        caplog.set_level(logging.INFO, logger="privacyidea.redaction-test")
        init_token({"pin": TEST_PIN})
        assert_not_logged(caplog.text)
        assert caplog.text == ""


class TestNoSecretsInApiLogs(MyApiTestCase):
    """
    Drive the API paths that carry a credential with the whole privacyidea logger at DEBUG and
    assert that no credential reaches the log. This is the safety net that per-call-site hiding
    configuration could not have: it fails when a secret becomes loggable anywhere along the call
    chain, not only in the one frame someone remembered to configure.
    """

    def setUp(self):
        self.log_stream = io.StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.logger = logging.getLogger("privacyidea")
        self.previous_level = self.logger.level
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.handler)

    def tearDown(self):
        self.logger.removeHandler(self.handler)
        self.logger.setLevel(self.previous_level)

    def request(self, path: str, data: dict, method: str = "POST") -> None:
        with self.app.test_request_context(path, data=data, method=method,
                                           headers={"Authorization": self.at}):
            self.app.full_dispatch_request()

    def test_token_init_does_not_log_the_pin_or_otpkey(self):
        self.request("/token/init", {"type": "hotp", "genkey": 1, "serial": "LOGTEST01",
                                     "pin": TEST_PIN})
        assert_not_logged(self.log_stream.getvalue(), [TEST_PIN])

    def test_radius_token_init_does_not_log_the_shared_secret(self):
        self.request("/token/init", {"type": "radius", "serial": "LOGTEST02",
                                     "radius.server": "1.2.3.4", "radius.user": "alice",
                                     "radius.secret": TEST_SECRET, "pin": TEST_PIN})
        assert_not_logged(self.log_stream.getvalue(), [TEST_SECRET, TEST_PIN])

    def test_motp_token_init_does_not_log_the_motppin(self):
        self.request("/token/init", {"type": "motp", "genkey": 1, "serial": "LOGTEST03",
                                     "motppin": TEST_PIN})
        assert_not_logged(self.log_stream.getvalue(), [TEST_PIN])

    def test_validate_check_does_not_log_the_password(self):
        self.request("/validate/check", {"user": "nonexistent", "pass": TEST_PASSWORD})
        assert_not_logged(self.log_stream.getvalue(), [TEST_PASSWORD])
