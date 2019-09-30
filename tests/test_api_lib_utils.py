# -*- coding: utf-8 -*-
"""
This tests the file api.lib.utils
"""
from .base import MyApiTestCase

from privacyidea.api.lib.utils import (getParam,
                                       check_policy_name,
                                       verify_auth_token)
from privacyidea.lib.error import ParameterError
import jwt
import mock
import datetime
from privacyidea.lib.error import AuthError


class UtilsTestCase(MyApiTestCase):

    def test_01_getParam(self):
        s = getParam({"serial": ""}, "serial", optional=False, allow_empty=True)
        self.assertEqual(s, "")

        self.assertRaises(ParameterError, getParam, {"serial": ""}, "serial", optional=False, allow_empty=False)

        # check for allowed values
        v = getParam({"sslverify": "0"}, "sslverify", allowed_values=["0", "1"], default="1")
        self.assertEqual("0", v)

        v = getParam({"sslverify": "rogue value"}, "sslverify", allowed_values=["0", "1"], default="1")
        self.assertEqual("1", v)

        v = getParam({}, "sslverify", allowed_values=["0", "1"], default="1")
        self.assertEqual("1", v)

    def test_02_check_policy_name(self):
        check_policy_name("This is a new valid Name")
        check_policy_name("THis-is-a-valid-Name")
        # The name "check" is reserved
        self.assertRaises(ParameterError, check_policy_name, "check")
        # This is an invalid name
        self.assertRaises(ParameterError, check_policy_name, "~invalid name")

        # some disallowed patterns:
        self.assertRaises(ParameterError, check_policy_name, "Check")
        self.assertRaises(ParameterError, check_policy_name, "pi-update-policy-something")
        # Some patterns that work
        check_policy_name("check this out.")
        check_policy_name("my own pi-update-policy-something")
        check_policy_name("pi-update-policysomething")

    def test_03_verify_auth_token(self):
        # create a jwt with a trusted private key
        with open("tests/testdata/jwt_sign.key", "r") as f:
            key = f.read()

        with mock.patch("logging.Logger.warning") as mock_log:
            auth_token = jwt.encode(payload={"role": "user",
                                             "user": "userA",
                                             "realm": "realm1",
                                             "resolver": "resolverX"},
                                    key=key,
                                    algorithm="RS256")
            r = verify_auth_token(auth_token=auth_token,
                                  required_role="user")
            self.assertEqual(r.get("realm"), "realm1")
            self.assertEqual(r.get("user"), "userA")
            self.assertEqual(r.get("resolver"), "resolverX",)
            self.assertEqual(r.get("role"), "user")
            mock_log.assert_called_once_with("Unsupported JWT algorithm in PI_TRUSTED_JWT.")

        # The signature has expired
        expired_token = jwt.encode(payload={"role": "admin",
                                            "exp": datetime.datetime.utcnow()-datetime.timedelta(seconds=1000)},
                                   key=key,
                                   algorithm="RS256")
        self.assertRaises(AuthError, verify_auth_token, auth_token=expired_token, required_role="admin")

        # The signature does not match
        with mock.patch("logging.Logger.info") as mock_log:
            auth_token = jwt.encode(payload={"role": "user",
                                             "user": "userA",
                                             "realm": "realm1",
                                             "resolver": "resolverX"},
                                    key=key,
                                    algorithm="RS256")
            r = verify_auth_token(auth_token=auth_token,
                                  required_role="user")
            mock_log.assert_any_call("A given JWT definition does not match.")