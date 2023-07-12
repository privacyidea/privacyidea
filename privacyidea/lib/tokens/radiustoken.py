# -*- coding: utf-8 -*-
#
#  2019-08-15 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Allow RADIUS challenge / response
#             Credits to @droobah, who provided the first pull request
#             https://github.com/privacyidea/privacyidea/pull/1389
#  2018-01-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add tokenkind
#  2016-02-22 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add the RADIUS identifier, which points to the system wide list
#             of RADIUS servers.
#  2015-10-09 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add the RADIUS-System-Config, so that not each
#             RADIUS-token needs his own secret. -> change the
#             secret globally
#  2015-01-29 Adapt for migration to flask
#             Cornelius Kölbel <cornelius@privacyidea.org>
#
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
__doc__ = """This module defines the RadiusTokenClass. The RADIUS token
forwards the authentication request to another RADIUS server.

The code is tested in tests/test_lib_tokens_radius
"""

import logging

import traceback
import binascii
from privacyidea.lib.utils import is_true, to_bytes, hexlify_and_unicode, to_unicode
from privacyidea.lib.tokens.remotetoken import RemoteTokenClass
from privacyidea.lib.tokenclass import TokenClass, TOKENKIND, AUTHENTICATIONMODE
from privacyidea.api.lib.utils import getParam, ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.config import get_from_config
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.radiusserver import get_radius
from privacyidea.models import Challenge
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.policydecorators import challenge_response_allowed

import pyrad.packet
from pyrad.client import Client, Timeout
from pyrad.dictionary import Dictionary
from pyrad.packet import AccessChallenge, AccessAccept, AccessReject
from privacyidea.lib import _
from privacyidea.lib.policy import SCOPE, ACTION, GROUP

optional = True
required = False

log = logging.getLogger(__name__)


