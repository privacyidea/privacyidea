# -*- coding: utf-8 -*-
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''     
  Description:  functional tests
                
  Dependencies: -

'''
from mock import patch
import smtplib
import re
import time

from privacyidea.tests import TestController, url


class TestEmailtokenController(TestController):

    pin = '1234'
    default_email_address = 'paul@example.com'
    patch_smtp = None
    mock_smtp_instance = None
    challenge_validity = 5
    token_serial = 'LSEM12345678'

    def setUp(self):
        TestController.setUp(self)
        parameters = {
            'EmailProvider': 'privacyidea.lib.emailprovider.SMTPEmailProvider',
            'EmailProviderConfig': '{ "SMTP_SERVER": "mail.example.com",\
                               "SMTP_USER": "secret_user",\
                               "SMTP_PASSWORD": "secret_pasword" }',
            'EmailChallengeValidityTime': self.challenge_validity,
            'EmailBlockingTimeout': 0
        }
        response = self.app.get(url(controller='system', action='setConfig'),
                                params=parameters)
        assert '"status": true' in response

        # Enroll token
        parameters = {
            'type': 'email',
            'serial': self.token_serial,
            'description': "E-mail token enrolled in functional tests",
            'email_address': self.default_email_address
        }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        assert '"value": true' in response

        parameters = {"serial": self.token_serial, "user": "root", "pin": self.pin}
        response = self.app.get(url(controller='admin', action='assign'), params=parameters)
        assert '"value": true' in response

        # Patch (replace) smtplib.SMTP class to prevent e-mails from being sent out
        self.patch_smtp = patch('smtplib.SMTP', spec=smtplib.SMTP)
        mock_smtp_class = self.patch_smtp.start()
        self.mock_smtp_instance = mock_smtp_class.return_value
        self.mock_smtp_instance.sendmail.return_value = []

    def tearDown(self):
        TestController.tearDown(self)
        self.patch_smtp.stop()

    def test_default(self):
        """
        Test the default case: enroll, assign, send challenge, get successful response
        """
        response, otp = self._trigger_challenge()
        self._assert_email_sent(response)
        response = self.app.get(url(controller='validate', action='check'),
                                params={'user': 'root', 'pass': self.pin + otp})
        response_json = response.json
        self.assertTrue(response_json['result']['status'])
        self.assertTrue(response_json['result']['value'])


    def test_multiple_challenges(self):
        """
        Test with multiple challenges

        To do this we extend the challenge validity time and set a small blocking timeout.
        By waiting 5 seconds after every request we make sure a new e-mail is sent (and challenge
        created). In the end we send a response with one of the challenges (not the last one).
        """
        parameters = {
            'EmailChallengeValidityTime': 120,
            'EmailBlockingTimeout': 3
        }
        response = self.app.get(url(controller='system', action='setConfig'),
                                params=parameters)
        assert '"status": true' in response

        # trigger 1st challenge
        response, _ = self._trigger_challenge()
        self._assert_email_sent(response)
        time.sleep(5)
        # trigger 2nd challenge
        response, _ = self._trigger_challenge()
        self._assert_email_sent(response)
        time.sleep(5)
        # trigger 3rd challenge and store resulting information
        stored_response, stored_otp = self._trigger_challenge()
        self._assert_email_sent(response)
        time.sleep(5)
        # trigger 4th challenge
        response, _ = self._trigger_challenge()
        self._assert_email_sent(response)

        # Send the response with the stored values from the 3rd challenge
        transaction_id = stored_response['detail']['transactionid']
        # since we are sending the transactionid we only need the otp (without pin)
        response = self.app.get(url(controller='validate', action='check'),
                                params={'user': 'root', 'pass': stored_otp, 'transactionid': transaction_id})
        response = response.json
        self.assertTrue(response['result']['status'])
        self.assertTrue(response['result']['value'])

    def test_timeout(self):
        """
        Test that challenges timeout after 'EmailChallengeValidityTime'
        """
        response, otp = self._trigger_challenge()
        self._assert_email_sent(response)
        time.sleep(int(self.challenge_validity * 1.2))  # we wait 120% of the challenge timeout
        response = self.app.get(url(controller='validate', action='check'),
                                params={'user': 'root', 'pass': self.pin + otp})
        response = response.json
        self.assertTrue(response['result']['status'])
        self.assertFalse(response['result']['value'], "Challenge should have timed out")

    def test_blocking(self):
        """
        Test that no new e-mails are sent out during EmailBlockingTimeout
        """
        parameters = {
            'EmailBlockingTimeout': 3
        }
        response = self.app.get(url(controller='system', action='setConfig'),
                                params=parameters)
        assert '"status": true' in response

        # Trigger 1st challenge (that should send e-mail)
        response, _ = self._trigger_challenge()
        self._assert_email_sent(response)

        # Trigger 2nd challenge (should send no e-mail)
        response, _ = self._trigger_challenge()
        self.assertEqual("e-mail with otp already submitted", response['detail']['message'])

        time.sleep(5)  # wait for blocking timeout to pass

        # Trigger 3rd challenge (that should send e-mail)
        response, otp = self._trigger_challenge()
        self._assert_email_sent(response)

        response = self.app.get(url(controller='validate', action='check'),
                                params={'user': 'root', 'pass': self.pin + otp})
        response_json = response.json
        self.assertTrue(response_json['result']['status'])
        self.assertTrue(response_json['result']['value'])

        time.sleep(5)  # wait again to prevent problems with other tests

    def test_smtplib_exceptions(self):
        """
        Verify that SMTPRecipientsRefused exception is caught and no challenge is created.

        We assume that this works for other smtplib exceptions as well, because from privacyIDEAs point
        of view they behave in the same way.
        """
        # Get existing challenges (to verify later that no new ones were added)
        existing_challenges = {}
        try:
            response_string = self.app.get(url(controller='admin', action='checkstatus'),
                                           params={'user': 'root'})
            response = response_string.json
            existing_challenges = response['result']['value']['values'][self.token_serial]['challenges']
        except KeyError:
            pass  # No challenges exist for this token

        senderrs = {self.default_email_address:  (450, '4.1.8 <test@invalid.subdomain.privacyidea.de>: ' +
                                                'Sender address rejected: Domain not found')}
        # Trigger SMTPRecipientsRefused exception when sendmail is called
        self.mock_smtp_instance.sendmail.side_effect = smtplib.SMTPRecipientsRefused(senderrs)
        response_string = self.app.get(url(controller='validate', action='check'),
                                       params={'user': 'root', 'pass': self.pin})
        response = response_string.json
        expected_error = "error sending e-mail " + str(senderrs)
        self.assertEqual(expected_error, response['detail']['message'], "Error message does not match")

        # Get new challenges
        response_string = self.app.get(url(controller='admin', action='checkstatus'),
                                       params={'user': 'root'})
        response = response_string.json
        new_challenges = response['result']['value']['values'][self.token_serial]['challenges']

        # Verify that no challenge was created (the exception should have prevented it)
        self.assertTrue(existing_challenges == new_challenges,
                        "No new challenges should have been created.")

    def _trigger_challenge(self):
        """
        Triggers a challenge by doing validate/check with only the pin

        :return: tuple of the response and the otp value
        :rtype: (dict, string)
        """
        response = self.app.get(url(controller='validate', action='check'),
                                params={'user': 'root', 'pass': self.pin})
        self.assertTrue(self.mock_smtp_instance.sendmail.call_count >= 1,
                        "smtplib.SMTP.sendmail() should have been called at least once")
        call_args = self.mock_smtp_instance.sendmail.call_args
        ordered_args = call_args[0]
        email_from = ordered_args[0]
        email_to = ordered_args[1]
        message = ordered_args[2]
        self.assertEqual("privacyidea@example.com", email_from)
        self.assertEqual(self.default_email_address, email_to)

        matches = re.search('\d{6}', message)
        self.assertTrue(matches is not None)
        otp = matches.group(0)
        self.assertEqual(6, len(otp))
        return response.json, otp

    def _assert_email_sent(self, response):
        """
        Assert that the response contains information stating that the e-mail with the challenge
        has been sent.

        :param response: The response returned by validate/check
        :response type: dict
        """
        self.assertEqual("e-mail sent successfully", response['detail']['message'])
        self.assertTrue(response['result']['status'])
        self.assertFalse(response['result']['value'])
