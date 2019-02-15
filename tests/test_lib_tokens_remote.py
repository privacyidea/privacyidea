"""
This test file tests the lib.tokens.remotetoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.remotetoken import RemoteTokenClass
from privacyidea.models import Token
import responses
import json
from privacyidea.lib.config import set_privacyidea_config


class RemoteTokenTestCase(MyTestCase):

    otppin = "topsecret"
    serial1 = "ser1"
    params1 = {"remote.server": "http://my.privacyidea.server",
               "remote.local_checkpin": True,
               "remote.serial": "s0001",
               "remote.user": "",
               "remote.realm": "",
               "remote.resolver": ""}
    serial2 = "use1"
    params2 = {"remote.server": "http://my.privacyidea.server",
               "remote.path": "/mypi/validate/check",
               "remote.local_checkpin": False,
               "remote.user": "user1",
               "remote.realm": "realm1",
               "remote.resolver": "reso1"}
    serial3 = "serial3"
    params3 = {"remote.server": "http://my.privacyidea.server"}

    success_body = {"detail": {"message": "matching 1 tokens",
                               "serial": "PISP0000AB00",
                               "type": "spass"},
                    "id": 1,
                    "jsonrpc": "2.0",
                    "result": {"status": True,
                               "value": True
                    },
                    "version": "privacyIDEA unknown"
    }

    fail_body = {"detail": {"message": "wrong otp value"},
                    "id": 1,
                    "jsonrpc": "2.0",
                    "result": {"status": True,
                               "value": False
                    },
                    "version": "privacyIDEA unknown"
    }

    def test_01_create_token(self):
        db_token = Token(self.serial3, tokentype="remote")
        db_token.save()
        token = RemoteTokenClass(db_token)
        token.update(self.params3)
        token.set_pin(self.otppin)

        db_token = Token(self.serial2, tokentype="remote")
        db_token.save()
        token = RemoteTokenClass(db_token)
        token.update(self.params2)
        token.set_pin(self.otppin)

        db_token = Token(self.serial1, tokentype="remote")
        db_token.save()
        token = RemoteTokenClass(db_token)
        token.update(self.params1)
        token.set_pin(self.otppin)

        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "remote",
                        token.token.tokentype)
        self.assertTrue(token.type == "remote", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "PIRE", class_prefix)
        self.assertTrue(token.get_class_type() == "remote", token)


    def test_02_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RemoteTokenClass(db_token)

        info = token.get_class_info()
        self.assertTrue(info.get("title") == "Remote Token",
                        "{0!s}".format(info.get("title")))

        info = token.get_class_info("title")
        self.assertTrue(info == "Remote Token", info)

    def test_03_check_pin_local(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RemoteTokenClass(db_token)

        r = token.check_pin_local
        self.assertTrue(r, r)

    @responses.activate
    def test_04_do_request_success(self):
        responses.add(responses.POST,
                      "http://my.privacyidea.server/validate/check",
                      body=json.dumps(self.success_body),
                      content_type="application/json")

        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RemoteTokenClass(db_token)

        otpcount = token.check_otp("123456")
        self.assertTrue(otpcount > 0, otpcount)


    @responses.activate
    def test_05_do_request_fail(self):
        responses.add(responses.POST,
                      "http://my.privacyidea.server/validate/check",
                      body=json.dumps(self.fail_body),
                      content_type="application/json")

        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RemoteTokenClass(db_token)

        otpcount = token.check_otp("123456")
        self.assertTrue(otpcount == -1, otpcount)

    @responses.activate
    def test_06_do_request_success_remote_user(self):
        # verify SSL
        set_privacyidea_config("remote.verify_ssl_certificate", True)
        responses.add(responses.POST,
                      "http://my.privacyidea.server/mypi/validate/check",
                      body=json.dumps(self.success_body),
                      content_type="application/json")

        db_token = Token.query.filter(Token.serial == self.serial2).first()
        token = RemoteTokenClass(db_token)
        otpcount = token.check_otp("123456")
        self.assertTrue(otpcount > 0, otpcount)

    @responses.activate
    def test_07_do_request_missing_config(self):
        responses.add(responses.POST,
                      "http://my.privacyidea.server/mypi/validate/check",
                      body=json.dumps(self.success_body),
                      content_type="application/json")

        db_token = Token.query.filter(Token.serial == self.serial3).first()
        token = RemoteTokenClass(db_token)
        # Authentication will fail, since neither remote.serial nor remote.user
        otpcount = token.check_otp("123456")
        self.assertTrue(otpcount == -1, otpcount)

    @responses.activate
    def test_08_authenticate_local_pin(self):
        responses.add(responses.POST,
                      "http://my.privacyidea.server/validate/check",
                      body=json.dumps(self.success_body),
                      content_type="application/json")
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RemoteTokenClass(db_token)

        # wrong PIN
        r = token.authenticate("wrong"+"123456")
        self.assertFalse(r[0], r)
        self.assertTrue(r[1] == -1, r)
        self.assertTrue(r[2].get("message") == "Wrong PIN", r)
        # rigth PIN
        r = token.authenticate(self.otppin+"123456")
        self.assertTrue(r[0], r)
        self.assertTrue(r[1] >= 0, r)
        self.assertTrue(r[2].get("message") == "matching 1 tokens", r)


    @responses.activate
    def test_09_authenticate_remote_pin(self):
        responses.add(responses.POST,
                      "http://my.privacyidea.server/mypi/validate/check",
                      body=json.dumps(self.success_body),
                      content_type="application/json")
        db_token = Token.query.filter(Token.serial == self.serial2).first()
        token = RemoteTokenClass(db_token)
        token.set_pin("")
        r = token.authenticate("remotePIN123456")
        self.assertTrue(r[0], r)
        self.assertTrue(r[1] >= 0, r)
        self.assertTrue(r[2].get("message") == "matching 1 tokens", r)

    def test_10_authenticate_challenge_response(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RemoteTokenClass(db_token)
        token.set_pin(self.otppin)
        r = token.is_challenge_request(self.otppin)
        # Return True, the PIN triggers a challenges request.
        self.assertTrue(r)

    def test_11_check_challenge_response(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RemoteTokenClass(db_token)
        token.set_pin(self.otppin)
        r = token.check_challenge_response(passw="somePW",
                                           options={"transactionid": "1234"})

        self.assertTrue(r)
