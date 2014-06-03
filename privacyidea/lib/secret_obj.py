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
'''This file is part of the privacyidea service
                It checks the given static password against the otpkey.
'''
from privacyidea.lib.crypto import zerome

import logging
log = logging.getLogger(__name__)


class secretPassword:

    def __init__(self, secObj):
        self.secretObject = secObj

    def checkOtp(self, anOtpVal):
        res = -1

        key = self.secretObject.getKey()

        if key == anOtpVal:
            res = 0

        zerome(key)
        del key

        return res
