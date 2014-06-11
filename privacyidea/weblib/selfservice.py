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
'''            
  Description:  base functions for the selfservice

  Dependencies: -

'''


from pylons import config
from privacyidea.lib.log import log_with
import logging
log = logging.getLogger(__name__)

@log_with(log)
def get_imprint(realm):
    '''
    This function returns the imprint for a certai realm.
    This is just the contents of the file <realm>.imprint in the directory
    <imprint_directory>
    '''
    res = ""
    realm = realm.lower()
    directory = config.get("privacyidea.imprint_directory", "/etc/privacyidea/imprint")
    filename = "%s/%s.imprint" % (directory, realm)
    try:
        pass
        f = open(filename)
        res = f.read()
        f.close()
    except Exception as e:
        log.info("can not read imprint file: %s. (%r)"
                 % (filename, e))

    return res
