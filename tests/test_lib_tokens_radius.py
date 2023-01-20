# coding: utf-8
"""
This test file tests the lib.tokens.radiustoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.radiustoken import RadiusTokenClass
from privacyidea.lib.challenge import get_challenges
from privacyidea.models import Token
from privacyidea.lib.error import ParameterError
from privacyidea.lib.config import set_privacyidea_config
from . import radiusmock
from privacyidea.lib.token import init_token
from privacyidea.lib.radiusserver import add_radius

DICT_FILE = "tests/testdata/dictionary"


class RadiusTokenTestCase(MyTestCase):

    otppin = "topsecret"
    serial1 = "ser1"
    params1 = {"radius.server": "my.other.radiusserver:1812",
               "radius.local_checkpin": True,
               "radius.user": "user1",
               "radius.secret": "testing123",
               "radius.dictfile": "tests/testdata/dictfile"}
    serial2 = "use1"
    params2 = {"radius.server": "my.other.radiusserver:1812",
               "radius.local_checkpin": False,
               "radius.user": "user1",
               "radius.secret": "testing123",
               "radius.dictfile": "tests/testdata/dictfile"}
    serial3 = "serial3"
    params3 = {"radius.server": "my.other.radiusserver:1812"}

    def test_01_create_token(self):
        db_token = Token(self.serial3, tokentype="radius")
        db_token.save()
        token = RadiusTokenClass(db_token)
        # Missing radius.user parameter
        self.assertRaises(ParameterError, token.update, self.params3)

        db_token = Token(self.serial2, tokentype="radius")
        db_token.save()
        token = RadiusTokenClass(db_token)
        token.update(self.params2)
        token.set_pin(self.otppin)

        db_token = Token(self.serial1, tokentype="radius")
        db_token.save()
        token = RadiusTokenClass(db_token)
        token.update(self.params1)
        token.set_pin(self.otppin)

        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "radius",
                        token.token.tokentype)
        self.assertTrue(token.type == "radius", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "PIRA", class_prefix)
        self.assertTrue(token.get_class_type() == "radius", token)


    def test_02_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RadiusTokenClass(db_token)

        info = token.get_class_info()
        self.assertTrue(info.get("title") == "RADIUS Token",
                        "{0!s}".format(info.get("title")))

        info = token.get_class_info("title")
        self.assertTrue(info == "RADIUS Token", info)

    def test_03_check_pin_local(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RadiusTokenClass(db_token)

        r = token.check_pin_local
        self.assertTrue(r, r)

    @radiusmock.activate
    def test_04_do_request_success(self):
        radiusmock.setdata(response=radiusmock.AccessAccept)
        set_privacyidea_config("radius.dictfile", DICT_FILE)
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RadiusTokenClass(db_token)
        otpcount = token.check_otp("123456")
        self.assertTrue(otpcount >= 0, otpcount)


    @radiusmock.activate
    def test_05_do_request_fail(self):
        radiusmock.setdata(response=radiusmock.AccessReject)
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RadiusTokenClass(db_token)
        otpcount = token.check_otp("123456")
        self.assertTrue(otpcount == -1, otpcount)

    @radiusmock.activate
    def test_08_authenticate_local_pin(self):
        radiusmock.setdata(response=radiusmock.AccessAccept)
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = RadiusTokenClass(db_token)
        # wrong PIN
        r = token.authenticate("wrong"+"123456")
        self.assertFalse(r[0], r)
        self.assertTrue(r[1] == -1, r)
        self.assertTrue(r[2].get("message") == "Wrong PIN", r)
        # right PIN
        r = token.authenticate(self.otppin+"123456")
        self.assertTrue(r[0], r)
        self.assertTrue(r[1] >= 0, r)

    @radiusmock.activate
    def test_09_authenticate_radius_pin(self):
        radiusmock.setdata(response=radiusmock.AccessAccept)
        db_token = Token.query.filter(Token.serial == self.serial2).first()
        token = RadiusTokenClass(db_token)
        token.set_pin("")
        r = token.authenticate("radiusPIN123456")
        self.assertTrue(r[0], r)
        self.assertTrue(r[1] >= 0, r)

    @radiusmock.activate
    def test_10_authenticate_system_radius_settings(self):
        set_privacyidea_config("radius.server", "my.other.radiusserver:1812")
        set_privacyidea_config("radius.secret", "testing123")
        radiusmock.setdata(response=radiusmock.AccessAccept)
        token = init_token({"type": "radius",
                            "radius.system_settings": True,
                            "radius.user": "user1",
                            "radius.server": "",
                            "radius.secret": ""})
        r = token.authenticate("radiuspassword")
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], 1)

    @radiusmock.activate
    def test_11_RADIUS_request(self):
        set_privacyidea_config("radius.dictfile", DICT_FILE)
        radiusmock.setdata(response=radiusmock.AccessAccept)
        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123", dictionary=DICT_FILE)
        self.assertTrue(r > 0)
        token = init_token({"type": "radius",
                            "radius.identifier": "myserver",
                            "radius.user": "user1"})
        r = token.authenticate("radiuspassword")
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], 1)

    @radiusmock.activate
    def test_12_non_ascii(self):
        set_privacyidea_config("radius.dictfile", DICT_FILE)
        radiusmock.setdata(response=radiusmock.AccessAccept)
        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123", dictionary=DICT_FILE)
        self.assertTrue(r > 0)
        token = init_token({"type": "radius",
                            "radius.identifier": "myserver",
                            "radius.user": "nönäscii"})
        r = token.authenticate("passwörd")
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], 1)

    @radiusmock.activate
    def test_00_test_check_radius(self):
        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123", dictionary=DICT_FILE)
        self.assertTrue(r > 0)
        token = init_token({"type": "radius",
                            "radius.identifier": "myserver",
                            "radius.local_checkpin": True,
                            "radius.user": "nönäscii"})

        # check the working of internal _check_radius
        radiusmock.setdata(response=radiusmock.AccessChallenge)
        r = token._check_radius("123456")
        self.assertEqual(r, radiusmock.AccessChallenge)

        radiusmock.setdata(response=radiusmock.AccessAccept)
        r = token._check_radius("123456")
        self.assertEqual(r, radiusmock.AccessAccept)

        radiusmock.setdata(response=radiusmock.AccessReject)
        r = token._check_radius("123456")
        self.assertEqual(r, radiusmock.AccessReject)

    @radiusmock.activate
    def test_13_privacyidea_challenge_response(self):
        # This tests the challenge response with the privacyIDEA PIN.
        # First an authentication request with only the local PIN of the
        # radius token is sent.
        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123", dictionary=DICT_FILE)
        self.assertTrue(r > 0)
        token = init_token({"type": "radius",
                            "pin": "local",
                            "radius.identifier": "myserver",
                            "radius.local_checkpin": True,
                            "radius.user": "nönäscii"})

        r = token.is_challenge_request("local")
        self.assertTrue(r)

        # create challenge of privacyidea
        r, message, transaction_id, _attr = token.create_challenge()
        self.assertTrue(r)
        self.assertEqual("Enter your RADIUS tokencode:", message)

        # check, if there is a challenge in the DB
        chals = get_challenges(token.token.serial)
        self.assertEqual(len(chals), 1)
        self.assertEqual(chals[0].transaction_id, transaction_id)

        # check if this is a response to a previously sent challenge
        r = token.is_challenge_response("radiuscode", options={"transaction_id": transaction_id})
        self.assertTrue(r)

        # Now check, if the answer for the challenge is correct
        radiusmock.setdata(response=radiusmock.AccessAccept)
        r = token.check_challenge_response(passw="radiuscode",
                                           options={"transaction_id": transaction_id})
        self.assertTrue(r)

    @radiusmock.activate
    def test_14_simple_challenge_response_in_radius_server(self):
        # In this case we test a simple challenge response in
        # the radius server. The PIN is checked locally.
        # A AccessRequest is sent to the RADIUS server, the RADIUS server
        # answers with an AccessChallenge, which creates a transaction id
        # in privacyIDEA.
        # This is answered and the RADIUS server sends an AccessAccept
        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123", dictionary=DICT_FILE)
        self.assertTrue(r > 0)
        token = init_token({"type": "radius",
                            "radius.identifier": "myserver",
                            "radius.local_checkpin": False,
                            "radius.user": "nönäscii"})

        # Check if the remote PIN would create a RADIUS challenge
        state1 = [b"123456"]
        radiusmock.setdata(timeout=False, response=radiusmock.AccessChallenge,
                           response_data={"State": state1,
                                          "Reply_Message": ["Please provide more information."]})
        opts = {}
        r = token.is_challenge_request("some_remote_value", options=opts)
        self.assertTrue(r)
        self.assertEqual(opts.get("radius_message"), "Please provide more information.")
        self.assertEqual(opts.get("radius_result"), radiusmock.AccessChallenge)
        self.assertEqual(opts.get("radius_state"), state1[0])

        # Creating the challenge within privacyIDEA
        r, message, transaction_id, _attr = token.create_challenge(options=opts)
        self.assertTrue(r)
        self.assertEqual(message, "Please provide more information.")

        # Check if a challenge is created
        chals = get_challenges(token.token.serial)
        self.assertEqual(len(chals), 1)
        self.assertEqual(chals[0].transaction_id, transaction_id)

        # Checking, if this is the answer attempt to a challenge
        r = token.is_challenge_response("some_response", options={"transaction_id": transaction_id})
        self.assertTrue(r)

        # Check what happens if the RADIUS server rejects the response
        radiusmock.setdata(timeout=False, response=radiusmock.AccessReject)
        r = token.check_challenge_response(passw="some_response",
                                           options={"transaction_id": transaction_id})
        self.assertLess(r, 0)

        # Now checking the response to the challenge and we issue a RADIUS request
        radiusmock.setdata(timeout=False, response=radiusmock.AccessAccept)
        r = token.check_challenge_response(passw="some_response",
                                           options={"transaction_id": transaction_id})
        self.assertGreaterEqual(r, 0)

    @radiusmock.activate
    def test_15_multi_challenge_response_in_radius_server(self):
        # The RADIUS server issues a AccessChallenge on the first and on the
        # second request
        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123", dictionary=DICT_FILE)
        self.assertTrue(r > 0)
        token = init_token({"type": "radius",
                            "radius.identifier": "myserver",
                            "radius.local_checkpin": False,
                            "radius.user": "nönäscii"})

        # Check if the remote PIN would create a RADIUS challenge
        state1 = [b"123456"]
        state2 = [b"999999"]
        radiusmock.setdata(timeout=False, response=radiusmock.AccessChallenge,
                           response_data={"State": state1,
                                          "Reply_Message": ["Please provide more information."]})
        opts = {}
        r = token.is_challenge_request("some_remote_value", options=opts)
        self.assertTrue(r)
        self.assertEqual(opts.get("radius_message"), "Please provide more information.")
        self.assertEqual(opts.get("radius_result"), radiusmock.AccessChallenge)
        self.assertEqual(opts.get("radius_state"), state1[0])

        # Creating the challenge within privacyIDEA
        r, message, transaction_id, _attr = token.create_challenge(options=opts)
        self.assertTrue(r)
        self.assertEqual(message, "Please provide more information.")

        # Check if a challenge is created
        chals = get_challenges(token.token.serial)
        self.assertEqual(len(chals), 1)
        self.assertEqual(chals[0].transaction_id, transaction_id)

        # Checking, if this is the answer attempt to a challenge
        r = token.is_challenge_response("some_response", options={"transaction_id": transaction_id})
        self.assertTrue(r)

        # Now checking the response to the challenge and we issue a RADIUS request
        # But the RADIUS server answers with a second AccessChallenge
        radiusmock.setdata(timeout=False, response=radiusmock.AccessChallenge,
                           response_data={"State": state2,
                                          "Reply_Message": ["Please provide even more information."]})
        opts2 = {"transaction_id": transaction_id}
        r = token.check_challenge_response(passw="some_response", options=opts2)
        # The answer might be correct, but since the RADIUS server want to get more answers, we get a -1
        self.assertEqual(r, -1)
        # but we get a new Challenge!
        self.assertEqual(opts2.get("radius_result"), radiusmock.AccessChallenge)
        self.assertEqual(opts2.get("radius_state"), state2[0])
        self.assertEqual(opts2.get("radius_message"), "Please provide even more information.")
        transaction_id2 = opts2.get("transaction_id")

        # Finally we send the last auth request
        opts3 = {"transaction_id": transaction_id2}
        radiusmock.setdata(timeout=False, response=radiusmock.AccessAccept)
        r = token.check_challenge_response(passw="some_other_response",
                                           options=opts3)
        # The answer is correct,
        self.assertEqual(r, 1)
        # and we do not get a new challenge, it is the same as before
        self.assertEqual(opts3.get("radius_result"), radiusmock.AccessAccept)
        transaction_id3 = opts3.get("transaction_id")
        self.assertEqual(transaction_id3, transaction_id2)

    @radiusmock.activate
    def test_16_single_shot_radius(self):
        # This is a single shot authentication, no challenge response.
        # One single auth request against the radius server.
        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123", dictionary=DICT_FILE)
        self.assertTrue(r > 0)
        token = init_token({"type": "radius",
                            "radius.identifier": "myserver",
                            "radius.local_checkpin": False,
                            "radius.user": "nönäscii"})
        radiusmock.setdata(timeout=False, response=radiusmock.AccessAccept)
        r, otp_count, _rpl = token.authenticate("some_remote_value")
        self.assertTrue(r)
        self.assertTrue(otp_count > 0)

        radiusmock.setdata(timeout=False, response=radiusmock.AccessReject)
        r, otp_count, _rpl = token.authenticate("some_remote_value")
        self.assertFalse(r)
        self.assertTrue(otp_count < 0)

