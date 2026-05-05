"""
Tests for the generic DeprecatedTokenClass.

See dev/token-deprecation-strategy.md for the design. The class is a
stand-in for token types that have been removed from privacyIDEA —
safe to list and delete, refusing any authentication or enrollment
operation.
"""
from privacyidea.lib.error import NoLongerSupportedError
from privacyidea.lib.token import get_tokens, remove_token
from privacyidea.lib.tokens.deprecated import DeprecatedTokenClass
from privacyidea.models import Token
from .base import MyTestCase


class DeprecatedTokenTestCase(MyTestCase):
    serial_u2f = "DEPR_U2F_001"
    serial_unknown = "DEPR_UNK_001"

    def _create_deprecated_token(self, serial: str, original: str | None) -> DeprecatedTokenClass:
        db_token = Token(serial, tokentype="deprecated")
        db_token.save()
        token = DeprecatedTokenClass(db_token)
        if original is not None:
            token.add_tokeninfo("original_tokentype", original)
        token.add_tokeninfo("deprecated_in", "3.14")
        return token

    def test_01_class_identity(self):
        self.assertEqual("deprecated", DeprecatedTokenClass.get_class_type())
        self.assertEqual("DEPR", DeprecatedTokenClass.get_class_prefix())
        self.assertEqual([], DeprecatedTokenClass.mode)

    def test_02_listable_via_get_tokens(self):
        """A deprecated token must show up in get_tokens() just like any other."""
        self._create_deprecated_token(self.serial_u2f, "u2f")

        # Fetch by serial
        tokens = get_tokens(serial=self.serial_u2f)
        self.assertEqual(1, len(tokens))
        self.assertIsInstance(tokens[0], DeprecatedTokenClass)
        self.assertEqual("u2f", tokens[0].get_tokeninfo("original_tokentype"))

        # Fetch by tokentype filter — the canonical janitor query
        tokens = get_tokens(tokentype="deprecated")
        self.assertEqual(1, len(tokens))
        self.assertEqual(self.serial_u2f, tokens[0].token.serial)

        remove_token(serial=self.serial_u2f)

    def test_03_deletable_via_remove_token(self):
        """remove_token() must cleanly delete a deprecated token, not crash."""
        self._create_deprecated_token(self.serial_u2f, "u2f")
        self.assertEqual(1, len(get_tokens(serial=self.serial_u2f)))

        removed = remove_token(serial=self.serial_u2f)
        self.assertEqual(1, removed)
        self.assertEqual(0, len(get_tokens(serial=self.serial_u2f)))

    def test_04_check_otp_returns_failure(self):
        token = self._create_deprecated_token(self.serial_u2f, "u2f")
        self.assertEqual(-1, token.check_otp("whatever"))
        remove_token(serial=self.serial_u2f)

    def test_05_create_challenge_returns_failure(self):
        token = self._create_deprecated_token(self.serial_u2f, "u2f")
        success, message, transaction_id, reply = token.create_challenge()
        self.assertFalse(success)
        remove_token(serial=self.serial_u2f)

    def test_06_authenticate_returns_failure(self):
        token = self._create_deprecated_token(self.serial_u2f, "u2f")
        pin_match, otp_counter, reply = token.authenticate("pin")
        self.assertFalse(pin_match)
        self.assertEqual(-1, otp_counter)
        remove_token(serial=self.serial_u2f)

    def test_07_update_refuses(self):
        token = self._create_deprecated_token(self.serial_u2f, "u2f")
        with self.assertRaises(NoLongerSupportedError):
            token.update({"description": "try to rewrite"})
        remove_token(serial=self.serial_u2f)

    def test_08_is_challenge_request_returns_false(self):
        """
        is_challenge_request MUST return False (not raise) so a user who has
        both a deprecated and a working token can still authenticate with
        the working one. See dev/token-deprecation-strategy.md.
        """
        token = self._create_deprecated_token(self.serial_u2f, "u2f")
        self.assertFalse(token.is_challenge_request("some_pass"))
        remove_token(serial=self.serial_u2f)

    def test_09_error_message_mentions_original_type(self):
        token = self._create_deprecated_token(self.serial_u2f, "u2f")
        with self.assertRaises(NoLongerSupportedError) as ctx:
            token.update({})
        self.assertIn("u2f", str(ctx.exception))
        remove_token(serial=self.serial_u2f)

    def test_10_unknown_original_type_handled(self):
        """
        If tokeninfo['original_tokentype'] is missing (e.g. a malformed row),
        the error must still be raised with an 'unknown' placeholder instead
        of crashing on a NoneType format.
        """
        token = self._create_deprecated_token(self.serial_unknown, original=None)
        with self.assertRaises(NoLongerSupportedError) as ctx:
            token.update({})
        self.assertIn("unknown", str(ctx.exception))
        remove_token(serial=self.serial_unknown)

    def test_11_enable_true_refused(self):
        """
        Calling enable(True) must refuse. Otherwise the admin could flip
        active=True via the UI and the token would look usable while
        still refusing to authenticate.
        """
        token = self._create_deprecated_token(self.serial_u2f, "u2f")
        token.token.active = False
        token.token.save()
        with self.assertRaises(NoLongerSupportedError):
            token.enable(True)
        # State must not have changed
        self.assertFalse(token.token.active)
        remove_token(serial=self.serial_u2f)

    def test_12_enable_false_allowed(self):
        """enable(False) must remain possible — it's a defensive disable."""
        token = self._create_deprecated_token(self.serial_u2f, "u2f")
        token.token.active = True
        token.token.save()
        token.enable(False)  # must not raise
        self.assertFalse(token.token.active)
        remove_token(serial=self.serial_u2f)

    def test_13_reset_refused(self):
        token = self._create_deprecated_token(self.serial_u2f, "u2f")
        with self.assertRaises(NoLongerSupportedError):
            token.reset()
        remove_token(serial=self.serial_u2f)

    def test_14_get_init_detail_refused(self):
        token = self._create_deprecated_token(self.serial_u2f, "u2f")
        with self.assertRaises(NoLongerSupportedError):
            token.get_init_detail()
        remove_token(serial=self.serial_u2f)

    def test_15_check_challenge_response_returns_failure(self):
        token = self._create_deprecated_token(self.serial_u2f, "u2f")
        self.assertEqual(-1, token.check_challenge_response(passw="anything"))
        remove_token(serial=self.serial_u2f)

    def test_16_api_endpoint_refused(self):
        """The class-level REST endpoint hook must refuse as well."""
        from privacyidea.lib.tokens.deprecated import DeprecatedTokenClass
        with self.assertRaises(NoLongerSupportedError):
            DeprecatedTokenClass.api_endpoint(request=None, g=None)

    def test_17_read_operations_still_work(self):
        """
        Inspection paths (get_as_dict, get_tokeninfo) must continue to work
        on a deprecated token — admins need these to see what they have.
        """
        token = self._create_deprecated_token(self.serial_u2f, "u2f")
        self.assertEqual("u2f", token.get_tokeninfo("original_tokentype"))
        self.assertEqual("3.14", token.get_tokeninfo("deprecated_in"))
        d = token.get_as_dict()
        self.assertEqual(self.serial_u2f, d.get("serial"))
        self.assertEqual("deprecated", d.get("tokentype"))
        remove_token(serial=self.serial_u2f)
