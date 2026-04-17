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
# SPDX-License-Identifier: AGPL-3.0-or-later
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
import base64
import hmac
import os

from privacyidea.lib.resolvers.UserIdResolver import UserIdResolver

from sqlalchemy import (Integer, cast, String, MetaData, Table, and_,
                        create_engine, select, insert, delete, update, RowMapping)
from sqlalchemy.orm import sessionmaker, scoped_session

import traceback
import hashlib
from privacyidea.lib.pooling import get_engine
from privacyidea.lib.lifecycle import register_finalizer
from privacyidea.lib.utils import (is_true, censor_connect_string,
                                   convert_column_to_unicode)
from privacyidea.lib.error import ParameterError, ResolverError

import bcrypt as _bcrypt

try:
    import crypt as _crypt
    _CRYPT_AVAILABLE = True
except ImportError:
    _CRYPT_AVAILABLE = False

log = logging.getLogger(__name__)

# --- phpass ($P$) helpers ---
# phpass uses a custom base64 with the Unix crypt alphabet (./0-9A-Za-z)
# and little-endian bit ordering — different from standard base64.

_ITOA64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
_ATOI64 = {c: i for i, c in enumerate(_ITOA64)}


def _h64_encode(data):
    """Encode bytes with the Unix crypt / phpass base64 (little-endian, ./0-9A-Za-z alphabet)."""
    out = []
    i = 0
    n = len(data)
    while i < n:
        b0 = data[i]
        i += 1
        out.append(_ITOA64[b0 & 0x3f])
        b1 = data[i] if i < n else 0
        out.append(_ITOA64[((b0 >> 6) | (b1 << 2)) & 0x3f])
        if i >= n:
            break
        i += 1
        b2 = data[i] if i < n else 0
        out.append(_ITOA64[((b1 >> 4) | (b2 << 4)) & 0x3f])
        if i >= n:
            break
        i += 1
        out.append(_ITOA64[(b2 >> 2) & 0x3f])
    return ''.join(out)


def _phpass_calc(password_bytes, hash_str, checksum_size):
    """Compute a phpass MD5 hash; returns the full reconstructed hash string."""
    rounds_char = hash_str[3]
    if rounds_char not in _ATOI64:
        return None
    real_rounds = 1 << _ATOI64[rounds_char]
    salt = hash_str[4:12].encode('ascii')
    result = hashlib.md5(salt + password_bytes).digest()
    for _ in range(real_rounds):
        result = hashlib.md5(result + password_bytes).digest()
    return hash_str[:12] + _h64_encode(result)[:checksum_size]


def _phpass_verify(password, hash_str):
    """Verify a phpass $P$ (MD5-based) hash."""
    if len(hash_str) < 12 or hash_str[:3] != '$P$':
        return False
    if isinstance(password, str):
        password = password.encode('utf-8')
    try:
        computed = _phpass_calc(password, hash_str, 22)
        return computed is not None and hmac.compare_digest(computed, hash_str[:len(computed)])
    except Exception:
        return False


def _phpass_generate(password):
    """Generate a new phpass $P$ (MD5-based, 2^11 rounds) hash."""
    if isinstance(password, str):
        password = password.encode('utf-8')
    salt = ''.join(_ITOA64[b & 0x3f] for b in os.urandom(8))
    return _phpass_calc(password, '$P$' + _ITOA64[11] + salt, 22)


# --- LDAP salted digest helpers ---

def _ssha_verify(password_bytes, hash_str, digest_func, digest_size, ident):
    """Verify an LDAP {SSHAx} salted hash."""
    try:
        raw = base64.b64decode(hash_str[len(ident):])
        return hmac.compare_digest(digest_func(password_bytes + raw[digest_size:]).digest(), raw[:digest_size])
    except Exception:
        return False


def _ssha_generate(password_bytes, digest_func, ident, salt_size=4):
    """Generate an LDAP {SSHAx} salted hash."""
    salt = os.urandom(salt_size)
    return ident + base64.b64encode(digest_func(password_bytes + salt).digest() + salt).decode('ascii')


# --- Verification dispatcher ---

