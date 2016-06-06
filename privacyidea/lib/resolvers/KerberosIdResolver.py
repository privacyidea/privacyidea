# -*- coding: utf-8 -*-
#  Copyright (C) 2014 Cornelius Kölbel
#  contact:  corny@cornelinux.de
#
#  2016-06-05 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial Kereberos resolver inherited from LDAP
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

The file is tested in tests/test_lib_resolver.py
"""

import logging
from .LDAPIdResolver import IdResolver as LDAPIdResolver

log = logging.getLogger(__name__)


class IdResolver (LDAPIdResolver):

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
        descriptor['config'] = {'LDAPURI': 'string',
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

