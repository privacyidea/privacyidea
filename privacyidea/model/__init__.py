# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel, info@privacyidea.org
#  http://www.privacyidea.org
#
#     2014-06-30    Cornelius Kölbel, added tables clientmachine,
#                                                clienttoken,
#                                                clientoptions
#
#     2014-08-01    Cornelius Kölbel, added table machinetoken, machineuser,
#                                                 and corresponding options
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
  Description:  This is part of the privacyidea service
                This file contains the database definition / database model

  Dependencies: -


'''


import binascii
import logging
import sys
import traceback

from datetime import datetime
from datetime import date

from json import loads, dumps


"""The application's model objects"""
import sqlalchemy as sa

from sqlalchemy import orm
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relation
from sqlalchemy import UniqueConstraint

from privacyidea.model import meta
from privacyidea.model.meta import Session
from privacyidea.lib.crypto import geturandom
from privacyidea.lib.crypto import encrypt, hash, SecretObj
from privacyidea.lib.crypto import encryptPin
from privacyidea.lib.crypto import decryptPin
from privacyidea.lib.crypto import get_rand_digit_str
from privacyidea.lib.log import log_with
log = logging.getLogger(__name__)

from pylons import config
implicit_returning = config.get('privacyideaSQL.implicit_returning', True)


@log_with(log)
def init_model(engine):
    """Call me before using any of the tables or classes in the model"""

    meta.Session.configure(bind=engine)
    meta.engine = engine


token_table = sa.Table('Token', meta.metadata,
                       sa.Column('privacyIDEATokenId', sa.types.Integer(),
                                 sa.Sequence('token_seq_id', optional=True),
                                 primary_key=True, nullable=False),
                       sa.Column('privacyIDEATokenDesc', sa.types.Unicode(80),
                                 default=u''),
                       sa.Column('privacyIDEATokenSerialnumber',
                                 sa.types.Unicode(40), default=u'',
                                 unique=True, nullable=False, index=True),
                       sa.Column('privacyIDEATokenType', sa.types.Unicode(30),
                                 default=u'HMAC', index=True),
                       sa.Column('privacyIDEATokenInfo',
                                 sa.types.Unicode(2000), default=u''),
                       sa.Column('privacyIDEATokenPinUser',
                                 sa.types.Unicode(512),
                                 default=u''),  # encrypt
                       sa.Column('privacyIDEATokenPinUserIV',
                                 sa.types.Unicode(32), default=u''),  # encrypt
                       sa.Column('privacyIDEATokenPinSO',
                                 sa.types.Unicode(512),
                                 default=u''),  # encrypt
                       sa.Column('privacyIDEATokenPinSOIV',
                                 sa.types.Unicode(32),
                                 default=u''),  # encrypt

                       sa.Column('privacyIDEAIdResolver',
                                 sa.types.Unicode(120), default=u'',
                                 index=True),
                       sa.Column('privacyIDEAIdResClass',
                                 sa.types.Unicode(120), default=u''),
                       sa.Column('privacyIDEAUserid',
                                 sa.types.Unicode(320),
                                 default=u'', index=True),
                       
                       sa.Column('privacyIDEASeed', sa.types.Unicode(32),
                                 default=u''),
                       sa.Column('privacyIDEAOtpLen', sa.types.Integer(),
                                 default=6),
                       sa.Column('privacyIDEAPinHash', sa.types.Unicode(512),
                                 default=u''),  # hashed
                       sa.Column('privacyIDEAKeyEnc', sa.types.Unicode(1024),
                                 default=u''),  # encrypt
                       sa.Column('privacyIDEAKeyIV', sa.types.Unicode(32),
                                 default=u''),

                       sa.Column('privacyIDEAMaxFail', sa.types.Integer(),
                                 default=10),
                       sa.Column('privacyIDEAIsactive', sa.types.Boolean(),
                                 default=True),
                       sa.Column('privacyIDEAFailCount', sa.types.Integer(),
                                 default=0),
                       sa.Column('privacyIDEACount', sa.types.Integer(),
                                 default=0),
                       sa.Column('privacyIDEACountWindow', sa.types.Integer(),
                                 default=10),
                       sa.Column('privacyIDEASyncWindow', sa.types.Integer(),
                                 default=1000),
                       implicit_returning=implicit_returning,
                       )


class Token(object):

    @log_with(log)
    def __init__(self, serial):

        # self.privacyIDEATokenId - will be generated DBType serial
        self.privacyIDEATokenSerialnumber = u'' + serial

        self.privacyIDEATokenType = u''

        self.privacyIDEACount = 0
        self.privacyIDEAFailCount = 0
        # get maxFail should have a configurable default
        self.privacyIDEAMaxFail = 10
        self.privacyIDEAIsactive = True
        self.privacyIDEACountWindow = 10
        self.privacyIDEAOtpLen = 6
        self.privacyIDEASeed = u''

        self.privacyIDEAIdResolver = None
        self.privacyIDEAIdResClass = None
        self.privacyIDEAUserid = None

        # will be assigned automaticaly
        # self.privacyIDEATokenId      = 0

    def _fix_spaces(self, data):
        '''
        On MS SQL server empty fields ("") like the privacyIDEATokenInfo
        are returned as a string with a space (" ").
        This functions helps fixing this.
        Also avoids running into errors, if the data is a None Type.

        :param data: a string from teh database
        :type data: usually a string
        :return: a stripped string
        '''
        if data:
            data = data.strip()

        return data

    def getSerial(self):
        return self.privacyIDEATokenSerialnumber

    @log_with(log)
    def setHKey(self, hOtpKey, reset_failcount=True):
        iv = geturandom(16)
        # bhOtpKey            = binascii.unhexlify(hOtpKey)
        enc_otp_key = encrypt(hOtpKey, iv)
        self.privacyIDEAKeyEnc = unicode(binascii.hexlify(enc_otp_key))
        self.privacyIDEAKeyIV = unicode(binascii.hexlify(iv))
        self.privacyIDEACount = 0
        if True == reset_failcount:
            self.privacyIDEAFailCount = 0

    @log_with(log)
    def setUserPin(self, userPin):
        iv = geturandom(16)
        enc_userPin = encrypt(userPin, iv)
        self.privacyIDEATokenPinUser = unicode(binascii.hexlify(enc_userPin))
        self.privacyIDEATokenPinUserIV = unicode(binascii.hexlify(iv))

    @log_with(log)
    def getHOtpKey(self):
        key = binascii.unhexlify(self.privacyIDEAKeyEnc)
        iv = binascii.unhexlify(self.privacyIDEAKeyIV)
        secret = SecretObj(key, iv)
        return secret

    @log_with(log)
    def getOtpCounter(self):
        return self.privacyIDEACount

    @log_with(log)
    def getUserPin(self):
        pu = self.privacyIDEATokenPinUser
        if pu is None:
            pu = ''
        puiv = self.privacyIDEATokenPinUserIV
        if puiv is None:
            puiv = ''

        key = binascii.unhexlify(pu)
        iv = binascii.unhexlify(puiv)
        secret = SecretObj(key, iv)
        return secret

    def setHashedPin(self, pin):
        log.debug('setHashedPin()')
        seed = geturandom(16)
        self.privacyIDEASeed = unicode(binascii.hexlify(seed))
        self.privacyIDEAPinHash = unicode(binascii.hexlify(hash(pin, seed)))
        return self.privacyIDEAPinHash

    def getHashedPin(self, pin):
        # TODO: we could log the PIN here.
        log.debug('getHashedPin()')

        # calculate a hash from a pin
        # Fix for working with MS SQL servers
        # MS SQL servers sometimes return a '<space>' when the
        # column is empty: ''
        seed_str = self._fix_spaces(self.privacyIDEASeed)
        seed = binascii.unhexlify(seed_str)
        hPin = hash(pin, seed)
        log.debug("hPin: %s, pin: %s, seed: %s" % (binascii.hexlify(hPin),
                                                   pin,
                                                   self.privacyIDEASeed))
        return binascii.hexlify(hPin)
        
    @log_with(log)
    def setDescription(self, desc):
        if desc is None:
            desc = ""
        self.privacyIDEATokenDesc = unicode(desc)
        return self.privacyIDEATokenDesc

    @log_with(log)
    def setOtpLen(self, otplen):
        self.privacyIDEAOtpLen = int(otplen)

    def setPin(self, pin, hashed=True):
        # TODO: we could log the PIN here
        log.debug("setPin()")

        upin = ""
        if pin != "" and pin is not None:
            upin = pin
        if hashed is True:
            self.setHashedPin(upin)
            log.debug("setPin(HASH:%r)" % self.privacyIDEAPinHash)
        elif hashed is False:
            self.privacyIDEAPinHash = "@@" + encryptPin(upin)
            log.debug("setPin(ENCR:%r)" % self.privacyIDEAPinHash)
        return self.privacyIDEAPinHash

    def comparePin(self, pin):
        log.debug("entering comparePin")
        res = False

        # check for a valid input
        if pin is None:
            log.error("no valid PIN!")
            return res

        if (self.isPinEncrypted() is True):
            log.debug("we got an encrypted PIN!")
            tokenPin = self.privacyIDEAPinHash[2:]
            decryptTokenPin = decryptPin(tokenPin)
            if (decryptTokenPin == pin):
                res = True
        else:
            log.debug("we got a hashed PIN!")
            if len(self.privacyIDEAPinHash) > 0:
                mypHash = self.getHashedPin(pin)
            else:
                mypHash = pin
            if (mypHash == self.privacyIDEAPinHash):
                res = True

        return res

    @log_with(log)
    def deleteToken(self):
        # some DBs (eg. DB2) run in deadlock, if the TokenRealm entry
        # is deleteted via foreign key relation
        # so we delete it explicit
        Session.query(TokenRealm).filter(TokenRealm.token_id == self.privacyIDEATokenId).delete()
        Session.delete(self)
        return True

    def isPinEncrypted(self, pin=None):
        ret = False
        if pin is None:
            pin = self.privacyIDEAPinHash
        if (pin.startswith("@@") is True):
            ret = True
        return ret

    def getPin(self):
        ret = -1
        if self.isPinEncrypted() is True:
            tokenPin = self.privacyIDEAPinHash[2:]
            ret = decryptPin(tokenPin)
        return ret

    def setSoPin(self, soPin):
        # TODO: we could log the PIN here
        log.debug('setSoPin()')
        iv = geturandom(16)
        enc_soPin = encrypt(soPin, iv)
        self.privacyIDEATokenPinSO = unicode(binascii.hexlify(enc_soPin))
        self.privacyIDEATokenPinSOIV = unicode(binascii.hexlify(iv))

    def __unicode__(self):
        return self.privacyIDEATokenDesc

    @log_with(log)
    def get(self, key=None, fallback=None, save=False):
        '''
        simulate the dict behaviour to make challenge processing
        easier, as this will have to deal as well with
        'dict only challenges'

        :param key: the attribute name - in case of key is not provided, a dict
                    of all class attributes are returned
        :param fallback: if the attribute is not found,
                         the fallback is returned
        :param save: in case of all attributes and save==True, the timestamp is
                     converted to a string representation
        '''
        if key is None:
            return self.get_vars(save=save)

        if hasattr(self, key):
            kMethod = "get" + key.capitalize()
            if hasattr(self, kMethod):
                return getattr(self, kMethod)()
            else:
                return getattr(self, key)
        else:
            return fallback

    @log_with(log)
    def get_vars(self, save=False):
        log.debug('get_vars()')

        ret = {}
        ret['privacyIDEA.TokenId'] = self.privacyIDEATokenId
        ret['privacyIDEA.TokenDesc'] = self.privacyIDEATokenDesc
        ret['privacyIDEA.TokenSerialnumber'] = self.privacyIDEATokenSerialnumber

        ret['privacyIDEA.TokenType'] = self.privacyIDEATokenType
        ret['privacyIDEA.TokenInfo'] = self._fix_spaces(self.privacyIDEATokenInfo)
        # ret['privacyIDEATokenPinUser']   = self.privacyIDEATokenPinUser
        # ret['privacyIDEATokenPinSO']     = self.privacyIDEATokenPinSO

        ret['privacyIDEA.IdResolver'] = self.privacyIDEAIdResolver
        ret['privacyIDEA.IdResClass'] = self.privacyIDEAIdResClass
        ret['privacyIDEA.Userid'] = self.privacyIDEAUserid
        ret['privacyIDEA.OtpLen'] = self.privacyIDEAOtpLen
        # ret['privacyIDEA.PinHash']        = self.privacyIDEAPinHash

        ret['privacyIDEA.MaxFail'] = self.privacyIDEAMaxFail
        ret['privacyIDEA.Isactive'] = self.privacyIDEAIsactive
        ret['privacyIDEA.FailCount'] = self.privacyIDEAFailCount
        ret['privacyIDEA.Count'] = self.privacyIDEACount
        ret['privacyIDEA.CountWindow'] = self.privacyIDEACountWindow
        ret['privacyIDEA.SyncWindow'] = self.privacyIDEASyncWindow

        # list of Realm names
        ret['privacyIDEA.RealmNames'] = self.getRealmNames()

        return ret

    __str__ = __unicode__

    def __repr__(self):
        '''
        return the token state as text

        :return: token state as string representation
        :rtype:  string
        '''
        ldict = {}
        for attr in self.__dict__:
            key = "%r" % attr
            val = "%r" % getattr(self, attr)
            ldict[key] = val
        res = "<%r %r>" % (self.__class__, ldict)
        return res

    def getSyncWindow(self):
        return self.privacyIDEASyncWindow

    def setCountWindow(self, counter):
        self.privacyIDEACountWindow = counter

    def getCountWindow(self):
        return self.privacyIDEACountWindow

    def getInfo(self):
        # Fix for working with MS SQL servers
        # MS SQL servers sometimes return a '<space>' when
        # the column is empty: ''
        return self._fix_spaces(self.privacyIDEATokenInfo)

    def setInfo(self, info):
        self.privacyIDEATokenInfo = info

    def _setPin(self, pin, hashed=True):
        log.debug("_setPin(%s)" % pin)
        if pin is None or pin == "":
            log.debug("Token pin was None")
        else:
            self.setPin(pin, hashed)

    @log_with(log)
    def storeToken(self):
        Session.add(self)
        Session.flush()
        Session.commit()
        return True

    def setType(self, typ):
        self.privacyIDEATokenType = typ
        return

    def getType(self):
        return self.privacyIDEATokenType

    def updateType(self, typ):
        # in case the prevoius has been different type
        # we must reset the counters
        # But be aware, ray, this could also be upper and lower case mixing...
        if self.privacyIDEATokenType.lower() != typ.lower():
            self.privacyIDEACount = 0
            self.privacyIDEAFailCount = 0

        self.privacyIDEATokenType = typ
        return

    def updateOtpKey(self, otpKey):
        # in case of a new hOtpKey we have to do some more things
        if (otpKey is not None):
            secretObj = self.getHOtpKey()
            if secretObj.compare(otpKey) is False:
                log.debug('update token OtpKey - counter reset')
                self.setHKey(otpKey)

    def updateToken(self, tokenDesc, otpKey, pin):
        log.debug('updateToken()')
        self.setDescription(tokenDesc)
        self._setPin(pin)
        self.updateOtpKey(otpKey)

    def getRealms(self):
        return self.realms

    def getRealmNames(self):
        r_list = []
        for r in self.realms:
            r_list.append(r.name)
        return r_list

    def addRealm(self, realm):
        if realm is not None:
            self.realms.append(realm)
        else:
            log.error("adding empty realm!")

    def setRealms(self, realms):
        if realms is not None:
            self.realms = realms
        else:
            log.error("assigning empty realm!")


@log_with(log)
def createToken(serial):
    serial = u'' + serial
    token = Token(serial)
    return token


config_table = sa.Table('Config', meta.metadata,
                        sa.Column('Key', sa.types.Unicode(255),
                                  primary_key=True, nullable=False),
                        sa.Column('Value', sa.types.Unicode(2000),
                                  default=u''),
                        sa.Column('Type', sa.types.Unicode(2000),
                                  default=u''),
                        sa.Column('Description', sa.types.Unicode(2000),
                                  default=u''),
                        implicit_returning=implicit_returning,
                        )

log.debug('config table append_column')


class Config(object):
    
    @log_with(log)
    def __init__(self, Key, Value, Type=u'', Description=u''):
        if (not Key.startswith("privacyidea.") and
                not Key.startswith("encprivacyidea.")):
            Key = "privacyidea." + Key

        self.Key = unicode(Key)
        self.Value = unicode(Value)
        self.Type = unicode(Type)
        self.Description = unicode(Description)

    def __unicode__(self):
        return self.Description

    __str__ = __unicode__


# This table connect a token to several realms
tokenrealm_table = sa.Table('TokenRealm', meta.metadata,
                            sa.Column('id', sa.types.Integer(),
                                      sa.Sequence('tokenrealm_seq_id',
                                                  optional=True),
                                      primary_key=True,
                                      nullable=False),
                            sa.Column('token_id', sa.types.Integer(),
                                      ForeignKey('Token.privacyIDEATokenId')),
                            sa.Column('realm_id', sa.types.Integer(),
                                      ForeignKey('Realm.id')),
                            implicit_returning=implicit_returning,
                            )


class TokenRealm(object):

    def __init__(self, realmid):
        log.debug("setting realm_id to %i" % realmid)
        self.realm_id = realmid
        self.token_id = 0


realm_table = sa.Table('Realm', meta.metadata,
                       sa.Column('id', sa.types.Integer(),
                                 sa.Sequence('realm_seq_id', optional=True),
                                 primary_key=True, nullable=False),
                       sa.Column('name', sa.types.Unicode(255), default=u'',
                                 unique=True, nullable=False),
                       sa.Column('default', sa.types.Boolean(), default=False),
                       sa.Column('option', sa.types.Unicode(40), default=u''),
                       implicit_returning=implicit_returning,
                       )


class Realm(object):
    
    @log_with(log)
    def __init__(self, realm):
        self.name = realm
        # self.id     = 0

    @log_with(log)
    def storeRealm(self):
        Session.add(self)
        Session.commit()
        return True


''' ''' '''
ocra challenges are stored
''' ''' '''

log.debug('creating ocra table')

ocra_table = sa.Table('ocra', meta.metadata,
                      sa.Column('id', sa.types.Integer(),
                                sa.Sequence('ocra_seq_id', optional=True),
                                primary_key=True, nullable=False),
                      sa.Column('transid', sa.types.Unicode(20), unique=True,
                                nullable=False, index=True),
                      sa.Column('data', sa.types.Unicode(512),
                                default=u''),
                      sa.Column('challenge', sa.types.Unicode(256),
                                default=u''),
                      sa.Column('session', sa.types.Unicode(512),
                                default=u''),
                      sa.Column('tokenserial', sa.types.Unicode(64),
                                default=u''),
                      sa.Column('timestamp', sa.types.DateTime,
                                default=datetime.now()),
                      sa.Column('received_count', sa.types.Integer(),
                                default=0),
                      sa.Column('received_tan', sa.types.Boolean,
                                default=False),
                      sa.Column('valid_tan', sa.types.Boolean,
                                default=False),
                      implicit_returning=implicit_returning,
                      )


class OcraChallenge(object):
    '''
    '''
    @log_with(log)
    def __init__(self, transId, challenge, tokenserial, data, session=u''):
        
        self.transid = u'' + transId
        self.challenge = u'' + challenge
        self.tokenserial = u'' + tokenserial
        self.data = u'' + data
        self.timestamp = datetime.now()
        self.session = u'' + session
        self.received_count = 0
        self.received_tan = False
        self.valid_tan = False

    def setData(self, data):
        self.data = unicode(data)

    def getData(self):
        return self.data

    def getSession(self):
        return self.session

    def setSession(self, session):
        self.session = unicode(session)

    def setChallenge(self, challenge):
        self.challenge = unicode(challenge)

    def setTanStatus(self, received=False, valid=False):
        self.received_tan = received
        self.received_count += 1
        self.valid_tan = valid

    def getTanStatus(self):
        return (self.received_tan, self.valid_tan)

    def getChallenge(self):
        return self.challenge

    def getTransactionId(self):
        return self.transid

    @log_with(log)
    def save(self):
        Session.add(self)
        Session.commit()
        return self.transid

    def __unicode__(self):
        descr = {}
        descr['id'] = self.id
        descr['transid'] = self.transid
        descr['challenge'] = self.challenge
        descr['tokenserial'] = self.tokenserial
        descr['data'] = self.data
        descr['timestamp'] = self.timestamp
        descr['received_tan'] = self.received_tan
        descr['valid_tan'] = self.valid_tan

        return "%s" % unicode(descr)

    __str__ = __unicode__


''' ''' '''
challenges are stored
''' ''' '''

log.debug('creating challenges table')

challenges_table = sa.Table('challenges', meta.metadata,
                            sa.Column('id', sa.types.Integer(),
                                      sa.Sequence('challenges_seq_id',
                                                  optional=True),
                                      primary_key=True, nullable=False),
                            sa.Column('transid', sa.types.Unicode(64),
                                      unique=True, nullable=False,
                                      index=True),
                            sa.Column('data', sa.types.Unicode(512),
                                      default=u''),
                            sa.Column('challenge', sa.types.Unicode(512),
                                      default=u''),
                            sa.Column('session', sa.types.Unicode(512),
                                      default=u''),
                            sa.Column('tokenserial', sa.types.Unicode(64),
                                      default=u''),
                            sa.Column('timestamp', sa.types.DateTime,
                                      default=datetime.now()),
                            sa.Column('received_count', sa.types.Integer(),
                                      default=0),
                            sa.Column('received_tan', sa.types.Boolean,
                                      default=False),
                            sa.Column('valid_tan', sa.types.Boolean,
                                      default=False),
                            implicit_returning=implicit_returning,
                            )


class Challenge(object):
    '''
    the generic challenge handling
    '''
    @log_with(log)
    def __init__(self, transid, tokenserial,
                 challenge=u'', data=u'', session=u''):

        self.transid = u'' + transid
        self.challenge = u'' + challenge
        self.tokenserial = u'' + tokenserial
        self.data = u'' + data
        self.timestamp = datetime.now()
        self.session = u'' + session
        self.received_count = 0
        self.received_tan = False
        self.valid_tan = False

    @classmethod
    def createTransactionId(cls, length=20):
        return get_rand_digit_str(length)

    def setData(self, data):
        if type(data) in [dict, list]:
            self.data = dumps(data)
        else:
            self.data = unicode(data)

    def get(self, key=None, fallback=None, save=False):
        '''
        simulate the dict behaviour to make challenge processing
        easier, as this will have to deal as well with
        'dict only challenges'

        :param key: the attribute name - in case of key is not provided, a dict
                    of all class attributes are returned
        :param fallback: if the attribute is not found, the
                         fallback is returned
        :param save: in case of all attributes and save==True, the timestamp is
                     converted to a string representation
        '''
        if key is None:
            return self.get_vars(save=save)

        if hasattr(self, key):
            kMethod = "get" + key.capitalize()
            if hasattr(self, kMethod):
                return getattr(self, kMethod)()
            else:
                return getattr(self, key)
        else:
            return fallback

    def getId(self):
        return self.id

    def getData(self):
        data = {}
        try:
            data = loads(self.data)
        except:
            data = self.data
        return data

    def getSession(self):
        return self.session

    def setSession(self, session):
        self.session = unicode(session)

    def setChallenge(self, challenge):
        self.challenge = unicode(challenge)

    def setTanStatus(self, received=False, valid=False):
        self.received_tan = received
        self.received_count += 1
        self.valid_tan = valid

    def getTanStatus(self):
        return (self.received_tan, self.valid_tan)

    def getTanCount(self):
        return self.received_count

    def getChallenge(self):
        return self.challenge

    def getTransactionId(self):
        return self.transid

    def getTokenSerial(self):
        return self.tokenserial

    @log_with(log)
    def save(self):
        '''
        enforce the saveing of a challenge
        - will guarentee the uniqness of the transaction id

        :return: transaction id of the stored challeng
        '''
        try:
            Session.add(self)
            Session.commit()
            log.debug('save challenge : success')

        except Exception as exce:
            log.error('Error during saving challenge: %r' % exce)
            log.error("%s" % traceback.format_exc())

        return self.transid

    def get_vars(self, save=False):
        '''
        return a dictionary of all vars in the challenge class

        :return: dict of vars
        '''
        descr = {}
        descr['id'] = self.id
        descr['transid'] = self.transid
        descr['challenge'] = self.challenge
        descr['tokenserial'] = self.tokenserial
        descr['data'] = self.getData()
        if save is True:
            descr['timestamp'] = "%s" % self.timestamp
        else:
            descr['timestamp'] = self.timestamp
        descr['received_tan'] = self.received_tan
        descr['valid_tan'] = self.valid_tan
        return descr

    def __unicode__(self):
        descr = self.get_vars()
        return "%s" % unicode(descr)

    __str__ = __unicode__

#
# Client machine table
# This is the table that holds the definition of a client machine

clientmachine_table = sa.Table('ClientMachine', meta.metadata,
                               sa.Column('id', sa.types.Integer(),
                                         sa.Sequence('clientmachine_seq_id',
                                                     optional=True),
                                         primary_key=True, nullable=False),
                               sa.Column("cm_ip", sa.types.Unicode(64),
                                         sa.Sequence('clientmachine_seq_ip',
                                                     optional=True),
                                         unique=True, nullable=False),
                               sa.Column("cm_name", sa.types.Unicode(64),
                                         sa.Sequence('clientmachine_seq_name',
                                                     optional=True),
                                         unique=True, nullable=False),
                               sa.Column("cm_desc", sa.types.Unicode(128)),
                               sa.Column("cm_decommission", sa.types.DateTime),
                               UniqueConstraint('id', 'cm_ip',
                                                'cm_name', name='uix_2'),
                               implicit_returning=implicit_returning,
                               )


class Machine(object):
    
    @log_with(log)
    def __init__(self, name, ip=u'',
                 desc=u'',
                 decommission=None):
        '''
        Create a new Machine database object
        
        :param decommission: This is the date, when the machine should be
                             decommissioned. 2014-07-02
        :type decommission: string, date or datetime
        '''
        self.cm_ip = ip
        self.cm_name = name
        self.cm_desc = desc
        if type(decommission) in [date, datetime]:
            self.cm_decommission = decommission
        elif type(decommission) == str:
            # convert the string to datetime:
            self.cm_decommission = datetime.strptime(decommission, '%Y-%m-%d')

    @log_with(log)
    def store(self):
        Session.add(self)
        Session.commit()
        return True

    def to_json(self):
        return {'id': self.id,
                'ip': self.cm_ip,
                'name': self.cm_name,
                'desc': self.cm_desc,
                'decommission': str(self.cm_decommission)}
        

#
# The clienttoken table is the mapping which tokens belong to which client
#

machinetoken_table = sa.Table('MachineToken', meta.metadata,
                              sa.Column('id', sa.types.Integer(),
                                        sa.Sequence('machinetoken_seq_id',
                                                    optional=True),
                                        primary_key=True, nullable=False),
                              sa.Column("token_id", sa.types.Integer(),
                                        ForeignKey('Token.privacyIDEATokenId')),
                              sa.Column("machine_id", sa.types.Integer(),
                                        ForeignKey('ClientMachine.id')),
                              sa.Column("application", sa.types.Unicode(64)),
                              UniqueConstraint('token_id', 'machine_id',
                                               'application', name='uix_1'),
                              implicit_returning=implicit_returning,
                              )


class MachineToken(object):
    '''
    The MachineToken maps a token to a client and
    an application on this client
    
    The tuple of (machine, token, application) is unique.
    
    This can be an n:m mapping.
    '''

    @log_with(log)
    def __init__(self, machine_id, token_id, application):
        log.debug("setting machine_id to %r" % machine_id)
        self.machine_id = machine_id
        self.token_id = token_id
        self.application = application
        
    @log_with(log)
    def store(self):
        Session.add(self)
        Session.commit()
        return True
    
    def to_json(self):
        machinename = ""
        serial = ""
        ip = ""
        if self.token:
            serial = self.token.privacyIDEATokenSerialnumber
            is_active = self.token.privacyIDEAIsactive
        
        if self.machine:
            machinename = self.machine.cm_name
            ip = self.machine.cm_ip
        return {'id': self.id,
                'token_id': self.token_id,
                'serial': serial,
                'is_active': is_active,
                'machine_id': self.machine_id,
                'machinename': machinename,
                'ip': ip,
                'application': self.application}


machineuser_table = sa.Table('MachineUser', meta.metadata,
                             sa.Column('id', sa.types.Integer(),
                                       sa.Sequence('machineuser_seq_id',
                                                   optional=True),
                                       primary_key=True, nullable=False),
                             sa.Column('resolver', sa.types.Unicode(120),
                                       default=u'', index=True),
                             sa.Column('resclass', sa.types.Unicode(120),
                                       default=u''),
                             sa.Column('user_id', sa.types.Unicode(320),
                                       default=u'', index=True),
                             sa.Column("machine_id", sa.types.Integer(),
                                       ForeignKey('ClientMachine.id')),
                             sa.Column("application", sa.types.Unicode(64)),
                             UniqueConstraint('resolver', 'resclass',
                                              'user_id', 'machine_id',
                                              'application', name='uixu_1'),
                             implicit_returning=implicit_returning,
                             )
        
        
class MachineUser(object):
    '''
    The MachineUser maps a user to a client and
    an application on this client
    
    The tuple of (machine, USER, application) is unique.
    
    This can be an n:m mapping.
    '''

    @log_with(log)
    def __init__(self, machine_id,
                 resolver,
                 resclass,
                 user_id,
                 application):
        log.debug("setting machine_id to %r" % machine_id)
        self.machine_id = machine_id
        self.resolver = resolver
        self.resclass = resclass
        self.user_id = user_id
        self.application = application
        
    @log_with(log)
    def store(self):
        Session.add(self)
        Session.commit()
        return True
    
    def to_json(self):
        machinename = ""
        ip = ""
        if self.machine:
            machinename = self.machine.cm_name
            ip = self.machine.cm_ip
        return {'id': self.id,
                'user_id': self.user_id,
                'resolver': self.resolver,
                'resclass': self.resclass,
                'machine_id': self.machine_id,
                'machinename': machinename,
                'ip': ip,
                'application': self.application}


machine_t_options_table = sa.Table('MachineTokenOptions', meta.metadata,
                                   sa.Column('id', sa.types.Integer(),
                                             sa.Sequence('machinetokenoptions_seq_id', optional=True),
                                             primary_key=True, nullable=False),
                                   sa.Column('machinetoken_id',
                                             sa.types.Integer(),
                                             ForeignKey('MachineToken.id')),
                                   sa.Column('mt_key', sa.types.Unicode(64),
                                             nullable=False),
                                   sa.Column('mt_value', sa.types.Unicode(64),
                                             nullable=False),
                                   implicit_returning=implicit_returning)


class MachineTokenOptions(object):
    '''
    This class holds an Option for the token assigned to
    a certain client machine.
    Each Token-Clientmachine-Combination can have several
    options.
    '''
    
    def __init__(self, machinetoken_id, key, value):
        log.debug("setting %r to %r for MachineToken %s" % (key,
                                                            value,
                                                            machinetoken_id))
        self.machinetoken_id = machinetoken_id
        self.mt_key = key
        self.mt_value = value
        Session.add(self)
        Session.commit()


machine_u_options_table = sa.Table('MachineUserOptions', meta.metadata,
                                   sa.Column('id', sa.types.Integer(),
                                             sa.Sequence('machineuseroptions_seq_id', optional=True),
                                             primary_key=True,
                                             nullable=False),
                                   sa.Column('machineuser_id',
                                             sa.types.Integer(),
                                             ForeignKey('MachineUser.id')),
                                   sa.Column('mu_key', sa.types.Unicode(64),
                                             nullable=False),
                                   sa.Column('mu_value', sa.types.Unicode(64),
                                             nullable=False),
                                   implicit_returning=implicit_returning)


class MachineUserOptions(object):
    '''
    This class holds an Option for the Users assigned to
    a certain client machine.
    Each User-Clientmachine-Combination can have several
    options.
    '''
    
    def __init__(self, machineuser_id, key, value):
        log.debug("setting %r to %r for MachineUser %s" % (key,
                                                           value,
                                                           machineuser_id))
        self.machineuser_id = machineuser_id
        self.mu_key = key
        self.mu_value = value
        Session.add(self)
        Session.commit()


log.debug('calling ORM Mapper')


orm.mapper(Token, token_table, properties={
    'realms': relation(Realm, secondary=tokenrealm_table,
                       primaryjoin=token_table.c.privacyIDEATokenId == tokenrealm_table.c.token_id,
                       secondaryjoin=tokenrealm_table.c.realm_id == realm_table.c.id)
    })
orm.mapper(Realm, realm_table)
orm.mapper(TokenRealm, tokenrealm_table)
orm.mapper(Config, config_table)
orm.mapper(OcraChallenge, ocra_table)
orm.mapper(Challenge, challenges_table)

orm.mapper(Machine, clientmachine_table)
orm.mapper(MachineToken, machinetoken_table,
           properties={'token': relation(Token, 
                                         primaryjoin=token_table.c.privacyIDEATokenId == machinetoken_table.c.token_id),
                       'machine': relation(Machine,
                                           primaryjoin=clientmachine_table.c.id == machinetoken_table.c.machine_id),
                       'machine_t_options': relation(MachineTokenOptions,
                                                     primaryjoin=machinetoken_table.c.id == machine_t_options_table.c.machinetoken_id)
                       }) 
orm.mapper(MachineTokenOptions, machine_t_options_table)
# The MachineUser table is not connected with a non existing user table!
orm.mapper(MachineUser, machineuser_table,
           properties={'machine': relation(Machine,
                                           primaryjoin=clientmachine_table.c.id == machineuser_table.c.machine_id)})
