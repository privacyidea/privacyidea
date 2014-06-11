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
from privacyidea.lib.config import storeConfig
from privacyidea.lib.config import get_privacyIDEA_config
from privacyidea.lib.config import removeFromConfig
import re 
from privacyidea.lib.error import ServerError
from privacyidea.lib.log import log_with
import logging
log = logging.getLogger(__name__)

@log_with(log)
def deletePolicy(name):
    '''
    Function to delete one named policy

    attributes:
        name:   (required) will only return the policy with the name
    '''
    res = {}
    if not re.match('^[a-zA-Z0-9_]*$', name):
        raise ServerError("policy name may only contain the "
                          "characters a-zA-Z0-9_", id=8888)

    Config = get_privacyIDEA_config()
    delEntries = []
    for entry in Config:
        if entry.startswith("privacyidea.Policy.%s." % name):
            delEntries.append(entry)

    for entry in delEntries:
        #delete this entry.
        log.debug("removing key: %s" % entry)
        ret = removeFromConfig(entry)
        res[entry] = ret

    return res

@log_with(log)
def setPolicy(param):
    '''
    Function to set a policy. It expects a dict of with the following keys:

      * name
      * action
      * scope
      * realm
      * user
      * time
      * client
      
    '''
    ret = {}
    name = param.get('name')
    action = param.get('action')
    scope = param.get('scope')
    realm = param.get('realm')
    user = param.get('user')
    time = param.get('time')
    client = param.get('client')
    active = param.get('active', True)
    ret["action"] = storeConfig("Policy.%s.action" % name,
                                action, "", "a policy definition")
    ret["scope"] = storeConfig("Policy.%s.scope" % name,
                               scope, "", "a policy definition")
    ret["realm"] = storeConfig("Policy.%s.realm" % name,
                               realm, "", "a policy definition")
    ret["user"] = storeConfig("Policy.%s.user" % name,
                              user, "", "a policy definition")
    ret["time"] = storeConfig("Policy.%s.time" % name,
                              time, "", "a policy definition")
    ret["client"] = storeConfig("Policy.%s.client" % name,
                                client, "", "a policy definition")
    ret["active"] = storeConfig("Policy.%s.active" % name,
                                active, "", "a policy definition")

    return ret
