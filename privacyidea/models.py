# -*- coding: utf-8 -*-
#
#  2016-02-19 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add radiusserver table
#  2015-08-27 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add revocation of token
# Nov 11, 2014 Cornelius Kölbel, info@privacyidea.org
# http://www.privacyidea.org
#
# privacyIDEA is a fork of LinOTP. This model definition
# is based on the LinOTP model.
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
import binascii
import logging
from datetime import datetime
from datetime import timedelta
from json import loads, dumps
from flask.ext.sqlalchemy import SQLAlchemy
from .lib.crypto import (encrypt,
                         encryptPin,
                         decryptPin,
                         geturandom,
                         hash,
                         SecretObj,
                         get_rand_digit_str)

from sqlalchemy import and_
from .lib.log import log_with
log = logging.getLogger(__name__)

implicit_returning = True

db = SQLAlchemy()


class MethodsMixin(object):
    """
    This class mixes in some common Class table functions like
    delete and save
    """
    
    def save(self):
        db.session.add(self)
        db.session.commit()
        return self.id
    
    def delete(self):
        ret = self.id
        db.session.delete(self)
        db.session.commit()
        return ret


class Token(MethodsMixin, db.Model):
    """
    The table "token" contains the basic token data like
     * serial number
     * assigned user
     * secret key...
    while the table "tokeninfo" contains additional information that is specific
    to the tokentype.
    """
    __tablename__ = 'token'
    id = db.Column(db.Integer,
                   primary_key=True,
                   nullable=False)
    description = db.Column(db.Unicode(80), default=u'')
    serial = db.Column(db.Unicode(40), default=u'',
                       unique=True,
                       nullable=False,
                       index=True)
    tokentype = db.Column(db.Unicode(30),
                          default=u'HOTP',
                          index=True)
    user_pin = db.Column(db.Unicode(512),
                         default=u'')  # encrypt
    user_pin_iv = db.Column(db.Unicode(32),
                            default=u'')  # encrypt
    so_pin = db.Column(db.Unicode(512),
                       default=u'')  # encrypt
    so_pin_iv = db.Column(db.Unicode(32),
                          default=u'')  # encrypt
    resolver = db.Column(db.Unicode(120), default=u'',
                         index=True)
    resolver_type = db.Column(db.Unicode(120), default=u'')
    user_id = db.Column(db.Unicode(320),
                        default=u'', index=True)
    pin_seed = db.Column(db.Unicode(32),
                         default=u'')
    otplen = db.Column(db.Integer(),
                       default=6)
    pin_hash = db.Column(db.Unicode(512),
                         default=u'')  # hashed
    key_enc = db.Column(db.Unicode(1024),
                        default=u'')  # encrypt
    key_iv = db.Column(db.Unicode(32),
                       default=u'')
    maxfail = db.Column(db.Integer(),
                        default=10)
    active = db.Column(db.Boolean(),
                       nullable=False,
                       default=True)
    revoked = db.Column(db.Boolean(),
                        default=False)
    locked = db.Column(db.Boolean(),
                       default=False)
    failcount = db.Column(db.Integer(),
                          default=0)
    count = db.Column(db.Integer(),
                      default=0)
    count_window = db.Column(db.Integer(),
                             default=10)
    sync_window = db.Column(db.Integer(),
                            default=1000)
    rollout_state = db.Column(db.Unicode(10),
                              default=u'')
    info = db.relationship('TokenInfo',
                           lazy='dynamic',
                           backref='info')
        
    def __init__(self, serial, tokentype=u"",
                 isactive=True, otplen=6,
                 otpkey=u"",
                 userid=None, resolver=None, realm=None,
                 **kwargs):
        super(Token, self).__init__(**kwargs)
        self.serial = u'' + serial
        self.tokentype = tokentype
        self.count = 0
        self.failcount = 0
        self.maxfail = 10
        self.active = isactive
        self.revoked = False
        self.locked = False
        self.count_window = 10
        self.otplen = otplen
        self.pin_seed = u""
        self.set_otpkey(otpkey)
        self.resolver = None
        self.resolver_type = None
        self.user_id = None
            
        # also create the user assignment
        if userid and resolver and realm:
            # get type of resolver
            res_type = Resolver.query.filter_by(name=resolver).first().rtype
            self.resolver = resolver
            self.resolver_type = res_type
            self.user_id = userid
            # We can not create the tokenrealm-connection, yet
            # since we need to token_id.
            token_id = self.save()
            realm_id = Realm.query.filter_by(name=realm).first().id
            tr = TokenRealm(realm_id=realm_id, token_id=token_id)
            if tr:
                db.session.add(tr)
                db.session.commit()
            
    @log_with(log)
    def delete(self):
        # some DBs (eg. DB2) run in deadlock, if the TokenRealm entry
        # is deleted via  key relation
        # so we delete it explicit
        ret = self.id
        db.session.query(TokenRealm)\
                  .filter(TokenRealm.token_id == self.id)\
                  .delete()
        db.session.query(TokenInfo)\
                  .filter(TokenInfo.token_id == self.id)\
                  .delete()
        db.session.delete(self)
        db.session.commit()
        return ret

    @staticmethod
    def _fix_spaces(data):
        """
        On MS SQL server empty fields ("") like the info
        are returned as a string with a space (" ").
        This functions helps fixing this.
        Also avoids running into errors, if the data is a None Type.

        :param data: a string from the database
        :type data: usually a string
        :return: a stripped string
        """
        if data:
            data = data.strip()

        return data

    @log_with(log)
    def set_otpkey(self, otpkey, reset_failcount=True):
        iv = geturandom(16)
        enc_otp_key = encrypt(otpkey, iv)
        self.key_enc = unicode(binascii.hexlify(enc_otp_key))
        length = len(self.key_enc)
        if length > Token.key_enc.property.columns[0].type.length:
            log.error("Key {0!s} exceeds database field {1:d}!".format(self.serial,
                                                             length))
        self.key_iv = unicode(binascii.hexlify(iv))
        self.count = 0
        if reset_failcount is True:
            self.failcount = 0

    def set_realms(self, realms):
        """
        Set the list of the realms.
        This is done by filling the tokenrealm table.
        :param realms: realms
        :type realms: list
        """
        # delete old TokenRealms
        db.session.query(TokenRealm)\
                  .filter(TokenRealm.token_id == self.id)\
                  .delete()
        # add new TokenRealms
        # We must not set the same realm more than once...
        # uniquify: realms -> set(realms)
        for realm in set(realms):
            Tr = TokenRealm(token_id=self.id,
                            realmname=realm)
            db.session.add(Tr)
        db.session.commit()
        
    def get_realms(self):
        """
        return a list of the assigned realms
        :return: realms
        :rtype: list
        """
        realms = []
        for tokenrealm in self.realm_list:
            realms.append(tokenrealm.realm.name)
        return realms

    @log_with(log)
    def set_user_pin(self, userPin):
        iv = geturandom(16)
        enc_userPin = encrypt(userPin, iv)
        self.user_pin = unicode(binascii.hexlify(enc_userPin))
        self.user_pin_iv = unicode(binascii.hexlify(iv))

    @log_with(log)
    def get_otpkey(self):
        key = binascii.unhexlify(self.key_enc)
        iv = binascii.unhexlify(self.key_iv)
        secret = SecretObj(key, iv)
        return secret

    @log_with(log)
    def get_user_pin(self):
        """
        return the userPin
        :rtype : the PIN as a secretObject
        """
        pu = self.user_pin or ''
        puiv = self.user_pin_iv or ''
        key = binascii.unhexlify(pu)
        iv = binascii.unhexlify(puiv)
        secret = SecretObj(key, iv)
        return secret

    def set_hashed_pin(self, pin):
        seed = geturandom(16)
        self.pin_seed = unicode(binascii.hexlify(seed))
        self.pin_hash = unicode(binascii.hexlify(hash(pin, seed)))
        return self.pin_hash

    def get_hashed_pin(self, pin):
        """
        calculate a hash from a pin
        Fix for working with MS SQL servers
        MS SQL servers sometimes return a '<space>' when the
        column is empty: ''
        """
        seed_str = self._fix_spaces(self.pin_seed)
        seed = binascii.unhexlify(seed_str)
        hPin = hash(pin, seed)
        log.debug("hPin: {0!s}, pin: {1!s}, seed: {2!s}".format(binascii.hexlify(hPin),
                                                   pin,
                                                   self.pin_seed))
        return binascii.hexlify(hPin)
    
    def check_hashed_pin(self, pin):
        hp = self.get_hashed_pin(pin)
        return hp == self.pin_hash
        
    @log_with(log)
    def set_description(self, desc):
        if desc is None:
            desc = ""
        self.description = unicode(desc)
        return self.description

    def set_pin(self, pin, hashed=True):
        """
        set the OTP pin in a hashed way
        """
        upin = ""
        if pin != "" and pin is not None:
            upin = pin
        if hashed is True:
            self.set_hashed_pin(upin)
            log.debug("setPin(HASH:{0!r})".format(self.pin_hash))
        elif hashed is False:
            self.pin_hash = "@@" + encryptPin(upin)
            log.debug("setPin(ENCR:{0!r})".format(self.pin_hash))
        return self.pin_hash

    def check_pin(self, pin):
        res = False
        # check for a valid input
        if pin is not None:
            if self.is_pin_encrypted() is True:
                log.debug("we got an encrypted PIN!")
                tokenPin = self.pin_hash[2:]
                decryptTokenPin = decryptPin(tokenPin)
                if (decryptTokenPin == pin):
                    res = True
            else:
                log.debug("we got a hashed PIN!")
                if self.pin_hash:
                    mypHash = self.get_hashed_pin(pin)
                else:
                    mypHash = pin
                if (mypHash == self.pin_hash):
                    res = True
    
        return res

    def split_pin_pass(self, passwd, prepend=True):
        """
        The password is split into the PIN and the OTP component.
        THe token knows its length, so it can split accordingly.

        :param passwd: The password that is to be split
        :param prepend: The PIN is put in front of the OTP value
        :return: tuple of (res, pin, otpval)
        """
        if prepend:
            pin = passwd[:-self.otplen]
            otp = passwd[-self.otplen:]
        else:
            otp = passwd[:self.otplen]
            pin = passwd[self.otplen:]
        return(True, pin, otp)

    def is_pin_encrypted(self, pin=None):
        ret = False
        if pin is None:
            pin = self.pin_hash
        if (pin.startswith("@@") is True):
            ret = True
        return ret

    def get_pin(self):
        ret = -1
        if self.is_pin_encrypted() is True:
            tokenPin = self.pin_hash[2:]
            ret = decryptPin(tokenPin)
        return ret

    def set_so_pin(self, soPin):
        """
        For smartcards this sets the security officer pin of the token
        
        :rtype : None
        """
        iv = geturandom(16)
        enc_soPin = encrypt(soPin, iv)
        self.so_pin = unicode(binascii.hexlify(enc_soPin))
        self.so_pin_iv = unicode(binascii.hexlify(iv))
        return (self.so_pin, self.so_pin_iv)

    def __unicode__(self):
        return self.serial

    @log_with(log)
    def get(self, key=None, fallback=None, save=False):
        """
        simulate the dict behaviour to make challenge processing
        easier, as this will have to deal as well with
        'dict only challenges'

        :param key: the attribute name - in case of key is not provided, a dict
                    of all class attributes are returned
        :param fallback: if the attribute is not found,
                         the fallback is returned
        :param save: in case of all attributes and save==True, the timestamp is
                     converted to a string representation
        """
        if key is None:
            return self.get_vars(save=save)

        if hasattr(self, key):
            return getattr(self, key)
        else:
            return fallback
    
    @log_with(log)
    def get_vars(self, save=False):
        log.debug('get_vars()')

        ret = {}
        ret['id'] = self.id
        ret['description'] = self.description
        ret['serial'] = self.serial
        ret['tokentype'] = self.tokentype
        ret['info'] = self.get_info()

        ret['resolver'] = self.resolver
        ret['resolver_type'] = self.resolver_type
        ret['user_id'] = self.user_id
        ret['otplen'] = self.otplen

        ret['maxfail'] = self.maxfail
        ret['active'] = self.active
        ret['revoked'] = self.revoked
        ret['locked'] = self.locked
        ret['failcount'] = self.failcount
        ret['count'] = self.count
        ret['count_window'] = self.count_window
        ret['sync_window'] = self.sync_window
        # list of Realm names
        realm_list = []
        for realm_entry in self.realm_list:
            realm_list.append(realm_entry.realm.name)
        ret['realms'] = realm_list
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
            key = "{0!r}".format(attr)
            val = "{0!r}".format(getattr(self, attr))
            ldict[key] = val
        res = "<{0!r} {1!r}>".format(self.__class__, ldict)
        return res

    def set_info(self, info):
        """
        Set the additional token info for this token

        Entries that end with ".type" are used as type for the keys.
        I.e. two entries sshkey="XYZ" and sshkey.type="password" will store
        the key sshkey as type "password".

        :param info: The key-values to set for this token
        :type info: dict
        """
        if not self.id:
            # If there is no ID to reference the token, we need to save the
            # token
            self.save()
        types = {}
        for k, v in info.items():
            if k.endswith(".type"):
                types[".".join(k.split(".")[:-1])] = v
        for k, v in info.items():
            if not k.endswith(".type"):
                TokenInfo(self.id, k, v,
                          Type=types.get(k)).save()

    def del_info(self, key=None):
        """
        Deletes tokeninfo for a given token.
        If the key is omitted, all Tokeninfo is deleted.

        :param key: searches for the given key to delete the entry
        :return:
        """
        if key:
            tokeninfos = TokenInfo.query.filter_by(token_id=self.id, Key=key)
        else:
            tokeninfos = TokenInfo.query.filter_by(token_id=self.id)
        for ti in tokeninfos:
            ti.delete()

    def get_info(self):
        """

        :return: The token info as dictionary
        """
        ret = {}
        tokeninfos = TokenInfo.query.filter_by(token_id=self.id)
        for ti in tokeninfos:
            if ti.Type:
                ret[ti.Key + ".type"] = ti.Type
            ret[ti.Key] = ti.Value
        return ret

    def update_type(self, typ):
        """
        in case the previous has been different type
        we must reset the counters
        But be aware, ray, this could also be upper and lower case mixing...
        """
        if self.tokentype.lower() != typ.lower():
            self.count = 0
            self.failcount = 0

        self.tokentype = typ
        return

    def update_otpkey(self, otpkey):
        """
        in case of a new hOtpKey we have to do some more things
        """
        if otpkey is not None:
            secretObj = self.get_otpkey()
            if secretObj.compare(otpkey) is False:
                log.debug('update token OtpKey - counter reset')
                self.set_otpkey(otpkey)

    def update_token(self, description=None, otpkey=None, pin=None):
        if description is not None:
            self.set_description(description)
        if pin is not None:
            self.set_pin(pin)
        if otpkey is not None:
            self.update_otpkey(otpkey)


