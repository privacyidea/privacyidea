# -*- coding: utf-8 -*-
#
#  2018-01-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Implement tokenkind. Token can be hardware, software or virtual
#  2017-07-08 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Failcount unlock
#  2017-04-27 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Change dateformat
#  2016-06-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add method to set the next_pin_change and next_password_change.
#  2016-04-29 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add get_default_settings to change the parameters before
#             the token is created
#  2016-04-08 Cornelius Kölbel <cornelius@privacyidea.org>
#             Avoid consecutive if statements
#             Remove unreachable code
#  2015-12-18 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add get_setting_type
#  2015-10-12 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add testconfig classmethod
#  2015-09-07 Cornelius Kölbel <cornelius@privacyidea.org>
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

The token object also contains a database token object as self.token.
The token object runs the self.update() method during the initialization 
process in the API /token/init.

The update method takes a dictionary. Some of the following parameters:

otpkey      -> the token gets created with this OTPKey
genkey      -> genkey=1 : privacyIDEA generates an OTPKey, creates the token
               and sends it to the client.
2stepinit   -> Will do a two step rollout.
               privacyIDEA creates the first part of the OTPKey, sends it
               to the client and the clients needs to send back the second part.
               
In case of 2stepinit the key is generated from the server_component and the 
client_component using the TokenClass method generate_symmetric_key.
This method is supposed to be overwritten by the corresponding token classes.
"""
import logging
import hashlib
import datetime

from .error import (TokenAdminError,
                    ParameterError)

from ..api.lib.utils import getParam
from .utils import generate_otpkey, is_true, decode_base32check
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
from .utils import parse_timedelta, parse_legacy_time
from policy import ACTION
from dateutil.parser import parse as parse_date_string
from dateutil.tz import tzlocal, tzutc
from privacyidea.lib.utils import is_true


#DATE_FORMAT = "%d/%m/%y %H:%M"
DATE_FORMAT = '%Y-%m-%dT%H:%M%z'
# LASTAUTH is utcnow()
AUTH_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f%z"
optional = True
required = False
FAILCOUNTER_EXCEEDED = "failcounter_exceeded"
FAILCOUNTER_CLEAR_TIMEOUT = "failcounter_clear_timeout"

TWOSTEP_DEFAULT_CLIENTSIZE = 8
TWOSTEP_DEFAULT_DIFFICULTY = 10000

log = logging.getLogger(__name__)


class TOKENKIND(object):
    SOFTWARE = "software"
    HARDWARE = "hardware"
    VIRTUAL = "virtual"


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

    @staticmethod
    def get_class_type():
        return None

    @staticmethod
    def get_class_info(key=None, ret='all'):
        return {}

    @staticmethod
    def get_class_prefix():
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

    @property
    def user(self):
        """
        return the user (owner) of a token
        If the token has no owner assigned, we return None

        :return: The owner of the token
        :rtype: User object
        """
        user_object = None
        realmname = ""
        if self.token.user_id and self.token.resolver:
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

    def is_orphaned(self):
        """
        Return True is the token is orphaned. 
        
        An orphaned token means, that it has a user assigned, but the user 
        does not exist in the user store (anymore)
        :return: True / False
        """
        orphaned = False
        if self.token.user_id:
            try:
                if not self.user or not self.user.login:
                    # The token is assigned, but the username does not resolve
                    orphaned = True
            except Exception:
                # If any other resolving error occurs, we also assume the
                # token to be orphaned
                orphaned = True
        return orphaned

    def get_user_displayname(self):
        """
        Returns a tuple of a user identifier like user@realm and the
        displayname of "givenname surname".

        :return: tuple
        """
        user_object = self.user
        user_info = user_object.info
        user_identifier = u"{0!s}_{1!s}".format(user_object.login, user_object.realm)
        user_displayname = u"{0!s} {1!s}".format(user_info.get("givenname", "."),
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
        if self.token.failcount:
            # reset the failcounter and write to database
            self.set_failcount(0)
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
            # check if type is a password
            if k.endswith(".type") and v == "password":
                # of type password, so we need to encrypt the value of
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
        :param options: additional token specific options
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


    @staticmethod
    def decode_otpkey(otpkey, otpkeyformat):
        """
        Decode the otp key which is given in a specific format.

        Supported formats:
         * ``hex``, in which the otpkey is returned verbatim
         * ``base32check``, which is specified in ``decode_base32check``

        In case the OTP key is malformed or if the format is unknown,
        a ParameterError is raised.

        :param otpkey: OTP key passed by the user
        :param otpkeyformat: "hex" or "base32check"
        :return: hex-encoded otpkey
        """
        if otpkeyformat == "hex":
            return otpkey
        elif otpkeyformat == "base32check":
            return decode_base32check(otpkey)
        else:
            raise ParameterError("Unknown OTP key format: {!r}".format(otpkeyformat))


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
        key_size = int(getParam(param, "keysize", optional) or 20)

        #
        # process the otpkey:
        #   if otpkey given - take this
        #   if not given
        #       if genkey == 1 : create one
        #   if required and otpkey == None:
        #      raise param Exception, that we require an otpkey
        #
        otpKey = getParam(param, "otpkey", optional)
        genkey = is_true(getParam(param, "genkey", optional))
        twostep_init = is_true(getParam(param, "2stepinit", optional))
        otpkeyformat = getParam(param, "otpkeyformat", optional)

        if otpKey is not None and otpkeyformat is not None:
            # have to decode OTP key
            otpKey = self.decode_otpkey(otpKey, otpkeyformat)

        if twostep_init:
            if self.token.rollout_state == "clientwait":
                # We do not do 2stepinit in the second step
                raise ParameterError("2stepinit is only to be used in the "
                                     "first initialization step.")
            # In a 2-step enrollment, the server always generates a key
            genkey = 1
            # The token is disabled
            self.token.active = False


        #if genkey not in [0, 1]:
        #    raise ParameterError("TokenClass supports only genkey in  range ["
        #                         "0,1] : %r" % genkey)

        if genkey and otpKey is not None:
            raise ParameterError('[ParameterError] You may either specify '
                                 'genkey or otpkey, but not both!', id=344)

        if otpKey is None and genkey:
            otpKey = self._genOtpKey_(key_size)

        # otpKey still None?? - raise the exception
        if otpKey is None and self.hKeyRequired is True:
            otpKey = getParam(param, "otpkey", required)

        if otpKey is not None:
            if self.token.rollout_state == "clientwait":
                # If we have otpkey and the token is in the enrollment-state
                # generate the new key
                server_component = self.token.get_otpkey().getKey()
                client_component = otpKey
                otpKey = self.generate_symmetric_key(server_component,
                                                     client_component,
                                                     param)
                self.token.rollout_state = ""
                self.token.active = True
            self.add_init_details('otpkey', otpKey)
            self.token.set_otpkey(otpKey, reset_failcount=reset_failcount)

        if twostep_init:
            # After the key is generated, we set "waiting for the client".
            self.token.rollout_state = "clientwait"

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

        # Add parameters starting with the tokentype-name to the tokeninfo:
        for p in param.keys():
            if p.startswith(self.type + "."):
                self.add_tokeninfo(p, getParam(param, p))

        # The base class will be a software tokenkind
        self.add_tokeninfo("tokenkind", TOKENKIND.SOFTWARE)

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
        if failcount == 0:
            self.del_tokeninfo(FAILCOUNTER_EXCEEDED)

    def get_max_failcount(self):
        return self.token.maxfail

    def get_user_id(self):
        return self.token.user_id

    def set_realms(self, realms, add=False):
        """
        Set the list of the realms of a token.
        :param realms: realms the token should be assigned to
        :type realms: list
        :param add: if the realms should be added and not replaced
        :type add: boolean
        """
        self.token.set_realms(realms, add=add)
        
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
            if self.token.failcount == self.token.maxfail:
                self.add_tokeninfo(FAILCOUNTER_EXCEEDED,
                                   datetime.datetime.now(tzlocal()).strftime(
                                       DATE_FORMAT))
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

    @staticmethod
    def get_hashlib(hLibStr):
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
        Sets the counter for the maximum allowed login attempts
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
        end = self.get_tokeninfo("validity_period_end", "")
        if end:
            end = parse_legacy_time(end)
        return end

    @check_token_locked
    def set_validity_period_end(self, end_date):
        """
        sets the end date of the validity period for a token
        :param end_date: the end date in the format YYYY-MM-DDTHH:MM+OOOO
                         if the format is wrong, the method will
                         throw an exception
        :type end_date: string
        """
        #  upper layer will catch. we just try to verify the date format
        d = parse_date_string(end_date)
        self.add_tokeninfo("validity_period_end", d.strftime(DATE_FORMAT))

    def get_validity_period_start(self):
        """
        returns the start of validity period (if set)
        if not set, "" is returned.
        :return: the start of the validity period
        :rtype: string
        """
        start = self.get_tokeninfo("validity_period_start", "")
        if start:
            start = parse_legacy_time(start)
        return start

    @check_token_locked
    def set_validity_period_start(self, start_date):
        """
        sets the start date of the validity period for a token
        :param start_date: the start date in the format YYYY-MM-DDTHH:MM+OOOO
                           if the format is wrong, the method will
                           throw an exception
        :type start_date: string
        """
        d = parse_date_string(start_date)
        self.add_tokeninfo("validity_period_start", d.strftime(DATE_FORMAT))

    def set_next_pin_change(self, diff=None, password=False):
        """
        Sets the timestamp for the next_pin_change. Provide a
        difference like 90d (90 days).

        Either provider the
        :param diff: The time delta.
        :type diff: basestring
        :param password: Do no set next_pin_change but next_password_change
        :return: None
        """
        days = int(diff.lower().strip("d"))
        key = "next_pin_change"
        if password:
            key = "next_password_change"
        new_date = datetime.datetime.now(tzlocal()) + datetime.timedelta(days=days)
        self.add_tokeninfo(key, new_date.strftime(DATE_FORMAT))

    def is_pin_change(self, password=False):
        """
        Returns true if the pin of the token needs to be changed.
        :param password: Whether the password needs to be changed.
        :type password: bool

        :return: True or False
        """
        key = "next_pin_change"
        if password:
            key = "next_password_change"
        sdate = self.get_tokeninfo(key)
        #date_change = datetime.datetime.strptime(sdate, DATE_FORMAT)
        date_change = parse_date_string(parse_legacy_time(sdate))
        return datetime.datetime.now(tzlocal()) > date_change


    @check_token_locked
    def inc_count_auth_success(self):
        """
        Increase the counter, that counts successful authentications
        Also increase the auth counter
        """
        succcess_counter = self.get_count_auth_success()
        succcess_counter += 1
        auth_counter = self.get_count_auth()
        auth_counter += 1
        self.token.set_info({"count_auth_success": int(succcess_counter),
                             "count_auth": int(auth_counter)})
        return succcess_counter

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
        timeout = 0
        try:
            timeout = int(get_from_config(FAILCOUNTER_CLEAR_TIMEOUT, 0))
        except Exception as exx:
            log.warning("Misconfiguration. Error retrieving "
                        "failcounter_clear_timeout: "
                        "{0!s}".format(exx))
        if timeout and self.token.failcount > 0:
            now = datetime.datetime.now(tzlocal())
            lastfail = self.get_tokeninfo(FAILCOUNTER_EXCEEDED)
            if lastfail is not None:
                failcounter_exceeded = parse_legacy_time(lastfail, return_date=True)
                if now > failcounter_exceeded + datetime.timedelta(minutes=timeout):
                    self.reset()

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
        if self.get_count_auth_max() != 0 and self.get_count_auth() >= \
                self.get_count_auth_max():
            return False

        if self.get_count_auth_success_max() != 0 and  \
                        self.get_count_auth_success() >=  \
                        self.get_count_auth_success_max():
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
            #dt_start = datetime.datetime.strptime(start, DATE_FORMAT)
            dt_start = parse_legacy_time(start, return_date=True)
            if dt_start > datetime.datetime.now(tzlocal()):
                return False

        if end:
            #dt_end = datetime.datetime.strptime(end, DATE_FORMAT)
            dt_end = parse_legacy_time(end, return_date=True)
            if dt_end < datetime.datetime.now(tzlocal()):
                return False

        return True

    def check_all(self, message_list):
        """
        Perform all checks on the token. Returns False if the token is either:
        * auth counter exceeded
        * not active
        * fail counter exceeded
        * validity period exceeded

        This is used in the function token.check_token_list

        :param message_list: A list of messages
        :return: False, if any of the checks fail
        """
        r = False
        # Check if the max auth is succeeded
        if not self.check_auth_counter():
            message_list.append("Authentication counter exceeded")
        # Check if the token is disabled
        elif not self.is_active():
            message_list.append("Token is disabled")
        elif not self.check_failcount():
            message_list.append("Failcounter exceeded")
        elif not self.check_validity_period():
            message_list.append("Outside validity period")
        else:
            r = True
        if not r:
            log.info("{0} {1}".format(message_list, self.get_serial()))
        return r

    @log_with(log)
    @check_token_locked
    def inc_otp_counter(self, counter=None, increment=1, reset=True):
        """
        Increase the otp counter and store the token in the database

        Before increasing the token.count the token.count can be set using the
        parameter counter.

        :param counter: if given, the token counter is first set to counter and then
                increased by increment
        :type counter: int
        :param increment: increase the counter by this amount
        :type increment: int
        :param reset: reset the failcounter if set to True
        :type reset: bool
        :return: the new counter value
        """
        reset_counter = False
        if counter:
            self.token.count = counter

        self.token.count += increment

        if reset is True and get_from_config("DefaultResetFailCount") == "True":
            reset_counter = True

        if (reset_counter and self.token.active and self.token.failcount <
            self.token.maxfail):
            self.set_failcount(0)

        # make DB persistent immediately, to avoid the re-usage of the counter
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
            key = "{0!r}".format(attr)
            val = "{0!r}".format(getattr(self, attr))
            ldict[key] = val
        res = "<{0!r} {1!r}>".format(self.__class__, ldict)
        return res

    def get_init_detail(self, params=None, user=None):
        """
        to complete the token initialization, the response of the initialisation
        should be build by this token specific method.
        This method is called from api/token after the token is enrolled

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
                                         "value": "seed://{0!s}".format(otpkey),
                                         "img": create_img(otpkey, width=200)}

        return response_detail

    def get_QRimage_data(self, response_detail):
        """
        FIXME: Do we really use this?
        """
        url = None
        hparam = {}

        if response_detail is not None and 'googleurl' in response_detail:
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
        if pin_match is True and "data" in options or "challenge" in options:
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
        transaction_id = options.get('transaction_id')
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
                    else:
                        # increase the received_count
                        challengeobject.set_otp_status()

        self.challenge_janitor()
        return otp_counter

    @staticmethod
    def challenge_janitor():
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
        self.challenge_janitor()
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
    def api_endpoint(cls, request, g):
        """
        This provides a function to be plugged into the API endpoint
        /ttype/<tokentype> which is defined in api/ttype.py

        The method should return
            return "json", {}
        or
            return "text", "OK"

        :param request: The Flask request
        :param g: The Flask global object g
        :return: Flask Response or text
        """
        raise ParameterError("{0!s} does not support the API endpoint".format(
                             cls.get_tokentype()))

    @staticmethod
    def test_config(params=None):
        """
        This method is used to test the token config. Some tokens require some
        special token configuration like the SMS-Token or the Email-Token.
        To test this configuration, this classmethod is used.

        It takes token specific parameters and returns a tuple of a boolean
        and a result description.

        :param params: token specific parameters
        :type params: dict
        :return: success, description
        :rtype: tuple
        """
        return False, "Not implemented"

    @staticmethod
    def get_setting_type(key):
        """
        This function returns the type of the token specific config/setting.
        This way a tokenclass can define settings, that can be "public" or a
        "password". If this setting is written to the database, the type of
        the setting is set automatically in set_privacyidea_config

        The key name needs to start with the token type.

        :param key: The token specific setting key
        :return: A string like "public"
        """
        return ""

    @classmethod
    def get_default_settings(cls, params, logged_in_user=None,
                             policy_object=None, client_ip=None):
        """
        This method returns a dictionary with default settings for token
        enrollment.
        These default settings depend on the token type and the defined
        policies.

        The returned dictionary is added to the parameters of the API call.
        :param params: The call parameters
        :type params: dict
        :param logged_in_user: The logged_in_user dictionary with "role",
            "username" and "realm"
        :type logged_in_user: dict
        :param policy_object: The policy_object
        :type policy_object: PolicyClass
        :return: default parameters
        """
        return {}

    def check_last_auth_newer(self, last_auth):
        """
        Check if the last successful authentication with the token is newer
        than the specified time delta which is passed as 10h, 7d or 1y.

        It returns True, if the last authentication with this token is
        **newer*** than the specified delta.

        :param last_auth: 10h, 7d or 1y
        :type last_auth: basestring
        :return: bool
        """
        # per default we return True
        res = True
        # The tdelta in the policy
        tdelta = parse_timedelta(last_auth)

        # The last successful authentication of the token
        date_s = self.get_tokeninfo(ACTION.LASTAUTH)
        if date_s:
            log.debug("Compare the last successful authentication of "
                      "token %s with policy "
                      "tdelta %s: %s" % (self.token.serial, tdelta,
                                         date_s))
            # parse the string from the database
            last_success_auth = parse_date_string(date_s)
            if not last_success_auth.tzinfo:
                # the date string has no timezone, default timezone is UTC
                # We need to reparse
                last_success_auth = parse_date_string(date_s,
                                                      tzinfos=tzutc)
            # The last auth is to far in the past
            if last_success_auth + tdelta < datetime.datetime.now(tzlocal()):
                res = False
                log.debug("The last successful authentication is too old: "
                          "{0!s}".format(last_success_auth))

        return res

    def generate_symmetric_key(self, server_component, client_component,
                               options=None):
        """
        This method generates a symmetric key, from a server component and a 
        client component. 
        This key generation could be based on HMAC, KDF or even Diffie-Hellman.
        
        The basic key-generation is simply replacing the last n byte of the 
        server component with bytes of the client component.
                
        :param server_component: The component usually generated by privacyIDEA
        :type server_component: hex string
        :param client_component: The component usually generated by the
            client (e.g. smartphone)
        :type server_component: hex string
        :param options: 
        :return: the new generated key as hex string
        """
        if len(server_component) <= len(client_component):
            raise Exception("The server component must be longer than the "
                            "client component.")

        key = server_component[:-len(client_component)] + client_component
        return key


