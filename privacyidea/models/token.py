# SPDX-FileCopyrightText: (C) 2025 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2025 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
import binascii
import logging
from typing import Optional

from sqlalchemy import Sequence, Unicode, Integer, Boolean, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privacyidea.lib.crypto import (geturandom, encrypt, hexlify_and_unicode,
                                    pass_hash, encryptPin, decryptPin, hash,
                                    verify_pass_hash, SecretObj)
from privacyidea.lib.error import ResourceNotFoundError
from privacyidea.lib.log import log_with
from privacyidea.lib.utils import convert_column_to_unicode
from privacyidea.models import db
from privacyidea.models.realm import Realm
from privacyidea.models.utils import MethodsMixin

log = logging.getLogger(__name__)


class TokenCredentialIdHash(MethodsMixin, db.Model):
    __tablename__ = "tokencredentialidhash"
    id: Mapped[int] = mapped_column("id", Integer, Sequence("tokencredentialidhash_seq"), primary_key=True)
    credential_id_hash: Mapped[str] = mapped_column(db.String(256), nullable=False)
    token_id: Mapped[int] = mapped_column(db.ForeignKey("token.id"), nullable=False)
    __table_args__ = (db.Index('ix_tokencredentialidhash_credentialidhash',
                               'credential_id_hash', unique=True),)

    def __init__(self, credential_id_hash, token_id):
        self.credential_id_hash = credential_id_hash
        self.token_id = token_id


