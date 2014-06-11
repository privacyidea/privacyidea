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
'''
Description:  functional tests
                
Dependencies: -
'''

import logging
from privacyidea.tests import TestController, url
from webtest.app import AppError

log = logging.getLogger(__name__)

class TestAuditController(TestController):



    def test_audit_search(self):
        response = self.app.get(url(controller='audit', action='search'), params={})
        print response
        self.assertTrue('page": 1,' in response)
        
        response = self.app.get(url(controller='audit', action='search'), params={"sortname" : "serial",
                                                                                  "outform" : "csv"})
        print response
        self.assertTrue(' null, "INFO", "0"' in response)
        
