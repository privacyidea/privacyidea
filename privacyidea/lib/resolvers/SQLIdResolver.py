# -*- coding: utf-8 -*-
#
#  Copyright (C) 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  cornelius@privacyidea.org
#
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

from UserIdResolver import UserIdResolver

from sqlalchemy import and_
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import traceback
from base64 import (b64decode,
                    b64encode)
import os
import time
import hashlib
import crypt
from privacyidea.lib.crypto import urandom, geturandom
from privacyidea.lib.utils import is_true
import binascii

log = logging.getLogger(__name__)
ENCODING = "utf-8"

SQLSOUP_LOADED = False
try:
    from sqlsoup import SQLSoup
    SQLSOUP_LOADED = True
except ImportError:  # pragma: no cover
    log.debug("SQLSoup could not be loaded!")

if SQLSOUP_LOADED is False:  # pragma: no cover
    try:
        from sqlalchemy.ext.sqlsoup import SQLSoup
        log.debug("SQLSoup loaded from SQLAlchemy.")
        SQLSOUP_LOADED = True
    except ImportError:
        log.error("SQLSoup could not be loaded from SQLAlchemy!")

try:
    import bcrypt
    _bcrypt_hashpw = bcrypt.hashpw
except ImportError:  # pragma: no cover
    _bcrypt_hashpw = None

# On App Engine, this function is not available.
if hasattr(os, 'getpid'):
    _pid = os.getpid()
else:  # pragma: no cover
    # Fake PID
    _pid = urandom.randint(0, 100000)


