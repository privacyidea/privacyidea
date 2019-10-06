"""
This test file tests the lib.challange methods.

This tests the token functions on an interface level
"""
from .base import MyTestCase
from privacyidea.lib.error import (TokenAdminError, ParameterError)
from privacyidea.lib.challenge import get_challenges, extract_answered_challenges
from privacyidea.lib.policy import (set_policy, delete_policy, SCOPE,
                                    ACTION)
from privacyidea.models import Challenge, db
from privacyidea.lib.token import init_token
from privacyidea.lib import _


class ChallengeTestCase(MyTestCase):
    """
    Test the lib.challenge on an interface level
    """

    def test_01_challenge(self):

        set_policy("chalresp", scope=SCOPE.AUTHZ,
                   action="{0!s}=hotp".format(ACTION.CHALLENGERESPONSE))
        token = init_token({"genkey": 1, "serial": "CHAL1", "pin": "pin"})
        from privacyidea.lib.token import check_serial_pass
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
        from privacyidea.lib.token import check_serial_pass
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
