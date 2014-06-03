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
        