class TokenInfo(MethodsMixin, db.Model):
    """
    The table "tokeninfo" is used to store additional, long information that
    is specific to the tokentype.
    E.g. the tokentype "TOTP" has additional entries in the tokeninfo table
    for "timeStep" and "timeWindow", which are stored in the
    column "Key" and "Value".

    The tokeninfo is reference by the foreign key to the "token" table.
    """
    __tablename__ = 'tokeninfo'
    id = db.Column(db.Integer, primary_key=True)
    Key = db.Column(db.Unicode(255),
                    nullable=False)
    Value = db.Column(db.UnicodeText(), default=u'')
    Type = db.Column(db.Unicode(100), default=u'')
    Description = db.Column(db.Unicode(2000), default=u'')
    token_id = db.Column(db.Integer(),
                         db.ForeignKey('token.id'), index=True)
    token = db.relationship('Token',
                            lazy='joined',
                            backref='info_list')
    __table_args__ = (db.UniqueConstraint('token_id',
                                          'Key',
                                          name='tiix_2'), {})

    def __init__(self, token_id, Key, Value,
                 Type= None,
                 Description=None):
        """
        Create a new tokeninfo for a given token_id
        """
        self.token_id = token_id
        self.Key = Key
        self.Value = Value
        self.Type = Type
        self.Description = Description

    def save(self):
        ti = TokenInfo.query.filter_by(token_id=self.token_id,
                                           Key=self.Key).first()
        if ti is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            TokenInfo.query.filter_by(token_id=self.token_id,
                                           Key=self.Key
                                           ).update({'Value': self.Value,
                                                     'Descrip'
                                                     'tion': self.Description,
                                                     'Type': self.Type})
            ret = ti.id
        db.session.commit()
        return ret