class Token(MethodsMixin, db.Model):
    """
    The "Token" table contains the basic token data.

    It contains data like
     * serial number
     * secret key
     * PINs
     * ...

    The table :py:class:`privacyidea.models.TokenOwner` contains the owner
    information of the specified token.
    The table :py:class:`privacyidea.models.TokenInfo` contains additional information
    that is specific to the tokentype.
    """
    __tablename__ = 'token'
    id: Mapped[int] = mapped_column(Integer, Sequence("token_seq"),
                                    primary_key=True,
                                    nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Unicode(80), default='')
    serial: Mapped[str] = mapped_column(Unicode(40), default='',
                                        unique=True,
                                        nullable=False,
                                        index=True)
    tokentype: Mapped[Optional[str]] = mapped_column(Unicode(30),
                                           default='HOTP',
                                           index=True)
    user_pin: Mapped[Optional[str]] = mapped_column(Unicode(512),
                                                    default='')  # encrypt
    user_pin_iv: Mapped[Optional[str]] = mapped_column(Unicode(32),
                                                       default='')  # encrypt
    so_pin: Mapped[Optional[str]] = mapped_column(Unicode(512),
                                                  default='')  # encrypt
    so_pin_iv: Mapped[Optional[str]] = mapped_column(Unicode(32),
                                                     default='')  # encrypt
    pin_seed: Mapped[Optional[str]] = mapped_column(Unicode(32),
                                                    default='')
    otplen: Mapped[Optional[int]] = mapped_column(Integer,
                                        default=6)
    pin_hash: Mapped[Optional[str]] = mapped_column(Unicode(512),
                                                    default='')  # hashed
    key_enc: Mapped[Optional[str]] = mapped_column(Unicode(2800),
                                                   default='')  # encrypt
    key_iv: Mapped[Optional[str]] = mapped_column(Unicode(32),
                                                  default='')
    maxfail: Mapped[Optional[int]] = mapped_column(Integer,
                                         default=10)
    active: Mapped[bool] = mapped_column(Boolean,
                                         nullable=False,
                                         default=True)
    revoked: Mapped[Optional[bool]] = mapped_column(Boolean,
                                          default=False)
    locked: Mapped[Optional[bool]] = mapped_column(Boolean,
                                         default=False)
    failcount: Mapped[Optional[int]] = mapped_column(Integer,
                                           default=0)
    count: Mapped[Optional[int]] = mapped_column(Integer,
                                       default=0)
    count_window: Mapped[Optional[int]] = mapped_column(Integer,
                                              default=10)
    sync_window: Mapped[Optional[int]] = mapped_column(Integer,
                                             default=1000)
    rollout_state: Mapped[Optional[str]] = mapped_column(Unicode(10),
                                                         default='')
    info_list = relationship('TokenInfo', lazy='select', back_populates='token')
    owners = relationship('TokenOwner', lazy='dynamic', back_populates='token')

    # Container
    container = relationship('TokenContainer', secondary='tokencontainertoken', back_populates='tokens')

    # This creates an attribute "realm_list" in the Token object
    realm_list = relationship('TokenRealm', lazy='joined', back_populates='token')

    def __init__(self, serial, tokentype="",
                 isactive=True, otplen=6,
                 otpkey="",
                 **kwargs):
        super(Token, self).__init__(**kwargs)
        self.serial = '' + serial
        self.tokentype = tokentype
        self.count = 0
        self.failcount = 0
        self.maxfail = 10
        self.active = isactive
        self.revoked = False
        self.locked = False
        self.count_window = 10
        self.otplen = otplen
        self.pin_seed = ""
        self.set_otpkey(otpkey)

    @property
    def first_owner(self):
        return self.owners.first()

    @property
    def all_owners(self):
        return self.owners.all()

    @staticmethod
    def _fix_spaces(data):
        """
        On MS SQL server empty fields ("") like the info
        are returned as a string with a space (" ").
        This functions helps to fix this.
        Also avoids running into errors, if the data is a None Type.

        :param data: a string from the database
        :type data: str
        :return: a stripped string
        :rtype: str
        """
        if data:
            data = data.strip()

        return data

    @log_with(log, hide_args=[1])
    def set_otpkey(self, otpkey, reset_failcount=True):
        iv = geturandom(16)
        self.key_enc = encrypt(otpkey, iv)
        length = len(self.key_enc)
        if length > Token.key_enc.property.columns[0].type.length:
            log.error(f"Key for token {self.serial} exceeds database field with length {length}!")
        self.key_iv = hexlify_and_unicode(iv)
        self.count = 0
        if reset_failcount is True:
            self.failcount = 0

    # TODO: Compare with lib function
    # def set_tokengroups(self, tokengroups, add=False):
    #     """
    #     Set the list of the tokengroups.
    #
    #     This is done by filling the :py:class:`privacyidea.models.TokenTokengroup` table.
    #
    #     :param tokengroups: the tokengroups
    #     :type tokengroups: list[str]
    #     :param add: If set, the tokengroups are added. I.e. old tokengroups are not deleted
    #     :type add: bool
    #     """
    #     # delete old Tokengroups
    #     if not add:
    #         delete_stmt = delete(TokenTokengroup).where(TokenTokengroup.token_id == self.id)
    #         db.session.execute(delete_stmt)
    #     # add new Tokengroups
    #     # We must not set the same tokengroup more than once...
    #     # uniquify: tokengroups -> set(tokengroups)
    #     for tokengroup in set(tokengroups):
    #         # Get the id of the realm to add
    #         stmt = select(Tokengroup).filter_by(name=tokengroup)
    #         g = db.session.execute(stmt).scalar_one_or_none()
    #         if g:
    #             # Check if TokenTokengroup already exists
    #             stmt_tg = select(TokenTokengroup).filter_by(token_id=self.id, tokengroup_id=g.id)
    #             tg = db.session.execute(stmt_tg).scalar_one_or_none()
    #             if not tg:
    #                 # If the Tokengroup is not yet attached to the token
    #                 token_group = TokenTokengroup(token_id=self.id, tokengroup_id=g.id)
    #                 db.session.add(token_group)
    #     db.session.commit()
    #
    # def set_realms(self, realms, add=False):
    #     """
    #     Set the list of the realms.
    #
    #     This is done by filling the :py:class:`privacyidea.models.TokenRealm` table.
    #
    #     :param realms: realms
    #     :type realms: list[str]
    #     :param add: If set, the realms are added. I.e. old realms are not deleted
    #     :type add: bool
    #     """
    #     # delete old TokenRealms
    #     if not add:
    #         delete_stmt = delete(TokenRealm).where(TokenRealm.token_id == self.id)
    #         db.session.execute(delete_stmt)
    #     # add new TokenRealms
    #     # We must not set the same realm more than once...
    #     # uniquify: realms -> set(realms)
    #     if self.first_owner:
    #         if self.first_owner.realm.name not in realms:
    #             realms.append(self.first_owner.realm.name)
    #             log.info(f"The realm of an assigned user cannot be removed from "
    #                      f"token {self.first_owner.token.serial} "
    #                      f"(realm: {self.first_owner.realm.name})")
    #     for realm in set(realms):
    #         # Get the id of the realm to add
    #         stmt_realm = select(Realm).filter_by(name=realm)
    #         realm_db = db.session.execute(stmt_realm).scalar_one_or_none()
    #         if realm_db:
    #             # Check if tokenrealm already exists
    #             stmt_token_realm = select(TokenRealm).filter_by(token_id=self.id, realm_id=realm_db.id)
    #             token_realm_db = db.session.execute(stmt_token_realm).scalar_one_or_none()
    #             if not token_realm_db:
    #                 # If the realm is not yet attached to the token
    #                 token_realm = TokenRealm(token_id=self.id, realm_id=realm_db.id)
    #                 db.session.add(token_realm)
    #     db.session.commit()

    def get_realms(self):
        """
        return a list of the assigned realms

        :return: the realms of the token
        :rtype: list
        """
        realms = []
        for tokenrealm in self.realm_list:
            realms.append(tokenrealm.realm.name)
        return realms

    @log_with(log)
    def set_user_pin(self, user_pin):
        iv = geturandom(16)
        self.user_pin = encrypt(user_pin, iv)
        self.user_pin_iv = hexlify_and_unicode(iv)

    @log_with(log)
    def get_otpkey(self):
        key = binascii.unhexlify(self.key_enc)
        iv = binascii.unhexlify(self.key_iv)
        secret = SecretObj(key, iv)
        return secret

    @log_with(log)
    def get_user_pin(self):
        """
        return the user_pin
        :rtype : the PIN as a secretObject
        """
        user_pin = self.user_pin or ''
        user_pin_iv = self.user_pin_iv or ''
        key = binascii.unhexlify(user_pin)
        iv = binascii.unhexlify(user_pin_iv)
        secret = SecretObj(key, iv)
        return secret

    def set_hashed_pin(self, pin):
        """
        Set the pin of the token in hashed format

        :param pin: the pin to hash
        :type pin: str
        :return: the hashed pin
        :rtype: str
        """
        self.pin_hash = pass_hash(pin)
        return self.pin_hash

    def get_hashed_pin(self, pin):
        """
        Calculate a hash from a pin
        Fix for working with MS SQL servers
        MS SQL servers sometimes return a '<space>' when the
        column is empty: ''

        :param pin: the pin to hash
        :type pin: str
        :return: hashed pin with current pin_seed
        :rtype: str
        """
        seed_str = self._fix_spaces(self.pin_seed)
        seed = binascii.unhexlify(seed_str)
        hashed_pin = hash(pin, seed)
        log.debug(f"hashed_pin: {hashed_pin}, pin: {pin!r}, seed: {self.pin_seed}")
        return hashed_pin

    @log_with(log)
    def set_description(self, desc):
        if desc is None:
            desc = ""
        length = len(desc)
        if length > Token.description.property.columns[0].type.length:
            desc = desc[:Token.description.property.columns[0].type.length]
        self.description = convert_column_to_unicode(desc)
        return self.description

    def set_pin(self, pin, hashed=True):
        """
        Set the OTP pin in a hashed way
        """
        real_pin = pin or ""
        if hashed:
            self.set_hashed_pin(real_pin)
            log.debug(f"set_pin hash: {self.pin_hash!r}")
        else:
            self.pin_hash = "@@" + encryptPin(real_pin)
            log.debug(f"set_pin encrypted: {self.pin_hash!r}")
        return self.pin_hash

    def check_pin(self, pin):
        res = False
        # check for a valid input
        if pin is not None:
            if self.is_pin_encrypted() is True:
                log.debug("we got an encrypted PIN!")
                token_pin = self.pin_hash[2:]
                decrypted_token_pin = decryptPin(token_pin)
                if decrypted_token_pin == pin:
                    res = True
            else:
                log.debug("we got a hashed PIN!")
                if self.pin_hash:
                    try:
                        # New PIN verification
                        return verify_pass_hash(pin, self.pin_hash)
                    except ValueError as _e:
                        # old PIN verification
                        pin_hash = self.get_hashed_pin(pin)
                else:
                    pin_hash = pin
                if pin_hash == (self.pin_hash or ""):
                    res = True
        return res

    def is_pin_encrypted(self, pin=None):
        ret = False
        if pin is None:
            pin = self.pin_hash or ""
        if pin.startswith("@@"):
            ret = True
        return ret

    def get_pin(self):
        ret = -1
        if self.is_pin_encrypted() is True:
            token_pin = self.pin_hash[2:]
            ret = decryptPin(token_pin)
        return ret

    def set_so_pin(self, security_officer_pin):
        """
        For smartcards this sets the security officer pin of the token

        :rtype : None
        """
        iv = geturandom(16)
        self.so_pin = encrypt(security_officer_pin, iv)
        self.so_pin_iv = hexlify_and_unicode(iv)
        return self.so_pin, self.so_pin_iv

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

        td = self.get_vars(save=save)
        return td.get(key, fallback)

    @log_with(log)
    def get_vars(self, save=False):
        log.debug('get_vars()')
        tokenowner = self.first_owner

        ret = {
            'id': self.id,
            'description': self.description,
            'serial': self.serial,
            'tokentype': self.tokentype,
            'info': self.get_info(),
            'resolver': "" if not tokenowner else tokenowner.resolver,
            'user_id': "" if not tokenowner else tokenowner.user_id,
            'otplen': self.otplen,
            'maxfail': self.maxfail,
            'active': self.active,
            'revoked': self.revoked,
            'locked': self.locked,
            'failcount': self.failcount,
            'count': self.count,
            'count_window': self.count_window,
            'sync_window': self.sync_window,
            'rollout_state': self.rollout_state}

        # list of Realm names
        realm_list = []
        for realm_entry in self.realm_list:
            realm_list.append(realm_entry.realm.name)
        ret['realms'] = realm_list
        # list of tokengroups
        tokengroup_list = []
        for tg_entry in self.tokengroup_list:
            tokengroup_list.append(tg_entry.tokengroup.name)
        ret['tokengroup'] = tokengroup_list
        return ret

    def __str__(self):
        return self.serial

    def __repr__(self):
        """
        return the token state as text

        :return: token state as string representation
        :rtype:  str
        """
        ldict = {}
        for attr in self.__dict__:
            key = "{0!r}".format(attr)
            val = "{0!r}".format(getattr(self, attr))
            ldict[key] = val
        res = "<{0!r} {1!r}>".format(self.__class__, ldict)
        return res

    def get_info(self):
        """

        :return: The token info as dictionary
        """
        ret = {}
        for tokeninfo in self.info_list:
            if tokeninfo.Type:
                ret[tokeninfo.Key + ".type"] = tokeninfo.Type
            ret[tokeninfo.Key] = tokeninfo.Value
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
            otp_key_secret = self.get_otpkey()
            if otp_key_secret.compare(otpkey) is False:
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
    id: Mapped[int] = mapped_column(Integer, Sequence("tokeninfo_seq"), primary_key=True)
    Key: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    Value: Mapped[Optional[str]] = mapped_column(Unicode(2000), default='')
    Type: Mapped[Optional[str]] = mapped_column(Unicode(100), default='')
    Description: Mapped[Optional[str]] = mapped_column(Unicode(2000), default='')
    token_id: Mapped[Optional[int]] = mapped_column(Integer, db.ForeignKey('token.id'), index=True)

    token = relationship("Token", back_populates="info_list")

    __table_args__ = (db.UniqueConstraint('token_id',
                                          'Key',
                                          name='tiix_2'),)

    def __init__(self, token_id, Key, Value, Type=None, Description=None):
        """
        Create a new tokeninfo for a given token_id
        """
        self.token_id = token_id
        self.Key = Key
        self.Value = convert_column_to_unicode(Value)
        self.Type = Type
        self.Description = Description

    # TODO: Compare with lib function
    # def save(self, persistent=True):
    #     stmt = select(TokenInfo).filter_by(token_id=self.token_id, Key=self.Key)
    #     ti = db.session.execute(stmt).scalar_one_or_none()
    #     if ti is None:
    #         # create a new one
    #         db.session.add(self)
    #         db.session.commit()
    #         if get_app_config_value(SAFE_STORE, False):
    #             stmt = select(TokenInfo).filter_by(token_id=self.token_id, Key=self.Key)
    #             ti = db.session.execute(stmt).scalar_one_or_none()
    #             ret = ti.id
    #         else:
    #             ret = self.id
    #     else:
    #         # update
    #         update_stmt = (
    #             update(TokenInfo)
    #             .where(and_(TokenInfo.token_id == self.token_id, TokenInfo.Key == self.Key))
    #             .values(Value=self.Value, Description=self.Description, Type=self.Type)
    #         )
    #         db.session.execute(update_stmt)
    #         ret = ti.id
    #     if persistent:
    #         db.session.commit()
    #     return ret


