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

log = logging.getLogger(__name__)

class TestOrphanedTokens(TestController):


    def test_httperror(self):

        param = { 'otpkey': 'AD8EABE235FC57C815B26CEF3709075580B44738',
                  'user': 'root', 'pin':'pin', 'serial':'T2', 'type':'spass', 'resConf':'def'
                 }

        response = self.app.get(url(controller='admin', action='init'), params=param)
        assert '"status": false,' in response


        param = { 'otpkey': 'AD8EABE235FC57C815B26CEF3709075580B44738',
                  'user': 'root', 'pin':'pin', 'serial':'T2', 'type':'spass', 'resConf':'def', 'httperror':'400'
                 }
        try:
            response = self.app.get(url(controller='admin', action='init'), params=param)
        except Exception as e:
            httperror = e.args[0]
            assert "400 Bad Request" in httperror


        param = { 'otpkey': 'AD8EABE235FC57C815B26CEF3709075580B44738',
                  'user': 'root', 'pin':'pin', 'serial':'T2', 'type':'spass', 'resConf':'def', 'httperror':''
                 }
        try:
            response = self.app.get(url(controller='admin', action='init'), params=param)
        except Exception as e:
            httperror = e.args[0]
            assert "500 Internal Server Error" in httperror

        return