class Admin(db.Model):
    """
    The administrators for managing the system.
    To manage the administrators use the command pi-manage.

    In addition certain realms can be defined to be administrative realms.

    :param username: The username of the admin
    :type username: basestring
    :param password: The password of the admin (stored using PBKDF2,
       salt and pepper)
    :type password: basestring
    :param email: The email address of the admin (not used at the moment)
    :type email: basestring
    """
    __tablename__ = "admin"
    username = db.Column(db.Unicode(120),
                         primary_key=True,
                         nullable=False)
    password = db.Column(db.Unicode(255))
    email = db.Column(db.Unicode(255))

    def save(self):
        c = Admin.query.filter_by(username=self.username).first()
        if c is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.username
        else:
            # update
            update_dict = {}
            if self.email:
                update_dict["email"] = self.email
            if self.password:
                update_dict["password"] = self.password
            Admin.query.filter_by(username=self.username)\
                .update(update_dict)
            ret = c.username
        db.session.commit()
        return ret

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class Config(db.Model):
    """
    The config table holds all the system configuration in key value pairs.

    Additional configuration for realms, resolvers and machine resolvers is
    stored in specific tables.
    """
    __tablename__ = "config"
    Key = db.Column(db.Unicode(255),
                    primary_key=True,
                    nullable=False)
    Value = db.Column(db.Unicode(2000), default=u'')
    Type = db.Column(db.Unicode(2000), default=u'')
    Description = db.Column(db.Unicode(2000), default=u'')

    @log_with(log)
    def __init__(self, Key, Value, Type=u'', Description=u''):
        self.Key = unicode(Key)
        self.Value = unicode(Value)
        self.Type = unicode(Type)
        self.Description = unicode(Description)

    def __unicode__(self):
        return "<{0!s} ({1!s})>".format(self.Key, self.Type)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
        return self.Key
    
    def delete(self):
        ret = self.Key
        db.session.delete(self)
        db.session.commit()
        return ret


class Realm(MethodsMixin, db.Model):
    """
    The realm table contains the defined realms. User Resolvers can be
    grouped to realms. This very table contains just contains the names of
    the realms. The linking to resolvers is stored in the table "resolverrealm".
    """
    __tablename__ = 'realm'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.Unicode(255), default=u'',
                     unique=True, nullable=False)
    default = db.Column(db.Boolean(), default=False)
    option = db.Column(db.Unicode(40), default=u'')
    
    @log_with(log)
    def __init__(self, realm):
        self.name = realm
        
    def delete(self):
        ret = self.id
        # delete all TokenRealm
        db.session.query(TokenRealm)\
                  .filter(TokenRealm.realm_id == ret)\
                  .delete()
        # delete all ResolverRealms
        db.session.query(ResolverRealm)\
                  .filter(ResolverRealm.realm_id == ret)\
                  .delete()
        # delete the token
        db.session.delete(self)
        db.session.commit()
        return ret


