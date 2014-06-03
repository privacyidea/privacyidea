# -*- coding: utf-8 -*-
#
#    privacyIDEA Account test suite
# 
#    Copyright (C)  2014 Cornelius Kölbel, cornelius@privacyidea.org
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
from privacyidea.tests import TestController, url
from webtest.app import AppError

log = logging.getLogger(__name__)

class TestAccountController(TestController):



    def test_login(self):
        try:
            response = self.app.get(url(controller='account', action='login'), params={"login" : "user",
                                                                                       "password" : "password"})
            print response
        except AppError as ae:
            self.assertTrue('576 Logout from privacyIDEA selfservice' in u"%r" % ae)