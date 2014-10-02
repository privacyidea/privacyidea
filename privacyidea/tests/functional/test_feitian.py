# -*- coding: utf-8 -*-
#
#    privacyIDEA Feitian ChalRep test suite
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
log = logging.getLogger(__name__)
import unittest
from privacyidea.lib.feitian import (calculate_optical_data,
                                     create_image,
                                     ACCOUNT,
                                     AMOUNT)


class TestFeitianChalRep(unittest.TestCase):

    def setUp(self):
        pass
    
    def test_feitian_chal_12345678(self):
        # data for challenge 12345678
        demo_data_challenge = [0, 1, 2, 0, 1, 2, 1, 0, 1, 0, 2, 1, 0, 1, 0, 2,
                               1, 0, 2, 1, 2, 1, 0, 1, 0, 2, 1, 2, 0, 2, 0, 2,
                               1, 0, 1, 0, 1, 0, 1, 2, 1, 0, 1, 2, 0, 1, 0, 2,
                               1, 0, 2, 0]
        optical = calculate_optical_data(value="12345678")
        print "-" * 70
        print "Cha D: %s" % demo_data_challenge
        print "Cha O: %s " % optical
        create_image(optical)
        assert demo_data_challenge == optical
    
    def test_feitian_chal_12345(self):
        # data for account 12345
        demo_data_account = [0, 1, 2, 0, 1, 2, 1, 2, 0, 2, 1, 0, 2, 1, 2, 1, 2,
                             1, 0, 2, 0, 2, 1, 2, 1, 0, 2, 0, 1, 0, 1, 0, 2, 1,
                             2, 1, 2, 1, 2, 0]
        optical = calculate_optical_data(value="12345", type=ACCOUNT)
        print "-" * 70
        print "Acc D: %s" % demo_data_account
        print "Acc O: %s " % optical
        create_image(optical, outfile="account.gif")
        assert demo_data_account == optical
    
    def test_feitian_chal_amount(self):
        # data for amount
        demo_data_amount = [0, 1, 2, 0, 1, 2, 1, 2, 1, 0, 2, 1, 0, 2, 0, 2, 0,
                            2, 0, 1, 0, 2, 0, 1, 2, 0, 2, 1, 0, 1, 0, 2, 0, 2,
                            1, 0, 2, 1, 2, 0]
        optical = calculate_optical_data(value="67890", type=AMOUNT)
        print "-" * 70
        print "Amo D: %s" % demo_data_amount
        print "Amo O: %s " % optical
        create_image(optical, outfile="amount.gif")
        assert demo_data_amount == optical
    
    
if __name__ == '__main__':
    unittest.main()