def _verify_sql_hash(password, hash_str):
    """
    Verify a password against a hash stored in an SQL user database.

    Supported formats:
      {SHA}, {SSHA}, {SSHA256}, {SSHA512} — LDAP digest formats
      $P$                                  — phpass (WordPress)
      $2a$/$2b$/$2x$/$2y$                 — bcrypt (passwords truncated to 72 bytes)
      $1$/$5$/$6$                         — md5_crypt/sha256_crypt/sha512_crypt
                                             (requires Python's 'crypt' module; unavailable on Python 3.13+)
      64 lowercase hex chars               — hex_sha256 (OTRS)
    """
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
        password_str = password
    else:
        password_bytes = password
        password_str = password.decode('utf-8', errors='replace')

    if hash_str.startswith('{SHA}'):
        try:
            return hmac.compare_digest(base64.b64decode(hash_str[5:]), hashlib.sha1(password_bytes).digest())
        except Exception:
            return False
    elif hash_str.startswith('{SSHA}'):
        return _ssha_verify(password_bytes, hash_str, hashlib.sha1, 20, '{SSHA}')
    elif hash_str.startswith('{SSHA256}'):
        return _ssha_verify(password_bytes, hash_str, hashlib.sha256, 32, '{SSHA256}')
    elif hash_str.startswith('{SSHA512}'):
        return _ssha_verify(password_bytes, hash_str, hashlib.sha512, 64, '{SSHA512}')
    elif hash_str.startswith('$P$'):
        return _phpass_verify(password_bytes, hash_str)
    elif hash_str[:4] in ('$2a$', '$2b$', '$2x$', '$2y$'):
        try:
            return _bcrypt.checkpw(password_bytes[:72], hash_str.encode('utf-8'))
        except Exception:
            return False
    elif hash_str.startswith(('$1$', '$5$', '$6$')):
        if not _CRYPT_AVAILABLE:
            log.warning("Cannot verify %s hash: Python's 'crypt' module is unavailable (removed in Python 3.13)",
                        hash_str[:3])
            return False
        try:
            return hmac.compare_digest(_crypt.crypt(password_str, hash_str), hash_str)
        except Exception:
            return False
    elif re.match(r'^[0-9a-f]{64}$', hash_str):
        return hmac.compare_digest(hashlib.sha256(password_bytes).hexdigest(), hash_str)
    else:
        return False


