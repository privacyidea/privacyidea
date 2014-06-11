# -*- coding: utf-8 -*-
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
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
from privacyidea.lib.log import log_with

from pylons import request, config, tmpl_context as c
from privacyidea.lib.config import get_privacyIDEA_config
from privacyidea.lib.policy import PolicyClass
ENCODING = "utf-8"


class UserModelPlugin(object):

    @log_with(log)
    def authenticate(self, environ, identity):
        username = None
        realm = None
        success = None
        try:
            if isSelfTest():
                if identity.has_key('login') == False and identity.has_key('repoze.who.plugins.auth_tkt.userid') == True:
                    u = identity.get('repoze.who.plugins.auth_tkt.userid')
                    identity['login'] = u
                    identity['password'] = u

            if getRealmBox():
                username = identity['login']
                realm = identity['realm']
            else:
                log.debug("no realmbox, so we are trying to split the loginname")
                m = re.match("(.*)\@(.*)", identity['login'])
                if m:
                    if 2 == len(m.groups()):
                        username = m.groups()[0]
                        realm = m.groups()[1]
                        log.debug("found @: username: %r, realm: %r" % (username, realm))
                else:
                    username = identity['login']
                    realm = getDefaultRealm()
                    log.debug("using default Realm: username: %r, realm: %r" % (username, realm))

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
                success = authenticate_privacyidea_user(username, realm, password) 
            else:
                # We do authentication against the user store
                success = check_user_password(username, realm, password)

        if not success and is_admin_identity("%s@%s" % (username, realm), exception=False):
            # user not found or authenticated in resolver. 
            # So let's see, if this is an administrative user.
            success = check_admin_password(username, password, realm)

        if success:
            log.info("User %r authenticated" % success)
        return success

    @log_with(log)
    def add_metadata(self, environ, identity):
        #username = identity.get('repoze.who.userid')
        #user = User.get(username)
        #user = "conelius koelbel"
        #log.info( "add_metadata: %s" % identity )

        #pp = pprint.PrettyPrinter(indent=4)

        #if identity.has_key('realm'):
        #    identity.update( { 'realm' : identity['realm'] } )


        return identity
