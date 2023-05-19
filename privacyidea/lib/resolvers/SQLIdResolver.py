# -*- coding: utf-8 -*-
#
#  Copyright (C) 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  cornelius@privacyidea.org
#
#  2019-47-14 Paul Lettich <paul.lettich@netknights.it>
#             Remove hash calculation and switch to passlib
#  2016-07-15 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add sha512 PHP hash as suggested by Rick Romero
#  2016-04-08 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Simplifying out of bounds check
#             Avoid repetition in comparison
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
__doc__ = """This is the resolver to find users in SQL databases.

The file is tested in tests/test_lib_resolver.py
"""

import logging
import yaml
import binascii
import re

from privacyidea.lib.resolvers.UserIdResolver import UserIdResolver

from sqlalchemy import (Integer, cast, String, MetaData, Table, and_,
                        create_engine, select, insert, delete)
from sqlalchemy.orm import sessionmaker, scoped_session

import traceback
import hashlib
from privacyidea.lib.pooling import get_engine
from privacyidea.lib.lifecycle import register_finalizer
from privacyidea.lib.utils import (is_true, censor_connect_string,
                                   convert_column_to_unicode)
from passlib.context import CryptContext
from passlib.utils import h64
from passlib.utils.compat import uascii_to_str
from passlib.utils.compat import unicode as pl_unicode
from passlib.utils import to_unicode
import passlib.utils.handlers as uh
import passlib.exc as exc
from passlib.registry import register_crypt_handler


class phpass_drupal(uh.HasRounds, uh.HasSalt, uh.GenericHandler):  # pragma: no cover
    """This class implements the PHPass Portable Hash (Drupal version), and follows the
    :ref:`password-hash-api`.
    """
    name = "phpass_drupal"
    setting_kwds = ("salt", "rounds")
    checksum_chars = uh.HASH64_CHARS
    checksum_size = 43

    min_salt_size = max_salt_size = 8
    salt_chars = uh.HASH64_CHARS

    default_rounds = 19
    min_rounds = 7
    max_rounds = 30
    rounds_cost = "log2"

    ident = '$S$'

    @classmethod
    def from_string(cls, hash):
        hash = to_unicode(hash, "ascii", "hash")
        ident, data = hash[0:3], hash[3:]
        if ident != cls.ident:
            raise exc.InvalidHashError()
        rounds, salt, chk = data[0], data[1:9], data[9:]
        return cls(
            rounds=h64.decode_int6(rounds.encode("ascii")),
            salt=salt,
            checksum=chk or None,
        )

    def to_string(self):
        hash = "%s%s%s%s" % (self.ident,
                              h64.encode_int6(self.rounds).decode("ascii"),
                              self.salt,
                              self.checksum or '')
        return uascii_to_str(hash)

    def _calc_checksum(self, secret):
        if isinstance(secret, pl_unicode):
            secret = secret.encode("utf-8")
        real_rounds = 1 << self.rounds
        result = hashlib.sha512(self.salt.encode("ascii") + secret).digest()
        r = 0
        while r < real_rounds:
            result = hashlib.sha512(result + secret).digest()
            r += 1
        return h64.encode_bytes(result).decode("ascii")[:self.checksum_size]


register_crypt_handler(phpass_drupal)

# The list of supported password hash types for verification (passlib handler)
pw_ctx = CryptContext(schemes=['phpass',
                               'phpass_drupal',
                               'ldap_salted_sha1',
                               'ldap_salted_sha256',
                               'ldap_salted_sha512',
                               'ldap_sha1',
                               'md5_crypt',
                               'bcrypt',
                               'sha512_crypt',
                               'sha256_crypt',
                               'hex_sha256',
                               ])

# List of supported password hash types for hash generation (name to passlib handler id)
hash_type_dict = {"PHPASS": 'phpass',
                  "SHA": 'ldap_sha1',
                  "SSHA": 'ldap_salted_sha1',
                  "SSHA256": 'ldap_salted_sha256',
                  "SSHA512": 'ldap_salted_sha512',
                  "OTRS": 'hex_sha256',
                  "SHA256CRYPT": 'sha256_crypt',
                  "SHA512CRYPT": 'sha512_crypt',
                  "MD5CRYPT": 'md5_crypt',
                  }

log = logging.getLogger(__name__)


