# -*- coding: utf-8 -*-
#
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
from pylons import request
from privacyidea.lib.config import getFromConfig
from privacyidea.lib.util import get_client_from_param
from privacyidea.lib.util import get_client_from_request

import logging

log = logging.getLogger(__name__)


def get_client():
    '''
    This function returns the client.

    It first tries to get the client as it is passed as the HTTP Client via REMOTE_ADDR.

    If this client Address is in a list, that is allowed to overwrite its client address (like e.g.
    a FreeRADIUS server, which will always pass the FreeRADIUS address but not the address of the
    RADIUS client) it checks for the existance of the client parameter.
    '''
    may_overwrite = []
    over_client = getFromConfig("mayOverwriteClient", "")
    log.debug("config entry mayOverwriteClient: %s" % over_client)
    try:
        may_overwrite = [ c.strip() for c in over_client.split(',') ]
    except Exception as e:
        log.warning("evaluating config entry 'mayOverwriteClient': %r" % e)

    client = get_client_from_request(request)
    log.debug("got the original client %s" % client)

    if client in may_overwrite or client == None:
        log.debug("client %s may overwrite!" % client)
        if get_client_from_param(request.params):
            client = get_client_from_param(request.params)
            log.debug("client overwritten to %s" % client)

    log.debug("returning %s" % client)
    return client
