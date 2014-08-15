# -*- coding: utf-8 -*-
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  Aug 15, 2014 Cornelius Kölbel: CHange login behaviour
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
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
import logging
log = logging.getLogger(__name__)

import re

from privacyidea.lib.user import getRealmBox
from privacyidea.lib.realm import getDefaultRealm
from privacyidea.lib.selftest import isSelfTest
import traceback
from privacyidea.lib.account import check_admin_password
from privacyidea.lib.account import authenticate_privacyidea_user
from privacyidea.lib.account import is_admin_identity
from privacyidea.lib.user import check_user_password
from privacyidea.lib.user import splitUser
from privacyidea.lib.log import log_with

from pylons import request, config, tmpl_context as c
from privacyidea.lib.config import get_privacyIDEA_config
from privacyidea.lib.config import getFromConfig
from privacyidea.lib.policy import PolicyClass
ENCODING = "utf-8"


class UserModelPlugin(object):

    def _get_user_from_login(self, login, default_realm=True):
        '''
        take the login and return a username and a realm name
        :default_realm: If set to True and no realm is found, the
                        default realm will be returned
        :return: tuple (username, realm)
        '''
        username = login
        realm = ""
        
        splitAtSign = getFromConfig("splitAtSign", "true")
        if splitAtSign.lower() == "true":
            (username, realm) = splitUser(login)

        if realm == "" and default_realm:
                realm = getDefaultRealm()
            
        return (username, realm)

    @log_with(log)
    def authenticate(self, environ, identity):
        username = None
        realm = None
        success = None
        try:
            if isSelfTest():
                if ('login' not in identity and 'repoze.who.plugins.auth_tkt.userid' in identity):
                    u = identity.get('repoze.who.plugins.auth_tkt.userid')
                    identity['login'] = u
                    identity['password'] = u

            username, realm = self._get_user_from_login(identity['login'],
                                                        default_realm=False)
            if getRealmBox() and realm == "":
                # The login name contained no realm
                realm = identity['realm']
            if realm == "":
                # The realm is still empty
                realm = getDefaultRealm()

            password = identity['password']
        except KeyError as e:
            log.error("Keyerror in identity: %r." % e)
            log.error("%s" % traceback.format_exc())
            return None

        # check username/realm, password
        if isSelfTest():
            success = "%s@%s" % (unicode(username), unicode(realm))
        else:
            Policy = PolicyClass(request, config, c,
                                 get_privacyIDEA_config())
            if Policy.is_auth_selfservice_otp(username, realm):
                # check the OTP
                success = authenticate_privacyidea_user(username,
                                                        realm,
                                                        password)
            else:
                # We do authentication against the user store
                success = check_user_password(username, realm, password)

        if not success and is_admin_identity("%s@%s" % (username, realm),
                                             exception=False):
            # user not found or authenticated in resolver.
            # So let's see, if this is an administrative user.
            success = check_admin_password(username, password, realm)

        if success:
            log.info("User %r authenticated" % success)
        return success

    @log_with(log)
    def add_metadata(self, environ, identity):
        # username = identity.get('repoze.who.userid')
        # user = User.get(username)
        # user = "conelius koelbel"
        # log.info( "add_metadata: %s" % identity )

        # pp = pprint.PrettyPrinter(indent=4)

        # if identity.has_key('realm'):
        #    identity.update( { 'realm' : identity['realm'] } )

        return identity
