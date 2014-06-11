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
from privacyidea.tests import TestController, url


class TestYubikeyController(TestController):

    def test_yubico_mode(self):
        """
        Enroll and test the Yubikey in yubico (AES) mode
        """
        serialnum = "01382015"
        yubi_slot = 1
        serial = "UBAM%s_%s" % (serialnum, yubi_slot)
        otpkey = "9163508031b20d2fbb1868954e041729"
        parameters = {
            'type': 'yubikey',
            'serial': serial,
            'otpkey': otpkey,
            'otplen': 48,
            'description': "Yubikey enrolled in functional tests"
        }
        public_uid = "ecebeeejedecebeg"

        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        assert '"value": true' in response
        ## test initial assign
        parameters = {"serial":serial, "user": "root" }
        response = self.app.get(url(controller='admin', action='assign'), params=parameters)
        # Test response...
        assert '"value": true' in response

        valid_otps = [
            public_uid + "fcniufvgvjturjgvinhebbbertjnihit",
            public_uid + "tbkfkdhnfjbjnkcbtbcckklhvgkljifu",
            public_uid + "ktvkekfgufndgbfvctgfrrkinergbtdj",
            public_uid + "jbefledlhkvjjcibvrdfcfetnjdjitrn",
            public_uid + "druecevifbfufgdegglttghghhvhjcbh",
            public_uid + "nvfnejvhkcililuvhntcrrulrfcrukll",
            public_uid + "kttkktdergcenthdredlvbkiulrkftuk",
            public_uid + "hutbgchjucnjnhlcnfijckbniegbglrt",
            public_uid + "vneienejjnedbfnjnnrfhhjudjgghckl",
            public_uid + "krgevltjnujcnuhtngjndbhbiiufbnki",
            public_uid + "kehbefcrnlfejedfdulubuldfbhdlicc",
            public_uid + "ljlhjbkejkctubnejrhuvljkvglvvlbk",
            public_uid + "eihtnehtetluntirtirrvblfkttbjuih",
        ]

        for otp in valid_otps:
            response = self.app.get(url(controller='validate', action='check_s'),
                                    params={'serial': serial, 'pass': otp})
            assert '"value": true' in response

        # Repeat an old (therefore invalid) OTP value
        invalid_otp = public_uid + "fcniufvgvjturjgvinhebbbertjnihit"
        response = self.app.get(url(controller='validate', action='check_s'),
                                params={'serial': serial, 'pass': invalid_otp})
        assert '"value": false' in response