class CAConnector(MethodsMixin, db.Model):
    """
    The table "caconnector" contains the names and types of the defined
    CA connectors. Each connector has a different configuration, that is
    stored in the table "caconnectorconfig".
    """
    __tablename__ = 'caconnector'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.Unicode(255), default=u"",
                     unique=True, nullable=False)
    catype = db.Column(db.Unicode(255), default=u"",
                      nullable=False)
    caconfig = db.relationship('CAConnectorConfig',
                               lazy='dynamic',
                               backref='caconnector')

    def __init__(self, name, catype):
        self.name = name
        self.catype = catype

    def delete(self):
        ret = self.id
        db.session.delete(self)
        # delete all CAConnectorConfig
        # FIXME: Sometimes not all entries are deleted.
        db.session.query(CAConnectorConfig)\
                  .filter(CAConnectorConfig.caconnector_id == ret)\
                  .delete()
        db.session.commit()
        return ret


class CAConnectorConfig(db.Model):
    """
    Each CAConnector can have multiple configuration entries.
    Each CA Connector type can have different required config values. Therefor
    the configuration is stored in simple key/value pairs. If the type of a
    config entry is set to "password" the value of this config entry is stored
    encrypted.

    The config entries are referenced by the id of the resolver.
    """
    __tablename__ = 'caconnectorconfig'
    id = db.Column(db.Integer, primary_key=True)
    caconnector_id = db.Column(db.Integer,
                            db.ForeignKey('caconnector.id'))
    Key = db.Column(db.Unicode(255), nullable=False)
    Value = db.Column(db.Unicode(2000), default=u'')
    Type = db.Column(db.Unicode(2000), default=u'')
    Description = db.Column(db.Unicode(2000), default=u'')
    cacon = db.relationship('CAConnector',
                            lazy='joined',
                            backref='config_list')
    __table_args__ = (db.UniqueConstraint('caconnector_id',
                                          'Key',
                                          name='ccix_2'), {})

    def __init__(self, caconnector_id=None,
                 Key=None, Value=None,
                 caconnector=None,
                 Type="", Description=""):
        if caconnector_id:
            self.caconnector_id = caconnector_id
        elif caconnector:
            self.caconnector_id = CAConnector.query\
                                       .filter_by(name=caconnector)\
                                       .first()\
                                       .id
        self.Key = Key
        self.Value = Value
        self.Type = Type
        self.Description = Description

    def save(self):
        c = CAConnectorConfig.query.filter_by(caconnector_id=self.caconnector_id,
                                           Key=self.Key).first()
        if c is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            CAConnectorConfig.query.filter_by(caconnector_id=self.caconnector_id,
                                           Key=self.Key
                                           ).update({'Value': self.Value,
                                                     'Type': self.Type,
                                                     'Descrip'
                                                     'tion': self.Description})
            ret = c.id
        db.session.commit()
        return ret


class Resolver(MethodsMixin, db.Model):
    """
    The table "resolver" contains the names and types of the defined User
    Resolvers. As each Resolver can have different required config values the
    configuration of the resolvers is stored in the table "resolverconfig".
    """
    __tablename__ = 'resolver'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.Unicode(255), default=u"",
                     unique=True, nullable=False)
    rtype = db.Column(db.Unicode(255), default=u"",
                      nullable=False)
    rconfig = db.relationship('ResolverConfig',
                              lazy='dynamic',
                              backref='resolver')
    
    def __init__(self, name, rtype):
        self.name = name
        self.rtype = rtype
        
    def delete(self):
        ret = self.id
        db.session.delete(self)
        # delete all ResolverConfig
        db.session.query(ResolverConfig)\
                  .filter(ResolverConfig.resolver_id == ret)\
                  .delete()
        db.session.commit()
        return ret


class ResolverConfig(db.Model):
    """
    Each Resolver can have multiple configuration entries.
    Each Resolver type can have different required config values. Therefor
    the configuration is stored in simple key/value pairs. If the type of a
    config entry is set to "password" the value of this config entry is stored
    encrypted.

    The config entries are referenced by the id of the resolver.
    """
    __tablename__ = 'resolverconfig'
    id = db.Column(db.Integer, primary_key=True)
    resolver_id = db.Column(db.Integer,
                            db.ForeignKey('resolver.id'))
    Key = db.Column(db.Unicode(255), nullable=False)
    Value = db.Column(db.Unicode(2000), default=u'')
    Type = db.Column(db.Unicode(2000), default=u'')
    Description = db.Column(db.Unicode(2000), default=u'')
    reso = db.relationship('Resolver',
                           lazy='joined',
                           backref='config_list')
    __table_args__ = (db.UniqueConstraint('resolver_id',
                                          'Key',
                                          name='rcix_2'), {})
    
    def __init__(self, resolver_id=None,
                 Key=None, Value=None,
                 resolver=None,
                 Type="", Description=""):
        if resolver_id:
            self.resolver_id = resolver_id
        elif resolver:
            self.resolver_id = Resolver.query\
                                       .filter_by(name=resolver)\
                                       .first()\
                                       .id
        self.Key = Key
        self.Value = Value
        self.Type = Type
        self.Description = Description

    def save(self):
        c = ResolverConfig.query.filter_by(resolver_id=self.resolver_id,
                                           Key=self.Key).first()
        if c is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            ResolverConfig.query.filter_by(resolver_id=self.resolver_id,
                                           Key=self.Key
                                           ).update({'Value': self.Value,
                                                     'Type': self.Type,
                                                     'Descrip'
                                                     'tion': self.Description})
            ret = c.id
        db.session.commit()
        return ret


class ResolverRealm(MethodsMixin, db.Model):
    """
    This table stores which Resolver is located in which realm
    This is a N:M relation
    """
    __tablename__ = 'resolverrealm'
    id = db.Column(db.Integer, primary_key=True)
    resolver_id = db.Column(db.Integer, db.ForeignKey("resolver.id"))
    realm_id = db.Column(db.Integer, db.ForeignKey("realm.id"))
    # If there are several resolvers in a realm, the priority is used the
    # find a user first in a resolver with a higher priority (i.e. lower number)
    priority = db.Column(db.Integer)
    # this will create a "realm_list" in the resolver object
    resolver = db.relationship(Resolver,
                               lazy="joined",
                               foreign_keys="ResolverRealm.resolver_id",
                               backref="realm_list")
    # this will create a "resolver list" in the realm object
    realm = db.relationship(Realm,
                            lazy="joined",
                            foreign_keys="ResolverRealm.realm_id",
                            backref="resolver_list")
    __table_args__ = (db.UniqueConstraint('resolver_id',
                                          'realm_id',
                                          name='rrix_2'), {})
    
    def __init__(self, resolver_id=None, realm_id=None,
                 resolver_name=None,
                 realm_name=None,
                 priority=None):
        self.resolver_id = None
        self.realm_id = None
        if priority:
            self.priority = priority
        if resolver_id:
            self.resolver_id = resolver_id
        elif resolver_name:
            self.resolver_id = Resolver.query\
                                       .filter_by(name=resolver_name)\
                                       .first().id
        if realm_id:
            self.realm_id = realm_id
        elif realm_name:
            self.realm_id = Realm.query\
                                 .filter_by(name=realm_name)\
                                 .first().id
    

