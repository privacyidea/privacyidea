# 2016-04-08 Cornelius Kölbel <cornelius@privacyidea.org>
#            Avoid consecutive if-statements
# 2014-10-03 fix getUsername function
#            Cornelius Kölbel <cornelius@privcyidea.org>
#
#  May, 08 2014 Cornelius Kölbel
#  http://www.privacyidea.org
#
#  product:  LinOTP2
#  module:   useridresolver
#  tool:     PasswdIdResolver
#  edition:  Comunity Edition
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
  Description:  This file is part of the privacyidea service
                This module implements the communication interface
                for resolvin user info to the /etc/passwd user base

  Dependencies: -
"""

import re
import os
import logging
import codecs
from typing import List

from passlib.context import CryptContext

from privacyidea.lib.utils import convert_column_to_unicode
from .UserIdResolver import UserIdResolver

log = logging.getLogger(__name__)
ENCODING = "utf-8"

crypt_ctx = CryptContext(schemes=["sha512_crypt", "sha256_crypt", "bcrypt"])


def tokenise(r):
    def _(s):
        ret = None
        st = s.strip()
        m = re.match("^" + r, st)
        if m:
            ret = (st[:m.end()].strip(), st[m.end():].strip())
        return ret
    return _


class IdResolver (UserIdResolver):

    fields = {"username": 1, "userid": 1,
              "description": 0,
              "phone": 0, "mobile": 0, "email": 0,
              "givenname": 0, "surname": 0, "gender": 0
              }

    search_fields = {"username": "text",
                    "userid": "numeric",
                    "description": "text",
                    "email": "text"
                     }

    search_field_indices = {"username": 0,
          "cryptpass": 1,
          "userid": 2,
          "description": 4,
          "email": 4,
                            }

    @staticmethod
    def setup(config=None, cache_dir=None):
        """
        this setup hook is triggered, when the server
        starts to serve the first request

        :param config: the privacyidea config
        :type  config: the privacyidea config dict
        """
        log.info("Setting up the PasswdResolver")
        return

    def __init__(self):
        """
        simple constructor
        """
        self.name = "etc-passwd"
        self.file_name = ""

        self.name = "P"
        self.name_dict = {}
        self.description_dict = {}
        self.revers_dict = {}
        self.pass_dict = {}
        self.office_phone_dict = {}
        self.home_phone_dict = {}
        self.surname_dict = {}
        self.given_name_dict = {}
        self.email_dict = {}

    def load_file(self):

        """
        Loads the data of the file initially.
        if the self.fileName is empty, it loads /etc/passwd.
        Empty lines are ignored.
        """

        if not self.file_name:
            self.file_name = "/etc/passwd"

        log.info('loading users from file {0!s} from within {1!r}'.format(self.file_name,
                                                                          os.getcwd()))
        with codecs.open(self.file_name, "r", ENCODING) as file_handle:
            ID = self.search_field_indices["userid"]
            NAME = self.search_field_indices["username"]
            PASS = self.search_field_indices["cryptpass"]
            DESCRIPTION = self.search_field_indices["description"]

            for line in file_handle:
                line = line.strip()
                if not line:
                    # continue on an empty line
                    continue

                fields = line.split(":", 7)
                self.name_dict[fields[NAME]] = fields[ID]

                # for speed reason - build a revers lookup
                self.revers_dict[fields[ID]] = fields[NAME]

                # for full info store the line
                self.description_dict[fields[ID]] = fields

                # store the crypted password
                self.pass_dict[fields[ID]] = fields[PASS]

                # store surname, givenname and phones
                descriptions = fields[DESCRIPTION].split(",")
                name = descriptions[0]
                names = name.split(' ', 1)
                self.given_name_dict[fields[ID]] = names[0]
                self.surname_dict[fields[ID]] = ""
                self.office_phone_dict[fields[ID]] = ""
                self.home_phone_dict[fields[ID]] = ""
                self.email_dict[fields[ID]] = ""
                if len(names) >= 2:
                    self.surname_dict[fields[ID]] = names[1]
                if len(descriptions) >= 4:
                    self.office_phone_dict[fields[ID]] = descriptions[2]
                    self.home_phone_dict[fields[ID]] = descriptions[3]
                if len(descriptions) >= 5:
                    for field in descriptions[4:]:
                        # very basic e-mail regex
                        email_match = re.search(r'.+@.+\..+', field)
                        if email_match:
                            self.email_dict[fields[ID]] = email_match.group(0)

    def checkPass(self, uid, password):
        """
        This function checks the password for a given uid.
        returns true in case of success
        false if password does not match

        We do not support shadow passwords. so the seconds column
        of the passwd file needs to contain the encrypted password

        If the password is a unicode object, it is encoded according
        to ENCODING first.

        :param uid: The uid of the user
        :type uid: int
        :param password: The password in cleartext
        :type password: sting
        :return: True or False
        :rtype: bool
        """
        log.info("checking password for user uid {0!s}".format(uid))
        cryptedpasswd = self.pass_dict.get(uid)
        log.debug("We found the encrypted pass {0!s} for uid {1!s}".format(cryptedpasswd, uid))
        if cryptedpasswd:
            if cryptedpasswd in ['x', '*']:
                err = "Sorry, currently no support for shadow passwords"
                log.error("{0!s}".format(err))
                raise NotImplementedError(err)
            if crypt_ctx.verify(password, cryptedpasswd):
                log.info("successfully authenticated user uid {0!s}".format(uid))
                return True
            else:
                log.warning("user uid {0!s} failed to authenticate".format(uid))
                return False
        else:
            log.warning("Failed to verify password. No encrypted password "
                        "found in file")
            return False

    def getUserInfo(self, userId, no_passwd=False):
        """
        get some info about the user
        as we only have the loginId, we have to traverse the dict for the value

        :param userId: the to be searched user
        :param no_passwd: return no password
        :return: dict of user info
        """
        ret = {}

        if userId in self.revers_dict:
            fields = self.description_dict.get(userId, [])
            if not fields:
                log.debug("User with user ID %s could not be found.", userId)

            for key in self.search_field_indices:
                if no_passwd and key == "cryptpass":
                    continue
                index = self.search_field_indices[key]
                if index < len(fields):
                    ret[key] = fields[index]

            ret['givenname'] = self.given_name_dict.get(userId)
            ret['surname'] = self.surname_dict.get(userId)
            ret['phone'] = self.home_phone_dict.get(userId)
            ret['mobile'] = self.office_phone_dict.get(userId)
            ret['email'] = self.email_dict.get(userId)

        return ret

    def getUsername(self, userId):
        '''
        Returns the username/loginname for a given userid
        :param userid: The userid in this resolver
        :type userid: string
        :return: username
        :rtype: str
        '''
        fields = self.description_dict.get(userId, [])
        index = self.search_field_indices["username"]
        username = ""
        if index < len(fields):
            username = fields[index]
        else:
            log.debug("Username for user ID %s could not be found.", userId)
        return username

    def getUserId(self, LoginName):
        """
        search the user id from the login name

        :param LoginName: the login of the user (as unicode)
        :return: the userId
        :rtype: str
        """
        # We do not encode the LoginName anymore, as we are
        # storing unicode in nameDict now.
        if LoginName in self.name_dict:
            return convert_column_to_unicode(self.name_dict.get(LoginName, ""))
        else:
            return ""

    def get_search_fields(self, search_dict=None):
        """
        show, which search fields this userIdResolver supports

        TODO: implementation is not completed

        :param search_dict: fields, which can be queried
        :type search_dict: dict
        :return: dict of all searchFields
        :rtype: dict
        """
        if search_dict is not None:
            for search in search_dict:
                pattern = search_dict[search]

                log.debug("searching for %s:%s",
                          search, pattern)

        return self.search_fields

    def getUserList(self, search_dict=None):
        """
        get a list of all users matching the search criteria of the searchdict

        :param search_dict: dict of search expressions
        """
        ret = []

        #  first check if the searches are in the searchDict
        for _id, line in self.description_dict.items():
            ok = True

            for search in search_dict:

                if search not in self.search_fields:
                    ok = False
                    break

                pattern = search_dict.get(search)

                log.debug("searching for %s:%s", search, pattern)

                if search in ["username", "description", "email"]:
                    ok = self.check_attribute(line, pattern, search)
                elif search == "userid":
                    ok = self.check_user_id(line, pattern)

                if ok is not True:
                    break

            if ok is True:
                uid_index = self.search_field_indices["userid"]
                uid = ""
                if uid_index < len(line):
                    uid = line[self.search_field_indices["userid"]]
                info = self.getUserInfo(uid, no_passwd=True)
                ret.append(info)

        return ret

    def check_attribute(self, line: List[str], pattern: str, attribute_name: str) -> bool:
        """
        Checks if a given attribute matches a pattern.

        :param line: the list of user attributes
        :param pattern: the pattern to match
        :param attribute_name: the name of the attribute to check
        :return: True if the attribute matches the pattern, False otherwise
        """
        index = self.search_field_indices.get(attribute_name)
        if index is None:
            log.debug("Unknown search field: %s", attribute_name)
            return False
        attribute = ""
        if index < len(line):
            attribute = line[index]
        ret = self._string_match(attribute, pattern)
        return ret

    @staticmethod
    def _string_match(value, pattern):
        """
        internal function to match strings.

        :param value: The string to match
        :param pattern: the pattern
        :return: If the sting matches
        :rtype: bool
        """
        ret = False
        e = s = ""

        string = value.lower()
        pattern = pattern.lower()

        if pattern.startswith("*"):
            e = "e"
            pattern = pattern[1:]

        if pattern.endswith("*"):
            s = "s"
            pattern = pattern[:-1]

        if e == "e" and s == "s" and string.find(pattern) != -1:
            return True
        elif e == "e" and string.endswith(pattern):
            return True
        elif s == "s" and string.startswith(pattern):
            return True
        elif string == pattern:
            return True

        return ret

    def check_user_id(self, line, pattern):
        """
        Check if a userid matches a pattern.
        A pattern can be "=1000", ">=1000",
        "<2000" or "between 1000,2000".

        :param line: the dictionary of a user
        :type line: dict
        :param pattern: match pattern with <, <=...
        :type pattern: string
        :return: True or False
        :rtype: bool
        """
        ret = False

        try:
            cUserId = int(line[self.search_field_indices["userid"]])
        except:  # pragma: no cover
            return ret

        (op, val) = tokenise(">=|<=|>|<|=|between")(pattern)

        if op == "between":
            (lVal, hVal) = val.split(",", 2)
            try:
                ilVal = int(lVal.strip())
                ihVal = int(hVal.strip())
                if ihVal < ilVal:
                    v = ihVal
                    ihVal = ilVal
                    ilVal = v
            except:  # pragma: no cover
                return ret

            if ilVal <= cUserId <= ihVal:
                ret = True
        else:
            try:
                ival = int(val)
            except:  # pragma: no cover
                return ret

            if op == "=" and cUserId == ival:
                ret = True

            elif op == ">" and cUserId > ival:
                ret = True

            elif op == ">=" and cUserId >= ival:
                ret = True

            elif op == "<" and cUserId < ival:
                ret = True

            elif op == "<=" and cUserId <= ival:
                ret = True

        return ret

#############################################################
# server info methods
#############################################################
    def getResolverId(self):
        """
        return the resolver identifier string, which in fact is
        filename, where it points to.
        """
        return self.file_name

    @staticmethod
    def getResolverClassType():
        return 'passwdresolver'

    @staticmethod
    def getResolverType():
        return IdResolver.getResolverClassType()

    @classmethod
    def getResolverClassDescriptor(cls):
        '''
        return the descriptor of the resolver, which is
        - the class name and
        - the config description

        :return: resolver description dict
        :rtype:  dict
        '''
        descriptor = {}
        typ = cls.getResolverClassType()
        descriptor['clazz'] = "useridresolver.PasswdIdResolver.IdResolver"
        descriptor['config'] = {'fileName': 'string'}
        return {typ: descriptor}

    @staticmethod
    def getResolverDescriptor():
        return IdResolver.getResolverClassDescriptor()

    def loadConfig(self, config):
        """ loadConfig(configDict)
            The UserIdResolver could be configured
            from the pylons app config - here
            this could be the passwd file ,
            whether it is /etc/passwd or /etc/shadow
        """
        self.file_name = config.get("fileName", config.get("filename"))
        self.load_file()

        return self