class PasswordHash(object):

    def __init__(self, iteration_count_log2=8, portable_hashes=True,
                 algorithm=''):
        alg = algorithm.lower()
        if alg in ['blowfish', 'bcrypt'] and _bcrypt_hashpw is None:
            raise NotImplementedError('The bcrypt module is required')
        self.itoa64 = \
            './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        if not (4 <= iteration_count_log2 <= 31):
            iteration_count_log2 = 8
        self.iteration_count_log2 = iteration_count_log2
        self.portable_hashes = portable_hashes
        self.algorithm = algorithm
        self.random_state = '{0!r}{1!r}'.format(time.time(), _pid)

    def get_random_bytes(self, count):
        outp = ''
        try:
            outp = os.urandom(count)
        except Exception as exx:  # pragma: no cover
            log.debug("problem getting os.urandom: {0!s}".format(exx))
        if len(outp) < count:  # pragma: no cover
            outp = ''
            rem = count
            while rem > 0:
                self.random_state = hashlib.md5(str(time.time())
                    + self.random_state).hexdigest()
                outp += hashlib.md5(self.random_state).digest()
                rem -= 1
            outp = outp[:count]
        return outp

    def encode64(self, inp, count):
        outp = ''
        cur = 0
        while cur < count:
            value = ord(inp[cur])
            cur += 1
            outp += self.itoa64[value & 0x3f]
            if cur < count:
                value |= (ord(inp[cur]) << 8)
            outp += self.itoa64[(value >> 6) & 0x3f]
            if cur >= count:
                break
            cur += 1
            if cur < count:
                value |= (ord(inp[cur]) << 16)
            outp += self.itoa64[(value >> 12) & 0x3f]
            if cur >= count:
                break
            cur += 1
            outp += self.itoa64[(value >> 18) & 0x3f]
        return outp

    def gensalt_private(self, inp):  # pragma: no cover
        outp = '$P$'
        outp += self.itoa64[min([self.iteration_count_log2 + 5, 30])]
        outp += self.encode64(inp, 6)
        return outp

    def crypt_private(self, pw, setting):  # pragma: no cover
        outp = '*0'
        if setting.startswith(outp):
            outp = '*1'
        if setting[0:3] not in ['$P$', '$H$', '$S$']:
            return outp
        count_log2 = self.itoa64.find(setting[3])
        if not (7 <= count_log2 <= 30):
            return outp
        count = 1 << count_log2
        salt = setting[4:12]
        if len(salt) != 8:
            return outp
        if not isinstance(pw, str):
            pw = pw.encode('utf-8')

        hash_func = hashlib.md5
        encoding_len = 16
        if setting.startswith('$S$'):
            hash_func = hashlib.sha512
            encoding_len = 33

        hx = hash_func(salt + pw).digest()
        while count:
            hx = hash_func(hx + pw).digest()
            count -= 1
        hashed_pw = self.encode64(hx, encoding_len)

        if setting.startswith('$S$'):
            hashed_pw = hashed_pw[:-1]
        return setting[:12] + hashed_pw

    def gensalt_extended(self, inp):  # pragma: no cover
        count_log2 = min([self.iteration_count_log2 + 8, 24])
        count = (1 << count_log2) - 1
        outp = '_'
        outp += self.itoa64[count & 0x3f]
        outp += self.itoa64[(count >> 6) & 0x3f]
        outp += self.itoa64[(count >> 12) & 0x3f]
        outp += self.itoa64[(count >> 18) & 0x3f]
        outp += self.encode64(inp, 3)
        return outp

    def gensalt_blowfish(self, inp):  # pragma: no cover
        itoa64 = \
            './ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        outp = '$2a$'
        outp += chr(ord('0') + self.iteration_count_log2 / 10)
        outp += chr(ord('0') + self.iteration_count_log2 % 10)
        outp += '$'
        cur = 0
        while True:
            c1 = ord(inp[cur])
            cur += 1
            outp += itoa64[c1 >> 2]
            c1 = (c1 & 0x03) << 4
            if cur >= 16:
                outp += itoa64[c1]
                break
            c2 = ord(inp[cur])
            cur += 1
            c1 |= c2 >> 4
            outp += itoa64[c1]
            c1 = (c2 & 0x0f) << 2
            c2 = ord(inp[cur])
            cur += 1
            c1 |= c2 >> 6
            outp += itoa64[c1]
            outp += itoa64[c2 & 0x3f]
        return outp

    def hash_password(self, pw):  # pragma: no cover
        rnd = ''
        alg = self.algorithm.lower()
        if (not alg or alg in ['blowfish', 'bcrypt'] and not
                self.portable_hashes):
            if _bcrypt_hashpw is None and alg in ['blowfish', 'bcrypt']:
                raise NotImplementedError('The bcrypt module is required')
            else:
                rnd = self.get_random_bytes(16)
                salt = self.gensalt_blowfish(rnd)
                hx = _bcrypt_hashpw(pw, salt)
                if len(hx) == 60:
                    return hx
        if (not alg or alg == 'ext-des') and not self.portable_hashes:
            if len(rnd) < 3:
                rnd = self.get_random_bytes(3)
            hx = crypt.crypt(pw, self.gensalt_extended(rnd))
            if len(hx) == 20:
                return hx
        if len(rnd) < 6:
            rnd = self.get_random_bytes(6)
        hx = self.crypt_private(pw, self.gensalt_private(rnd))
        if len(hx) == 34:
            return hx
        return '*'

    def check_password(self, pw, stored_hash):
        # This part is different with the original PHP
        if stored_hash.startswith('$2a$'):
            # bcrypt
            if _bcrypt_hashpw is None:  # pragma: no cover
                raise NotImplementedError('The bcrypt module is required')
            hx = _bcrypt_hashpw(pw, stored_hash)
        elif stored_hash.startswith('_'):
            # ext-des
            stored_hash = stored_hash[1:]
            hx = crypt.crypt(pw, stored_hash)
        else:
            # portable hash
            hx = self.crypt_private(pw, stored_hash)
        return stored_hash == hx


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
        self.password = ""
        self.table = ""
        self.map = {}
        self.reverse_map = {}
        self.where = ""
        self.encoding = ""
        self.conParams = ""
        self.connect_string = ""
        self.session = None
        self.pool_size = 10
        self.pool_timeout = 120
        self.engine = None
        self._editable = False
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
            # this might result in errors if the
            # administrator enters nonsense
            (w_column, w_cond, w_value) = where.split()
            if w_cond.lower() == "like":
                conditions.append(getattr(table, w_column).like(w_value))
            elif w_cond == "==":
                conditions.append(getattr(table, w_column) == w_value)
            elif w_cond == ">":
                conditions.append(getattr(table, w_column) > w_value)
            elif w_cond == "<":
                conditions.append(getattr(table, w_column) < w_value)

        return conditions

    def checkPass(self, uid, password):
        """
        This function checks the password for a given uid.
        - returns true in case of success
        -         false if password does not match

        """
        def _check_ssha(pw_hash, password, hashfunc, length):
            pw_hash_bin = b64decode(pw_hash.split("}")[1])
            digest = pw_hash_bin[:length]
            salt = pw_hash_bin[length:]
            hr = hashfunc(password)
            hr.update(salt)
            return digest == hr.digest()

        def _check_sha(pw_hash, password):
            b64_db_password = pw_hash[5:]
            hr = hashlib.sha1(password).digest()
            b64_password = b64encode(hr)
            return b64_password == b64_db_password

        def _otrs_sha256(pw_hash, password):
            hr = hashlib.sha256(password)
            digest = binascii.hexlify(hr.digest())
            return pw_hash == digest

        res = False
        userinfo = self.getUserInfo(uid)

        database_pw = userinfo.get("password", "XXXXXXX")
        if database_pw[:2] in ["$P", "$S"]:
            # We have a phpass (wordpress) password
            PH = PasswordHash()
            res = PH.check_password(password, userinfo.get("password"))
        # check salted hashed passwords
