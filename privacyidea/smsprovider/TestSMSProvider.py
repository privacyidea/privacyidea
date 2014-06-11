# -*- coding: utf-8 -*-
#
#    privacyIDEA is a fork of LinOTP
#    May 28, 2014 Cornelius Kölbel
#    E-mail: info@privacyidea.org
#    Contact: www.privacyidea.org
#
#    Copyright (C) LinOTP: 2010 - 2014 LSE Leading Security Experts GmbH
#
#    This program is free software: you can redistribute it and/or
#    modify it under the terms of the GNU Affero General Public
#    License, version 3, as published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the
#               GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

#

"""
                This is a dummy class for testing
"""
from privacyidea.smsprovider.SMSProvider import ISMSProvider


import logging
log = logging.getLogger(__name__)


class TestSMSProvider(ISMSProvider):
    def __init__(self):
        self.config = {}

    '''
      submitMessage()
      - send out a message to a phone

    '''

    def submitMessage(self, phone, message):
        return

    def getParameters(self, message, phone):
        return

    def loadConfig(self, configDict):
        self.config = configDict

