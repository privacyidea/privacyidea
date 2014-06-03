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
'''idetify if module runs in selftest
'''

from privacyidea.lib.config import getFromConfig

import logging
log = logging.getLogger(__name__)


def isSelfTest():
    '''
        check if we are running in the selftest mode, which is
        used especially for debugging / development or unit tests
        
        @return : True or False
        @rtype  : boolean
    '''
    ret = False

    if False != getFromConfig("selfTest", False):
        ret = True

    return ret