class TokenRealm(MethodsMixin, db.Model):
    """
    This table stored to wich realms a token is assigned. A token is in the
    realm of the user it is assigned to. But a token can also be put into
    many additional realms.
    """
    __tablename__ = 'tokenrealm'
    id = db.Column(db.Integer(), primary_key=True, nullable=True)
    token_id = db.Column(db.Integer(),
                         db.ForeignKey('token.id'))
    realm_id = db.Column(db.Integer(),
                         db.ForeignKey('realm.id'))
    token = db.relationship('Token',
                            lazy='joined',
                            backref='realm_list')
    realm = db.relationship('Realm',
                            lazy='joined',
                            backref='token_list')
    __table_args__ = (db.UniqueConstraint('token_id',
                                          'realm_id',
                                          name='trix_2'), {})
                                      
    def __init__(self, realm_id=0, token_id=0, realmname=None):
        """
        Create a new TokenRealm entry.
        :param realm_id: The id of the realm
        :param token_id: The id of the token
        """
        log.debug("setting realm_id to {0:d}".format(realm_id))
        if realmname:
            r = Realm.query.filter_by(name=realmname).first()
            self.realm_id = r.id
        if realm_id:
            self.realm_id = realm_id
        self.token_id = token_id

    def save(self):
        """
        We only save this, if it does not exist, yet.
        """
        tr = TokenRealm.query.filter_by(realm_id=self.realm_id,
                                        token_id=self.token_id).first()
        if tr is None:
            # create a new one
            db.session.add(self)
            db.session.commit()

        ret = self.id
        return ret


class PasswordReset(MethodsMixin, db.Model):
    """
    Table for handling password resets.
    This table stores the recoverycodes sent to a given user

    The application should save the HASH of the recovery code. Just like the
    password for the Admins the appliaction shall salt and pepper the hash of
    the recoverycode. A database admin will not be able to inject a rogue
    recovery code.

    A user can get several recoverycodes.
    A recovery code has a validity period

    Optional: The email to which the recoverycode was sent, can be stored.
    """
    __tablename__ = "passwordreset"
    id = db.Column(db.Integer(), primary_key=True, nullable=False)
    recoverycode = db.Column(db.Unicode(255), nullable=False)
    username = db.Column(db.Unicode(64), nullable=False, index=True)
    realm = db.Column(db.Unicode(64), nullable=False, index=True)
    resolver = db.Column(db.Unicode(64))
    email = db.Column(db.Unicode(255))
    timestamp = db.Column(db.DateTime, default=datetime.now())
    expiration = db.Column(db.DateTime)

    @log_with(log)
    def __init__(self, recoverycode, username, realm, resolver="", email=None,
                 timestamp=None, expiration=None, expiration_seconds=3600):
        # The default expiration time is 60 minutes
        self.recoverycode = recoverycode
        self.username = username
        self.realm = realm
        self.resolver = resolver
        self.email = email
        self.timestamp = timestamp or datetime.now()
        self.expiration = expiration or datetime.now() + \
                                        timedelta(seconds=expiration_seconds)


class Challenge(MethodsMixin, db.Model):
    """
    Table for handling of the generic challenges.
    """
    __tablename__ = "challenge"
    id = db.Column(db.Integer(), primary_key=True, nullable=False)
    transaction_id = db.Column(db.Unicode(64), unique=True, nullable=False,
                               index=True)
    data = db.Column(db.Unicode(512), default=u'')
    challenge = db.Column(db.Unicode(512), default=u'')
    session = db.Column(db.Unicode(512), default=u'')
    # The token serial number
    serial = db.Column(db.Unicode(40), default=u'')
    timestamp = db.Column(db.DateTime, default=datetime.now())
    expiration = db.Column(db.DateTime)
    received_count = db.Column(db.Integer(), default=0)
    otp_valid = db.Column(db.Boolean, default=False)

    @log_with(log)
    def __init__(self, serial, transaction_id=None,
                 challenge=u'', data=u'', session=u'', validitytime=120):

        self.transaction_id = transaction_id or self.create_transaction_id()
        self.challenge = challenge
        self.serial = serial
        self.data = data
        self.timestamp = datetime.now()
        self.session = session
        self.received_count = 0
        self.otp_valid = False
        self.expiration = datetime.now() + timedelta(seconds=validitytime)

    @staticmethod
    def create_transaction_id(length=20):
        return get_rand_digit_str(length)

    def is_valid(self):
        """
        Returns true, if the expiration time has not passed, yet.
        :return: True if valid
        :rtype: bool
        """
        ret = False
        c_now = datetime.now()
        if c_now < self.expiration:
            ret = True
        return ret

    def set_data(self, data):
        """
        set the internal data of the challenge
        :param data: unicode data
        :type data: string, length 512
        """
        if type(data) in [dict, list]:
            self.data = dumps(data)
        else:
            self.data = unicode(data)

    def get_data(self):
        data = {}
        try:
            data = loads(self.data)
        except:
            data = self.data
        return data

    def get_session(self):
        return self.session

    def set_session(self, session):
        self.session = unicode(session)

    def set_challenge(self, challenge):
        self.challenge = unicode(challenge)
    
    def get_challenge(self):
        return self.challenge

    def set_otp_status(self, valid=False):
        self.received_count += 1
        self.otp_valid = valid

    def get_otp_status(self):
        """
        This returns how many OTPs were already received for this challenge.
        and if a valid OTP was received.

        :return: tuple of count and True/False
        :rtype: tuple
        """
        return self.received_count, self.otp_valid

    def get_transaction_id(self):
        return self.transaction_id

    def get(self, timestamp=False):
        """
        return a dictionary of all vars in the challenge class
        
        :param timestamp: if true, the timestamp will given in a readable
                          format
                          2014-11-29 21:56:43.057293
        :type timestamp: bool
        :return: dict of vars
        """
        descr = {}
        descr['id'] = self.id
        descr['transaction_id'] = self.transaction_id
        descr['challenge'] = self.challenge
        descr['serial'] = self.serial
        descr['data'] = self.get_data()
        if timestamp is True:
            descr['timestamp'] = "{0!s}".format(self.timestamp)
        else:
            descr['timestamp'] = self.timestamp
        descr['otp_received'] = self.received_count > 0
        descr['received_count'] = self.received_count
        descr['otp_valid'] = self.otp_valid
        descr['expiration'] = self.expiration
        return descr

    def __unicode__(self):
        descr = self.get()
        return "{0!s}".format(unicode(descr))

    __str__ = __unicode__


