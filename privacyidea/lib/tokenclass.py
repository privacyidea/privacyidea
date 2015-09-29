# -*- coding: utf-8 -*-
#  privacyIDEA is a fork of LinOTP
#
#  2015-09-07 Corneluis Kölbel <cornelius@privacyidea.org>
#             Add challenge response decorator
#  2015-08-27 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add revocation of token
#  * Nov 27, 2014 Cornelius Kölbel <cornelius@privacyidea.org>
#                 Migration to flask
#                 Rewrite of methods
#                 100% test code coverage
#  * Oct 03, 2014 Cornelius Kölbel <cornelius@privacyidea.org>
#                 Move the QR stuff in getInitDetail into the token classes
#  * Sep 17, 2014 Cornelius Kölbel, cornelius@privacyidea.org
#                 Improve the return value of the InitDetail
#  * May 08, 2014 Cornelius Kölbel
#
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
"""
This is the Token Base class, which is inherited by all token types.
It depends on lib.user and lib.config.

You can add your own Tokens by adding the modules comma
seperated to the directive
              privacyideaTokenModules
in the privacyidea.ini file.
"""
import logging
import hashlib
import datetime

from .error import (TokenAdminError,
                    ParameterError)

from ..api.lib.utils import getParam
from .utils import generate_otpkey
from .log import log_with

from .config import (get_from_config, get_prepend_pin)
from .utils import create_img
from .user import (User,
                   get_username)
from ..models import (TokenRealm, Challenge, cleanup_challenges)
from .challenge import get_challenges
from .crypto import encryptPassword
from .crypto import decryptPassword
from .policydecorators import libpolicy, auth_otppin, challenge_response_allowed
from .decorators import check_token_locked

DATE_FORMAT = "%d/%m/%y %H:%M"
optional = True
required = False

log = logging.getLogger(__name__)


