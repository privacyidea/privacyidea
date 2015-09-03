# -*- coding: utf-8 -*-
#
#  http://www.privacyidea.org
#  2015-09-03 Initial writeup.
#             Cornelius Kölbel <cornelius@privacyidea.org>
#
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
__doc__ = """
The OCRA class provides an OCRA object, that can handle all OCRA tasks and
do all calculations.

http://tools.ietf.org/html/rfc6287

The OCRA class is tested in tests/test_lib_tokens_tiqr.py
"""

from privacyidea.lib.crypto import (geturandom, get_rand_digit_str,
                                    get_alphanum_str)


class OCRASuite(object):

    def __init__(self, ocrasuite):
        """
        Check if the given *ocrasuite* is a valid ocrasuite according to
        chapter 6 of RFC6287.

        If it is not a valid OCRA Suite an exception is raised.

        :param ocrasuite: The OCRAsuite
        :type ocrasuite: basestring
        :return: bool
        """
        ocrasuite = ocrasuite.upper()
        algo_crypto_data = ocrasuite.split(":")
        if len(algo_crypto_data) != 3:
            raise Exception("The OCRAsuite consists of three fields "
                            "'algorithm', 'cryptofunction' and 'datainput' "
                            "delimited by ':'")
        self.algorithm = algo_crypto_data[0]
        self.cryptofunction = algo_crypto_data[1]
        self.datainput = algo_crypto_data[2]

        # Test algorithm
        if self.algorithm != "OCRA-1":
            raise Exception("Error in algorithm. At the moment only version "
                            "OCRA-1 is supported.")

        # Test cryptofunction
        hotp_sha_trunc = self.cryptofunction.split("-")
        if len(hotp_sha_trunc) != 3:
            raise Exception("The cryptofunction consists of three fields "
                            "'HOTP', 'SHA' and 'Truncation' "
                            "delimited by '-'")
        hotp = hotp_sha_trunc[0]
        self.sha = hotp_sha_trunc[1]
        self.truncation = int(hotp_sha_trunc[2])
        if hotp != "HOTP":
            raise Exception("Only HOTP is allowed. You specified %s" % hotp)
        if self.sha not in ["SHA1", "SHA256", "SHA512"]:
            raise Exception("Only SHA1, SHA256 or SHA512 is allowed. You "
                            "specified %s" % self.sha)
        if self.truncation not in [0, 4, 5, 6, 7, 8, 9, 10]:
            raise Exception("Only truncation of 0 or 4-10 is allowed. "
                            "You specified %s" % self.truncation)

        ########################################################
        # test datainput
        counter_input_signature = self.datainput.split("-")
        if len(counter_input_signature) not in [2, 3]:
            raise Exception("Error in datainput. The datainput must consist "
                            "of 2 or 3 fields separated by '-'")
        if len(counter_input_signature) == 2:
            self.counter = None
            self.challenge = counter_input_signature[0]
            self.signature = counter_input_signature[1]
        elif len(counter_input_signature) == 3:
            self.counter = counter_input_signature[0]
            self.challenge = counter_input_signature[1]
            self.signature = counter_input_signature[2]

            if self.counter != "C":
                raise Exception("The counter in the datainput must be 'C'")

        # test challenge
        # the first two characters of the challenge need to be Q[A|N|H]
        self.challenge_type = self.challenge[:2]
        if self.challenge_type not in ["QA", "QH", "QN"]:
            raise Exception("Error in challenge. The challenge must start "
                            "with QA, QN or QH. You specified %" %
                            self.challenge)

        self.challenge_length = 0
        try:
            self.challenge_length = int(self.challenge[2:])
        except ValueError:
            raise Exception("The last characters in the challenge must be a "
                            "number. You specified %s" % self.challenge)

        if self.challenge_length < 4 or self.challenge_length > 64:
            raise Exception("The length of the challenge must be specified "
                            "between 4 and 64. You specified %s" %
                            self.challenge_length)

        # signature
        self.signature_type = self.signature[0]
        if self.signature_type not in ["P", "S", "T"]:
            raise Exception("The signature needs to be P, S or T. You "
                            "specified %s" % self.signature_type)
        if self.signature_type == "P":
            # P is followed by a Hashing Algorithm SHA1, SHA256, SHA512
            self.signature_hash = self.signature[1:]
            if self.signature_hash not in ["SHA1", "SHA256", "SHA512"]:
                raise Exception("The signature hash needs to be SHA1, SHA256 "
                                "or SHA512")
        elif self.signature_type == "S":
            # Allowed Session length is 64, 128, 256 or 512
            try:
                self.session_length = int(self.signature[1:])
            except ValueError:
                raise Exception("The session length needs to be a number.")
            if self.session_length not in [64, 128, 256, 512]:
                raise Exception("The session length needs to be 64, 128, "
                                "256 or 512")

        elif self.signature_type == "T":
            # Allowed timestamp is [1-59]S, [1-56]M, [0-48]H
            self.time_frame = self.signature[-1:]
            if self.time_frame not in ["S", "M", "H"]:
                raise Exception("The time in the signature must be 'S', 'M' or "
                                "'H'")
            self.time_value = self.signature[1:-1]
            try:
                self.time_value = int(self.time_value)
            except ValueError:
                raise Exception("You must specify a valid number in the "
                                "timestamp in the signature.")
            if self.time_value < 0 or self.time_value > 59:
                raise Exception("You must specify a time value between 0 and "
                                "59.")

    def create_challenge(self):
        """
        Depending on the self.challenge_type and the self.challenge_length
        we create a challenge
        :return: a challenge string
        """
        ret = None
        if self.challenge_type == "QH":
            ret = geturandom(length=self.challenge_length, hex=True)
        elif self.challenge_type == "QA":
            ret = get_alphanum_str(self.challenge_length)
        elif self.challenge_type == "QN":
            ret = get_rand_digit_str(length=self.challenge_length)

        if not ret:  # pragma: no cover
            raise Exception("OCRA.create_challenge failed. Obviously no good "
                            "challenge_type!")

        return ret
