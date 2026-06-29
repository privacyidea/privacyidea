"""
This test file tests the lib.challange methods.

This tests the token functions on an interface level
"""
import json

from privacyidea.lib.crypto import get_rand_digit_str
from .base import MyTestCase
from privacyidea.lib.challenge import (get_challenges, extract_answered_challenges, delete_challenges,
                                       cancel_enrollment_via_multichallenge)
from privacyidea.lib.cache import redis_feature_enabled
from privacyidea.lib.policy import (set_policy, delete_policy, SCOPE)
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.models import Challenge, db
from privacyidea.lib.token import init_token, check_serial_pass
from privacyidea.lib import _


class ChallengeTestCase(MyTestCase):
    """
    Test the lib.challenge on an interface level
    """

    def test_01_challenge(self):
        set_policy("chalresp", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")
        token = init_token({"genkey": 1, "serial": "CHAL1", "pin": "pin"})

        r = check_serial_pass(token.token.serial, "pin")
        # The OTP PIN is correct
        self.assertEqual(r[0], False)
        self.assertEqual(r[1].get("message"), _("please enter otp: "))
        transaction_id = r[1].get("transaction_id")
        chals = get_challenges()
        if redis_feature_enabled("challenges"):
            # Unfiltered list-all is not served from the cache (the aggregate
            # listing is degraded under Redis); the per-serial lookup below
            # confirms the challenge was created.
            self.assertEqual(len(chals), 0)
        else:
            self.assertEqual(len(chals), 1)
            self.assertEqual(chals[0].transaction_id, transaction_id)

        # get challenge for this serial
        chals = get_challenges(serial="CHAL1")
        self.assertEqual(len(chals), 1)
        self.assertEqual(chals[0].transaction_id, transaction_id)

        # get challenge for another seial
        chals = get_challenges(serial="CHAL2")
        self.assertEqual(len(chals), 0)

        delete_policy("chalresp")

    def test_02_extract_answered_challenges(self):
        token = init_token({"genkey": 1, "serial": "CHAL2", "pin": "pin"})
        # no challenges yet
        challenges = get_challenges(serial="CHAL2")
        self.assertEqual(challenges, [])
        self.assertEqual(extract_answered_challenges(challenges), [])
        # we trigger two challenges
        r = check_serial_pass(token.token.serial, "pin")
        self.assertEqual(r[0], False)
        transaction_id1 = r[1].get("transaction_id")
        r = check_serial_pass(token.token.serial, "pin")
        self.assertEqual(r[0], False)
        transaction_id2 = r[1].get("transaction_id")
        # two challenges, but no answered challenges
        challenges = get_challenges(serial="CHAL2")
        self.assertEqual(len(challenges), 2)
        self.assertEqual(extract_answered_challenges(challenges), [])
        # answer one challenge (backend-agnostic: set_otp_status + save work
        # against both the DB and the Redis cache, unlike a raw Challenge.query
        # update which would silently miss the Redis-backed challenge)
        answered_challenge = get_challenges(transaction_id=transaction_id1)[0]
        answered_challenge.set_otp_status(True)
        answered_challenge.save()
        # two challenges, one answered challenge
        challenges = get_challenges(serial="CHAL2")
        answered = extract_answered_challenges(challenges)
        self.assertEqual(len(challenges), 2)
        self.assertEqual(len(answered), 1)
        self.assertEqual(answered[0].transaction_id, transaction_id1)

    def test_03_delete_challenges(self):
        hotp = init_token({"type": "hotp", "genkey": 1, "pin": "pin"})
        # no challenges yet
        challenges = get_challenges(serial=hotp.get_serial())
        self.assertEqual(challenges, [])

        # trigger two challenges for hotp
        r = check_serial_pass(hotp.get_serial(), "pin")
        self.assertEqual(r[0], False)
        r = check_serial_pass(hotp.get_serial(), "pin")
        self.assertEqual(r[0], False)
        transaction_id = r[1].get("transaction_id")

        # trigger one challenges for totp
        totp = init_token({"type": "totp", "genkey": 1, "pin": "pin"})
        r = check_serial_pass(totp.get_serial(), "pin")
        self.assertEqual(r[0], False)

        # delete challenges by serial
        self.assertEqual(1, len(get_challenges(serial=totp.get_serial())))
        delete_challenges(serial=totp.get_serial())
        self.assertEqual(0, len(get_challenges(serial=totp.get_serial())))

        # delete challenges by transaction_id
        self.assertEqual(1, len(get_challenges(transaction_id=transaction_id)))
        delete_challenges(transaction_id=transaction_id)
        self.assertEqual(0, len(get_challenges(transaction_id=transaction_id)))

    def test_04_cancel_enrollment_failures(self):
        transaction_id = get_rand_digit_str()
        ret = cancel_enrollment_via_multichallenge(transaction_id=transaction_id)
        self.assertFalse(ret)

        # More than one challenge found returns False because that should not be possible in that step
        c1 = Challenge(serial="test1", transaction_id=transaction_id)
        c2 = Challenge(serial="test2", transaction_id=transaction_id)
        c1.save()
        c2.save()
        ret = cancel_enrollment_via_multichallenge(transaction_id=transaction_id)
        self.assertFalse(ret)
        c1.delete()
        c2.delete()

        # Challenge without data can not be confirmed to be for enrollment, so it won't be cancelled
        c1 = Challenge(serial="test1", transaction_id=transaction_id)
        c1.save()
        ret = cancel_enrollment_via_multichallenge(transaction_id=transaction_id)
        self.assertFalse(ret)
        c1.delete()

        # Challenge without action ENROLL_VIA_MULTICHALLENGE can not be confirmed to be for enrollment,
        # so it won't be cancelled
        c1 = Challenge(serial="test1", transaction_id=transaction_id, data={"type": "token"})
        c1.save()
        ret = cancel_enrollment_via_multichallenge(transaction_id=transaction_id)
        self.assertFalse(ret)
        c1.delete()

        # Challenge without action ENROLL_VIA_MULTICHALLENGE_OPTIONAL can not be confirmed to be cancellable
        c1 = Challenge(serial="test1", transaction_id=transaction_id, data={
            "type": "token",
            PolicyAction.ENROLL_VIA_MULTICHALLENGE: True
        })
        c1.save()
        ret = cancel_enrollment_via_multichallenge(transaction_id=transaction_id)
        self.assertFalse(ret)
        c1.delete()

        # Trying to cancel an enrollment which has optional=False will not cancel the enrollment
        c1 = Challenge(serial="test1", transaction_id=transaction_id, data={
            "type": "token",
            PolicyAction.ENROLL_VIA_MULTICHALLENGE: True,
            PolicyAction.ENROLL_VIA_MULTICHALLENGE_OPTIONAL: False
        })
        c1.save()
        ret = cancel_enrollment_via_multichallenge(transaction_id=transaction_id)
        self.assertFalse(ret)
        c1.delete()


class ChallengeDataEncryptionTestCase(MyTestCase):
    """Test that challenge data is encrypted in the database."""

    def test_01_challenge_data_encrypted(self):
        """OTP data stored in a challenge is encrypted in the database."""
        otp_value = "123456"
        c = Challenge(serial="SPASS01", transaction_id="tid_enc_001",
                      data=otp_value, validitytime=300)
        c.save()

        # Verify the raw _data attribute is the encrypted form (not plaintext)
        self.assertNotEqual(c._data, otp_value,
                            "OTP data should be stored encrypted!")
        self.assertIn(":", c._data)

        # Verify the data property transparently decrypts
        self.assertEqual(c.data, otp_value)

        # Verify get_data() also works (parses JSON)
        self.assertEqual(c.get_data(), int(otp_value))  # json.loads("123456") -> 123456

        # Clean up
        db.session.delete(c)
        db.session.commit()

    def test_02_challenge_dict_data_encrypted(self):
        """Dict data stored in a challenge is encrypted in the database."""
        data_dict = {"smartphone_confirmed": True, "display_code": "4829"}
        c = Challenge(serial="PUSH01", transaction_id="tid_enc_002",
                      data=data_dict, validitytime=300)
        c.save()

        # Verify raw _data value is encrypted
        self.assertNotEqual(c._data, json.dumps(data_dict))
        self.assertIn(":", c._data)

        # Verify data property returns the decrypted JSON string
        self.assertEqual(json.loads(c.data), data_dict)

        # Verify get_data() returns the correct dict
        retrieved = c.get_data()
        self.assertEqual(retrieved, data_dict)

        # Clean up
        db.session.delete(c)
        db.session.commit()

    def test_03_challenge_empty_data(self):
        """Empty/None data is stored as empty string, not encrypted."""
        c = Challenge(serial="HOTP01", transaction_id="tid_enc_003",
                      data=None, validitytime=120)
        c.save()

        self.assertEqual(c._data, "")
        self.assertEqual(c.get_data(), {})

        # Clean up
        db.session.delete(c)
        db.session.commit()

    def test_04_challenge_empty_string_data(self):
        """Empty string data is stored as empty string."""
        c = Challenge(serial="HOTP02", transaction_id="tid_enc_004",
                      data="", validitytime=120)
        c.save()

        self.assertEqual(c._data, "")
        self.assertEqual(c.get_data(), {})

        # Clean up
        db.session.delete(c)
        db.session.commit()

    def test_05_challenge_set_data_after_creation(self):
        """set_data() called after creation also encrypts the data."""
        c = Challenge(serial="PUSH02", transaction_id="tid_enc_005",
                      validitytime=300)
        c.save()

        # Now set data after creation (like pushtoken does)
        new_data = {"smartphone_confirmed": True, "display_code": "1234"}
        c.set_data(new_data)
        db.session.commit()

        # Verify encrypted in raw _data
        self.assertNotEqual(c._data, json.dumps(new_data))
        self.assertIn(":", c._data)

        # Verify correct decryption via property
        self.assertEqual(json.loads(c.data), new_data)

        # Verify correct decryption via get_data()
        self.assertEqual(c.get_data(), new_data)

        # Clean up
        db.session.delete(c)
        db.session.commit()

    def test_06_challenge_legacy_plaintext_data_readable(self):
        """Legacy unencrypted data (pre-migration) can still be read."""
        c = Challenge(serial="LEGACY01", transaction_id="tid_enc_006",
                      validitytime=120)
        c.save()

        # Bypass set_data() and write plaintext directly to _data (pre-migration state)
        c._data = "654321"  # raw plaintext OTP
        db.session.commit()

        # data property should fall back to returning raw value when decryption fails
        self.assertEqual(c.data, "654321")

        # get_data() parses as JSON -> returns int
        retrieved = c.get_data()
        self.assertEqual(retrieved, 654321)

        # Clean up
        db.session.delete(c)
        db.session.commit()

    def test_07_challenge_legacy_json_data_readable(self):
        """Legacy unencrypted JSON data (pre-migration) can still be read."""
        c = Challenge(serial="LEGACY02", transaction_id="tid_enc_007",
                      validitytime=120)
        c.save()

        # Bypass set_data() and write plaintext JSON directly to _data
        legacy_data = {"user_verification": "preferred"}
        c._data = json.dumps(legacy_data)
        db.session.commit()

        # data property should return the raw JSON string (decryption fails, falls back)
        self.assertEqual(c.data, json.dumps(legacy_data))

        # get_data() should parse the JSON
        retrieved = c.get_data()
        self.assertEqual(retrieved, legacy_data)

        # Clean up
        db.session.delete(c)
        db.session.commit()

    def test_08_data_property_setter_encrypts(self):
        """Assigning to c.data via the property setter encrypts the value."""
        c = Challenge(serial="SETTER01", transaction_id="tid_enc_008",
                      validitytime=300)
        c.save()

        # Assign via property setter (c.data = ...)
        c.data = "secret_otp_789"
        db.session.commit()

        # Raw _data should be encrypted (not plaintext)
        self.assertNotEqual(c._data, "secret_otp_789")
        self.assertIn(":", c._data)

        # Reading via property should decrypt
        self.assertEqual(c.data, "secret_otp_789")

        # Assign a dict via setter
        c.data = {"push_confirmed": True}
        db.session.commit()

        self.assertNotEqual(c._data, json.dumps({"push_confirmed": True}))
        self.assertIn(":", c._data)
        self.assertEqual(json.loads(c.data), {"push_confirmed": True})

        # Assign empty string via setter - stored as empty, not encrypted
        c.data = ""
        db.session.commit()
        self.assertEqual(c._data, "")

        # Assign None via setter
        c.data = None
        db.session.commit()
        self.assertEqual(c._data, "")

        # Clean up
        db.session.delete(c)
        db.session.commit()