class TokenClass(object):

    # Class properties
    using_pin = True
    hKeyRequired = False
    mode = ['authenticate', 'challenge']

    @log_with(log)
    def __init__(self, db_token):
        """
        Create a new token object.
        
        :param db_token: A database token object
        :type db_token: Token
        :return: A TokenClass object
        """
        self.token = db_token
        self.type = db_token.tokentype
        # the init_details is a generic container, to store token specific
        # processing init_details e.g. for the initialization process
        # which could be retrieved in the controllers
        # this is not to be confused with the tokeninfo!
        self.init_details = {}
        # These are temporary details to store during authentication
        # like the "matched_otp_counter".
        self.auth_details = {}

    def set_type(self, tokentype):
        """
        Set the tokentype in this object and
        also in the underlying database-Token-object.
        
        :param tokentype: The type of the token like HOTP or TOTP
        :type tokentype: string
        """
        tokentype = u'' + tokentype
        self.type = tokentype
        self.token.tokentype = tokentype

    @classmethod
    def get_class_type(cls):
        return None

    @classmethod
    def get_class_info(cls, key=None, ret='all'):
        return {}

    @classmethod
    def get_class_prefix(cls):
        return "UNK"

    def get_type(self):
        return self.token.tokentype

    @check_token_locked
    def set_user(self, user, report=None):
        """
        Set the user attributes (uid, resolvername, resolvertype) of a token.
        
        :param user: a User() object, consisting of loginname and realm
        :param report: tbdf.
        :return: None
        """
        (uid, resolvertype, resolvername) = user.get_user_identifiers()
        self.token.resolver = resolvername
        self.token.resolver_type = resolvertype
        self.token.user_id = uid
        # set the tokenrealm
        self.set_realms([user.realm])

    def get_user(self):
        """
        return the user (owner) of a token
        If the token has no owner assigned, we return None

        :return: The owner of the token
        :rtype: User object
        """
        user_object = None
        realmname = ""
        username = get_username(self.token.user_id, self.token.resolver)
        rlist = self.token.realm_list
        # FIXME: What if the token has more than one realm assigned?
        if len(rlist) == 1:
            realmname = rlist[0].realm.name
        if username and realmname:
            user_object = User(login=username,
                               resolver=self.token.resolver,
                               realm=realmname)
        return user_object

    def get_user_displayname(self):
        """
        Returns a tuple of a user identifier like user@realm and the
        displayname of "givenname surname".

        :return: tuple
        """
        user_object = self.get_user()
        user_info = user_object.get_user_info()
        user_identifier = "%s_%s" % (user_object.login, user_object.realm)
        user_displayname = "%s %s" % (user_info.get("givenname", "."),
                                      user_info.get("surname", "."))
        return user_identifier, user_displayname

    @check_token_locked
    def set_user_identifiers(self, uid, resolvername, resolvertype):
        """
        (was setUid)
        Set the user attributes of a token
        :param uid: The user id in the user source
        :param resolvername: The name of the resolver
        :param resolvertype: The type of the resolver
        :return: None
        """
        self.token.resolver = resolvername
        self.token.resolver_type = resolvertype
        self.token.user_id = uid

    @check_token_locked
    def reset(self):
        """
        Reset the failcounter
        """
        self.token.failcount = 0
        self.token.save()

    @check_token_locked
    def add_init_details(self, key, value):
        """
        (was addInfo)
        Adds information to a volatile internal dict
        """
        self.init_details[key] = value
        return self.init_details

    @check_token_locked
    def set_init_details(self, details):
        if type(details) not in [dict]:
            raise Exception("Details setting: wrong data type - must be dict")
        self.init_details = details
        return self.init_details

    @log_with(log)
    def get_init_details(self):
        """
        return the status of the token rollout

        :return: return the status dict.
        :rtype: dict
        """
        return self.init_details

    @check_token_locked
    def set_tokeninfo(self, info):
        """
        Set the tokeninfo field in the DB. Old values will be deleted.
        :param info: dictionary with key and value
        :type info: dict
        :return:
        """
        self.token.del_info()
        for k, v in info.items():
            if k.endswith(".type"):
                # we have a type
                if v == "password":
                    # of type password, so we need to entrypt the value of
                    # the original key (without type)
                    orig_key = ".".join(k.split(".")[:-1])
                    info[orig_key] = encryptPassword(info.get(orig_key, ""))

        self.token.set_info(info)

    @check_token_locked
    def add_tokeninfo(self, key, value, value_type=None):
        """
        Add a key and a value to the DB tokeninfo
        :param key:
        :param value:
        :return:
        """
        add_info = {key: value}
        if value_type:
            add_info[key + ".type"] = value_type
            if value_type == "password":
                # encrypt the value
                add_info[key] = encryptPassword(value)
        self.token.set_info(add_info)

    @check_token_locked
    def check_otp(self, otpval, counter=None, window=None, options=None):
        """
        This checks the OTP value, AFTER the upper level did
        the checkPIN

        In the base class we do not know, how to calculate the
        OTP value. So we return -1.
        In case of success, we should return >=0, the counter

        :param otpval: the OTP value
        :param counter: The counter for counter based otp values
        :type counter: int
        :param window: a counter window
        :type counter: int
        :param options: additional token specific otpions
        :type options: dict
        :return: counter of the matching OTP value.
        :rtype: int
        """
        if not counter:
            counter = self.token.count
        if not window:
            window = self.token.count_window

        return -1

    def get_otp(self, current_time=""):
        """
        The default token does not support getting the otp value
        will return a tuple of four values
        a negative value is a failure.
        
        :return: something like:  (1, pin, otpval, combined)
        """
        return -2, 0, 0, 0

    def get_multi_otp(self, count=0, epoch_start=0, epoch_end=0,
                      curTime=None, timestamp=None):
        """
        This returns a dictionary of multiple future OTP values of a token.

        :param count: how many otp values should be returned
        :param epoch_start: time based tokens: start when
        :param epoch_end: time based tokens: stop when
        :param curTime: current time for TOTP token (for selftest)
        :type curTime: datetime object
        :param timestamp: unix time, current time for TOTP token (for selftest)
        :type timestamp: int

        :return: True/False, error text, OTP dictionary
        :rtype: Tuple
        """
        return False, "get_multi_otp not implemented for this tokentype", {}

    @libpolicy(auth_otppin)
    @check_token_locked
    def check_pin(self, pin, user=None, options=None):
        """
        Check the PIN of the given Password.
        Usually this is only dependent on the token itself,
        but the user object can cause certain policies.

        Each token could implement its own PIN checking behaviour.

        :param pin: the PIN (static password component), that is to be checked.
        :type pin: string
        :param user: for certain PIN policies (e.g. checking against the
                     user store) this is the user, whose
                     password would be checked. But at the moment we are
                     checking against the userstore in the decorator
                     "auth_otppin".
        :type user: User object
        :param options: the optional request parameters
        :return: If the PIN is correct, return True
        :rtype: bool
        """
        # check PIN against the token database
        res = self.token.check_pin(pin)
        return res

    @check_token_locked
    def authenticate(self, passw, user=None, options=None):
        """
        High level interface which covers the check_pin and check_otp
        This is the method that verifies single shot authentication like
        they are done with push button tokens.

        It is a high level interface to support other tokens as well, which
        do not have a pin and otp separation - they could overwrite
        this method

        If the authentication succeeds an OTP counter needs to be increased,
        i.e. the OTP value that was used for this authentication is invalidated!

        :param passw: the password which could be pin+otp value
        :type passw: string
        :param user: The authenticating user
        :type user: User object
        :param options: dictionary of additional request parameters
        :type options: dict

        :return: returns tuple of
                 1. true or false for the pin match,
                 2. the otpcounter (int) and the
                 3. reply (dict) that will be added as
                    additional information in the JSON response
                    of ``/validate/check``.
        :rtype: tuple
        """
        pin_match = False
        otp_counter = -1
        reply = None

        (res, pin, otpval) = self.split_pin_pass(passw, user=user,
                                                 options=options)
        if res != -1:
            pin_match = self.check_pin(pin, user=user, options=options)
            if pin_match is True:
                otp_counter = self.check_otp(otpval, options=options)
                #self.set_otp_count(otp_counter)

        return pin_match, otp_counter, reply

    def update(self, param, reset_failcount=True):
        """
        Update the token object
        
        :param param: a dictionary with different params like keysize,
                      description, genkey, otpkey, pin
        :type: param: dict
        """
        tdesc = getParam(param, "description", optional)
        if tdesc is not None:
            self.token.set_description(tdesc)

        # key_size as parameter overrules a prevoiusly set
        # value e.g. in hashlib in the upper classes
        key_size = getParam(param, "keysize", optional)
        if key_size is None:
            key_size = 20

        #
        # process the otpkey:
        #   if otpkey given - take this
        #   if not given
        #       if genkey == 1 : create one
        #   if required and otpkey == None:
        #      raise param Exception, that we require an otpkey
        #
        otpKey = getParam(param, "otpkey", optional)
        genkey = int(getParam(param, "genkey", optional) or 0)

        assert(genkey in [0, 1]), ("TokenClass supports only genkey in"
                                   " range [0,1] : %r" % genkey)

        if genkey == 1 and otpKey is not None:
            raise ParameterError('[ParameterError] You may either specify '
                                 'genkey or otpkey, but not both!', id=344)

        if otpKey is not None:
            self.token.set_otpkey(otpKey, reset_failcount=reset_failcount)
        else:
            if genkey == 1:
                otpKey = self._genOtpKey_()

        # otpKey still None?? - raise the exception
        if otpKey is None:
            if self.hKeyRequired is True:
                otpKey = getParam(param, "otpkey", required)

        if otpKey is not None:
            self.add_init_details('otpkey', otpKey)
            self.set_otpkey(otpKey)

        pin = getParam(param, "pin", optional)
        if pin is not None:
            storeHashed = True
            enc = getParam(param, "encryptpin", optional)
            if enc is not None and (enc is True or enc.lower() == "true"):
                storeHashed = False
            self.token.set_pin(pin, storeHashed)

        otplen = getParam(param, 'otplen', optional)
        if otplen is not None:
            self.set_otplen(otplen)

        return

    def _genOtpKey_(self, otpkeylen=None):
        '''
        private method, to create an otpkey
        '''
        if otpkeylen is None:
            if hasattr(self, 'otpkeylen'):
                otpkeylen = getattr(self, 'otpkeylen')
            else:
                otpkeylen = 20
        return generate_otpkey(otpkeylen)

    @check_token_locked
    def set_description(self, description):
        """
        Set the description on the database level
        
        :param description: description of the token
        :type description: string
        """
        self.token.set_description(u'' + description)
        return

    def set_defaults(self):
        """
        Set the default values on the database level
        """
        self.token.otplen = int(get_from_config("DefaultOtpLen") or 6)
        self.token.count_window = int(get_from_config("DefaultCountWindow")
                                      or 10)
        self.token.maxfail = int(get_from_config("DefaultMaxFailCount") or 10)
        self.token.sync_window = int(get_from_config("DefaultSyncWindow")
                                     or 1000)

        self.token.tokentype = u'' + self.type
        return

    def delete_token(self):
        """
        delete the database token
        """
        self.token.delete()

    def save(self):
        """
        Save the database token
        """
        self.token.save()

    def resync(self, otp1, otp2, options=None):
        pass

    def get_otp_count_window(self):
        return self.token.count_window

    def get_otp_count(self):
        return self.token.count

    def is_active(self):
        return self.token.active

    def get_failcount(self):
        return self.token.failcount

    def set_failcount(self, failcount):
        """
        Set the failcounter in the database
        """
        self.token.failcount = failcount

    def get_max_failcount(self):
        return self.token.maxfail

    def get_user_id(self):
        return self.token.user_id

    def set_realms(self, realms):
        """
        Set the list of the realms of a token.
        :param realms: realms the token should be assigned to
        :type realms: list
        """
        self.token.set_realms(realms)
        
    def get_realms(self):
        """
        Return a list of realms the token is assigned to
        :return: realms
        :rtype:l list
        """
        return self.token.get_realms()
        
    def get_serial(self):
        return self.token.serial
    
    def get_tokentype(self):
        return self.token.tokentype

    @check_token_locked
    def set_so_pin(self, soPin):
        self.token.set_so_pin(soPin)

    @check_token_locked
    def set_user_pin(self, userPin):
        self.token.set_user_pin(userPin)

    @check_token_locked
    def set_otpkey(self, otpKey):
        self.token.set_otpkey(otpKey)

    @check_token_locked
    def set_otplen(self, otplen):
        self.token.otplen = int(otplen)

    @check_token_locked
    def get_otplen(self):
        return self.token.otplen

    @check_token_locked
    def set_otp_count(self, otpCount):
        self.token.count = int(otpCount)
        self.token.save()

    @check_token_locked
    def set_pin(self, pin, encrypt=False):
        """
        set the PIN of a token.
        Usually the pin is stored in a hashed way.
        :param pin: the pin to be set for the token
        :type pin: basestring
        :param encrypt: If set to True, the pin is stored encrypted and
                        can be retrieved from the database again
        :type encrypt: bool
        """
        storeHashed = not encrypt
        self.token.set_pin(pin, storeHashed)

    def get_pin_hash_seed(self):
        return self.token.pin_hash, self.token.pin_seed

    @check_token_locked
    def set_pin_hash_seed(self, pinhash, seed):
        self.token.pin_hash = pinhash
        self.token.pin_seed = seed

    @check_token_locked
    def enable(self, enable=True):
        self.token.active = enable

    def revoke(self):
        """
        This revokes the token.
        By default it
        1. sets the revoked-field
        2. set the locked field
        3. disables the token.

        Some token types may revoke a token without locking it.
        """
        self.token.revoked = True
        self.token.locked = True
        self.token.active = False

    def is_revoked(self):
        """
        Check if the token is in the revoked state

        :return: True, if the token is revoked
        """
        return self.token.revoked

    def is_locked(self):
        """
        Check if the token is in a locked state
        A locked token can not be modified

        :return: True, if the token is locked.
        """
        return self.token.locked

    @check_token_locked
    def set_maxfail(self, maxFail):
        self.token.maxfail = maxFail

    @check_token_locked
    def set_hashlib(self, hashlib):
        self.add_tokeninfo("hashlib", hashlib)

    @check_token_locked
    def inc_failcount(self):
        if self.token.failcount < self.token.maxfail:
            self.token.failcount = (self.token.failcount + 1)
        try:
            self.token.save()
        except:  # pragma: no cover
            log.error('update failed')
            raise TokenAdminError("Token Fail Counter update failed", id=1106)
        return self.token.failcount

    @check_token_locked
    def set_count_window(self, countWindow):
        self.token.count_window = int(countWindow)

    def get_count_window(self):
        return self.token.count_window

    @check_token_locked
    def set_sync_window(self, syncWindow):
        self.token.sync_window = int(syncWindow)

    def get_sync_window(self):
        return self.token.sync_window

    # hashlib algorithms:
    # http://www.doughellmann.com/PyMOTW/hashlib/index.html#module-hashlib

    @classmethod
    def get_hashlib(cls, hLibStr):
        """
        Returns a hashlib function for a given string
        :param hLibStr: the hashlib
        :type hLibStr: string
        :return: the hashlib
        :rtype: function
        """
        if hLibStr is None:
            return hashlib.sha1

        hashlibStr = hLibStr.lower()

        if hashlibStr == "md5":
            return hashlib.md5
        elif hashlibStr == "sha1":
            return hashlib.sha1
        elif hashlibStr == "sha224":
            return hashlib.sha224
        elif hashlibStr == "sha256":
            return hashlib.sha256
        elif hashlibStr == "sha384":
            return hashlib.sha384
        elif hashlibStr == "sha512":
            return hashlib.sha512
        else:
            return hashlib.sha1

    def get_tokeninfo(self, key=None, default=None):
        """
        return the complete token info or a single key of the tokeninfo.
        When returning the complete token info dictionary encrypted entries
        are not decrypted.
        If you want to receive a decrypted value, you need to call it
        directly with the key.

        :param key: the key to return
        :type key: string
        :param default: the default value, if the key does not exist
        :type default: string
        :return: the value for the key
        :rtype: int or string
        """
        tokeninfo = self.token.get_info()
        if key:
            ret = tokeninfo.get(key, default)
            if tokeninfo.get(key + ".type") == "password":
                # we need to decrypt the return value
                ret = decryptPassword(ret)
        else:
            ret = tokeninfo
        return ret

    def del_tokeninfo(self, key=None):
        self.token.del_info(key)

    @check_token_locked
    def set_count_auth_success_max(self, count):
        """
        Sets the counter for the maximum allowed successful logins
        as key "count_auth_success_max" in token info
        :param count: a number
        :type count: int
        """
        self.add_tokeninfo("count_auth_success_max", int(count))

    @check_token_locked
    def set_count_auth_success(self, count):
        """
        Sets the counter for the occurred successful logins
        as key "count_auth_success" in token info
        :param count: a number
        :type count: int
        """
        self.add_tokeninfo("count_auth_success", int(count))

    @check_token_locked
    def set_count_auth_max(self, count):
        """
        Sets the counter for the maximum allowed login attemps
        as key "count_auth_max" in token info
        :param count: a number
        :type count: int
        """
        self.add_tokeninfo("count_auth_max", int(count))

    @check_token_locked
    def set_count_auth(self, count):
        """
        Sets the counter for the occurred login attepms
        as key "count_auth" in token info
        :param count: a number
        :type count: int
        """
        self.add_tokeninfo("count_auth", int(count))

    def get_count_auth_success_max(self):
        """
        Return the maximum allowed successful authentications
        """
        ret = int(self.get_tokeninfo("count_auth_success_max", 0))
        return ret

    def get_count_auth_success(self):
        """
        Return the number of successful authentications
        """
        ret = int(self.get_tokeninfo("count_auth_success", 0))
        return ret

    def get_count_auth_max(self):
        """
        Return the number of maximum allowed authentications
        """
        ret = int(self.get_tokeninfo("count_auth_max", 0))
        return ret

    def get_count_auth(self):
        """
        Return the number of all authentication tries
        """
        ret = int(self.get_tokeninfo("count_auth", 0))
        return ret

    def get_validity_period_end(self):
        """
        returns the end of validity period (if set)
        if not set, "" is returned.
        :return: the end of the validity period
        :rtype: string
        """
        ret = self.get_tokeninfo("validity_period_end", "")
        return ret

    @check_token_locked
    def set_validity_period_end(self, end_date):
        """
        sets the end date of the validity period for a token
        :param end_date: the end date in the format "%d/%m/%y %H:%M"
                         if the format is wrong, the method will
                         throw an exception
        :type end_date: string
        """
        try:
            # try the first date format
            dt = datetime.datetime.strptime(end_date,
                                            "%Y-%m-%dT%H:%M:%S.000Z")
            end_date = dt.strftime(DATE_FORMAT)
        except ValueError:
            # upper layer will catch. we just try to verify the date format
            datetime.datetime.strptime(end_date, DATE_FORMAT)

        self.add_tokeninfo("validity_period_end", end_date)

    def get_validity_period_start(self):
        """
        returns the start of validity period (if set)
        if not set, "" is returned.
        :return: the start of the validity period
        :rtype: string
        """
        ret = self.get_tokeninfo("validity_period_start", "")
        return ret

    @check_token_locked
    def set_validity_period_start(self, start_date):
        """
        sets the start date of the validity period for a token
        :param start_date: the start date in the format "%d/%m/%y %H:%M"
                           if the format is wrong, the method will
                           throw an exception
        :type start_date: string
        """
        try:
            # try the first date format
            dt = datetime.datetime.strptime(start_date,
                                            "%Y-%m-%dT%H:%M:%S.000Z")
            start_date = dt.strftime(DATE_FORMAT)
        except ValueError:
            #  upper layer will catch. we just try to verify the date format
            datetime.datetime.strptime(start_date, DATE_FORMAT)

        self.add_tokeninfo("validity_period_start", start_date)

    @check_token_locked
    def inc_count_auth_success(self):
        """
        Increase the counter, that counts successful authentications
        """
        count = self.get_count_auth_success()
        count += 1
        self.set_count_auth_success(count)
        return count

    @check_token_locked
    def inc_count_auth(self):
        """
        Increase the counter, that counts authentications - successful and
        unsuccessful
        """
        count = self.get_count_auth()
        count += 1
        self.set_count_auth(count)
        return count

    def check_failcount(self):
        """
        Checks if the failcounter is exceeded. It returns True, if the
        failcounter is less than maxfail
        :return: True or False
        """
        return self.token.failcount < self.token.maxfail

    def check_auth_counter(self):
        """
        This function checks the count_auth and the count_auth_success.
        If the count_auth is less than count_auth_max
        and count_auth_success is less than count_auth_success_max
        it returns True. Otherwise False.
        
        :return: success if the counter is less than max
        :rtype: bool
        """
        if self.get_count_auth_max() != 0:
            if self.get_count_auth() >= self.get_count_auth_max():
                return False

        if self.get_count_auth_success_max() != 0:
            if self.get_count_auth_success() >= self.get_count_auth_success_max():
                return False

        return True

    def check_validity_period(self):
        """
        This checks if the datetime.datetime.now() is within the validity
        period of the token.

        :return: success
        :rtype: bool
        """
        start = self.get_validity_period_start()
        end = self.get_validity_period_end()

        if start:
            dt_start = datetime.datetime.strptime(start, DATE_FORMAT)
            if dt_start > datetime.datetime.now():
                return False

        if end:
            dt_end = datetime.datetime.strptime(end, DATE_FORMAT)
            if dt_end < datetime.datetime.now():
                return False

        return True

    @log_with(log)
    @check_token_locked
    def inc_otp_counter(self, counter=None, reset=True):
        """
        Increase the otp counter and store the token in the database
        :param counter: the new counter value. If counter is given, than
                        the counter is increased by (counter+1)
                        If the counter is not given, the counter is increased
                        by +1
        :type counter: int
        :param reset: reset the failcounter if set to True
        :type reset: bool
        :return: the new counter value
        """
        resetCounter = False
        if counter:
            self.token.count = counter + 1
        else:
            self.token.count += 1

        if reset is True:
            if get_from_config("DefaultResetFailCount") == "True":
                resetCounter = True

        if resetCounter and self.token.active:
            if self.token.failcount < self.token.maxfail:
                self.token.failcount = 0

        # make DB persistent immediately, to avoud the reusage of the counter
        self.token.save()
        return self.token.count

    def check_otp_exist(self, otp, window=None):
        """
        checks if the given OTP value is/are values of this very token.
        This is used to autoassign and to determine the serial number of
        a token.
        
        :param otp: the OTP value
        :param window: The look ahead window
        :type window: int
        :return: True or a value > 0 in case of success
        """
        return -1

    def is_previous_otp(self, otp, window=10):
        """
        checks if a given OTP value is a previous OTP value, that lies in the
        past or has a lower counter.

        This is used in case of a failed authentication to return the
        information, that this OTP values was used previously and is invalid.

        :param otp: The OTP value.
        :type otp: basestring
        :param window: A counter window, how far we should look into the past.
        :type window: int
        :return: bool
        """
        return False

    def split_pin_pass(self, passw, user=None, options=None):
        """
        Split the password into the token PIN and the OTP value

        take the given password and split it into the PIN and the
        OTP value. The splitting can be dependent of certain policies.
        The policies may depend on the user.

        Each token type may define its own way to slit the PIN and
        the OTP value.

        :param passw: the password to split
        :return: tuple of pin and otp value
        :param user: The user/owner of the token
        :type user: User object
        :param options: can be used be the token types.
        :type options: dict
        :return: tuple of (split status, pin, otp value)
        :rtype: tuple
        """
        # The database field is always an integer
        otplen = self.token.otplen
        if get_prepend_pin():
            pin = passw[0:-otplen]
            otpval = passw[-otplen:]
        else:
            pin = passw[otplen:]
            otpval = passw[0:otplen]

        return True, pin, otpval

    def status_validation_fail(self):
        """
        callback to enable a status change, if auth failed
        """
        return

    def status_validation_success(self):
        """
        callback to enable a status change, if auth succeeds
        """
        return

    def __repr__(self):
        """
        return the token state as text

        :return: token state as string representation
        :rtype:  string
        """
        ldict = {}
        for attr in self.__dict__:
            key = "%r" % attr
            val = "%r" % getattr(self, attr)
            ldict[key] = val
        res = "<%r %r>" % (self.__class__, ldict)
        return res

    def get_init_detail(self, params=None, user=None):
        """
        to complete the token normalisation, the response of the initialiastion
        should be build by this token specific method.
        
        get_init_detail returns additional information after an admin/init
        like the QR code of an HOTP/TOTP token.
        Can be anything else.
        
        :param params: The request params during token creation token/init
        :type params: dict
        :param user: the user, token owner
        :type user: User object
        :return: additional descriptions
        :rtype: dict
        """
        response_detail = {}

        init_details = self.get_init_details()
        response_detail.update(init_details)
        response_detail['serial'] = self.get_serial()

        otpkey = None
        if 'otpkey' in init_details:
            otpkey = init_details.get('otpkey')

        if otpkey is not None:
            response_detail["otpkey"] = {"description": "OTP seed",
                                         "value": "seed://%s" % otpkey,
                                         "img": create_img(otpkey, width=200)}

        return response_detail

    def get_QRimage_data(self, response_detail):
        """
        FIXME: Do we really use this?
        """
        url = None
        hparam = {}

        if response_detail is not None:
            if 'googleurl' in response_detail:
                url = response_detail.get('googleurl')
                hparam['alt'] = url

        return url, hparam

    # challenge interfaces starts here
    @challenge_response_allowed
    def is_challenge_request(self, passw, user=None, options=None):
        """
        This method checks, if this is a request, that triggers a challenge.

        The default behaviour to trigger a challenge is,
        if the ``passw`` parameter only contains the correct token pin *and*
        the request contains a ``data`` or a ``challenge`` key i.e. if the
        ``options`` parameter contains a key ``data`` or ``challenge``.

        Each token type can decide on its own under which condition a challenge
        is triggered by overwriting this method.

        **please note**: in case of pin policy == 2 (no pin is required)
        the ``check_pin`` would always return true! Thus each request
        containing a ``data`` or ``challenge`` would trigger a challenge!

        The Challenge workflow is like this.

        When an authentication request is issued, first it is checked if this is
        a request which will create a new challenge (is_challenge_request) or if
        this is a response to an existing challenge (is_challenge_response).
        In these two cases during request processing the following functions are
        called.

        is_challenge_request or is_challenge_response
                 |                       |
                 V                       V
        create_challenge        check_challenge
                 |                       |
                 V                       V
        challenge_janitor       challenge_janitor

        :param passw: password, which might be pin or pin+otp
        :type passw: string
        :param user: The user from the authentication request
        :type user: User object
        :param options: dictionary of additional request parameters
        :type options: dict

        :return: true or false
        :rtype: bool
        """

        request_is_challenge = False
        options = options or {}
        pin_match = self.check_pin(passw, user=user, options=options)
        if pin_match is True:
            if "data" in options or "challenge" in options:
                request_is_challenge = True

        return request_is_challenge

    def is_challenge_response(self, passw, user=None, options=None):
        """
        This method checks, if this is a request, that is the response to
        a previously sent challenge.

        The default behaviour to check if this is the response to a
        previous challenge is simply by checking if the request contains
        a parameter ``state`` or ``transactionid`` i.e. checking if the
        ``options`` parameter contains a key ``state`` or ``transactionid``.

        This method does not try to verify the response itself!
        It only determines, if this is a response for a challenge or not.
        The response is verified in check_challenge_response.

        :param passw: password, which might be pin or pin+otp
        :type passw: string
        :param user: the requesting user
        :type user: User object
        :param options: dictionary of additional request parameters
        :type options: dict
        :return: true or false
        :rtype: bool
        """
        options = options or {}
        challenge_response = False
        if "state" in options or "transaction_id" in options:
            challenge_response = True

        return challenge_response

    @check_token_locked
    def check_challenge_response(self, user=None, passw=None, options=None):
        """
        This method verifies if there is a matching challenge for the given
        passw and also verifies if the response is correct.

        It then returns the new otp_counter of the token.

        In case of success the otp_counter will be >= 0.

        :param user: the requesting user
        :type user: User object
        :param passw: the password (pin+otp)
        :type passw: string
        :param options: additional arguments from the request, which could
                        be token specific. Usually "transactionid"
        :type options: dict
        :return: return otp_counter. If -1, challenge does not match
        :rtype: int
        """
        options = options or {}
        otp_counter = -1

        # fetch the transaction_id
        transaction_id = options.get('transaction_id', None)
        if transaction_id is None:
            transaction_id = options.get('state')

        # get the challenges for this transaction ID
        if transaction_id is not None:
            challengeobject_list = get_challenges(serial=self.token.serial,
                                                  transaction_id=transaction_id)

            for challengeobject in challengeobject_list:
                if challengeobject.is_valid():
                    # challenge is still valid
                    # Add the challenge to the options for check_otp
                    options["challenge"] = challengeobject.challenge
                    # Now see if the OTP matches:
                    otp_counter = self.check_otp(passw, options=options)
                    if otp_counter >= 0:
                        # We found the matching challenge, so lets return the
                        #  successful result and delete the challenge object.
                        challengeobject.delete()
                        break

        return otp_counter

    def challenge_janitor(self):
        """
        Just clean up all challenges, for which the expiration has expired.

        :return: None
        """
        cleanup_challenges()

    def create_challenge(self, transactionid=None, options=None):
        """
        This method creates a challenge, which is submitted to the user.
        The submitted challenge will be preserved in the challenge
        database.

        If no transaction id is given, the system will create a transaction
        id and return it, so that the response can refer to this transaction.

        :param transactionid: the id of this challenge
        :param options: the request context parameters / data
        :type options: dict
        :return: tuple of (bool, message, transactionid, attributes)
        :rtype: tuple

        The return tuple builds up like this:
        ``bool`` if submit was successful;
        ``message`` which is displayed in the JSON response;
        additional ``attributes``, which are displayed in the JSON response.
        """
        options = options or {}
        message = 'please enter otp: '
        data = None
        attributes = None

        validity = int(get_from_config('DefaultChallengeValidityTime', 120))
        tokentype = self.get_tokentype().lower()
        # Maybe there is a HotpChallengeValidityTime...
        lookup_for = tokentype.capitalize() + 'ChallengeValidityTime'
        validity = int(get_from_config(lookup_for, validity))

        # Create the challenge in the database
        db_challenge = Challenge(self.token.serial,
                                 transaction_id=transactionid,
                                 challenge=options.get("challenge"),
                                 data=data,
                                 session=options.get("session"),
                                 validitytime=validity)
        db_challenge.save()
        return True, message, db_challenge.transaction_id, attributes

    def get_as_dict(self):
        """
        This returns the token data as a dictionary.
        It is used to display the token list at /token/list.

        :return: The token data as dict
        :rtype: dict
        """
        # first get the database values as dict
        token_dict = self.token.get()

        return token_dict

    @classmethod
    def api_endpoint(cls, params):
        """
        This provides a function to be plugged into the API endpoint
        /ttype/<tokentype> which is defined in api/ttype.py

        :param params: The Request Parameters which can be handled with getParam
        :return: Flask Response or text
        """
        raise ParameterError("%s does not support the API endpoint" %
                             cls.get_tokentype())
        return "json", {}
        # or return "text", "OK"
