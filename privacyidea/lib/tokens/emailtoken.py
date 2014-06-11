# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  LSE
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
  Description:  This file contains the e-mail token implementation:
              - EmailTokenClass   (HOTP)

  Dependencies: -

'''

import logging
import traceback
import sys
import datetime

from privacyidea.lib.tokens.hmactoken import HmacTokenClass
from privacyidea.lib.config import getFromConfig
from privacyidea.lib.util import getParam
from privacyidea.lib.HMAC import HmacOtp

from privacyidea.lib.validate import split_pin_otp
from privacyidea.lib.validate import check_pin
from privacyidea.lib.validate import check_otp
from privacyidea.lib.log import log_with
from json import loads

optional = True
required = False

LOG = logging.getLogger(__name__)


class EmailTokenClass(HmacTokenClass):
    """
    E-mail token (similar to SMS token)
    """

    EMAIL_ADDRESS_KEY = "email_address"
    DEFAULT_EMAIL_PROVIDER = "privacyidea.lib.emailprovider.SMTPEmailProvider"
    DEFAULT_EMAIL_BLOCKING_TIMEOUT = 120

    def __init__(self, aToken):
        HmacTokenClass.__init__(self, aToken)
        self.setType(u"email")
        self.hKeyRequired = False

        # we support various hashlib methods, but only on create
        # which is effectively set in the update
        self.hashlibStr = getFromConfig("hotp.hashlib", "sha1")
        self.mode = ['challenge']

    @property
    def _email_address(self):
        return self.getFromTokenInfo(self.EMAIL_ADDRESS_KEY)

    @_email_address.setter
    def _email_address(self, value):
        self.addToTokenInfo(self.EMAIL_ADDRESS_KEY, value)

    @classmethod
    def getClassType(cls):
        return "email"

    @classmethod
    def getClassPrefix(cls):
        return "LSEM"

    @classmethod
    @log_with(LOG)
    def getClassInfo(cls, key=None, ret='all'):
        """
        getClassInfo - returns a subtree of the token definition

        :param key: subsection identifier
        :type key: string

        :param ret: default return value, if nothing is found
        :type ret: user defined

        :return: subsection if key exists or user defined
        :rtype: s.o.

        """
        res = {
            'type':         'email',
            'title':        'E-mail Token',
            'description':  'An e-mail token.',
            'init': {
                'page': {
                    'html': 'emailtoken.mako',
                    'scope': 'enroll',
                },
                'title': {
                    'html': 'emailtoken.mako',
                    'scope': 'enroll.title',
                },
            },
            'config': {
                'title': {
                    'html': 'emailtoken.mako',
                    'scope': 'config.title',
                },
                'page': {
                    'html': 'emailtoken.mako',
                    'scope': 'config',
                },
            },
            'selfservice': {},
            'policy': {},
        }

        # do we need to define the lost token policies here... [comment copied from sms token]
        if key is not None and key in res:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res

        return ret

    @log_with(LOG)
    def update(self, param, reset_failcount=True):
        """
        update - process initialization parameters

        :param param: dict of initialization parameters
        :type param: dict

        :return: nothing

        """
        # specific - e-mail
        self._email_address = getParam(param, self.EMAIL_ADDRESS_KEY, optional=False)

        ## in case of the e-mail token, only the server must know the otpkey
        ## thus if none is provided, we let create one (in the TokenClass)
        if not 'genkey' in param and not 'otpkey' in param:
            param['genkey'] = 1

        HmacTokenClass.update(self, param, reset_failcount)
        return

    @log_with(LOG)
    def _getNextOtp(self):
        """
        access the nex valid otp

        :return: otpval
        :rtype: string
        """
        try:
            otplen = int(self.token.privacyIDEAOtpLen)
        except ValueError as ex:
            LOG.error("ValueError %r" % ex)
            raise Exception(ex)

        secret_obj = self.token.getHOtpKey()
        counter = self.token.getOtpCounter()

        #log.debug("serial: %s",serialNum)
        hmac2otp = HmacOtp(secret_obj, counter, otplen)
        nextotp = hmac2otp.generate(counter + 1)
        return nextotp

    @log_with(LOG)
    def initChallenge(self, transactionid, challenges=None, options=None):
        """
        initialize the challenge -
        This method checks if the creation of a new challenge (identified by transactionid)
        should proceed or if an old challenge should be used instead.

        :param transactionid: the id of the new challenge
        :param options: the request parameters

        :return: tuple of
                success - bool
                transactionid_to_use - the best transaction id for this request context
                message - which is shown to the user
                attributes - further info (dict) shown to the user
        """
        success = True
        transactionid_to_use = transactionid
        message = 'challenge init ok'
        attributes = {}

        now = datetime.datetime.now()
        blocking_time = int(getFromConfig('EmailBlockingTimeout', self.DEFAULT_EMAIL_BLOCKING_TIMEOUT))

        for challenge in challenges:
            challenge_timestamp = challenge.get('timestamp')
            assert(challenge_timestamp <= now)
            block_timeout = challenge_timestamp + datetime.timedelta(seconds=blocking_time)
            # check if there is a challenge that is blocking the creation of new challenges
            if now <= block_timeout:
                transactionid_to_use = challenge.getTransactionId()
                message = 'e-mail with otp already submitted'
                success = False
                attributes = {'info': 'challenge already submitted',
                              'state': transactionid_to_use}
                break

        return success, transactionid_to_use, message, attributes

    @log_with(LOG)
    def createChallenge(self, transactionid, options=None):
        """
        create a challenge, which is submitted to the user

        :param transactionid: the id of this challenge
        :param options: the request context parameters / data
        :return: tuple of (bool, message, data and attributes)
                 bool, if submit was successful
                 message is status-info submitted to the user
                 data is preserved in the challenge
                 attributes - additional attributes, which are displayed in the
                    output
        :rtype: bool, string, dict, dict
        """
        attributes = {}
        data = {'counter_value': "%s" % self.getOtpCount()}
        success, status_message = self._sendEmail()
        if success:
            attributes = {'state': transactionid}
        return success, status_message, data, attributes

    def _getEmailMessage(self):
        """
        Could be used to implement some more complex logic similar to the
        SMS token where the SMS text is read from a policy.

        :return: The message that is sent to the user. It should contain
            at least the placeholder <otp>
        :rtype: string
        """
        return "<otp>"

    @log_with(LOG)
    def _sendEmail(self):
        """
        Prepares the e-mail by gathering all relevant information and then sends
        it out.

        :return: A tuple of success and status_message
        :rtype: bool, string
        """
        otp = self._getNextOtp()
        email_address = self._email_address
        if not email_address:
            raise Exception("No e-mail address was defined for this token.")
        message = self._getEmailMessage()
        message = message.replace("<otp>", otp)
        message = message.replace("<serial>", self.getSerial())
        try:
            email_provider_class = self._getEmailProviderClass()
            email_provider = email_provider_class()
        except Exception as exc:
            LOG.error("Failed to load EmailProvider: %r" % exc)
            LOG.error(traceback.format_exc())
            raise exc

        ## now we need the config from the env
        LOG.debug("loading e-mail configuration for class %s" % email_provider)
        config = self._getEmailProviderConfig()
        LOG.debug("config: %r" % config)
        email_provider.loadConfig(config)
        status, status_message = email_provider.submitMessage(email_address, message)
        return status, status_message

    @log_with(LOG)
    def _getEmailProviderConfig(self):
        """
        get the defined e-mail provider config definition

        :return: dict of the e-mail provider definition
        :rtype: dict
        """
        config = {}
        tConfig = getFromConfig("encprivacyidea.EmailProviderConfig", None)
        if tConfig is None:
            tConfig = getFromConfig("EmailProviderConfig", "{}")

        if tConfig is not None:
            config = loads(tConfig)
        return config

    @log_with(LOG)
    def _getEmailProviderClass(self):
        """
        getEmailProviderClass():

        helper method to load the EmailProvider class from config

        checks, if the submitMessage method exists
        if not an error is thrown
        """
        email_provider = getFromConfig("EmailProvider", self.DEFAULT_EMAIL_PROVIDER)
        if not email_provider:
            raise Exception("No EmailProvider defined.")
        (email_provider_package, email_provider_class_name) = email_provider.rsplit(".", 1)

        if not email_provider_package or not email_provider_class_name:
            raise Exception("Could not load e-mail provider class. Maybe EmailProvider is "
                            "not set in the config file.")

        mod = __import__(email_provider_package, globals(), locals(), [email_provider_class_name])
        # TODO Kay sagt hier soll das Modul global geladen werden (mit einem bisher nicht existierenden Hook)
        provider_class = getattr(mod, email_provider_class_name)
        if not hasattr(provider_class, "submitMessage"):
            raise NameError("EmailProvider AttributeError: " + email_provider_package + "." +
                            email_provider_class_name + " instance of EmailProvider has no method 'submitMessage'")
        return provider_class

    @log_with(LOG)
    def is_challenge_response(self, passw, user, options=None, challenges=None):
        """
        Checks if the request is a challenge response.

        With the e-mail token every request has to be either a challenge
        request or a challenge response.

        Normally the client is unable to generate OTP values for this token
        himself (because the seed is generated on the server and not published)
        and has to wait to get it by e-mail. Therefore he either makes a
        challenge-request (triggering the e-mail) or he makes a challenge-
        response (sending the OTP value he received).

        :return: Is this a challenge response?
        :rtype: bool
        """
        challenge_response = False
        if options and ("state" in options or "transactionid" in options):
            challenge_response = True
        elif not self.is_challenge_request(passw, user, options):
            # If it is not a request then it is a response
            challenge_response = True

        return challenge_response

    @log_with(LOG)
    def checkResponse4Challenge(self, user, passw, options=None, challenges=None):
        """
        verify the response of a previous challenge

        There are two possible cases:

        1) The 'transaction_id' (also know as 'state', which has the same
           value) is available in options
        2) No 'transaction_id'

        In the first case we can safely assume that the passw only contains the OTP (no pin).
        In the second case passw will contain both and we split to get the OTP.

        :param user:     the requesting user
        :param passw:    the to be checked pass (pin+otp)
        :param options:  options an additional argument, which could be token
                          specific
        :param challenges: the list of challenges, where each challenge is
                            described as dict
        :return: tuple of (otpcounter and the list of matching challenges)

        """
        transaction_id = None
        otp_counter = -1
        matching_challenges = []

        if challenges is None or len(challenges) == 0:
            # There are no challenges for this token
            return -1, []

        if options and ('transactionid' in options or 'state' in options):
            ## fetch the transactionid
            transaction_id = options.get('transactionid', None)
            if transaction_id is None:
                transaction_id = options.get('state', None)

        if transaction_id:
            otp = passw
            # if the transaction_id is set we can assume that we have only received a single
            # challenge with that transaction_id thanks to
            # privacyidea.lib.validate.ValidateToken.get_challenges()
            assert(len(challenges) == 1)
            assert(transaction_id == challenges[0].getTransactionId())
        else:
            # If no transaction_id is set the request came through the WebUI and
            # we have to check all challenges
            split_status, _, otp = split_pin_otp(self, passw, user, options)
            if split_status < 0:
                raise Exception("Could not split passw")

        window = self.getOtpCountWindow()

        for challenge in challenges:
            challenge_data = challenge.getData()
            stored_counter = challenge_data.get("counter_value")
            temp_otp_counter = self.checkOtp(otp, int(stored_counter), window, options)
            if temp_otp_counter > 0:
                otp_counter = temp_otp_counter
                matching_challenges = [challenge]
                break

        # The matching_challenges list will either contain a single challenge or will be empty.
        # Returning multiple challenges is not useful in this case because all older challenges are
        # cleaned up anyway.
        return otp_counter, matching_challenges

    @log_with(LOG)
    def authenticate(self, passw, user, options=None):
        """
        The e-mail token only supports challenge response mode therefore when a 'normal
        authenticate' request arrives we return false.

        :return: pin_match, otp_counter, reply
        :rtype: bool, int, string
        """
        pin_match = False
        otp_counter = -1
        reply = None
        return pin_match, otp_counter, reply
