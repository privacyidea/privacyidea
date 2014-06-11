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
  Description: Helper functions
                Consists of functions to typically be used within templates, but also
                available to Controllers. This module is available to templates as 'h'. 
      
  Dependencies: -

'''

# Import helpers as desired, or define your own, ie:
#from webhelpers.html.tags import checkbox, password
import logging


#CKO: depending on the version there are two different possible locations...
# see http://stackoverflow.com/questions/2219316/pylons-webhelpers-missing-secure-form-module
from privacyidea.lib.error import ParameterError


log = logging.getLogger(__name__)

def getParam(param, which, optional):
    if param.has_key(which):
        return  param[which]
    else:
        if (optional == False):
            raise ParameterError("Missing parameter: %r" % which, id=905)
    return
