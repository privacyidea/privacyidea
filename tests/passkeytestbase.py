# (c) NetKnights GmbH 2024,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2024 Nils Behlen <nils.behlen@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
import json
import unittest


class PasskeyTestBase(unittest.TestCase):
    def setUp(self):
        self.expected_origin = "https://cool.nils:5000"
        self.rp_id = "cool.nils"
        # Registration data
        self.registration_attestation = ("o2NmbXRmcGFja2VkZ2F0dFN0bXSjY2FsZyZjc2lnWEcwRQIgK7ebYj05Y6qA+24k8agpjVT2mlang"
                                         "mxPaSuX4uRzbXsCIQCwMxSuGqo7fQ7mALIgJACL7rsijjAIYTRztmeN11esk2N4NWOBWQLdMIIC2T"
                                         "CCAcGgAwIBAgIJAPDqu31oBEyKMA0GCSqGSIb3DQEBCwUAMC4xLDAqBgNVBAMTI1l1YmljbyBVMkY"
                                         "gUm9vdCBDQSBTZXJpYWwgNDU3MjAwNjMxMCAXDTE0MDgwMTAwMDAwMFoYDzIwNTAwOTA0MDAwMDAw"
                                         "WjBvMQswCQYDVQQGEwJTRTESMBAGA1UECgwJWXViaWNvIEFCMSIwIAYDVQQLDBlBdXRoZW50aWNhd"
                                         "G9yIEF0dGVzdGF0aW9uMSgwJgYDVQQDDB9ZdWJpY28gVTJGIEVFIFNlcmlhbCAyMTA5NDY3Mzc2MF"
                                         "kwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE5mfTO7qcRZuAnvzLaguuLFz8S9eB1XNIPZb96SUfZCz"
                                         "N5sIGVRTzM4JGrJlSgAAq0jivvANxttf6w7/LnnnSMKOBgTB/MBMGCisGAQQBgsQKDQEEBQQDBQQD"
                                         "MCIGCSsGAQQBgsQKAgQVMS4zLjYuMS40LjEuNDE0ODIuMS43MBMGCysGAQQBguUcAgEBBAQDAgQwM"
                                         "CEGCysGAQQBguUcAQEEBBIEEC/AV5+BE0fqsRa7Wo25ICowDAYDVR0TAQH/BAIwADANBgkqhkiG9w"
                                         "0BAQsFAAOCAQEAtjGoKNeTOK0pAIoNf3mjoD3PLgybH2L6z7SKnlWVd6dRbJWbZCsY8AxMdyKNGfn"
                                         "UQiJcEmi9IxigjGoXcwZPApnJm7JDike7Z7HQ2yUrlJZ+EgFamivp5C3UVCaIkGH+HyJW/vh23XOZ"
                                         "MkaDcRqwbeq8b0Voavnu4YF5bCM7PtnsPcCsvfL5DahPGSfpc9YyANG49OQBOZolNF3MBKKrspOAI"
                                         "7RfW0JSQY0NUnWFYx9hxFbNuYsKFN4NblJ/Zz9tMk1YYSkTJ6VfxHTo5tfIcaLfZ1dIrMeY12+Wev"
                                         "jMufFW/qB4ErY5Gjft3cbiZBELmbQ9QLUyLX78lHiLC9pJImhhdXRoRGF0YVjCtPp8c+wXo6hFUbd"
                                         "edkHcOP1s+xkwOrHsxfvNfhI7wVfFAAAABC/AV5+BE0fqsRa7Wo25ICoAMOahMN3L0hTTKOfgQKQd"
                                         "7CE080aCZ5vjyLKK+L9iNUda3jORikb6O6r4tHO5VCczX6UBAgMmIAEhWCDmoTDdy9IU0yjn4ECkq"
                                         "0qarKlb9ievA0lEmPteOlIaDCJYINGjogwc489wfkT98B/X7M8WedSRt/OxnI042/+4MWMQoWtjcm"
                                         "VkUHJvdGVjdAI=")
        self.registration_client_data = ("eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiY1dGMlVWZDBUalZQYmpGVk1Xe"
                                         "HNkR0p4ZFY5emQwVnBiSFJFWldwVFMxWkJWV0p3VjJoMU0zQjFNQSIsIm9yaWdpbiI6Imh0dHBzOi"
                                         "8vY29vbC5uaWxzOjUwMDAiLCJjcm9zc09yaWdpbiI6ZmFsc2V9")
        self.registration_cred_id = "5qEw3cvSFNMo5-BApB3sITTzRoJnm-PIsor4v2I1R1reM5GKRvo7qvi0c7lUJzNf"
        self.authenticator_attachment = "cross-platform"
        self.registration_challenge = "qavQWtN5On1U1lltbqu_swEiltDejSKVAUbpWhu3pu0"

        # Authentication data
        self.authentication_challenge = "EMQVDNhU9A3wx8wYUESd-S2uUiy5f8LObeipZTGu8PM"
        self.authenticator_data = "tPp8c+wXo6hFUbdedkHcOP1s+xkwOrHsxfvNfhI7wVcFAAAACA=="
        self.authentication_client_data = ("eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiUlUxUlZrUk9hRlU1UVROM2VEaDN"
                                           "XVlZGVTJRdFV6SjFWV2w1TldZNFRFOWlaV2x3V2xSSGRUaFFUUSIsIm9yaWdpbiI6Imh0dHBzOi"
                                           "8vY29vbC5uaWxzOjUwMDAiLCJjcm9zc09yaWdpbiI6ZmFsc2UsIm90aGVyX2tleXNfY2FuX2JlX"
                                           "2FkZGVkX2hlcmUiOiJkbyBub3QgY29tcGFyZSBjbGllbnREYXRhSlNPTiBhZ2FpbnN0IGEgdGVt"
                                           "cGxhdGUuIFNlZSBodHRwczovL2dvby5nbC95YWJQZXgifQ==")
        self.authentication_signature = ("MEYCIQD4tLRDFmbG2eE3vFqoaMtxErUvAFmtDROOgDgpWFMEggIhAIBnQFKtPTZKWSIh/yGG25yDv"
                                         "eC6WHkK8R9PL7sivb/1")
        self.user_handle = "VUVsUVN6QXdNREUwTTBVdw=="
        self.credential_id = "NXFFdzNjdlNGTk1vNS1CQXBCM3NJVFR6Um9Kbm0tUElzb3I0djJJMVIxcmVNNUdLUnZvN3F2aTBjN2xVSnpOZg"
        self.authentication_response = {
            "clientDataJSON": self.authentication_client_data,
            "authenticatorData": self.authenticator_data,
            "signature": self.authentication_signature,
            "userHandle": self.user_handle,
            "credentialId": self.credential_id,
            "HTTP_ORIGIN": self.expected_origin
        }

    def validate_default_passkey_registration(self, passkey_registration:str):
        """
        Validates the passkey registration response with the default values and the values set in this class
        Only checks if pubKeyCredParams and excludeCredentials exists not their content
        """
        pk_reg = json.loads(passkey_registration)
        # RP
        self.assertIn("rp", pk_reg)
        self.assertEqual(pk_reg["rp"]["id"], self.rp_id)
        self.assertEqual(pk_reg["rp"]["name"], self.rp_id)
        # User
        self.assertIn("user", pk_reg)
        self.assertIn("name", pk_reg["user"])
        self.assertEqual("hans", pk_reg["user"]["name"])
        self.assertIn("id", pk_reg["user"])
        self.assertIn("displayName", pk_reg["user"])
        # Challenge should be the mock_nonce
        self.assertIn("challenge", pk_reg)
        self.assertEqual(self.registration_challenge, pk_reg["challenge"])
        # PubKeyCredParams: Via the API, all three key algorithms are valid by default
        self.assertIn("pubKeyCredParams", pk_reg)
        self.assertIn("timeout", pk_reg)
        self.assertIn("excludeCredentials", pk_reg)
        # AuthenticatorSelection: Require residentKey and userVerification is preferred by default
        self.assertIn("authenticatorSelection", pk_reg)
        self.assertEqual(pk_reg["authenticatorSelection"]["requireResidentKey"], True)
        self.assertEqual(pk_reg["authenticatorSelection"]["residentKey"], "required")
        self.assertEqual(pk_reg["authenticatorSelection"]["userVerification"], "preferred")
        # Attestation is none by default
        self.assertEqual(pk_reg["attestation"], "none")