def cleanup_challenges():
    """
    Delete all challenges, that have expired.

    :return: None
    """
    c_now = datetime.now()
    Challenge.query.filter(Challenge.expiration < c_now).delete()
    db.session.commit()

# -----------------------------------------------------------------------------
#
# POLICY
#


class Policy(db.Model):
    """
    The policy table contains policy definitions which control
    the behaviour during
     * enrollment
     * authentication
     * authorization
     * administration
     * user actions
    """
    __tablename__ = "policy"
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column(db.Boolean, default=True)
    name = db.Column(db.Unicode(64), unique=True, nullable=False)
    scope = db.Column(db.Unicode(32), nullable=False)
    action = db.Column(db.Unicode(2000), default=u"")
    realm = db.Column(db.Unicode(256), default=u"")
    adminrealm = db.Column(db.Unicode(256), default=u"")
    resolver = db.Column(db.Unicode(256), default=u"")
    user = db.Column(db.Unicode(256), default=u"")
    client = db.Column(db.Unicode(256), default=u"")
    time = db.Column(db.Unicode(64), default=u"")
    condition = db.Column(db.Integer, default=0, nullable=False)
    
    def __init__(self, name,
                 active=True, scope="", action="", realm="", adminrealm="",
                 resolver="", user="", client="", time="", condition=0):
        if type(active) in [str, unicode]:
            if active.lower() in ["true", "1"]:
                active = True
            else:
                active = False
        self.name = name
        self.action = action
        self.scope = scope
        self.active = active
        self.realm = realm
        self.adminrealm = adminrealm
        self.resolver = resolver
        self.user = user
        self.client = client
        self.time = time
        self.condition = condition

    @staticmethod
    def _split_string(value):
        """
        Split the value at the "," and returns an array.
        If value is empty, it returns an empty array.
        The normal split would return an array with an empty string.

        :param value: The string to be splitted
        :type value: basestring
        :return: list
        """
        ret = [r.strip() for r in (value or "").split(",")]
        if ret == ['']:
            ret = []
        return ret

    def get(self, key=None):
        """
        Either returns the complete policy entry or a single value
        :param key: return the value for this key
        :type key: string
        :return: complete dict or single value
        :rytpe: dict or value
        """
        d = {"name": self.name,
             "active": self.active,
             "scope": self.scope,
             "realm": self._split_string(self.realm),
             "adminrealm": self._split_string(self.adminrealm),
             "resolver": self._split_string(self.resolver),
             "user": self._split_string(self.user),
             "client": self._split_string(self.client),
             "time": self.time,
             "condition": self.condition}
        action_list = [x.strip().split("=") for x in (self.action or "").split(
            ",")]
        action_dict = {}
        for a in action_list:
            if len(a) > 1:
                action_dict[a[0]] = a[1]
            else:
                action_dict[a[0]] = True
        d["action"] = action_dict
        if key:
            ret = d.get(key)
        else:
            ret = d
        return ret
    
    def save(self):
        p = Policy.query.filter_by(name=self.name).first()
        if p is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            update_param = {}
            if self.action is not None:
                update_param["action"] = self.action
            if self.scope is not None:
                update_param["scope"] = self.scope
            if self.realm is not None:
                update_param["realm"] = self.realm
            if self.adminrealm is not None:
                update_param["adminrealm"] = self.adminrealm
            if self.resolver is not None:
                update_param["resolver"] = self.resolver
            if self.user is not None:
                update_param["user"] = self.user
            if self.client is not None:
                update_param["client"] = self.client
            if self.time is not None:
                update_param["time"] = self.time
            update_param["active"] = self.active
            if self.condition is not None:
                update_param["condition"] = self.condition
            # update
            Policy.query.filter_by(name=self.name,
                                   ).update(update_param)
            ret = p.id
        db.session.commit()
        return ret

# ------------------------------------------------------------------
#
#  Machines
#

class MachineToken(MethodsMixin, db.Model):
    """
    The MachineToken assigns a Token and an application type to a
    machine.
    The Machine is represented as the tuple of machineresolver.id and the
    machine_id.
    The machine_id is defined by the machineresolver.

    This can be an n:m mapping.
    """
    __tablename__ = 'machinetoken'
    id = db.Column(db.Integer(), primary_key=True, nullable=False)
    token_id = db.Column(db.Integer(),
                         db.ForeignKey('token.id'))
    machineresolver_id = db.Column(db.Integer(), nullable=False)
    machine_id = db.Column(db.Unicode(255), nullable=False)
    application = db.Column(db.Unicode(64))
    # This connects the machine with the token and makes the machines visible
    # in the token as "machine_list".
    token = db.relationship('Token',
                            lazy='joined',
                            backref='machine_list')

    @log_with(log)
    def __init__(self, machineresolver_id=None,
                 machineresolver=None, machine_id=None, token_id=None,
                 serial=None, application=None):

        if machineresolver_id:
            self.machineresolver_id = machineresolver_id
        elif machineresolver:
            # determine the machineresolver_id:
            self.machineresolver_id = MachineResolver.query.filter(
                MachineResolver.name == machineresolver).first().id
        if token_id:
            self.token_id = token_id
        elif serial:
            # determine token_id
            self.token_id = Token.query.filter_by(serial=serial).first().id
        self.machine_id = machine_id
        self.application = application

"""
class MachineUser(db.Model):
    '''
    The MachineUser maps a user to a client and
    an application on this client
    
    The tuple of (machine, USER, application) is unique.
    
    This can be an n:m mapping.
    '''
    __tablename__ = "machineuser"
    id = db.Column(db.Integer(), primary_key=True, nullable=False)
    resolver = db.Column(db.Unicode(120), default=u'', index=True)
    resclass = db.Column(db.Unicode(120),  default=u'')
    user_id = db.Column(db.Unicode(120), default=u'', index=True)
    machine_id = db.Column(db.Integer(), 
                           db.ForeignKey('clientmachine.id'))
    application = db.Column(db.Unicode(64))
    
    __table_args__ = (db.UniqueConstraint('resolver', 'resclass',
                                          'user_id', 'machine_id',
                                          'application', name='uixu_1'),
                      {})
    
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
        db.session.add(self)
        db.session.commit()
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
"""


