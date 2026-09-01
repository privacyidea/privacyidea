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
import unittest


class PasskeyTestBase(unittest.TestCase):
    def setUp(self):
        self.expected_origin = "https://cool.nils:5000"
        self.rp_id = "cool.nils"
        # Registration data
        self.registration_attestation = (
            "o2NmbXRmcGFja2VkZ2F0dFN0bXSjY2FsZyZjc2lnWEYwRAIgTvRUAlwwtn9kmWGvIDZSdeIuOK/g8nK8icbnroQT2M8CIAqv3A0nH0m8j1"
            "yuNvgfTHt3FOgItHgcqYqefBVoU7zYY3g1Y4FZAt0wggLZMIIBwaADAgECAgkA8Oq7fWgETIowDQYJKoZIhvcNAQELBQAwLjEsMCoGA1UE"
            "AxMjWXViaWNvIFUyRiBSb290IENBIFNlcmlhbCA0NTcyMDA2MzEwIBcNMTQwODAxMDAwMDAwWhgPMjA1MDA5MDQwMDAwMDBaMG8xCzAJBg"
            "NVBAYTAlNFMRIwEAYDVQQKDAlZdWJpY28gQUIxIjAgBgNVBAsMGUF1dGhlbnRpY2F0b3IgQXR0ZXN0YXRpb24xKDAmBgNVBAMMH1l1Ymlj"
            "byBVMkYgRUUgU2VyaWFsIDIxMDk0NjczNzYwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAATmZ9M7upxFm4Ce/MtqC64sXPxL14HVc0g9lv"
            "3pJR9kLM3mwgZVFPMzgkasmVKAACrSOK+8A3G21/rDv8ueedIwo4GBMH8wEwYKKwYBBAGCxAoNAQQFBAMFBAMwIgYJKwYBBAGCxAoCBBUx"
            "LjMuNi4xLjQuMS40MTQ4Mi4xLjcwEwYLKwYBBAGC5RwCAQEEBAMCBDAwIQYLKwYBBAGC5RwBAQQEEgQQL8BXn4ETR+qxFrtajbkgKjAMBg"
            "NVHRMBAf8EAjAAMA0GCSqGSIb3DQEBCwUAA4IBAQC2Mago15M4rSkAig1/eaOgPc8uDJsfYvrPtIqeVZV3p1FslZtkKxjwDEx3Io0Z+dRC"
            "IlwSaL0jGKCMahdzBk8CmcmbskOKR7tnsdDbJSuUln4SAVqaK+nkLdRUJoiQYf4fIlb++Hbdc5kyRoNxGrBt6rxvRWhq+e7hgXlsIzs+2e"
            "w9wKy98vkNqE8ZJ+lz1jIA0bj05AE5miU0XcwEoquyk4AjtF9bQlJBjQ1SdYVjH2HEVs25iwoU3g1uUn9nP20yTVhhKRMnpV/EdOjm18hx"
            "ot9nV0isx5jXb5Z6+My58Vb+oHgStjkaN+3dxuJkEQuZtD1AtTItfvyUeIsL2kkiaGF1dGhEYXRhWLS0+nxz7BejqEVRt152Qdw4/Wz7GT"
            "A6sezF+81+EjvBV0UAAAAEL8BXn4ETR+qxFrtajbkgKgAwT9TJpDbUuq0TIdIpErltERuboEdR1GBa7pVtdYMQYTQZ582wmBwp5TWuZ/sE"
            "/Ag4pQECAyYgASFYIE/UyaQ21LqtEyHSKRJpShO+wOGDv7qDWURk30/U26xtIlgglAzzrE4UkAFqhrNdg2OToNFk6it8EAzLuZwfWM8ney"
            "c=")
        self.registration_client_data = ("eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiUWtZeU16Uk5iV3hwVFVwb05re"
                                         "FhOVUZpT0RoUWJpMWtUVXBXUjBvMk5qQkxibEpoTTJaR2QwNVdVUSIsIm9yaWdpbiI6Imh0dHBzOi"
                                         "8vY29vbC5uaWxzOjUwMDAifQ==")
        self.credential_id = "T9TJpDbUuq0TIdIpErltERuboEdR1GBa7pVtdYMQYTQZ582wmBwp5TWuZ_sE_Ag4"
        self.authenticator_attachment = "cross-platform"
        self.registration_challenge = "BF234MmliMJh6LW5Ab88Pn-dMJVGJ660KnRa3fFwNVQ"
        self.user_handle = "MUgalqvLZPGWqucFj7GKXiUtx3ZzIkHJtNbmrwc5PbzAKlGB/As1IKa8jjfUnidVw1qK7YgoZMDanf1yVnVryQ=="

        # Authentication data NO UV
        self.authentication_challenge_no_uv = "SPRITfnl8pStiyaHx4v0kgdmNy5HdLCUvBjIsd5PUV0"
        self.authenticator_data_no_uv = "tPp8c+wXo6hFUbdedkHcOP1s+xkwOrHsxfvNfhI7wVcBAAAABg=="
        self.authentication_client_data_no_uv = ("eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiVTFCU1NWUm1ibXc0Y0ZOM"
                                                 "GFYbGhTSGcwZGpCcloyUnRUbmsxU0dSTVExVjJRbXBKYzJRMVVGVldNQSIsIm9yaWdpbi"
                                                 "I6Imh0dHBzOi8vY29vbC5uaWxzOjUwMDAifQ==")
        self.authentication_signature_no_uv = ("MEUCIQCDrNi+Jf50YslBH7qXSQIaieA9kgHdUvefxuMYeFcSvgIgfZado1mzhj/ORaawpyv"
                                               "RIAXJRmaD1sruO5PVlJRi6xg=")
        self.authentication_response_no_uv = {
            "clientDataJSON": self.authentication_client_data_no_uv,
            "authenticatorData": self.authenticator_data_no_uv,
            "signature": self.authentication_signature_no_uv,
            "userHandle": self.user_handle,
            "credential_id": self.credential_id,
        }

        # Authentication data WITH UV
        self.authentication_challenge_uv = "MisSxHzhdilz_l3f_qH6YkR1eQkmPQ7DDWsvrPkMDJQ"
        self.authenticator_data_uv = "tPp8c+wXo6hFUbdedkHcOP1s+xkwOrHsxfvNfhI7wVcFAAAADw=="
        self.authentication_client_data_uv = ("eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiVFdselUzaEllbWhrYVd4Nlgy"
                                              "d3pabDl4U0RaWmExSXhaVkZyYlZCUk4wUkVWM04yY2xCclRVUktVUSIsIm9yaWdpbiI6Imh0"
                                              "dHBzOi8vY29vbC5uaWxzOjUwMDAifQ==")
        self.authentication_signature_uv = ("MEYCIQDoJIuFrZKda+kKerNnSIVpUgb6dGHKTF6chAKN+ZUJGgIhAJP+nmIP1YOKBQ3HbJh7vv"
                                            "wKUSFZgxRODFg+Bm2vPPMR")
        self.authentication_response_uv = {
            "clientDataJSON": self.authentication_client_data_uv,
            "authenticatorData": self.authenticator_data_uv,
            "signature": self.authentication_signature_uv,
            "userHandle": self.user_handle,
            "credential_id": self.credential_id,
        }

        # Multi-device (backup-eligible) registration and authentication data. The backup-eligible flag
        # lives inside the signed region of authenticatorData, so it cannot be produced by editing the
        # single-device fixture above without invalidating its signature - this is a second, independently
        # generated credential (locally simulated ECDSA P-256 authenticator, not real hardware) that is
        # genuinely signed as backup-eligible, verified against the real py_webauthn verification functions
        # at generation time.
        self.registration_challenge_multi_device = "k-euGqXEZ15hg6lvGlJL9KlgN1FR9pkBlrCVtZswgmw"
        self.registration_attestation_multi_device = ("o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YViktPp8c+wXo6hFUbdedkHcOP1s"
                                                      "+xkwOrHsxfvNfhI7wVdZAAAAAAAAAAAAAAAAAAAAAAAAAAAAIJcUquK5S//Ox+jV"
                                                      "7luek0n1Zf7w56FwYhEB7s3kSlgkpQECAyYgASFYIBzOyVwt5sTQSqnib2fe3nnV"
                                                      "H4396fpRNWB71LqTGkm9IlggKG00jE6DEBYR/bFuRyPFNBEFdNVtKFHyGUTNzgu2"
                                                      "0tc=")
        self.registration_client_data_multi_device = ("eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiYXkxbGRVZHhX"
                                                      "RVZhTVRWb1p6WnNka2RzU2t3NVMyeG5UakZHVWpsd2EwSnNja05XZEZwemQyZHRk"
                                                      "dyIsIm9yaWdpbiI6Imh0dHBzOi8vY29vbC5uaWxzOjUwMDAifQ==")
        self.credential_id_multi_device = "lxSq4rlL_87H6NXuW56TSfVl_vDnoXBiEQHuzeRKWCQ"
        self.authenticator_attachment_multi_device = "platform"
        self.user_handle_multi_device = ("I3nF9Zf6ycQcCx/mp5Q+DIEO4qgtDUgIMf/tkBCXVpRJFRRPKWp31CVwjiZvNMMeBz6JAnImAP86m"
                                         "03YnvzXVw==")

        # Reject case: used with a SCOPE.AUTH policy restricting to single_device, must be denied
        self.authentication_challenge_multi_device_reject = "35lL32q5rzuXEwQrK6-BnxYkfl0lBnEDWX4xZKlxkaU"
        self.authenticator_data_multi_device_reject = "tPp8c+wXo6hFUbdedkHcOP1s+xkwOrHsxfvNfhI7wVcZAAAABg=="
        self.authentication_client_data_multi_device_reject = ("eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiTXpWc1R"
                                                               "ETXljVFZ5ZW5WWVJYZFJja3MyTFVKdWVGbHJabXd3YkVKdVJVUlhXRF"
                                                               "I0V2t0c2VHdGhWUSIsIm9yaWdpbiI6Imh0dHBzOi8vY29vbC5uaWxzO"
                                                               "jUwMDAifQ==")
        self.authentication_signature_multi_device_reject = ("MEUCIH/KO4HZuF/iupfGcTmrm3QHJbCHICYoiyn0Qo5yYioeAiEA7yy6B"
                                                             "sKFercCGLfOiquMnUypE6hUAi9jetjZdpvfuEE=")
        self.authentication_response_multi_device_reject = {
            "clientDataJSON": self.authentication_client_data_multi_device_reject,
            "authenticatorData": self.authenticator_data_multi_device_reject,
            "signature": self.authentication_signature_multi_device_reject,
            "userHandle": self.user_handle_multi_device,
            "credential_id": self.credential_id_multi_device,
        }

        # Accept case: used with a SCOPE.AUTH policy restricting to multi_device, must succeed
        self.authentication_challenge_multi_device_accept = "YIzIkO_EbEbNJhM8iVoYpy_DnOd9vwyCZhvJKALKJuc"
        self.authenticator_data_multi_device_accept = "tPp8c+wXo6hFUbdedkHcOP1s+xkwOrHsxfvNfhI7wVcdAAAABw=="
        self.authentication_client_data_multi_device_accept = ("eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiV1VsNlN"
                                                               "XdFBYMFZpUldKT1NtaE5PR2xXYjFsd2VWOUViazlrT1haM2VVTmFhSF"
                                                               "pLUzBGTVMwcDFZdyIsIm9yaWdpbiI6Imh0dHBzOi8vY29vbC5uaWxzO"
                                                               "jUwMDAifQ==")
        self.authentication_signature_multi_device_accept = ("MEQCIASyrpY4h90Dm9C0I+liwq8HW9avMtSGVNC6ipQN8jh/AiBFFw4HV"
                                                             "fcOHdamongh4gGEvV3iPUz6xF1GFVBoZKeyEw==")
        self.authentication_response_multi_device_accept = {
            "clientDataJSON": self.authentication_client_data_multi_device_accept,
            "authenticatorData": self.authenticator_data_multi_device_accept,
            "signature": self.authentication_signature_multi_device_accept,
            "userHandle": self.user_handle_multi_device,
            "credential_id": self.credential_id_multi_device,
        }

        # Tamper case: a genuine multi_device response with the backup-eligible bit flipped off in
        # authenticatorData while keeping the ORIGINAL signature (an attacker forging this has no private
        # key), used to prove the device type cannot be spoofed by editing the wire data post-signature.
        self.authentication_challenge_multi_device_tamper = "gEUBW03dsRdsNiJBDNVGQWkAlvWcMe-BnqIhf0Tqq10"
        self.authentication_client_data_multi_device_tamper = ("eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiWjBWVlF"
                                                               "sY3dNMlJ6VW1SelRtbEtRa1JPVmtkUlYydEJiSFpYWTAxbExVSnVjVW"
                                                               "xvWmpCVWNYRXhNQSIsIm9yaWdpbiI6Imh0dHBzOi8vY29vbC5uaWxzO"
                                                               "jUwMDAifQ==")
        self.authentication_signature_multi_device_tamper = ("MEUCIBCUHLeJC9HxmWA0UD+pvByYGktM4q82962So2EckbgYAiEAltK4n"
                                                             "2dZPw03hNtf4mhmUSC4OdiICmjOGR0fekQOGP4=")
        self.authenticator_data_multi_device_tamper_be_flipped = "tPp8c+wXo6hFUbdedkHcOP1s+xkwOrHsxfvNfhI7wVcFAAAACA=="
        self.authentication_response_multi_device_tamper = {
            "clientDataJSON": self.authentication_client_data_multi_device_tamper,
            "authenticatorData": self.authenticator_data_multi_device_tamper_be_flipped,
            "signature": self.authentication_signature_multi_device_tamper,
            "userHandle": self.user_handle_multi_device,
            "credential_id": self.credential_id_multi_device,
        }

    def validate_default_passkey_registration(self, passkey_registration: dict):
        """
        Validates the passkey registration response with the default values and the values set in this class
        Only checks if pubKeyCredParams and excludeCredentials exists not their content
        """
        # RP
        self.assertIn("rp", passkey_registration)
        self.assertEqual(passkey_registration["rp"]["id"], self.rp_id)
        self.assertEqual(passkey_registration["rp"]["name"], self.rp_id)
        # User
        self.assertIn("user", passkey_registration)
        self.assertIn("name", passkey_registration["user"])
        self.assertEqual("hans", passkey_registration["user"]["name"])
        self.assertIn("id", passkey_registration["user"])
        self.assertIn("displayName", passkey_registration["user"])
        # Challenge should be the mock_nonce
        self.assertIn("challenge", passkey_registration)
        self.assertEqual(self.registration_challenge, passkey_registration["challenge"])
        # PubKeyCredParams: Via the API, all three key algorithms are valid by default
        self.assertIn("pubKeyCredParams", passkey_registration)
        self.assertIn("timeout", passkey_registration)
        self.assertIn("excludeCredentials", passkey_registration)
        # AuthenticatorSelection: Require residentKey and userVerification is preferred by default
        self.assertIn("authenticatorSelection", passkey_registration)
        self.assertEqual(passkey_registration["authenticatorSelection"]["requireResidentKey"], True)
        self.assertEqual(passkey_registration["authenticatorSelection"]["residentKey"], "required")
        self.assertEqual(passkey_registration["authenticatorSelection"]["userVerification"], "preferred")
        # Attestation is none by default
        self.assertEqual(passkey_registration["attestation"], "none")
