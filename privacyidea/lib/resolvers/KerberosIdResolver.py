# -*- coding: utf-8 -*-
#  Copyright (C) 2014 Cornelius Kölbel
#  contact:  corny@cornelinux.de
#
#  2017-04-06 Nickolas Wood <nick@woodden.org>
#             Initial Kerberos resolver; extends LDAP
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
__doc__ = """This is the resolver to find users in LDAP directories like
OpenLDAP and Active Directory but authenticates the users against Kerberos.

LDAP functionality can be tested with the existing LDAP tests

Kerberos functionality cannot be tested by straight python
https://github.com/apple/ccs-pykerberos

A complete and functional kerberos infrastructure is required as the python kerberos
module only presents bindings and not the entire framework.
Additionally, the system running the application must have a valid kerberos ticket
for authenticating with kerberos and the service running this application must
also have a valid ticket. (See the 'Testing' section of the kerberos python module)

Testing this would require automated kerberos setup and bootstrap within the CI/CD
pipeline.

The majority of this work comes from Gabriel Faber and this thread:
https://groups.google.com/forum/#!msg/privacyidea/zr2wepesUnU/kWXYHyPtPQAJ
"""

import logging
import kerberos
from privacyidea.lib.utils import to_utf8
from .LDAPIdResolver import IdResolver as LDAPIdResolver

log = logging.getLogger(__name__)


class IdResolver (LDAPIdResolver):

    def __init__(self):
        LDAPIdResolver.__init__(self)
        self.realm = ""
        self.servicePrincipal = ""
        log.debug("__init__ called in KerberosIdResolver.py" )

    @staticmethod
    def getResolverClassType():
        return 'kerberosresolver'

    @staticmethod
    def getResolverType():
        return IdResolver.getResolverClassType()

    @classmethod
    def getResolverClassDescriptor(cls):
        """
        return the descriptor of the resolver, which is
        - the class name and
        - the config description

        :return: resolver description dict
        :rtype:  dict
        """
        descriptor = {}
        typ = cls.getResolverType()
        descriptor['clazz'] = "useridresolver.KerberosIdResolver.IdResolver"
        descriptor['config'] = {'REALM': 'string',
                                'SERVICEPRINCIPAL': 'string',
                                'LDAPURI': 'string',
                                'LDAPBASE': 'string',
                                'BINDDN': 'string',
                                'BINDPW': 'password',
                                'TIMEOUT': 'int',
                                'SIZELIMIT': 'int',
                                'LOGINNAMEATTRIBUTE': 'string',
                                'LDAPSEARCHFILTER': 'string',
                                'LDAPFILTER': 'string',
                                'USERINFO': 'string',
                                'UIDTYPE': 'string',
                                'NOREFERRALS': 'bool',
                                'CACERTIFICATE': 'string',
                                'EDITABLE': 'bool',
                                'SCOPE': 'string',
                                'AUTHTYPE': 'string'}
        return {typ: descriptor}

    def checkPass(self, uid, password):
        """
        This function checks the password for a given uid.
        - returns true in case of success
        -         false if password does not match

        """

        realm = self.realm
        password = to_utf8(password)
        service = self.servicePrincipal
        userId = LDAPIdResolver.getUsername(self, uid)

        try:
            log.debug("(Kerberos) user: %s; realm: %s; service %s" % (userId, realm, service))
            kerberos.checkPassword(userId,password,service,realm)
        except kerberos.BasicAuthError, e:
            log.warning("failed to check password for %r: %r"
                        % (userId, e))
            return False

        return True

    def loadConfig(self, config):
        LDAPIdResolver.loadConfig(self, config)
        self.realm = config.get("REALM")
        self.servicePrincipal = config.get("SERVICEPRINCIPAL")
        log.debug("loadConfig called in KerberosIdResolver.py" )