class MachineTokenOptions(db.Model):
    """
    This class holds an Option for the token assigned to
    a certain client machine.
    Each Token-Clientmachine-Combination can have several
    options.
    """
    __tablename__ = 'machinetokenoptions'
    id = db.Column(db.Integer(), primary_key=True, nullable=False)
    machinetoken_id = db.Column(db.Integer(),
                                db.ForeignKey('machinetoken.id'))
    mt_key = db.Column(db.Unicode(64), nullable=False)
    mt_value = db.Column(db.Unicode(64), nullable=False)
    # This connects the MachineTokenOption with the MachineToken and makes the
    # options visible in the MachineToken as "option_list".
    machinetoken = db.relationship('MachineToken',
                                   lazy='joined',
                                   backref='option_list')

    def __init__(self, machinetoken_id, key, value):
        log.debug("setting {0!r} to {1!r} for MachineToken {2!s}".format(key,
                                                            value,
                                                            machinetoken_id))
        self.machinetoken_id = machinetoken_id
        self.mt_key = key
        self.mt_value = value

        # if the combination machinetoken_id / mt_key already exist,
        # we need to update
        c = MachineTokenOptions.query.filter_by(
            machinetoken_id=self.machinetoken_id,
            mt_key=self.mt_key).first()
        if c is None:
            # create a new one
            db.session.add(self)
        else:
            # update
            MachineTokenOptions.query.filter_by(
                machinetoken_id=self.machinetoken_id,
                mt_key=self.mt_key).update({'mt_value': self.mt_value})
        db.session.commit()


"""
class MachineUserOptions(db.Model):
    '''
    This class holds an Option for the Users assigned to
    a certain client machine.
    Each User-Clientmachine-Combination can have several
    options.
    '''
    __tablename__ = 'machineuseroptions'
    id = db.Column(db.Integer(), primary_key=True, nullable=False)
    machineuser_id = db.Column(db.Integer(), db.ForeignKey('machineuser.id'))
    mu_key = db.Column(db.Unicode(64), nullable=False)
    mu_value = db.Column(db.Unicode(64), nullable=False)
    
    def __init__(self, machineuser_id, key, value):
        log.debug("setting %r to %r for MachineUser %s" % (key,
                                                           value,
                                                           machineuser_id))
        self.machineuser_id = machineuser_id
        self.mu_key = key
        self.mu_value = value
        db.session.add(self)
        db.session.commit()

"""


class EventHandler(MethodsMixin, db.Model):
    """
    This model holds the list of defined events and actions to this events.
    A handler module can be bound to an event with the corresponding
    condition and action.
    """
    __tablename__ = 'eventhandler'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    ordering = db.Column(db.Integer, nullable=False, default=0)
    # This is the name of the event in the code
    event = db.Column(db.Unicode(255), nullable=False)
    # This is the identifier of an event handler module
    handlermodule = db.Column(db.Unicode(255), nullable=False)
    condition = db.Column(db.Unicode(1024), default=u"")
    action = db.Column(db.Unicode(1024), default=u"")
    options = db.relationship('EventHandlerOption',
                              lazy='dynamic',
                              backref='eventhandler')

    def __init__(self, event, handlermodule, action, condition="",
                 ordering=0, options=None, id=None):
        self.odering = ordering
        self.event = event
        self.handlermodule = handlermodule
        self.condition = condition
        self.action = action
        if id == "":
            id = None
        self.id = id
        self.save()
        # add the options to the event handler
        options = options or {}
        for k, v in options.iteritems():
            EventHandlerOption(eventhandler_id=self.id, Key=k, Value=v).save()

    def save(self):
        if self.id is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
        else:
            # update
            EventHandler.query.filter_by(id=self.id).update({
                "ordering": self.ordering or 0,
                "event": self.event,
                "handlermodule": self.handlermodule,
                "condition": self.condition,
                "action": self.action
            })
            db.session.commit()
        return self.id

    def delete(self):
        ret = self.id
        db.session.delete(self)
        # delete all EventHandlerOptions
        db.session.query(EventHandlerOption) \
            .filter(EventHandlerOption.eventhandler_id == ret) \
            .delete()
        db.session.commit()
        return ret

    def get(self):
        """
        Return the serialized policy object including the options

        :return: complete dict
        :rytpe: dicte
        """
        d = {"handlermodule": self.handlermodule,
             "id": self.id,
             "ordering": self.ordering,
             "action": self.action,
             "condition": self.condition}
        event_list = [x.strip() for x in self.event.split(",")]
        d["event"] = event_list
        option_dict = {}
        for option in self.options:
            option_dict[option.Key] = option.Value
        d["options"] = option_dict
        return d


class EventHandlerOption(db.Model):
    """
    Each EventHandler entry can have additional options according to the
    handler module.
    """
    __tablename__ = 'eventhandleroption'
    id = db.Column(db.Integer, primary_key=True)
    eventhandler_id = db.Column(db.Integer,
                                db.ForeignKey('eventhandler.id'))
    Key = db.Column(db.Unicode(255), nullable=False)
    Value = db.Column(db.Unicode(2000), default=u'')
    Type = db.Column(db.Unicode(2000), default=u'')
    Description = db.Column(db.Unicode(2000), default=u'')
    evhdl = db.relationship('EventHandler',
                            lazy='joined',
                            backref='option_list')
    __table_args__ = (db.UniqueConstraint('eventhandler_id',
                                          'Key',
                                          name='ehoix_1'), {})

    def __init__(self, eventhandler_id, Key, Value, Type="", Description=""):
        self.eventhandler_id = eventhandler_id
        self.Key = Key
        self.Value = Value
        self.Type = Type
        self.Description = Description
        self.save()

    def save(self):
        eho = EventHandlerOption.query.filter_by(
            eventhandler_id=self.eventhandler_id, Key=self.Key).first()
        if eho is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            EventHandlerOption.query.filter_by(
                eventhandler_id=self.eventhandler_id, Key=self.Key) \
                .update({'Value': self.Value,
                         'Type': self.Type,
                         'Description': self.Description})
            ret = eho.id
        db.session.commit()
        return ret


class MachineResolver(MethodsMixin, db.Model):
    """
    This model holds the definition to the machinestore.
    Machines could be located in flat files, LDAP directory or in puppet
    services or other...

    The usual MachineResolver just holds a name and a type and a reference to
    its config
    """
    __tablename__ = 'machineresolver'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.Unicode(255), default=u"",
                     unique=True, nullable=False)
    rtype = db.Column(db.Unicode(255), default=u"",
                      nullable=False)
    rconfig = db.relationship('MachineResolverConfig',
                              lazy='dynamic',
                              backref='machineresolver')

    def __init__(self, name, rtype):
        self.name = name
        self.rtype = rtype

    def delete(self):
        ret = self.id
        db.session.delete(self)
        # delete all MachineResolverConfig
        db.session.query(MachineResolverConfig)\
                  .filter(MachineResolverConfig.resolver_id == ret)\
                  .delete()
        db.session.commit()
        return ret