###############################################
class RadiusTokenClass(RemoteTokenClass):
    mode = [AUTHENTICATIONMODE.AUTHENTICATE, AUTHENTICATIONMODE.CHALLENGE]

    def __init__(self, db_token):
        RemoteTokenClass.__init__(self, db_token)
        self.set_type("radius")

    @staticmethod
    def get_class_type():
        return "radius"

    @staticmethod
    def get_class_prefix():
        return "PIRA"

    @staticmethod
    @log_with(log)
    def get_class_info(key=None, ret='all'):
        """
        returns a subtree of the token definition

        :param key: subsection identifier
        :type key: string
        :param ret: default return value, if nothing is found
        :type ret: user defined
        :return: subsection if key exists or user defined
        :rtype: dict or string
        """
        res = {'type': 'radius',
               'title': 'RADIUS Token',
               'description': _('RADIUS: Forward authentication request to a '
                                'RADIUS server.'),
               'user': ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {
                   SCOPE.ENROLL: {
                       ACTION.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of RADIUS tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXACTIVETOKENUSER: {
                           'type': 'int',
                           'desc': _(
                               "The user may only have this maximum number of active RADIUS tokens assigned."),
                           'group': GROUP.TOKEN
                       }
                   }
               },
               }

        if key:
            ret = res.get(key, {})
        else:
            if ret == 'all':
                ret = res

        return ret

    @log_with(log)
    def update(self, param):
        # New value
        radius_identifier = getParam(param, "radius.identifier")
        self.add_tokeninfo("radius.identifier", radius_identifier)

        # old values
        if not radius_identifier:
            radiusServer = getParam(param, "radius.server", optional=required)
            self.add_tokeninfo("radius.server", radiusServer)
            radius_secret = getParam(param, "radius.secret", optional=required)
            self.token.set_otpkey(hexlify_and_unicode(radius_secret))
            system_settings = getParam(param, "radius.system_settings",
                                       default=False)
            self.add_tokeninfo("radius.system_settings", system_settings)

            if not (radiusServer or radius_secret) and not system_settings:
                raise ParameterError("Missing parameter: radius.identifier", id=905)

        # if another OTP length would be specified in /admin/init this would
        # be overwritten by the parent class, which is ok.
        self.set_otplen(6)
        TokenClass.update(self, param)
        val = getParam(param, "radius.local_checkpin", optional) or 0
        self.add_tokeninfo("radius.local_checkpin", val)
        val = getParam(param, "radius.user", required)
        self.add_tokeninfo("radius.user", val)
        self.add_tokeninfo("tokenkind", TOKENKIND.VIRTUAL)

    @log_with(log)
    @challenge_response_allowed
    def is_challenge_request(self, passw, user=None, options=None):
        """
        This method checks, if this is a request, that triggers a challenge.
        It depends on the way, the pin is checked - either locally or remotely.
        In addition, the RADIUS token has to be configured to allow challenge response.

        communication with RADIUS server: yes
        modification of options: The communication with the RADIUS server can
            change the options, radius_state, radius_result, radius_message

        :param passw: password, which might be pin or pin+otp
        :type passw: string
        :param user: The user from the authentication request
        :type user: User object
        :param options: dictionary of additional request parameters
        :type options: dict

        :return: true or false
        """
        if options is None:
            options = {}

        # should we check the pin locally?
        if self.check_pin_local:
            # With a local PIN the challenge response is always a privacyIDEA challenge response!
            res = self.check_pin(passw, user=user, options=options)
            return res

        else:
            state = options.get('radius_state')
            # The pin is checked remotely
            res = options.get('radius_result')
            if res is None:
                res = self._check_radius(passw, options=options, radius_state=state)

            return res == AccessChallenge

    @log_with(log)
    def create_challenge(self, transactionid=None, options=None):
        """
        create a challenge, which is submitted to the user

        This method is called after ``is_challenge_request`` has verified,
        that a challenge needs to be created.

        communication with RADIUS server: no
        modification of options: no

        :param transactionid: the id of this challenge
        :param options: the request context parameters / data
        :return: tuple of (bool, message and data)
                 bool, if submit was successful
                 message is submitted to the user
                 data is preserved in the challenge
                 reply_dict - additional attributes, which are displayed in the
                    output
        """
        if options is None:
            options = {}
        message = options.get('radius_message') or "Enter your RADIUS tokencode:"
        state = hexlify_and_unicode(options.get('radius_state') or b'')
        reply_dict = {'attributes': {'state': transactionid}}
        validity = int(get_from_config('DefaultChallengeValidityTime', 120))

        db_challenge = Challenge(self.token.serial,
                                 transaction_id=transactionid,
                                 data=state,
                                 challenge=message,
                                 validitytime=validity)
        db_challenge.save()
        self.challenge_janitor()
        return True, message, db_challenge.transaction_id, reply_dict

    @log_with(log)
    def is_challenge_response(self, passw, user=None, options=None):
        """
        This method checks, if this is a request, that is the response to
        a previously sent challenge. But we do not query the RADIUS server.

        This is the first method in the loop ``check_token_list``.

        communication with RADIUS server: no
        modification of options: The "radius_result" key is set to None

        :param passw: password, which might be pin or pin+otp
        :type passw: string
        :param user: the requesting user
        :type user: User object
        :param options: dictionary of additional request parameters
        :type options: dict
        :return: true or false
        :rtype: bool
        """
        if options is None:
            options = {}

        challenge_response = False

        # clear the radius_result since this is the first function called in the chain
        # this value will be utilized to ensure we do not _check_radius more than once in the loop
        options.update({'radius_result': None})

        # fetch the transaction_id
        transaction_id = options.get('transaction_id')
        if transaction_id is None:
            transaction_id = options.get('state')

        if transaction_id:
            # get the challenges for this transaction ID
            challengeobject_list = get_challenges(serial=self.token.serial,
                                                  transaction_id=transaction_id)

            for challengeobject in challengeobject_list:
                if challengeobject.is_valid():
                    challenge_response = True

        return challenge_response

    @log_with(log)
    @check_token_locked
    def check_challenge_response(self, user=None, passw=None, options=None):
        """
        This method verifies if there is a matching question for the given
        passw and also verifies if the answer is correct.

        It then returns the the otp_counter = 1

        :param user: the requesting user
        :type user: User object
        :param passw: the password - in fact it is the answer to the question
        :type passw: string
        :param options: additional arguments from the request, which could
                        be token specific. Usually "transaction_id"
        :type options: dict
        :return: return otp_counter. If -1, challenge does not match
        :rtype: int
        """
        if options is None:
            options = {}
        otp_counter = -1

        # fetch the transaction_id
        transaction_id = options.get('transaction_id') or options.get('state')

        # get the challenges for this transaction ID
        if transaction_id is not None:
            challengeobject_list = get_challenges(serial=self.token.serial,
                                                  transaction_id=transaction_id)

            for challengeobject in challengeobject_list:
                if challengeobject.is_valid():
                    state = binascii.unhexlify(challengeobject.data)

                    # challenge is still valid
                    radius_response = self._check_radius(passw, options=options, radius_state=state)
                    if radius_response == AccessAccept:
                        # We found the matching challenge,
                        # and the RADIUS server returned AccessAccept
                        challengeobject.delete()
                        otp_counter = 1
                        break
                    elif radius_response == AccessChallenge:
                        # The response was valid but triggered a new challenge
                        # Note: The second challenge currently does not work correctly
                        # see https://github.com/privacyidea/privacyidea/issues/1792
                        challengeobject.delete()
                        _, _, transaction_id, _ = self.create_challenge(options=options)
                        options["transaction_id"] = transaction_id
                        otp_counter = -1
                        break
                    else:
                        otp_counter = -1
                        # increase the received_count
                        challengeobject.set_otp_status()

        self.challenge_janitor()
        return otp_counter

    @property
    def check_pin_local(self):
        """
        lookup if pin should be checked locally or on radius host

        :return: bool
        """
        local_check = is_true(self.get_tokeninfo("radius.local_checkpin"))
        log.debug("local checking pin? {0!r}".format(local_check))

        return local_check

    @log_with(log)
    def split_pin_pass(self, passw, user=None, options=None):
        """
        Split the PIN and the OTP value.
        Only if it is locally checked and not remotely.
        """
        res = True
        pin = ""
        otpval = passw
        if self.check_pin_local:
            (res, pin, otpval) = TokenClass.split_pin_pass(self, passw)

        return res, pin, otpval

    @log_with(log)
    @check_token_locked
    def authenticate(self, passw, user=None, options=None):
        """
        do the authentication on base of password / otp and user and
        options, the request parameters.

        This is only called after it is verified, that the upper level is no challenge-request
        or challenge-response

        The "options" are read-only in this method. They are not modified here. authenticate
        is the last method in the loop ``check_token_list``.

        communication with RADIUS server: yes, if is no previous "radius_result"
            If there is a "radius" result in the options, we do not query the radius server
        modification of options: options can be modified if we query the radius server.
            However, this is not important since authenticate is the last call.

        :param passw: the password / otp
        :param user: the requesting user
        :param options: the additional request parameters

        :return: tuple of (success, otp_count - 0 or -1, reply)

        """
        options = options or {}
        res = False
        otp_counter = -1
        reply = None
        otpval = passw

        # should we check the pin locally?
        if self.check_pin_local:
            (_res, pin, otpval) = self.split_pin_pass(passw, user,
                                                      options=options)

            if not self.check_pin(pin, user=user, options=options):
                return False, -1, {'message': "Wrong PIN"}

        # attempt to retrieve saved state/result
        state = options.get('radius_state')
        result = options.get('radius_result')
        if result is None:
            radius_response = self._check_radius(otpval, options=options, radius_state=state)
        else:
            radius_response = result

        if radius_response == AccessAccept:
            res = True
            otp_counter = 1

        return res, otp_counter, reply

    @log_with(log)
    @check_token_locked
    def check_otp(self, otpval, counter=None, window=None, options=None):
        """
        Originally check_otp returns an OTP counter. I.e. in a failed attempt
        we return -1. In case of success we return 1
        :param otpval:
        :param counter:
        :param window:
        :param options:
        :return:
        """
        res = self._check_radius(otpval, options=options)
        if res == AccessAccept:
            return 1
        else:
            return -1

    @log_with(log)
    @check_token_locked
    def _check_radius(self, otpval, options=None, radius_state=None):
        """
        run the RADIUS request against the RADIUS server

        :param otpval: the OTP value
        :param options: additional token specific options
        :type options: dict
        :return: counter of the matching OTP value.
        :rtype: AccessAccept, AccessReject, AccessChallenge
        """
        result = AccessReject
        radius_message = None
        if options is None:
            options = {}

        radius_dictionary = None
        radius_identifier = self.get_tokeninfo("radius.identifier")
        radius_user = self.get_tokeninfo("radius.user")
        system_radius_settings = self.get_tokeninfo("radius.system_settings")
        radius_timeout = 5
        radius_retries = 3
        if radius_identifier:
            # New configuration
            radius_server_object = get_radius(radius_identifier)
            radius_server = radius_server_object.config.server
            radius_port = radius_server_object.config.port
            radius_server = "{0!s}:{1!s}".format(radius_server, radius_port)
            radius_secret = radius_server_object.get_secret()
            radius_dictionary = radius_server_object.config.dictionary
            radius_timeout = int(radius_server_object.config.timeout or 10)
            radius_retries = int(radius_server_object.config.retries or 1)
        elif system_radius_settings:
            # system configuration
            radius_server = get_from_config("radius.server")
            radius_secret = get_from_config("radius.secret")
        else:
            # individual token settings
            radius_server = self.get_tokeninfo("radius.server")
            # Read the secret
            secret = self.token.get_otpkey()
            radius_secret = binascii.unhexlify(secret.getKey())

        # here we also need to check for radius.user
        log.debug("checking OTP len:{0!s} on radius server: "
                  "{1!s}, user: {2!r}".format(len(otpval), radius_server,
                                               radius_user))

        try:
            # pyrad does not allow to set timeout and retries.
            # it defaults to retries=3, timeout=5

            # TODO: At the moment we support only one radius server.
            # No round robin.
            server = radius_server.split(':')
            r_server = server[0]
            r_authport = 1812
            if len(server) >= 2:
                r_authport = int(server[1])
            nas_identifier = get_from_config("radius.nas_identifier",
                                             "privacyIDEA")
            if not radius_dictionary:
                radius_dictionary = get_from_config("radius.dictfile",
                                                    "/etc/privacyidea/dictionary")
            log.debug("NAS Identifier: %r, "
                      "Dictionary: %r" % (nas_identifier, radius_dictionary))
            log.debug("constructing client object "
                      "with server: %r, port: %r, secret: %r" %
                      (r_server, r_authport, to_unicode(radius_secret)))

            srv = Client(server=r_server,
                         authport=r_authport,
                         secret=to_bytes(radius_secret),
                         dict=Dictionary(radius_dictionary))

            # Set retries and timeout of the client
            srv.timeout = radius_timeout
            srv.retries = radius_retries

            req = srv.CreateAuthPacket(code=pyrad.packet.AccessRequest,
                                       User_Name=radius_user.encode('utf-8'),
                                       NAS_Identifier=nas_identifier.encode('ascii'))

            req["User-Password"] = req.PwCrypt(otpval)

            if radius_state:
                req["State"] = radius_state
                log.info("Sending saved challenge to radius server: {0!r} ".format(radius_state))

            try:
                response = srv.SendPacket(req)
            except Timeout:
                log.warning("The remote RADIUS server {0!s} timeout out for user {1!s}.".format(
                    r_server, radius_user))
                return AccessReject

            # handle the RADIUS challenge
            if response.code == pyrad.packet.AccessChallenge:
                # now we map this to a privacyidea challenge
                if "State" in response:
                    radius_state = response["State"][0]
                if "Reply-Message" in response:
                    radius_message = response["Reply-Message"][0]

                result = AccessChallenge
            elif response.code == pyrad.packet.AccessAccept:
                radius_state = '<SUCCESS>'
                radius_message = 'RADIUS authentication succeeded'
                log.info("RADIUS server {0!s} granted "
                         "access to user {1!s}.".format(r_server, radius_user))
                result = AccessAccept
            else:
                radius_state = '<REJECTED>'
                radius_message = 'RADIUS authentication failed'
                log.debug('radius response code {0!s}'.format(response.code))
                log.info("Radiusserver {0!s} "
                         "rejected access to user {1!s}.".format(r_server, radius_user))
                result = AccessReject

        except Exception as ex:  # pragma: no cover
            log.error("Error contacting radius Server: {0!r}".format((ex)))
            log.info("{0!s}".format(traceback.format_exc()))

        options.update({'radius_result': result})
        options.update({'radius_state': radius_state})
        options.update({'radius_message': radius_message})
        return result