class TokenOwner(MethodsMixin, db.Model):
    """
    This tables stores the owner of a token.
    A token can be assigned to several users.
    """
    __tablename__ = 'tokenowner'
    id: Mapped[int] = mapped_column(Integer, Sequence("tokenowner_seq"), primary_key=True)
    token_id: Mapped[Optional[int]] = mapped_column(Integer, db.ForeignKey('token.id'))
    resolver: Mapped[Optional[str]] = mapped_column(Unicode(120), default='', index=True)
    user_id: Mapped[Optional[str]] = mapped_column(Unicode(320), default='', index=True)
    realm_id: Mapped[Optional[int]] = mapped_column(Integer, db.ForeignKey('realm.id'))

    token = relationship('Token', lazy='joined', back_populates='owners')
    realm = relationship('Realm', lazy='joined', back_populates='tokenowners')

    def __init__(self, token_id=None, serial=None, user_id=None, resolver=None,
                 realm_id=None, realmname=None):
        """
        Create a new token assignment to a user.

        :param token_id: The database ID of the token
        :param serial:  The alternate serial number of the token
        :param resolver: The identifying name of the resolver
        :param realm_id: The database ID of the realm
        :param realmname: The alternate name of realm
        """
        if realm_id is not None:
            self.realm_id = realm_id
        elif realmname:
            stmt = select(Realm).filter_by(name=realmname)
            r = db.session.execute(stmt).scalar_one_or_none()
            if not r:
                raise ResourceNotFoundError(f"Realm '{realmname}' does not exist.")
            self.realm_id = r.id
        if token_id is not None:
            self.token_id = token_id
        elif serial:
            stmt = select(Token).filter_by(serial=serial)
            r = db.session.execute(stmt).scalar_one_or_none()
            if not r:  # pragma: no cover
                # usually this is already covered by the lib / token class functions
                raise ResourceNotFoundError(f"Token with serial '{serial}' does not exist.")
            self.token_id = r.id
        self.resolver = resolver
        self.user_id = user_id

    # TODO: Compare with lib function
    # def save(self, persistent=True):
    #     stmt = select(TokenOwner).filter_by(token_id=self.token_id,
    #                                         user_id=self.user_id,
    #                                         realm_id=self.realm_id,
    #                                         resolver=self.resolver)
    #     to = db.session.execute(stmt).scalar_one_or_none()
    #     if to is None:
    #         # This very assignment does not exist, yet:
    #         db.session.add(self)
    #         db.session.commit()
    #         if get_app_config_value(SAFE_STORE, False):
    #             stmt = select(TokenOwner).filter_by(token_id=self.token_id,
    #                                                 user_id=self.user_id,
    #                                                 realm_id=self.realm_id,
    #                                                 resolver=self.resolver)
    #             to = db.session.execute(stmt).scalar_one_or_none()
    #             ret = to.id
    #         else:
    #             ret = self.id
    #     else:
    #         ret = to.id
    #         # There is nothing to update
    #
    #     if persistent:
    #         db.session.commit()
    #     return ret