class MachineResolverConfig(db.Model):
    """
    Each Machine Resolver can have multiple configuration entries.
    The config entries are referenced by the id of the machine resolver
    """
    __tablename__ = 'machineresolverconfig'
    id = db.Column(db.Integer, primary_key=True)
    resolver_id = db.Column(db.Integer,
                            db.ForeignKey('machineresolver.id'))
    Key = db.Column(db.Unicode(255), nullable=False)
    Value = db.Column(db.Unicode(2000), default=u'')
    Type = db.Column(db.Unicode(2000), default=u'')
    Description = db.Column(db.Unicode(2000), default=u'')
    reso = db.relationship('MachineResolver',
                           lazy='joined',
                           backref='config_list')
    __table_args__ = (db.UniqueConstraint('resolver_id',
                                          'Key',
                                          name='mrcix_2'), {})

    def __init__(self, resolver_id=None, Key=None, Value=None, resolver=None,
                 Type="", Description=""):
        if resolver_id:
            self.resolver_id = resolver_id
        elif resolver:
            self.resolver_id = MachineResolver.query\
                                .filter_by(name=resolver)\
                                .first()\
                                .id
        self.Key = Key
        self.Value = Value
        self.Type = Type
        self.Description = Description

    def save(self):
        c = MachineResolverConfig.query.filter_by(
            resolver_id=self.resolver_id, Key=self.Key).first()
        if c is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            MachineResolverConfig.query.filter_by(
                resolver_id=self.resolver_id, Key=self.Key)\
                .update({'Value': self.Value,
                         'Type': self.Type,
                         'Description': self.Description})
            ret = c.id
        db.session.commit()
        return ret


def get_token_id(serial):
    """
    Return the database token ID for a given serial number
    :param serial:
    :return: token ID
    :rtpye: int
    """
    token = Token.query.filter(Token.serial == serial).first()
    return token.id


def get_machineresolver_id(resolvername):
    """
    Return the database ID of the machine resolver
    :param resolvername:
    :return:
    """
    mr = MachineResolver.query.filter(MachineResolver.name ==
                                      resolvername).first()
    return mr.id


def get_machinetoken_id(machine_id, resolver_name, serial, application):
    """
    Returns the ID in the machinetoken table

    :param machine_id: The resolverdependent machine_id
    :type machine_id: basestring
    :param resolver_name: The name of the resolver
    :type resolver_name: basestring
    :param serial: the serial number of the token
    :type serial: basestring
    :param application: The application type
    :type application: basestring
    :return: The ID of the machinetoken entry
    :rtype: int
    """
    ret = None
    token_id = get_token_id(serial)
    resolver = MachineResolver.query.filter(MachineResolver.name ==
                                            resolver_name).first()

    mt = MachineToken.query.filter(and_(MachineToken.token_id == token_id,
                                        MachineToken.machineresolver_id ==
                                        resolver.id,
                                        MachineToken.machine_id == machine_id,
                                        MachineToken.application ==
                                        application)).first()
    if mt:
        ret = mt.id
    return ret


class RADIUSServer(MethodsMixin, db.Model):
    """
    This table can store configurations of RADIUS servers.
    https://github.com/privacyidea/privacyidea/issues/321

    It saves
    * a unique name
    * a description
    * an IP address a
    * a Port
    * a secret

    These RADIUS server definition can be used in RADIUS tokens or in a
    radius passthru policy.
    """
    __tablename__ = 'radiusserver'
    id = db.Column(db.Integer, primary_key=True)
    # This is a name to refer to
    identifier = db.Column(db.Unicode(255), nullable=False, unique=True)
    # This is the FQDN or the IP address
    server = db.Column(db.Unicode(255), nullable=False)
    port = db.Column(db.Integer, default=25)
    secret = db.Column(db.Unicode(255), default=u"")
    dictionary = db.Column(db.Unicode(255),
                           default="/etc/privacyidea/dictionary")
    description = db.Column(db.Unicode(2000), default=u'')

    def save(self):
        """
        If a RADIUS server with a given name is save, then the existing
        RADIUS server is updated.
        """
        radius = RADIUSServer.query.filter(RADIUSServer.identifier ==
                                           self.identifier).first()
        if radius is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            values = {"server": self.server}
            if self.port is not None:
                values["port"] = self.port
            if self.secret is not None:
                values["secret"] = self.secret
            if self.dictionary is not None:
                values["dictionary"] = self.dictionary
            if self.description is not None:
                values["description"] = self.description
            RADIUSServer.query.filter(RADIUSServer.identifier ==
                                      self.identifier).update(values)
            ret = radius.id
        db.session.commit()
        return ret


class SMTPServer(MethodsMixin, db.Model):
    """
    This table can store configurations for SMTP servers.
    Each entry represents an SMTP server.
    EMail Token, SMS SMTP Gateways or Notifications like PIN handlers are
    supposed to use a reference to to a server definition.
    Each Machine Resolver can have multiple configuration entries.
    The config entries are referenced by the id of the machine resolver
    """
    __tablename__ = 'smtpserver'
    id = db.Column(db.Integer, primary_key=True)
    # This is a name to refer to
    identifier = db.Column(db.Unicode(255), nullable=False)
    # This is the FQDN or the IP address
    server = db.Column(db.Unicode(255), nullable=False)
    port = db.Column(db.Integer, default=25)
    username = db.Column(db.Unicode(255), default=u"")
    password = db.Column(db.Unicode(255), default=u"")
    sender = db.Column(db.Unicode(255), default=u"")
    tls = db.Column(db.Boolean, default=False)
    description = db.Column(db.Unicode(2000), default=u'')

    def save(self):
        smtp = SMTPServer.query.filter(SMTPServer.identifier ==
                                       self.identifier).first()
        if smtp is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            values = {"server": self.server}
            if self.port is not None:
                values["port"] = self.port
            if self.username is not None:
                values["username"] = self.username
            if self.password is not None:
                values["password"] = self.password
            if self.sender is not None:
                values["sender"] = self.sender
            if self.tls is not None:
                values["tls"] = self.tls
            if self.description is not None:
                values["description"] = self.description
            SMTPServer.query.filter(SMTPServer.identifier ==
                                    self.identifier).update(values)
            ret = smtp.id
        db.session.commit()
        return ret