_SUPPORTED_HASH_TYPES = ['PHPASS', 'SHA', 'SSHA', 'SSHA256', 'SSHA512', 'OTRS',
                          'SHA256CRYPT', 'SHA512CRYPT', 'MD5CRYPT']

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
        userinfo = self.get_user_info(uid)

        database_pw = userinfo.get("password", "XXXXXXX")

        # remove owncloud hash format identifier (currently only version 1)
        database_pw = re.sub(r'^1\|', '', database_pw)

        # translate lower case hash identifier to uppercase
        database_pw = re.sub(r'^{([a-z0-9]+)}',
                             lambda match: f'{{{match.group(1).upper()}}}',
                             database_pw)

        res = _verify_sql_hash(password, database_pw)

        return res

    def get_user_info(self, user_id: int or str, attributes: list[str] = None) -> dict:
        """
        This function returns all user info for a given userid/object.

        :param user_id: The userid of the object
        :param attributes: list of attribute names to be returned for the user. If None, all attributes are returned.
        :return: A dictionary with the keys defined in self.map
        """
        userinfo = {}

        try:
            conditions = [self._get_userid_filter(user_id)]
            conditions = self._append_where_filter(conditions, self.TABLE,
                                                   self.where)
            filter_condition = and_(*conditions)
            result = self.session.execute(select(self.TABLE).filter(filter_condition))

            for r in result.mappings():
                if userinfo:  # pragma: no cover
                    raise Exception(f"More than one user with userid {user_id!s} found!")
                userinfo = self._get_user_from_mapped_object(r, attributes)
        except Exception as exx:  # pragma: no cover
            log.error(f"Could not get the user information: {exx!r}")

        return userinfo

    def get_available_info_keys(self) -> list[str]:
        """
        This function returns a list of known privacyIDEA user attributes which can be used, e.g. for getUserList or
        get_user_info

        :return: list of possible keys for searching users
        """
        info_keys = list(self.map.keys())
        info_keys.append("id")  # id is always added
        return info_keys

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
        info = self.get_user_info(userId)
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
                                    f" {LoginName} found!")
                user = self._get_user_from_mapped_object(r)
                userid = convert_column_to_unicode(user["userid"])
        except Exception as exx:    # pragma: no cover
            log.error(f"Could not get the user ID: {exx!r}")

        return userid

    def _get_user_from_mapped_object(self, row: RowMapping, attributes: list[str] = None) -> dict:
        """
        :param row: row
        :param attributes: list of attribute names to be returned for the user. If None or an empty list, all
            attributes are returned.
        :return: user info as dictionary
        """
        user = {}
        try:
            if self.map.get("userid") in row:
                user["id"] = row[self.map.get("userid")]
        except UnicodeEncodeError:  # pragma: no cover
            log.error(f"Failed to convert user: {row!r}")
            log.debug(f"{traceback.format_exc()!s}")


        for key in self.map.keys():
            if attributes and key not in attributes:
                # only include the requested attributes
                continue
            try:
                raw_value = row.get(self.map.get(key))
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
                log.error(f"Failed to convert user: {row!r}")
                log.debug(f"{traceback.format_exc()!s}")

        return user

    def getUserList(self, search_dict: dict = None, attributes: list[str] = None) -> list[dict]:
        """
        :param search_dict: A dictionary with search parameters
        :type search_dict: dict
        :param attributes: list of attributes to be returned for each user (id and userid are always returned).
            If None or an empty list, all attributes are returned.
        :return: list of users, where each user is a dictionary
        :raises ParameterError: when the search key does not exist in the
          mapping or database
        """
        users = []
        conditions = []
        if search_dict is None:
            search_dict = {}
        # Check if all the search keys are available in the mapping
        unknown_search_keys = [x for x in search_dict.keys() if x not in self.map.keys()]
        if unknown_search_keys:
            log.error(f"Could not find search key ({unknown_search_keys}) in "
                      f"the column mapping keys ({list(self.map.keys())}).")
            raise ParameterError(f"Search parameter ({unknown_search_keys}) not available "
                                 f"in column mapping.")
        for key, value in search_dict.items():
            column = self.map.get(key)
            value = value.replace("*", "%")
            if column in self.TABLE.columns:
                conditions.append(self.TABLE.columns[column].like(value))
            else:
                # This is a configuration error, the mapping does not correspond with the table definition
                log.error(f"Mapped column ('{column}') is not available in the database "
                          f"table '{self.table}' ({list(self.TABLE.columns.keys())}).")
                raise ResolverError(f"Search parameter ({key}) not available in resolver.")

        conditions = self._append_where_filter(conditions, self.TABLE,
                                               self.where)
        if conditions:
            filter_condition = and_(*conditions)
        else:
            filter_condition = and_(True, *conditions)

        result = self.session.execute(select(self.TABLE).
                                      filter(filter_condition).
                                      limit(self.limit))

        if attributes and "userid" not in attributes:
            attributes.append("userid")
        for r in result.mappings():
            user = self._get_user_from_mapped_object(r, attributes)
            if "userid" in user:
                # Remove the "password" attribute
                user.pop("password", None)
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

        table_parts = self.table.split(".")
        schema = table_parts[0] if len(table_parts) > 1 else None
        self.table = table_parts[-1]
        log.debug(f"Loading table {self.table!s} from schema {schema!s}")
        self.TABLE = Table(self.table, MetaData(), autoload_with=self.engine, schema=schema)
        return self

    def _create_engine(self):
        log.debug("using the connect string "
                  f"{censor_connect_string(self.connect_string)!s}")
        log.debug(f"using pool_size={self.pool_size!s}, pool_timeout={self.pool_timeout!s}, "
                  f"pool_recycle={self.pool_recycle!s}")
        try:
            engine = create_engine(self.connect_string,
                                   pool_size=self.pool_size,
                                   pool_recycle=self.pool_recycle,
                                   pool_timeout=self.pool_timeout)
        except TypeError:
            # The DB Engine/Poolclass might not support the pool_size.
            log.debug("connecting without pool_size.")
            engine = create_engine(self.connect_string)
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
            port = ":{!s}".format(param.get("Port"))
        if param.get("Password"):
            password = ":{!s}".format(param.get("Password"))
        if param.get("conParams"):
            conParams = "?{!s}".format(param.get("conParams"))
        connect_string = "{!s}://{!s}{!s}{!s}{!s}{!s}/{!s}{!s}".format(param.get("Driver") or "",
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
        try:
            connect_string = cls._create_connect_string(param)
            log.info(f"using the connect string {censor_connect_string(connect_string)!s}")
            engine = create_engine(connect_string)
            # create a configured "Session" class
            session = scoped_session(sessionmaker(bind=engine))()
        except Exception as e:
            log.warning(f"Unable to connect to database: {e}")
            return -1, "Unable to connect to database."

        table_parts = param.get("Table").split(".")
        schema = table_parts[0] if len(table_parts) > 1 else None
        table_name = table_parts[-1]
        log.debug(f"Loading table {table_name!s} from schema {schema!s}")

        try:
            TABLE = Table(table_name, MetaData(), autoload_with=engine, schema=schema)
            conditions = cls._append_where_filter([], TABLE,
                                                  param.get("Where"))
            if conditions:
                filter_condition = and_(*conditions)
            else:
                filter_condition = and_(True, *conditions)
            result = session.query(TABLE).filter(filter_condition).count()

            num = result
            desc = f"Found {num:d} users."
        except Exception as e:
            log.warning(f"Failed to retrieve users: {e!r}")
            desc = "Failed to retrieve users."
        finally:
            # We do not want any leftover DB connection, so we first need to close
            # the session such that the DB connection gets returned to the pool (it
            # is still open at that point!) and then dispose the engine such that the
            # checked-in connection gets closed.
            session.close()
            engine.dispose()

        return num, desc

    def add_user(self, attributes: dict=None):
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
        log.info(f"Insert new user with attributes {kwargs!s}")
        r = self.session.execute(insert(self.TABLE).values(**kwargs))
        self.session.commit()
        # Return the UID of the new object
        primary_key_dict = r.inserted_primary_key._asdict()
        return primary_key_dict[self.map.get("userid")]

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
            log.info(f'Deleted user with uid: {uid!s}')
        except Exception as exx:
            log.error(f"Error deleting user: {exx!s}")
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
        success = False
        attributes = attributes or {}
        try:
            params = self.prepare_attributes_for_db(attributes)
            filter_condition = self._get_userid_filter(uid)
            stmt = update(self.TABLE).filter(filter_condition).values(**params)
            result = self.session.execute(stmt)
            success = result.rowcount > 0
            self.session.commit()
            log.info(f'Updated user attributes for user with uid {uid!s}')
        except Exception as exx:
            log.error(f'Error updating user attributes for user with uid {uid!s}: '
                      f'{exx!s}')
            log.debug(f'Error updating attributes {attributes!s}', exc_info=True)

        return success

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
    Hash a password for storage in an SQL user database.

    :param password: The password in plain text
    :type password: str
    :param hashtype: One of PHPASS, SHA, SSHA, SSHA256, SSHA512, OTRS,
                     SHA256CRYPT, SHA512CRYPT, MD5CRYPT
    :type hashtype: str
    :return: The hashed password
    :rtype: str
    """
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
        password_str = password
    else:
        password_bytes = password
        password_str = password.decode('utf-8')

    hashtype = hashtype.upper()

    if hashtype == 'PHPASS':
        return _phpass_generate(password_bytes)
    elif hashtype == 'SHA':
        return '{SHA}' + base64.b64encode(hashlib.sha1(password_bytes).digest()).decode('ascii')
    elif hashtype == 'SSHA':
        return _ssha_generate(password_bytes, hashlib.sha1, '{SSHA}', salt_size=4)
    elif hashtype == 'SSHA256':
        return _ssha_generate(password_bytes, hashlib.sha256, '{SSHA256}', salt_size=16)
    elif hashtype == 'SSHA512':
        return _ssha_generate(password_bytes, hashlib.sha512, '{SSHA512}', salt_size=16)
    elif hashtype == 'OTRS':
        return hashlib.sha256(password_bytes).hexdigest()
    elif hashtype in ('SHA256CRYPT', 'SHA512CRYPT', 'MD5CRYPT'):
        if not _CRYPT_AVAILABLE:
            raise NotImplementedError(
                f"{hashtype} requires Python's 'crypt' module, which was removed in Python 3.13."
            )
        method = {'SHA256CRYPT': _crypt.METHOD_SHA256,
                  'SHA512CRYPT': _crypt.METHOD_SHA512,
                  'MD5CRYPT': _crypt.METHOD_MD5}[hashtype]
        return _crypt.crypt(password_str, _crypt.mksalt(method))
    else:
        raise Exception(f"Unsupported password hashtype '{hashtype!s}'. "
                        f"Use one of {_SUPPORTED_HASH_TYPES!s}.")
