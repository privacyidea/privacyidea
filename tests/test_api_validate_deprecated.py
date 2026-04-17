"""
Integration tests for deprecated tokens in the validate API.

A user who has both a deprecated token and a working token must still
be able to authenticate with the working one.  The deprecated token
must be silently skipped — no exception, no abort.

See dev/token-deprecation-strategy.md for the design.
"""
from privacyidea.lib import _
from privacyidea.lib.token import init_token, remove_token
from privacyidea.lib.tokens.deprecated import DeprecatedTokenClass
from privacyidea.lib.user import User
from privacyidea.lib.utils import AUTH_RESPONSE
from privacyidea.models import Token
from .base import MyApiTestCase


class DeprecatedTokenValidateTestCase(MyApiTestCase):

    def test_01_triggerchallenge_skips_deprecated_token(self):
        """
        A user has an HOTP token (challenge-response capable) and a
        deprecated token.  triggerchallenge must create a challenge for
        the HOTP token and silently skip the deprecated one.
        """
        self.setUp_user_realms()
        user = User("cornelius", self.realm1)
        hotp_serial = "HOTP_WORK_001"
        depr_serial = "DEPR_SKIP_001"

        # Create a working HOTP token
        hotp_token = init_token({"serial": hotp_serial,
                                 "type": "hotp",
                                 "otpkey": self.otpkey,
                                 "pin": "pin"},
                                user=user)
        self.assertTrue(hotp_token)

        # Create a deprecated token for the same user
        db_token = Token(depr_serial, tokentype="deprecated")
        db_token.save()
        depr_token = DeprecatedTokenClass(db_token)
        depr_token.add_tokeninfo("original_tokentype", "u2f")
        depr_token.add_tokeninfo("deprecated_in", "3.14")
        depr_token.add_user(user)
        depr_token.token.active = True
        depr_token.token.save()

        try:
            # triggerchallenge must succeed — the deprecated token must not abort the flow
            with self.app.test_request_context('/validate/triggerchallenge',
                                               method='POST',
                                               data={"user": "cornelius"},
                                               headers={"Authorization": self.at}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                result = res.json.get("result")
                self.assertEqual(1, result.get("value"))
                self.assertEqual(AUTH_RESPONSE.CHALLENGE, result.get("authentication"))
                detail = res.json.get("detail")
                self.assertEqual(detail.get("messages")[0], _("please enter otp: "))
                transaction_id = detail.get("transaction_id")

            # The challenge must be for the HOTP token, not the deprecated one
            multi = res.json["detail"]["multi_challenge"]
            self.assertEqual(1, len(multi))
            self.assertEqual(hotp_serial, multi[0]["serial"])

            # Verify the user can authenticate with the HOTP token
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "transaction_id": transaction_id,
                                                     "pass": "287082"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                result = res.json.get("result")
                self.assertTrue(result.get("value"))
        finally:
            remove_token(serial=hotp_serial)
            remove_token(serial=depr_serial)

    def test_02_validate_check_skips_deprecated_token(self):
        """
        A user authenticates via /validate/check with PIN+OTP.
        The deprecated token must be silently skipped and the working
        HOTP token must handle the authentication.
        """
        self.setUp_user_realms()
        user = User("cornelius", self.realm1)
        hotp_serial = "HOTP_WORK_002"
        depr_serial = "DEPR_SKIP_002"

        # Create a working HOTP token
        init_token({"serial": hotp_serial,
                     "type": "hotp",
                     "otpkey": self.otpkey,
                     "pin": "pin"},
                    user=user)

        # Create a deprecated token for the same user
        db_token = Token(depr_serial, tokentype="deprecated")
        db_token.save()
        depr_token = DeprecatedTokenClass(db_token)
        depr_token.add_tokeninfo("original_tokentype", "u2f")
        depr_token.add_user(user)
        depr_token.token.active = True
        depr_token.token.save()

        try:
            # Authenticate with the HOTP token — deprecated token must not interfere
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "pass": "pin287082"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                result = res.json.get("result")
                self.assertTrue(result.get("value"))
        finally:
            remove_token(serial=hotp_serial)
            remove_token(serial=depr_serial)

    def test_03_only_deprecated_token_fails_gracefully(self):
        """
        A user with only a deprecated token must get a clean rejection,
        not a server error.
        """
        self.setUp_user_realms()
        user = User("cornelius", self.realm1)
        depr_serial = "DEPR_ONLY_001"

        db_token = Token(depr_serial, tokentype="deprecated")
        db_token.save()
        depr_token = DeprecatedTokenClass(db_token)
        depr_token.add_tokeninfo("original_tokentype", "u2f")
        depr_token.add_user(user)
        depr_token.token.active = True
        depr_token.token.save()

        try:
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "pass": "anything"}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                result = res.json.get("result")
                # Authentication must fail, but not with a 500
                self.assertFalse(result.get("value"))
        finally:
            remove_token(serial=depr_serial)