class IdResolver (UserIdResolver):

    searchFields = {"username": "text",
                    "userid": "numeric",
                    "phone": "text",
                    "mobile": "text",
                    "surname": "text",
                    "givenname": "text",
                    "email": "text",
                    "description": "text",
                    }

    # If the resolver could be configured editable
    updateable = True

    @staticmethod
    def setup(config=None, cache_dir=None):
        """
        this setup hook is triggered, when the server
        starts to serve the first request

        :param config: the privacyidea config
        :type  config: the privacyidea config dict
        """
        log.info("Setting up the SQLResolver")

    def __init__(self):
        self.resolverId = ""
        self.server = ""
        self.driver = ""
        self.database = ""
        self.port = 0
        self.limit = 100
        self.user = ""
        self.password = "" # nosec B105 # default parameter
        self.table = ""
        self.TABLE = None
        self.map = {}
        self.reverse_map = {}
        self.where = ""
        self.encoding = ""
        self.conParams = ""
        self.connect_string = ""
        self.session = None
        self.pool_size = 10
        self.pool_timeout = 120
        self.pool_recycle = 7200
        self.engine = None
        self._editable = False
        self.password_hash_type = None
        return

    def getSearchFields(self):
        return self.searchFields

    @staticmethod
    def _append_where_filter(conditions, table, where):
        """
        Append contents of WHERE statement to the list of filter conditions

        :param conditions: filter conditions
        :type conditions: list
        :return: list of filter conditions
        """
        if where:
            parts = re.split(' and ', where, flags=re.IGNORECASE)
            for part in parts:
                # this might result in errors if the
                # administrator enters nonsense
                (w_column, w_cond, w_value) = part.split()
                if w_cond.lower() == "like":
                    conditions.append(table.columns[w_column].like(w_value))
                elif w_cond == "==":
                    conditions.append(table.columns[w_column] == w_value)
                elif w_cond == ">":
                    conditions.append(table.columns[w_column] > w_value)
                elif w_cond == "<":
                    conditions.append(table.columns[w_column] < w_value)

        return conditions

    def checkPass(self, uid, password):
        """
        This function checks the password for a given uid.

        :param uid: uid of the user for which the password should be checked
        :type uid: str
        :param password: the password to check
        :type password: str
        :return: True if password matches the saved password hash, False otherwise
        :rtype: bool
        """

        res = False
        userinfo = self.getUserInfo(uid)

        database_pw = userinfo.get("password", "XXXXXXX")

        # remove owncloud hash format identifier (currently only version 1)
        database_pw = re.sub(r'^1\|', '', database_pw)

        # translate lower case hash identifier to uppercase
        database_pw = re.sub(r'^{([a-z0-9]+)}',
                             lambda match: '{{{}}}'.format(match.group(1).upper()),
                             database_pw)

        try:
            res = pw_ctx.verify(password, database_pw)
        except ValueError as _e:
            # if the hash could not be identified / verified, just return False
            pass

        return res

    def getUserInfo(self, userId):
        """
        This function returns all user info for a given userid/object.

        :param userId: The userid of the object
        :type userId: string
        :return: A dictionary with the keys defined in self.map
        :rtype: dict
        """
        userinfo = {}

        try:
            conditions = [self._get_userid_filter(userId)]
            conditions = self._append_where_filter(conditions, self.TABLE,
                                                   self.where)
            filter_condition = and_(*conditions)
            result = self.session.execute(select(self.TABLE).filter(filter_condition))

            for r in result.mappings():
                if userinfo:  # pragma: no cover
                    raise Exception("More than one user with userid {0!s} found!".format(userId))
                userinfo = self._get_user_from_mapped_object(r)
        except Exception as exx:  # pragma: no cover
            log.error("Could not get the user information: {0!r}".format(exx))

        return userinfo
    
    def _get_userid_filter(self, userId):
        column = self.TABLE.columns[self.map.get("userid")]
        if isinstance(column.type, String):
            return column == str(userId)
        elif isinstance(column.type, Integer):
            # since our user ID is usually a string we need to cast
            return column == int(userId)

        # otherwise we cast the column to string (in case of postgres UUIDs)
        return cast(column, String).like(userId)

    def getUsername(self, userId):
        """
        Returns the username/loginname for a given userid

        :param userId: The userid in this resolver
        :type userId: string
        :return: username
        :rtype: string
        """
        info = self.getUserInfo(userId)
        return info.get('username', "")

    def getUserId(self, LoginName):
        """
        resolve the loginname to the userid.

        :param LoginName: The login name from the credentials
        :type LoginName: string
        :return: UserId as found for the LoginName
        :rtype: str
        """
        userid = ""

        try:
            conditions = []
            column = self.map.get("username")
            conditions.append(self.TABLE.columns[column].like(LoginName))
            conditions = self._append_where_filter(conditions, self.TABLE,
                                                   self.where)
            filter_condition = and_(*conditions)
            result = self.session.execute(select(self.TABLE).filter(filter_condition))

            for r in result.mappings():
                if userid != "":    # pragma: no cover
                    raise Exception("More than one user with loginname"
                                    " %s found!" % LoginName)
                user = self._get_user_from_mapped_object(r)
                userid = convert_column_to_unicode(user["userid"])
        except Exception as exx:    # pragma: no cover
            log.error("Could not get the user ID: {0!r}".format(exx))

        return userid

    def _get_user_from_mapped_object(self, ro):
        """
        :param ro: row
        :type ro: Mapped Object
        :return: User
        :rtype: dict
        """
        user = {}
        try:
            if self.map.get("userid") in ro:
                user["id"] = ro[self.map.get("userid")]
        except UnicodeEncodeError:  # pragma: no cover
            log.error("Failed to convert user: {0!r}".format(ro))
            log.debug("{0!s}".format(traceback.format_exc()))

        for key in self.map.keys():
            try:
                raw_value = ro.get(self.map.get(key))
                if raw_value:
                    if key == 'userid':
                        val = convert_column_to_unicode(raw_value)
                    elif isinstance(raw_value, bytes):
                        val = raw_value.decode(self.encoding)
                    else:
                        val = raw_value
                    user[key] = val

            except UnicodeDecodeError:  # pragma: no cover
                user[key] = "decoding_error"
                log.error("Failed to convert user: {0!r}".format(ro))
                log.debug("{0!s}".format(traceback.format_exc()))

        return user

    def getUserList(self, searchDict=None):
        """
        :param searchDict: A dictionary with search parameters
        :type searchDict: dict
        :return: list of users, where each user is a dictionary
        """
        users = []
        conditions = []
        if searchDict is None:
            searchDict = {}
        for key in searchDict.keys():
            column = self.map.get(key)
            value = searchDict.get(key)
            value = value.replace("*", "%")
            conditions.append(self.TABLE.columns[column].like(value))

        conditions = self._append_where_filter(conditions, self.TABLE,
                                               self.where)
        filter_condition = and_(*conditions)

        result = self.session.execute(select(self.TABLE).
                                      filter(filter_condition).
                                      limit(self.limit))

        for r in result.mappings():
            user = self._get_user_from_mapped_object(r)
            if "userid" in user:
                users.append(user)

        return users

    def getResolverId(self):
        """
        Returns the resolver Id
        This should be an Identifier of the resolver, preferable the type
        and the name of the resolver.

        :return: identifier of the resolver
        :rtype: str
        """
        # Take the following parts, join them with the NULL byte and return
        # the hexlified SHA-1 digest
        id_parts = (self.connect_string,
                    str(self.pool_size),
                    str(self.pool_recycle),
                    str(self.pool_timeout))
        id_str = "\x00".join(id_parts)
        resolver_id = binascii.hexlify(hashlib.sha1(id_str.encode('utf8')).digest())  # nosec B324 # hash used as unique identifier
        return "sql." + resolver_id.decode('utf8')

    @staticmethod
    def getResolverClassType():
        return 'sqlresolver'

    @staticmethod
    def getResolverType():
        return IdResolver.getResolverClassType()

    def loadConfig(self, config):
        """
        Load the config from conf.

        :param config: The configuration from the Config Table
        :type config: dict
        """
        self.server = config.get('Server', "")
        self.driver = config.get('Driver', "")
        self.database = config.get('Database', "")
        self.resolverId = self.database
        self.port = config.get('Port', "")
        self.limit = config.get('Limit', 100)
        self.user = config.get('User', "")
        self.password = config.get('Password', "")
        self.table = config.get('Table', "")
        self._editable = config.get("Editable", False)
        self.password_hash_type = config.get("Password_Hash_Type", "SSHA256")
        usermap = config.get('Map', {})
        self.map = yaml.safe_load(usermap)
        self.reverse_map = {v: k for k, v in self.map.items()}
        self.where = config.get('Where', "")
        self.encoding = str(config.get('Encoding') or "latin1")
        self.conParams = config.get('conParams', "")
        self.pool_size = int(config.get('poolSize') or 5)
        self.pool_timeout = int(config.get('poolTimeout') or 10)
        # recycle SQL connections after 2 hours by default
        # (necessary for MySQL servers, which terminate idle connections after some hours)
        self.pool_recycle = int(config.get('poolRecycle') or 7200)

        # create the connect-string like
        params = {'Port': self.port,
                  'Password': self.password,
                  'conParams': self.conParams,
                  'Driver': self.driver,
                  'User': self.user,
                  'Server': self.server,
                  'Database': self.database}
        self.connect_string = self._create_connect_string(params)

        # get an engine from the engine registry, using self.getResolverId() as the key,
        # which involves the connect-string and the pool settings.
        self.engine = get_engine(self.getResolverId(), self._create_engine)
        # We use ``scoped_session``.
        self.session = scoped_session(sessionmaker(bind=self.engine))()
        # Session should be closed on teardown
        register_finalizer(self.session.close)
        self.session._model_changes = {}
        self.TABLE = Table(self.table, MetaData(), autoload_with=self.engine)

        return self

    def _create_engine(self):
        log.info("using the connect string "
                 "{0!s}".format(censor_connect_string(self.connect_string)))
        try:
            log.debug("using pool_size={0!s}, pool_timeout={1!s}, pool_recycle={2!s}".format(
                self.pool_size, self.pool_timeout, self.pool_recycle))
            engine = create_engine(self.connect_string,
                                   encoding=self.encoding,
                                   convert_unicode=False,
                                   pool_size=self.pool_size,
                                   pool_recycle=self.pool_recycle,
                                   pool_timeout=self.pool_timeout)
        except TypeError:
            # The DB Engine/Poolclass might not support the pool_size.
            log.debug("connecting without pool_size.")
            engine = create_engine(self.connect_string,
                                   encoding=self.encoding,
                                   convert_unicode=False)
        return engine

    @classmethod
    def getResolverClassDescriptor(cls):
        descriptor = {}
        typ = cls.getResolverType()
        descriptor['clazz'] = "useridresolver.SQLIdResolver.IdResolver"
        descriptor['config'] = {'Server': 'string',
                                'Driver': 'string',
                                'Database': 'string',
                                'User': 'string',
                                'Password': 'password',
                                'Password_Hash_Type': 'string',
                                'Port': 'int',
                                'Limit': 'int',
                                'Table': 'string',
                                'Map': 'string',
                                'Where': 'string',
                                'Editable': 'int',
                                'poolTimeout': 'int',
                                'poolSize': 'int',
                                'poolRecycle': 'int',
                                'Encoding': 'string',
                                'conParams': 'string'}
        return {typ: descriptor}

    @staticmethod
    def getResolverDescriptor():
        return IdResolver.getResolverClassDescriptor()

    @staticmethod
    def _create_connect_string(param):
        """
        create the connect-string.

        Port, Password, conParams, Driver, User,
        Server, Database
        """
        port = ""
        password = "" # nosec B105 # default parameter
        conParams = ""
        if param.get("Port"):
            port = ":{0!s}".format(param.get("Port"))
        if param.get("Password"):
            password = ":{0!s}".format(param.get("Password"))
        if param.get("conParams"):
            conParams = "?{0!s}".format(param.get("conParams"))
        connect_string = "{0!s}://{1!s}{2!s}{3!s}{4!s}{5!s}/{6!s}{7!s}".format(param.get("Driver") or "",
                                                   param.get("User") or "",
                                                   password,
                                                   "@" if (param.get("User")
                                                           or
                                                           password) else "",
                                                   param.get("Server") or "",
                                                   port,
                                                   param.get("Database") or "",
                                                   conParams)
        return connect_string

    @classmethod
    def testconnection(cls, param):
        """
        This function lets you test the to be saved SQL connection.

        :param param: A dictionary with all necessary parameter
                        to test the connection.
        :type param: dict
        :return: Tuple of success and a description
        :rtype: (bool, string)

        Parameters are: Server, Driver, Database, User, Password, Port,
                        Limit, Table, Map
                        Where, Encoding, conParams

        """
        num = -1

        connect_string = cls._create_connect_string(param)
        log.info("using the connect string {0!s}".format(censor_connect_string(connect_string)))
        engine = create_engine(connect_string)
        # create a configured "Session" class
        session = scoped_session(sessionmaker(bind=engine))()
        try:
            TABLE = Table(param.get("Table"), MetaData(), autoload_with=engine)
            conditions = cls._append_where_filter([], TABLE,
                                                  param.get("Where"))
            filter_condition = and_(*conditions)
            result = session.query(TABLE).filter(filter_condition).count()

            num = result
            desc = "Found {0:d} users.".format(num)
        except Exception as exx:
            desc = "failed to retrieve users: {0!s}".format(exx)
        finally:
            # We do not want any leftover DB connection, so we first need to close
            # the session such that the DB connection gets returned to the pool (it
            # is still open at that point!) and then dispose the engine such that the
            # checked-in connection gets closed.
            session.close()
            engine.dispose()

        return num, desc

    def add_user(self, attributes=None):
        """
        Add a new user to the SQL database.

        attributes are these
        "username", "surname", "givenname", "email",
        "mobile", "phone", "password"

        :param attributes: Attributes according to the attribute mapping
        :return: The new UID of the user. The UserIdResolver needs to
        determine the way how to create the UID.
        """
        attributes = attributes or {}
        # TODO: add try/except
        kwargs = self.prepare_attributes_for_db(attributes)
        log.info("Insert new user with attributes {0!s}".format(kwargs))
        r = self.session.execute(insert(self.TABLE).values(**kwargs))
        self.session.commit()
        # Return the UID of the new object
        return r.inserted_primary_key[self.map.get("userid")]

    def prepare_attributes_for_db(self, attributes):
        """
        Given a dictionary of attributes, return a dictionary
        mapping columns to values.
        If the attributes contain a password, hash the password according to the
        configured password hash type.

        :param attributes: attributes dictionary
        :return: dictionary with column name as keys
        """
        attributes = attributes.copy()
        if "password" in attributes:
            attributes["password"] = hash_password(attributes["password"],
                                                   self.password_hash_type)
        columns = {}
        for fieldname in attributes:
            if fieldname in self.map:
                columns[self.map[fieldname]] = attributes[fieldname]
        return columns

    def delete_user(self, uid):
        """
        Delete a user from the SQL database.

        The user is referenced by the user id.
        :param uid: The uid of the user object, that should be deleted.
        :type uid: basestring
        :return: Returns True in case of success
        :rtype: bool
        """
        res = True
        try:
            conditions = [self._get_userid_filter(uid)]
            conditions = self._append_where_filter(conditions, self.TABLE,
                                                   self.where)
            filter_condition = and_(*conditions)
            self.session.execute(delete(self.TABLE).where(filter_condition))
            self.session.commit()
            log.info('Deleted user with uid: {0!s}'.format(uid))
        except Exception as exx:
            log.error("Error deleting user: {0!s}".format(exx))
            res = False
        return res

    def update_user(self, uid, attributes=None):
        """
        Update an existing user.
        This function is also used to update the password. Since the
        attribute mapping know, which field contains the password,
        this function can also take care for password changing.

        Attributes that are not contained in the attributes dict are not
        modified.

        :param uid: The uid of the user object in the resolver.
        :type uid: basestring
        :param attributes: Attributes to be updated.
        :type attributes: dict
        :return: True in case of success
        """
        r = False
        attributes = attributes or {}
        try:
            params = self.prepare_attributes_for_db(attributes)
            kwargs = {self.map.get("userid"): uid}
            r = self.session.query(self.TABLE).filter_by(**kwargs).update(params)
            self.session.commit()
            log.info('Updated user attributes for user with uid {0!s}'.format(uid))
        except Exception as exx:
            log.error('Error updating user attributes for user with uid {0!s}: '
                      '{1!s}'.format(uid, exx))
            log.debug('Error updating attributes {0!s}'.format(attributes), exc_info=True)

        return r

    @property
    def editable(self):
        """
        Return true, if the instance of the resolver is configured editable

        :return:
        :rtype: bool
        """
        # Depending on the database this might look different
        # Usually this is "1"
        return is_true(self._editable)


def hash_password(password, hashtype):
    """
    Hash a password with phppass, SHA, SSHA, SSHA256, SSHA512, OTRS

    :param password: The password in plain text
    :type password: str
    :param hashtype: One of the hash types as string
    :type hashtype: str
    :return: The hashed password
    :rtype: str
    """
    hashtype = hashtype.upper()
    try:
        password = pw_ctx.handler(hash_type_dict[hashtype]).hash(password)
    except KeyError as _e:  # pragma: no cover
        raise Exception("Unsupported password hashtype '{0!s}'. "
                        "Use one of {1!s}.".format(hashtype, hash_type_dict.keys()))

    return password