#        elif database_pw[:2] == "$6":
#            res = sha512_crypt.verify(password, userinfo.get("password"))
        elif database_pw[:6].upper() == "{SSHA}":
            res = _check_ssha(database_pw, password, hashlib.sha1, 20)
        elif database_pw[:9].upper() == "{SSHA256}":
            res = _check_ssha(database_pw, password, hashlib.sha256, 32)
        elif database_pw[:9].upper() == "{SSHA512}":
            res = _check_ssha(database_pw, password, hashlib.sha512, 64)
        # check for hashed password.
        elif userinfo.get("password", "XXXXX")[:5].upper() == "{SHA}":
            res = _check_sha(database_pw, password)
        elif len(userinfo.get("password")) == 64:
            # OTRS sha256 password
            res = _otrs_sha256(database_pw, password)

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
            conditions = []
            column = self.map.get("userid")
            conditions.append(getattr(self.TABLE, column).like(userId))
            conditions = self._append_where_filter(conditions, self.TABLE,
                                                   self.where)
            filter_condition = and_(*conditions)
            result = self.session.query(self.TABLE).filter(filter_condition)

            for r in result:
                if userinfo.keys():  # pragma: no cover
                    raise Exception("More than one user with userid {0!s} found!".format(userId))
                userinfo = self._get_user_from_mapped_object(r)
        except Exception as exx:  # pragma: no cover
            log.error("Could not get the userinformation: {0!r}".format(exx))

        return userinfo

    def getUsername(self, userId):
        """
        Returns the username/loginname for a given userid
        :param userid: The userid in this resolver
        :type userid: string
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
        """
        userid = ""

        try:
            conditions = []
            column = self.map.get("username")
            conditions.append(getattr(self.TABLE, column).like(LoginName))
            conditions = self._append_where_filter(conditions, self.TABLE,
                                                   self.where)
            filter_condition = and_(*conditions)
            result = self.session.query(self.TABLE).filter(filter_condition)

            for r in result:
                if userid != "":    # pragma: no cover
                    raise Exception("More than one user with loginname"
                                    " %s found!" % LoginName)
                user = self._get_user_from_mapped_object(r)
                userid = user["id"]
        except Exception as exx:    # pragma: no cover
            log.error("Could not get the userinformation: {0!r}".format(exx))

        return userid

    def _get_user_from_mapped_object(self, ro):
        """
        :param ro: row
        :type ro: Mapped Object
        :return: User
        :rtype: dict
        """
        r = ro.__dict__
        user = {}
        try:
            if self.map.get("userid") in r:
                user["id"] = r[self.map.get("userid")]
        except UnicodeEncodeError:  # pragma: no cover
            log.error("Failed to convert user: {0!r}".format(r))
            log.debug("{0!s}".format(traceback.format_exc()))

        for key in self.map.keys():
            try:
                raw_value = r.get(self.map.get(key))
                if raw_value:
                    if type(raw_value) == str:
                        val = raw_value.decode(self.encoding)
                    else:
                        val = raw_value
                    user[key] = val

            except UnicodeDecodeError:  # pragma: no cover
                user[key] = "decoding_error"
                log.error("Failed to convert user: {0!r}".format(r))
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
            conditions.append(getattr(self.TABLE, column).like(value))

        conditions = self._append_where_filter(conditions, self.TABLE,
                                               self.where)
        filter_condition = and_(*conditions)

        result = self.session.query(self.TABLE).\
            filter(filter_condition).\
            limit(self.limit)

        for r in result:
            user = self._get_user_from_mapped_object(r)
            if "id" in user:
                users.append(user)

        return users

    def getResolverId(self):
        """
        Returns the resolver Id
        This should be an Identifier of the resolver, preferable the type
        and the name of the resolver.
        """
        return "sql." + self.resolverId

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
        usermap = config.get('Map', {})
        self.map = yaml.safe_load(usermap)
        self.reverse_map = dict([[v, k] for k, v in self.map.items()])
        self.where = config.get('Where', "")
        self.encoding = str(config.get('Encoding') or "latin1")
        self.conParams = config.get('conParams', "")
        self.pool_size = int(config.get('poolSize') or 5)
        self.pool_timeout = int(config.get('poolTimeout') or 10)

        # create the connectstring like
        params = {'Port': self.port,
                  'Password': self.password,
                  'conParams': self.conParams,
                  'Driver': self.driver,
                  'User': self.user,
                  'Server': self.server,
                  'Database': self.database}
        self.connect_string = self._create_connect_string(params)
        log.info("using the connect string {0!s}".format(self.connect_string))
        try:
            log.debug("using pool_size={0!s} and pool_timeout={1!s}".format(
                      self.pool_size, self.pool_timeout))
            self.engine = create_engine(self.connect_string,
                                        encoding=self.encoding,
                                        convert_unicode=False,
                                        pool_size=self.pool_size,
                                        pool_timeout=self.pool_timeout)
        except TypeError:
            # The DB Engine/Poolclass might not support the pool_size.
            log.debug("connecting without pool_size.")
            self.engine = create_engine(self.connect_string,
                                        encoding=self.encoding,
                                        convert_unicode=False)
        # create a configured "Session" class
        Session = sessionmaker(bind=self.engine)

        # create a Session
        self.session = Session()
        self.session._model_changes = {}
        self.db = SQLSoup(self.engine)
        self.TABLE = self.db.entity(self.table)

        return self

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
                                'Port': 'int',
                                'Limit': 'int',
                                'Table': 'string',
                                'Map': 'string',
                                'Where': 'string',
                                'Editable': 'int',
                                'Encoding': 'string',
                                'conParams': 'string'}
        return {typ: descriptor}

    @staticmethod
    def getResolverDescriptor():
        return IdResolver.getResolverClassDescriptor()

    @staticmethod
    def _create_connect_string(param):
        """
        create the connectstring

        Port, Password, conParams, Driver, User,
        Server, Database
        """
        port = ""
        password = ""
        conParams = ""
        if param.get("Port"):
            port = ":{0!s}".format(param.get("Port"))
        if param.get("Password"):
            password = ":{0!s}".format(param.get("Password"))
        if param.get("conParams"):
            conParams = "?{0!s}".format(param.get("conParams"))
        connect_string = "{0!s}://{1!s}{2!s}{3!s}{4!s}{5!s}/{6!s}{7!s}".format(param.get("Driver", ""),
                                                   param.get("User", ""),
                                                   password,
                                                   "@" if (param.get("User")
                                                           or
                                                           password) else "",
                                                   param.get("Server", ""),
                                                   port,
                                                   param.get("Database", ""),
                                                   conParams)
        # SQLAlchemy does not like a unicode connect string!
        if param.get("Driver").lower() == "sqlite":
            connect_string = str(connect_string)
        log.debug("SQL connectstring: {0!r}".format(connect_string))
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
        desc = None

        connect_string = cls._create_connect_string(param)
        log.info("using the connect string {0!s}".format(connect_string))
        engine = create_engine(connect_string)
        # create a configured "Session" class
        session = sessionmaker(bind=engine)()
        db = SQLSoup(engine)
        try:
            TABLE = db.entity(param.get("Table"))
            conditions = cls._append_where_filter([], TABLE,
                                                  param.get("Where"))
            filter_condition = and_(*conditions)
            result = session.query(TABLE).filter(filter_condition).count()

            num = result
            desc = "Found {0:d} users.".format(num)
        except Exception as exx:
            desc = "failed to retrieve users: {0!s}".format(exx)

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
        kwargs = self._attributes_to_db_columns(attributes)
        log.debug("Insert new user with attributes {0!s}".format(kwargs))
        r = self.TABLE.insert(**kwargs)
        self.db.commit()
        # Return the UID of the new object
        return getattr(r, self.map.get("userid"))

    def _attributes_to_db_columns(self, attributes):
        """
        takes the attributes and maps them to the DB columns
        :param attributes:
        :return: dict with column name as keys and values
        """
        columns = {}
        for fieldname in attributes.keys():
            if self.map.get(fieldname):
                if fieldname == "password":
                    password = attributes.get(fieldname)
                    # Create a {SSHA256} password
                    salt = geturandom(16)
                    hr = hashlib.sha256(password)
                    hr.update(salt)
                    hash_bin = hr.digest()
                    hash_b64 = b64encode(hash_bin + salt)
                    columns[self.map.get(fieldname)] = "{SSHA256}" + hash_b64
                else:
                    columns[self.map.get(fieldname)] = attributes.get(fieldname)
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
            conditions = []
            column = self.map.get("userid")
            conditions.append(getattr(self.TABLE, column).like(uid))
            conditions = self._append_where_filter(conditions, self.TABLE,
                                                   self.where)
            filter_condition = and_(*conditions)
            user_obj = self.session.query(self.TABLE).filter(
                filter_condition).first()
            self.session.delete(user_obj)
            self.session.commit()
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

        Attributes that are not contained in the dict attributes are not
        modified.

        :param uid: The uid of the user object in the resolver.
        :type uid: basestring
        :param attributes: Attributes to be updated.
        :type attributes: dict
        :return: True in case of success
        """
        attributes = attributes or {}
        params = self._attributes_to_db_columns(attributes)
        kwargs = {self.map.get("userid"): uid}
        r = self.TABLE.filter_by(**kwargs).update(params)
        self.db.commit()
        return r

    @property
    def editable(self):
        """
        Return true, if the instance of the resolver is configured editable
        :return:
        """
        # Depending on the database this might look different
        # Usually this is "1"
        return is_true(self._editable)
