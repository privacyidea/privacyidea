"""
This test file tests the lib.challange methods.

This tests the token functions on an interface level
"""
from privacyidea.lib.crypto import get_rand_digit_str
from .base import MyTestCase
from privacyidea.lib.challenge import (get_challenges, extract_answered_challenges, delete_challenges,
                                       cancel_enrollment_via_multichallenge)
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
        # answer one challenge
        Challenge.query.filter_by(transaction_id=transaction_id1).update({"otp_valid": True})
        db.session.commit()
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

