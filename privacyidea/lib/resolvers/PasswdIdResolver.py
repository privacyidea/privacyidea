# -*- coding: utf-8 -*-
#
#  product:  privacyIDEA is a fork of LinOTP
#  module:   privacyidea resolver library
#
#  May, 08 2014 Cornelius Kölbel
#  http://www.privacyidea.org
#
# 2014-10-03 fix getUsername function
#            Cornelius Kölbel <cornelius@privcyidea.org>
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
import crypt


from UserIdResolver import UserIdResolver

log = logging.getLogger(__name__)
ENCODING = "utf-8"


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

    searchFields = {"username": "text",
                    "userid": "numeric",
                    "description": "text",
                    "email": "text"
                    }

    sF = {"username": 0,
          "cryptpass": 1,
          "userid": 2,
          "description": 4,
          "email": 4,
          }

    @classmethod
    def setup(cls, config=None, cache_dir=None):
        '''
        this setup hook is triggered, when the server
        starts to serve the first request

        :param config: the privacyidea config
        :type  config: the privacyidea config dict
        '''
        log.info("Setting up the PasswdResolver")
        return

    def __init__(self):
        """
        simple constructor
        """
        self.name = "etc-passwd"
        self.fileName = ""

        self.name = "P"
        self.nameDict = {}
        self.descDict = {}
        self.reversDict = {}
        self.passDict = {}
        self.officePhoneDict = {}
        self.homePhoneDict = {}
        self.surnameDict = {}
        self.givennameDict = {}
        self.emailDict = {}

    def loadFile(self):

        """
        Loads the data of the file initially.
        if the self.fileName is empty, it loads /etc/passwd.
        Empty lines are ignored.
        """

        if (self.fileName == ""):
            self.fileName = "/etc/passwd"

        log.info('loading users from file %s from within %r' % (self.fileName,
                                                                os.getcwd()))
        fileHandle = open(self.fileName, "r")

        ID = self.sF["userid"]
        NAME = self.sF["username"]
        PASS = self.sF["cryptpass"]
        DESCRIPTION = self.sF["description"]

        for line in fileHandle:
            line = line.strip()
            if len(line) == 0:
                continue

            fields = line.split(":", 7)
            self.nameDict["%s" % fields[NAME]] = fields[ID]

            # for speed reason - build a revers lookup
            self.reversDict[fields[ID]] = "%s" % fields[NAME]

            # for full info store the line
            self.descDict[fields[ID]] = fields

            # store the crypted password
            self.passDict[fields[ID]] = fields[PASS]

            # store surname, givenname and phones
            descriptions = fields[DESCRIPTION].split(",")
            name = descriptions[0]
            names = name.split(' ', 1)
            self.givennameDict[fields[ID]] = names[0]
            self.surnameDict[fields[ID]] = ""
            self.officePhoneDict[fields[ID]] = ""
            self.homePhoneDict[fields[ID]] = ""
            self.emailDict[fields[ID]] = ""
            if len(names) >= 2:
                self.surnameDict[fields[ID]] = names[1]
            if len(descriptions) >= 4:
                self.officePhoneDict[fields[ID]] = descriptions[2]
                self.homePhoneDict[fields[ID]] = descriptions[3]
            if len(descriptions) >= 5:
                for field in descriptions[4:]:
                    # very basic e-mail regex
                    email_match = re.search('.+@.+\..+', field)
                    if email_match:
                        self.emailDict[fields[ID]] = email_match.group(0)

        fileHandle.close()

    def checkPass(self, uid, password):
        """
        This function checks the password for a given uid.
        returns true in case of success
        false if password does not match

        We do not support shadow passwords. so the seconds column
        of the passwd file needs to contain the crypted password

        :param uid: The uid of the user
        :type uid: int
        :param password: The password in cleartext
        :type password: sting
        :return: True or False
        :rtype: bool
        """
        log.info("checking password for user uid %s" % uid)
        cryptedpasswd = self.passDict[uid]
        log.debug("We found the crypted pass %s for uid %s"
                  % (cryptedpasswd, uid))
        if cryptedpasswd:
            if cryptedpasswd == 'x' or cryptedpasswd == '*':
                err = "Sorry, currently no support for shadow passwords"
                log.error("%s" % err)
                raise NotImplementedError(err)
            cp = crypt.crypt(password, cryptedpasswd)
            log.debug("crypted pass is %s" % cp)
            if crypt.crypt(password, cryptedpasswd) == cryptedpasswd:
                log.info("successfully authenticated user uid %s" % uid)
                return True
            else:
                log.warning("user uid %s failed to authenticate" % uid)
                return False
        else:
            log.warning("Failed to verify password. No crypted password "
                        "found in file")
            return False

    def getUserInfo(self, userId, no_passwd=False):
        """
        get some info about the user
        as we only have the loginId, we have to traverse the dict for the value

        :param userId: the to be searched user
        :param no_passwd: retrun no password
        :return: dict of user info
        """
        ret = {}

        if userId in self.reversDict:
            fields = self.descDict.get(userId)

            for key in self.sF:
                if no_passwd and key == "cryptpass":
                    continue
                index = self.sF[key]
                ret[key] = fields[index]

            ret['givenname'] = self.givennameDict.get(userId)
            ret['surname'] = self.surnameDict.get(userId)
            ret['phone'] = self.homePhoneDict.get(userId)
            ret['mobile'] = self.officePhoneDict.get(userId)
            ret['email'] = self.emailDict.get(userId)

        return ret

    def getUsername(self, userId):
        '''
        Returns the username/loginname for a given userid
        :param userid: The userid in this resolver
        :type userid: string
        :return: username
        :rtype: string
        '''
        fields = self.descDict.get(userId)
        index = self.sF["username"]
        return fields[index]

    def getUserId(self, LoginName):
        """
        search the user id from the login name

        :param LoginName: the login of the user
        :return: the userId
        """
        # We need the encoding, to be also able to read usernames
        # with Umlauts from files.

        if type(LoginName) == unicode:
            LoginName = LoginName.encode(ENCODING)

        if LoginName in self.nameDict.keys():
            return self.nameDict[LoginName]
        else:
            return ""

    def getSearchFields(self, searchDict=None):
        """
        show, which search fields this userIdResolver supports

        TODO: implementation is not completed

        :param searchDict: fields, which can be queried
        :type searchDict: dict
        :return: dict of all searchFields
        :rtype: dict
        """
        if searchDict is not None:
            for search in searchDict:
                pattern = searchDict[search]

                log.debug("searching for %s:%s",
                          search, pattern)

        return self.searchFields

    def getUserList(self, searchDict):
        """
        get a list of all users matching the search criteria of the searchdict

        :param searchDict: dict of search expressions
        """
        ret = []

        #  first check if the searches are in the searchDict
        for l in self.descDict:
            line = self.descDict[l]
            ok = True

            for search in searchDict:

                if search not in self.searchFields:
                    ok = False
                    break

                pattern = searchDict[search]

                log.debug("searching for %s:%s", search, pattern)

                if search == "username":
                    ok = self.checkUserName(line, pattern)
                elif search == "userid":
                    ok = self.checkUserId(line, pattern)
                elif search == "description":
                    ok = self.checkDescription(line, pattern)
                elif search == "email":
                    ok = self.checkEmail(line, pattern)

                if ok is not True:
                    break

            if ok is True:
                uid = line[self.sF["userid"]]
                info = self.getUserInfo(uid, no_passwd=True)
                ret.append(info)

        return ret

    def checkUserName(self, line, pattern):
        """
        check for user name
        """

        username = line[self.sF["username"]]
        ret = self._stringMatch(username, pattern)
        return ret

    def checkDescription(self, line, pattern):
        description = line[self.sF["description"]]
        ret = self._stringMatch(description, pattern)
        return ret

    def checkEmail(self, line, pattern):
        email = line[self.sF["email"]]
        ret = self._stringMatch(email, pattern)
        return ret

    def _stringMatch(self, cString, cPattern):
        """
        internal function to match strings.

        :param cString: The string to match
        :param cPattern: the pattern
        :return: If the sting matches
        :rtype: bool
        """
        ret = False
        e = s = ""

        if type(cString) == unicode:
            cString = cString.encode(ENCODING)

        if type(cPattern) == unicode:
            cPattern = cPattern.encode(ENCODING)

        string = cString.lower()
        pattern = cPattern.lower()

        if pattern.startswith("*"):
            e = "e"
            pattern = pattern[1:]

        if pattern.endswith("*"):
            s = "s"
            pattern = pattern[:-1]

        if e == "e" and s == "s":
            if string.find(pattern) != -1:
                return True
        elif e == "e":
            if string.endswith(pattern):
                return True
        elif s == "s":
            if string.startswith(pattern):
                return True
        else:
            if string == pattern:
                return True

        return ret

    def checkUserId(self, line, pattern):
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
            cUserId = int(line[self.sF["userid"]])
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

            if (cUserId <= ihVal and cUserId >= ilVal):
                ret = True
        else:
            try:
                ival = int(val)
            except:  # pragma: no cover
                return ret

            if op == "=":
                if (cUserId == ival):
                    ret = True

            elif op == ">":
                if (cUserId > ival):
                    ret = True

            elif op == ">=":
                if (cUserId >= ival):
                    ret = True

            elif op == "<":
                if (cUserId < ival):
                    ret = True

            elif op == "<=":
                if (cUserId <= ival):
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
        return self.fileName

    @classmethod
    def getResolverClassType(cls):
        return 'passwdresolver'

    def getResolverType(self):
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

    def getResolverDescriptor(self):
        return IdResolver.getResolverClassDescriptor()


    def loadConfig(self, config):
        """ loadConfig(configDict)
            The UserIdResolver could be configured
            from the pylons app config - here
            this could be the passwd file ,
            whether it is /etc/passwd or /etc/shadow
        """
        self.fileName = config.get("fileName", config.get("filename"))
        self.loadFile()

        return self
