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
library to do validation
'''


import logging

from sqlalchemy import desc

from privacyidea.lib.user import getUserId

import privacyidea.lib.token
from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.config import get_privacyIDEA_config
from pylons import request, config, tmpl_context as c

from privacyidea.model import Challenge
from privacyidea.model.meta import Session
from privacyidea.lib.config  import getFromConfig
from privacyidea.lib.resolver import getResolverObject
import traceback
from privacyidea.lib.log import log_with

LOG = logging.getLogger(__name__)


@log_with(LOG)
def transform_challenges(challenges):
    '''
    small helper to transfor a set of DB Challenges to a list
    of challenge data as dicts

    :param challenges: list of database challenges

    :return: a list with challenge data dicts
    '''
    channel_list = []
    for challenge in challenges:
        channel_list.append(challenge.get())
    #return channel_list
    return challenges

@log_with(LOG)
def get_challenges(serial=None, transid=None):
    '''
    get_challenges - give all challenges for a given token

    :param serial:   serial of the token
    :param transid:  transaction id, if None, all will be retrieved
    :return:         return a list of challenge dict
    '''
    challenges = []
    if transid is None and serial is None:
        return challenges

    if transid is None:
        db_challenges = Session.query(Challenge)\
            .filter(Challenge.tokenserial == u'' + serial)\
            .order_by(desc(Challenge.id))\
            .all()
    else:
        db_challenges = Session.query(Challenge)\
            .filter(Challenge.transid == transid)\
            .all()

    challenges.extend(db_challenges)
    return challenges

@log_with(LOG)
def create_challenge(token, options=None):
    """
    dedicated method to create a challenge to support the implementation
    of challenge policies in future

    :param options: optional parameters for token specific tokens
                    eg. request a signed challenge
    :return: a tuple of  (boolean, and a dict, which contains the
             {'challenge' : challenge} description)
    """

    ## response dict, describing the challenge reply
    challenge = {}
    ## the allocated db challenge object
    challenge_obj = None
    retry_counter = 0
    reason = None

    id_length = int(getFromConfig('TransactionIdLength', 12))

    while True:
        try:

            transactionid = Challenge.createTransactionId(length=id_length)
            num_challenges = Session.query(Challenge).\
                    filter(Challenge.transid == transactionid).count()

            if num_challenges == 0:
                challenge_obj = Challenge(transid=transactionid,
                                                tokenserial=token.getSerial())
            if challenge_obj is not None:
                break

        except Exception as exce:
            LOG.info("Failed to create Challenge: %r", exce)
            reason = exce

        ## prevent an unlimited loop
        retry_counter = retry_counter + 1
        if retry_counter > 100:
            LOG.info("Failed to create Challenge for %d times: %r -quiting!",
                     retry_counter, reason)
            raise Exception('Failed to create challenge %r' % reason)

    challenges = get_challenges(serial=token.getSerial())

    ## carefully create a new challenge
    try:

        ## we got a challenge object allocated and initialize the challenge
        (res, open_transactionid, message, attributes) = \
                             token.initChallenge(transactionid,
                                                 challenges=challenges,
                                                 options=options)

        if res == False:
            ## if a different transid is returned, this indicates, that there
            ## is already an outstanding challenge we can refere to
            if open_transactionid != transactionid:
                transactionid = open_transactionid

        else:
            ## in case the init was successfull, we preserve no the challenge data
            ## to support the implementation of a blocking based on the previous
            ## stored data
            challenge_obj.setChallenge(message)
            challenge_obj.save()

            (res, message, data, attributes) = \
                        token.createChallenge(transactionid, options=options)

            if res == True:
                ## persist the final challenge data + message
                challenge_obj.setChallenge(message)
                challenge_obj.setData(data)
                challenge_obj.save()
            else:
                transactionid = ''

    except Exception as exce:
        reason = exce
        res = False


    ## if something goes wrong with the challenge, remove it
    if res == False and challenge_obj is not None:
        try:
            LOG.debug("deleting session")
            Session.delete(challenge_obj)
            Session.commit()
        except Exception as exx:
            LOG.debug("deleting session failed: %r" % exx)
            try:
                Session.expunge(challenge_obj)
                Session.commit()
            except Exception as exx:
                LOG.debug("expunge session failed: %r" % exx)

    ## in case that create challenge fails, we must raise this reason
    if reason is not None:
        message = "%r" % reason
        LOG.error("Failed to create or init challenge %r " % reason)
        raise reason

    ## prepare the response for the user
    if transactionid is not None:
        challenge['transactionid'] = transactionid

    if message is not None:
        challenge['message'] = message

    if attributes is not None and type(attributes) == dict:
        challenge.update(attributes)

    return (res, challenge)

@log_with(LOG)
def check_pin(token, passw, user=None, options=None):
    '''
    check the provided pin w.r.t. the policy definition

    :param passw: the to be checked pass
    :param user: if otppin==1, this is the user, which resolver should
                 be checked
    :param options: the optional request parameters

    :return: boolean, if pin matched True
    '''
    res = False
    Policy = PolicyClass(request, config, c,
                         get_privacyIDEA_config())
    pin_policies = Policy.get_pin_policies(user)

    if 1 in pin_policies:
        # We check the Users Password as PIN
        LOG.debug("pin policy=1: checking the users"
                                                    " password as pin")
        if (user is None):
            raise Exception("fail for pin policy == 1 with user = None")

        (uid, _resolver, resolver_class) = getUserId(user)

        r_obj = getResolverObject(resolver_class)
        if  r_obj.checkPass(uid, passw):
            LOG.debug("Successfully authenticated user %r." % uid)
            res = True
        else:
            LOG.info("user %r failed to authenticate." % uid)

    elif 2 in pin_policies:
        # NO PIN should be entered atall
        LOG.debug("pin policy=2: checking no pin")
        if len(passw) == 0:
            res = True
    else:
        # old stuff: We check The fixed OTP PIN
        LOG.debug("pin policy=0: checkin the PIN")
        res = token.checkPin(passw, options=options)

    return res

@log_with(LOG)
def check_otp(token, otpval, options=None):
    '''
    check the otp value

    :param otpval: the to be checked otp value
    :param options: the additional request parameters

    :return: result of the otp check, which is
            the matching otpcounter or -1 if not valid
    '''
    res = -1

    counter = token.getOtpCount()
    window = token.getOtpCountWindow()

    res = token.checkOtp(otpval, counter, window, options=options)
    return res

@log_with(LOG)
def split_pin_otp(token, passw, user=None, options=None):
    '''
    split the pin and the otp fron the given password

    :param passw: the to be splitted password
    :param options: currently not used, but might be forwarded to the
                    token.splitPinPass
    :return: tuple of (split status, pin and otpval)
    '''
    Policy = PolicyClass(request, config, c,
                         get_privacyIDEA_config())
    pin_policies = Policy.get_pin_policies(user)

    policy = 0

    if 1 in pin_policies:
        LOG.debug("pin policy=1: checking the users password as pin")
        # split the passw into password and otp value
        (res, pin, otp) = token.splitPinPass(passw)
        policy = 1
    elif 2 in pin_policies:
        # NO PIN should be entered atall
        LOG.debug("pin policy=2: checking no pin")
        (res, pin, otp) = (0, "", passw)
        policy = 2
    else:
        # old stuff: We check The fixed OTP PIN
        LOG.debug("pin policy=0: checkin the PIN")
        (res, pin, otp) = token.splitPinPass(passw)

    if res != -1:
        res = policy
    return (res, pin, otp)


class ValidateToken(object):
    '''
    class to manage the validation of a token
    '''

    class Context(object):
        '''
        little helper class to prove the interface calls valid
        '''
        def __init__(self):
            '''
            initlize the only api member
            '''
            self.audit = {}


    #@log_with(LOG)
    def __init__(self, token, user=None, context=None):
        '''
        ValidateToken constructor

        :param token: the to checked token
        :param user: the user of the check request of the token user
        :param context: this is used to preserve the context, which is used
                        to not import the global c
        '''
        self.token = token
        self.user = user
        self.pin_policies = None

        ## these lists will be returned as result of the token check
        self.challenge_token = []
        self.pin_matching_token = []
        self.invalid_token = []
        self.valid_token = []

        ## support of context  : c.audit
        if context == None:
            self.context = self.Context()
        else:
            self.context = context

    @log_with(LOG)
    def get_verification_result(self):
        '''
        return the internal result representation of the token verification
        which are a set of list, which stand for the challenge, pinMatching
        or invalid or valid token list

        - the lists are returned as they easily could be joined into the final
          token list, independent of they are empty or contain a token obj

        :return: tuple of token lists
        '''

        return (self.challenge_token, self.pin_matching_token,
                self.invalid_token, self.valid_token)

    #@log_with(LOG)
    def checkToken(self, passw, user, options=None):
        '''
        validate a token against the provided pass

        :raises: "challenge not found",
                 if a state is given and no challenge is found for this
                 challenge id

        :param passw: the password, which could either be a pin, a pin+otp
                       or otp
        :param user: the user which the token belongs to
        :param options: dict with additional request parameters

        :return: tuple of otpcounter and potential reply
        '''
        res = -1
        if options is None:
            options = {}

        ## are there outstanding challenges
        challenges = self.get_challenges(options)

        ## is the request refering to a previous challenge
        if self.token.is_challenge_response(passw, user,
                                             options=options,
                                             challenges=challenges):

            (res, reply) = self.check_challenges(challenges,
                                        user, passw, options=options)

        else:
            ## do the standard check
            (res, reply) = self.check_standard(passw, user, options=options)

        return (res, reply)

    @log_with(LOG)
    def check_challenges(self, challenges, user, passw, options=None):
        '''
        This function checks, if the given response (passw) matches
        any of the open challenges

        to prevent the token author to deal with the database layer, the
        token.checkResponse4Challenge will recieve only the dictionary of the
        challenge data

        :param challenges: the list of database challenges
        :param user: the requesting use
        :param passw: the to password of the request, which must be pin+otp
        :param options: the addtional request parameters
        :return: tuple of otpcount (as result of an internal token.checkOtp)
                 and additional optional reply
        '''
        ## challenge reply will stay None as we are in the challenge response
        ## mode
        reply = None
        matching_challenges = []
        if options == None: options = {}

        otp = passw

        (otpcount, matching_challenges) = self.token.checkResponse4Challenge(
                                            user, otp, options=options,
                                            challenges=challenges)
        if otpcount >= 0:
            self.valid_token.append(self.token)
            if len(self.invalid_token) > 0:
                del self.invalid_token[0]
        else:
            self.invalid_token.append(self.token)

        ## delete all challenges, which belong to the token and
        ## the token could decide on its own, which should be deleted
        ## default is: challenges which are younger than the matching one
        ## are to be deleted

        all_challenges = self.lookup_challenge()
        to_be_deleted = self.token.challenge_janitor(matching_challenges,
                                                      all_challenges)
        self.delete_challenges(to_be_deleted)

        return (otpcount, reply)

    #@log_with(LOG)
    def check_standard(self, passw, user, options=None):
        '''
        do a standard verification, as we are not in a challengeResponse mode

        the upper interfaces expect in the success the otp counter or at
        least 0 if we have a success. A -1 identifies an error

        :param passw: the password, which should be checked
        :param options: dict with additional request parameters

        :return: tuple of matching otpcounter and a potential reply
        '''

        otp_count = -1
        pin_match = False
        reply = None

        ttype = self.token.getType()

        ## fallback eg. in case of check_s, which does not provide a user
        if user is None:
            user = privacyidea.lib.token.get_token_owner(self.token)
            
        Policy = PolicyClass(request, config, c,
                             get_privacyIDEA_config())
        support_challenge_response = Policy.get_auth_challenge_response(user, ttype)

        ## special handling for tokens, who support only challenge modes
        ## like the sms, email or ocra2 token
        challenge_mode_only = False

        mode = self.token.mode
        if type(mode) == list and len(mode) == 1 and mode[0] == "challenge":
            challenge_mode_only = True

        ## the support_challenge_response is overruled, if the token
        ## supports only challenge processing
        if challenge_mode_only == True:
            support_challenge_response = True

        try:
            ## call the token authentication
            (pin_match, otp_count, reply) = self.token.authenticate(passw, user,
                                                                options=options)
        except Exception as exx:
            if (support_challenge_response == True and
                self.token.is_challenge_request(passw, user, options=options)):
                LOG.info("Retry on base of a challenge request:")
                pin_match = False
                otp_count = -1
            else:
                LOG.error("%s" % (traceback.format_exc()))
                raise Exception(exx)

        if otp_count < 0 or pin_match == False:

            if (support_challenge_response == True and
                self.token.isActive() and
                self.token.is_challenge_request(passw, user, options=options)):
                # we are in createChallenge mode
                # fix for #12413:
                # - moved the create_challenge call to the checkTokenList!
                ## after all tokens are processed and only one is challengeing
                # (_res, reply) = create_challenge(self.token, options=options)
                self.challenge_token.append(self.token)

        if len(self.challenge_token) == 0:
            if otp_count >= 0:
                self.valid_token.append(self.token)
            elif pin_match is True:
                self.pin_matching_token.append(self.token)
            else:
                self.invalid_token.append(self.token)

        return (otp_count, reply)

    @log_with(LOG)
    def get_challenges(self, options=None):
        '''
        get all challenges, defined either by the option=state
        or identified by the token serial reference

        :param options: the request options

        :return: a list of challenges
        '''
        challenges = []
        valid_challenges = []

        if (options is not None and
            options.has_key("state") or options.has_key("transactionid")):

            if options.has_key("state"):
                state = options.get('state')
            elif options.has_key("transactionid"):
                state = options.get('transactionid')

            challenges = self.lookup_challenge(state)
            if len(challenges) == 0 and self.token.getType() not in ['ocra']:
                ## if state argument is given, but no open challenge found
                ## this might be a problem, so make a log entry
                LOG.info('no challenge with state %s found for %s'
                            % (state, self.token.getSerial()))

        else:
            challenges = self.lookup_challenge()

        ## now verify that the challenge is valid
        for ch in challenges:
            if self.token.is_challenge_valid(ch):
                valid_challenges.append(ch)

        return valid_challenges

    @log_with(LOG)
    def lookup_challenge(self, state=0):
        '''
        database lookup to find all challenges belonging to a token and or
        if exist with a transaction state

        :param state: the optional parameter identified the state/transactionId

        :return: the list of challenges
        '''

        challenges = []

        if state == 0:
            challenges = Session.query(Challenge).\
              filter(Challenge.tokenserial == self.token.getSerial()).\
              all()
        else:
            challenges = Session.query(Challenge).\
              filter(Challenge.tokenserial == self.token.getSerial()).\
              filter(Challenge.transid == state).\
              all()

        return challenges

    @log_with(LOG)
    def delete_challenges(self, challenges):
        '''
        delete challenges, which match those listed ones

        :param challenges: list of (dict|int|str) challenges
        :return: result of the delete operation
        '''

        challenge_ids = []
        for challenge in challenges:
            if type(challenge) == dict:
                if challenge.has_key('id'):
                    challenge_id = challenge.get('id')
            elif type(challenge) == Challenge:
                challenge_id = challenge.get('id')
            elif type(challenge) in (unicode , str , int):
                challenge_id = challenge

            try:
                challenge_ids.append(int(challenge_id))
            except ValueError:
                ## ignore
                LOG.warning("failed to concert the challengeId %r to int()" %
                            challenge_id)

        res = 1

        # 1. get all challeges which are to be deleted
        # 2. self.token.select_challenges()

        if len(challenge_ids) > 0:

            del_challes = Session.query(Challenge).\
                filter(Challenge.tokenserial == u'' + self.token.getSerial()).\
                filter(Challenge.id.in_(challenge_ids)).all()

            for dell in del_challes:
                Session.delete(dell)
                #pass

        return res

#eof###########################################################################