class TokenRealm(MethodsMixin, db.Model):
    """
    This table stores to which realms a token is assigned. A token is in the
    realm of the user it is assigned to. But a token can also be put into
    many additional realms.
    """
    __tablename__ = 'tokenrealm'
    id: Mapped[int] = mapped_column(Integer, Sequence("tokenrealm_seq"), primary_key=True)
    token_id: Mapped[Optional[int]] = mapped_column(Integer,
                                          db.ForeignKey('token.id'))
    realm_id: Mapped[Optional[int]] = mapped_column(Integer,
                                          db.ForeignKey('realm.id'))
    # This creates an attribute "realm_list" in the Token object
    token = relationship('Token',
                         lazy='joined',
                         back_populates='realm_list')
    # This creates an attribute "token_list" in the Realm object
    realm = relationship('Realm',
                         lazy='joined',
                         back_populates='token_list')
    __table_args__ = (db.UniqueConstraint('token_id',
                                          'realm_id',
                                          name='trix_2'),)

    def __init__(self, realm_id=0, token_id=0, realmname=None):
        log.debug(f"setting realm_id to {realm_id}")
        if realmname:
            stmt = select(Realm).filter_by(name=realmname)
            r = db.session.execute(stmt).scalar_one_or_none()
            self.realm_id = r.id
        if realm_id:
            self.realm_id = realm_id
        self.token_id = token_id


def get_token_id(serial):
    stmt = select(Token).filter(Token.serial == serial)
    token = db.session.scalars(stmt).unique().one_or_none()
    return token.id if token else None
