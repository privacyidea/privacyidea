
from mock.mock import patch

from .base import MyApiTestCase
from privacyidea.models import TokenCredentialIdHash, TokenInfo
from privacyidea.lib.fido2.util import hash_credential_id
from privacyidea.lib.machine import attach_token, detach_token
from privacyidea.lib.policy import SCOPE, ACTION, set_policy, delete_policy
from privacyidea.lib.token import (get_tokens, init_token, remove_token,
                                   get_one_token)
from privacyidea.lib.tokenclass import ROLLOUTSTATE
from privacyidea.lib.tokens.webauthn import webauthn_b64_decode
from privacyidea.lib.user import User
from privacyidea.lib.utils import hexlify_and_unicode


class WebAuthn(MyApiTestCase):
    username = "selfservice"
    pin = "webauthnpin"
    serial = "WAN0001D434"

    def setUp(self):
        # Set up the WebAuthn Token from the lib test case
        super(MyApiTestCase, self).setUp()
        self.setUp_user_realms()

        set_policy("wan1", scope=SCOPE.ENROLL,
                   action="webauthn_relying_party_id=example.com")
        set_policy("wan2", scope=SCOPE.ENROLL,
                   action="webauthn_relying_party_name=example")

    def test_01_enroll_token_custom_description(self):
        client_data = "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoibmgwaUJ6MFNNbmRsVnNQUkdM" \
                      "dk9DUWMtUHByUHhPSmYzMEtlWm1UWFk5NCIsIm9yaWdpbiI6Imh0dHBzOi8vcGkuZXhhbXBsZS5jb" \
                      "20iLCJjcm9zc09yaWdpbiI6ZmFsc2V9"
        regdata = """o2NmbXRmcGFja2VkZ2F0dFN0bXSjY2FsZyZjc2lnWEgwRgIhANAt-cBR3mZglj13PZPXA3srJYxX
↵J6v-LzxAhmxZM7AsAiEAxu4gi8AiKOfyhU68HcIBHuIwgjBWJUlt4cIETWFYdetjeDVjgVkCwDCC
↵ArwwggGkoAMCAQICBAOt8BIwDQYJKoZIhvcNAQELBQAwLjEsMCoGA1UEAxMjWXViaWNvIFUyRiBS
↵b290IENBIFNlcmlhbCA0NTcyMDA2MzEwIBcNMTQwODAxMDAwMDAwWhgPMjA1MDA5MDQwMDAwMDBa
↵MG0xCzAJBgNVBAYTAlNFMRIwEAYDVQQKDAlZdWJpY28gQUIxIjAgBgNVBAsMGUF1dGhlbnRpY2F0
↵b3IgQXR0ZXN0YXRpb24xJjAkBgNVBAMMHVl1YmljbyBVMkYgRUUgU2VyaWFsIDYxNzMwODM0MFkw
↵EwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEGZ6HnBYtt9w57kpCoEYWpbMJ_soJL3a-CUj5bW6VyuTM
↵Zc1UoFnPvcfJsxsrHWwYRHnCwGH0GKqVS1lqLBz6F6NsMGowIgYJKwYBBAGCxAoCBBUxLjMuNi4x
↵LjQuMS40MTQ4Mi4xLjcwEwYLKwYBBAGC5RwCAQEEBAMCBDAwIQYLKwYBBAGC5RwBAQQEEgQQ-iuZ
↵3J45QlePkkow0jxBGDAMBgNVHRMBAf8EAjAAMA0GCSqGSIb3DQEBCwUAA4IBAQAo67Nn_tHY8OKJ
↵68qf9tgHV8YOmuV8sXKMmxw4yru9hNkjfagxrCGUnw8t_Awxa_2xdbNuY6Iru1gOrcpSgNB5hA5a
↵HiVyYlo7-4dgM9v7IqlpyTi4nOFxNZQAoSUtlwKpEpPVRRnpYN0izoon6wXrfnm3UMAC_tkBa3Ee
↵ya10UBvZFMu-jtlXEoG3T0TrB3zmHssGq4WpclUmfujjmCv0PwyyGjgtI1655M5tspjEBUJQQCMr
↵K2HhDNcMYhW8A7fpQHG3DhLRxH-WZVou-Z1M5Vp_G0sf-RTuE22eYSBHFIhkaYiARDEWZTiJuGSG
↵2cnJ_7yThUU1abNFdEuMoLQ3aGF1dGhEYXRhWMSjeab27q-5pV43jBGANOJ1Hmgvq58tMKsT0hJV
↵hs4ZR0EAAAD4-iuZ3J45QlePkkow0jxBGABAkNhnmLSbmlUebUHbpXxU-zMfqtnIqT5y2E3sfQgW
↵wE1FlUGvPg_c4zNcIucBnQAN8qTHJ8clzq7v5oQnnJz7T6UBAgMmIAEhWCBARZY9ak9nT6EI-dwL
↵uj0TB5-XjlmAvivyWLi9WSI7pCJYIEJicw0LtP_hdy8yh6ANEUXBJsWtkGDci9DcN1rDG1tE"""
        # First enrollment step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pin": self.pin,
                                                 "serial": self.serial,
                                                 "type": "webauthn",
                                                 "description": "my description",
                                                 "genkey": 1},
                                           headers={"authorization": self.at,
                                                    "Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            webauthn_request = data.get("detail").get("webAuthnRegisterRequest")
            self.assertEqual("Please confirm with your WebAuthn token", webauthn_request.get("message"))
            transaction_id = webauthn_request.get("transaction_id")

        # We need to change the nonce in the challenge database to use our recorded WebAuthN enrollment data
        recorded_nonce = "nh0iBz0SMndlVsPRGLvOCQc-PprPxOJf30KeZmTXY94"
        recorded_nonce_hex = hexlify_and_unicode(webauthn_b64_decode(recorded_nonce))
        # Update the nonce in the challenge database.
        from privacyidea.lib.challenge import get_challenges
        chal = get_challenges(serial=self.serial, transaction_id=transaction_id)[0]
        chal.challenge = recorded_nonce_hex
        chal.save()

        # 2nd enrollment step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pin": self.pin,
                                                 "serial": self.serial,
                                                 "type": "webauthn",
                                                 "transaction_id": transaction_id,
                                                 "clientdata": client_data,
                                                 "regdata": regdata},
                                           headers={"authorization": self.at,
                                                    "Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual('my description',
                             data.get("detail").get("webAuthnRegisterResponse").get("subject"))

        # Test, if the token received the automatic description
        self.assertEqual(get_tokens(serial=self.serial)[0].token.description, "my description")
        remove_token(self.serial)

    def test_02_enroll_token(self):
        client_data = "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoibmgwaUJ6MFNNbmRsVnNQUkdM" \
                      "dk9DUWMtUHByUHhPSmYzMEtlWm1UWFk5NCIsIm9yaWdpbiI6Imh0dHBzOi8vcGkuZXhhbXBsZS5jb" \
                      "20iLCJjcm9zc09yaWdpbiI6ZmFsc2V9"
        regdata = """o2NmbXRmcGFja2VkZ2F0dFN0bXSjY2FsZyZjc2lnWEgwRgIhANAt-cBR3mZglj13PZPXA3srJYxX
↵J6v-LzxAhmxZM7AsAiEAxu4gi8AiKOfyhU68HcIBHuIwgjBWJUlt4cIETWFYdetjeDVjgVkCwDCC
↵ArwwggGkoAMCAQICBAOt8BIwDQYJKoZIhvcNAQELBQAwLjEsMCoGA1UEAxMjWXViaWNvIFUyRiBS
↵b290IENBIFNlcmlhbCA0NTcyMDA2MzEwIBcNMTQwODAxMDAwMDAwWhgPMjA1MDA5MDQwMDAwMDBa
↵MG0xCzAJBgNVBAYTAlNFMRIwEAYDVQQKDAlZdWJpY28gQUIxIjAgBgNVBAsMGUF1dGhlbnRpY2F0
↵b3IgQXR0ZXN0YXRpb24xJjAkBgNVBAMMHVl1YmljbyBVMkYgRUUgU2VyaWFsIDYxNzMwODM0MFkw
↵EwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEGZ6HnBYtt9w57kpCoEYWpbMJ_soJL3a-CUj5bW6VyuTM
↵Zc1UoFnPvcfJsxsrHWwYRHnCwGH0GKqVS1lqLBz6F6NsMGowIgYJKwYBBAGCxAoCBBUxLjMuNi4x
↵LjQuMS40MTQ4Mi4xLjcwEwYLKwYBBAGC5RwCAQEEBAMCBDAwIQYLKwYBBAGC5RwBAQQEEgQQ-iuZ
↵3J45QlePkkow0jxBGDAMBgNVHRMBAf8EAjAAMA0GCSqGSIb3DQEBCwUAA4IBAQAo67Nn_tHY8OKJ
↵68qf9tgHV8YOmuV8sXKMmxw4yru9hNkjfagxrCGUnw8t_Awxa_2xdbNuY6Iru1gOrcpSgNB5hA5a
↵HiVyYlo7-4dgM9v7IqlpyTi4nOFxNZQAoSUtlwKpEpPVRRnpYN0izoon6wXrfnm3UMAC_tkBa3Ee
↵ya10UBvZFMu-jtlXEoG3T0TrB3zmHssGq4WpclUmfujjmCv0PwyyGjgtI1655M5tspjEBUJQQCMr
↵K2HhDNcMYhW8A7fpQHG3DhLRxH-WZVou-Z1M5Vp_G0sf-RTuE22eYSBHFIhkaYiARDEWZTiJuGSG
↵2cnJ_7yThUU1abNFdEuMoLQ3aGF1dGhEYXRhWMSjeab27q-5pV43jBGANOJ1Hmgvq58tMKsT0hJV
↵hs4ZR0EAAAD4-iuZ3J45QlePkkow0jxBGABAkNhnmLSbmlUebUHbpXxU-zMfqtnIqT5y2E3sfQgW
↵wE1FlUGvPg_c4zNcIucBnQAN8qTHJ8clzq7v5oQnnJz7T6UBAgMmIAEhWCBARZY9ak9nT6EI-dwL
↵uj0TB5-XjlmAvivyWLi9WSI7pCJYIEJicw0LtP_hdy8yh6ANEUXBJsWtkGDci9DcN1rDG1tE"""
        # First enrollment step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pin": self.pin,
                                                 "serial": self.serial,
                                                 "type": "webauthn",
                                                 "genkey": 1},
                                           headers={"authorization": self.at,
                                                    "Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            webAuthnRequest = data.get("detail").get("webAuthnRegisterRequest")
            self.assertEqual("Please confirm with your WebAuthn token", webAuthnRequest.get("message"))
            transaction_id = webAuthnRequest.get("transaction_id")

        # We need to change the nonce in the challenge database to use our recorded WebAuthN enrollment data
        recorded_nonce = "nh0iBz0SMndlVsPRGLvOCQc-PprPxOJf30KeZmTXY94"
        recorded_nonce_hex = hexlify_and_unicode(webauthn_b64_decode(recorded_nonce))
        # Update the nonce in the challenge database.
        from privacyidea.lib.challenge import get_challenges
        chal = get_challenges(serial=self.serial, transaction_id=transaction_id)[0]
        chal.challenge = recorded_nonce_hex
        chal.save()

        # 2nd enrollment step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pin": self.pin,
                                                 "serial": self.serial,
                                                 "type": "webauthn",
                                                 "transaction_id": transaction_id,
                                                 "clientdata": client_data,
                                                 "regdata": regdata},
                                           headers={"authorization": self.at,
                                                    "Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual('Yubico U2F EE Serial 61730834',
                             data.get("detail").get("webAuthnRegisterResponse").get("subject"))

        # Test, if the token received the automatic description
        self.assertEqual(get_tokens(serial=self.serial)[0].token.description, "Yubico U2F EE Serial 61730834")

    def test_10_validate_check(self):
        # Run challenge request against /validate/check
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pass": self.pin},
                                           headers={"Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            data = res.json
            self.assertTrue("transaction_id" in data.get("detail"))
            self.assertEqual(self.serial, data.get("detail").get("serial"))
            self.assertEqual("Please confirm with your WebAuthn token (Yubico U2F EE Serial 61730834)",
                             data.get("detail").get("message"))

    def test_11_trigger_challenge(self):
        # Run challenge request against /validate/triggerchallenge
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": self.username},
                                           headers={"Host": "pi.example.com",
                                                    "authorization": self.at,
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            data = res.json
            self.assertEqual(200, res.status_code)
            self.assertTrue("transaction_id" in data.get("detail"))
            self.assertEqual(self.serial, data.get("detail").get("serial"))
            self.assertEqual("Please confirm with your WebAuthn token (Yubico U2F EE Serial 61730834)",
                             data.get("detail").get("message"))

        remove_token(self.serial)

    def test_12_authenticate_multiple_tokens(self):
        delete_policy("wan1")
        delete_policy("wan2")

        set_policy("wan1", scope=SCOPE.ENROLL, action="webauthn_relying_party_id=fritz.box")
        set_policy("wan2", scope=SCOPE.ENROLL, action="webauthn_relying_party_name=fritz.box")
        set_policy("challenge_response", scope=SCOPE.AUTH, action=f"{ACTION.CHALLENGERESPONSE}=totp hotp")

        pin = "12"
        user = User("hans", self.realm1)
        hotp = init_token({"type": "hotp", "pin": pin, "genkey": "1"}, user=user)
        totp = init_token({"type": "totp", "pin": pin, "genkey": "1"}, user=user)
        headers = {"authorization": self.at,
                   "Host": "pi.fritz.box:5000",
                   "Origin": "https://pi.fritz.box:5000"}

        # Enroll WebAuthn via the API
        data = {
            "2stepinit": False,
            "genkey": True,
            "realm": self.realm1,
            "timeStep": 30,
            "type": "webauthn",
            "user": "hans",
            "pin": "12"
        }
        with patch('privacyidea.lib.tokens.webauthntoken.WebAuthnTokenClass._get_nonce') as mock_nonce:
            mock_nonce.return_value = webauthn_b64_decode("RjCK6QlzmOpWN4BwE6xD5tx5P0czKCFemfqMBnAhch0")
            with self.app.test_request_context('/token/init',
                                               method='POST',
                                               data=data,
                                               headers=headers):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res)
                data = res.json
                webauthn_request = data.get("detail").get("webAuthnRegisterRequest")
                transaction_id = webauthn_request.get("transaction_id")
                webauthn_serial = data.get("detail").get("serial")

        # 2nd enrollment step
        data = {"user": "hans",
                "realm": self.realm1,
                "serial": webauthn_serial,
                "type": "webauthn",
                "transaction_id": transaction_id,
                "clientdata": "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiUmpDSzZRbHptT3BXTjRCd0U2eEQ1dHg1UDBj"
                              "ektDRmVtZnFNQm5BaGNoMCIsIm9yaWdpbiI6Imh0dHBzOi8vcGkuZnJpdHouYm94OjUwMDAifQ",
                "regdata": "o2NmbXRmcGFja2VkZ2F0dFN0bXSjY2FsZyZjc2lnWEcwRQIga75EjPA16t5Tck2dwpAE-PoalJVtpqVCauYvZz_FU3c"
                           "CIQCrR-KSlaLQhuuAVkmx0KYkoQIgHDYeZX4Dxi98BW4itGN4NWOBWQLdMIIC2TCCAcGgAwIBAgIJAPDqu31oBEyKMA"
                           "0GCSqGSIb3DQEBCwUAMC4xLDAqBgNVBAMTI1l1YmljbyBVMkYgUm9vdCBDQSBTZXJpYWwgNDU3MjAwNjMxMCAXDTE0M"
                           "DgwMTAwMDAwMFoYDzIwNTAwOTA0MDAwMDAwWjBvMQswCQYDVQQGEwJTRTESMBAGA1UECgwJWXViaWNvIEFCMSIwIAYD"
                           "VQQLDBlBdXRoZW50aWNhdG9yIEF0dGVzdGF0aW9uMSgwJgYDVQQDDB9ZdWJpY28gVTJGIEVFIFNlcmlhbCAyMTA5ND"
                           "Y3Mzc2MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE5mfTO7qcRZuAnvzLaguuLFz8S9eB1XNIPZb96SUfZCzN5sIGV"
                           "RTzM4JGrJlSgAAq0jivvANxttf6w7_LnnnSMKOBgTB_MBMGCisGAQQBgsQKDQEEBQQDBQQDMCIGCSsGAQQBgsQKAgQV"
                           "MS4zLjYuMS40LjEuNDE0ODIuMS43MBMGCysGAQQBguUcAgEBBAQDAgQwMCEGCysGAQQBguUcAQEEBBIEEC_AV5-BE0f"
                           "qsRa7Wo25ICowDAYDVR0TAQH_BAIwADANBgkqhkiG9w0BAQsFAAOCAQEAtjGoKNeTOK0pAIoNf3mjoD3PLgybH2L6z7"
                           "SKnlWVd6dRbJWbZCsY8AxMdyKNGfnUQiJcEmi9IxigjGoXcwZPApnJm7JDike7Z7HQ2yUrlJZ-EgFamivp5C3UVCaIk"
                           "GH-HyJW_vh23XOZMkaDcRqwbeq8b0Voavnu4YF5bCM7PtnsPcCsvfL5DahPGSfpc9YyANG49OQBOZolNF3MBKKrspOA"
                           "I7RfW0JSQY0NUnWFYx9hxFbNuYsKFN4NblJ_Zz9tMk1YYSkTJ6VfxHTo5tfIcaLfZ1dIrMeY12-WevjMufFW_qB4Er"
                           "Y5Gjft3cbiZBELmbQ9QLUyLX78lHiLC9pJImhhdXRoRGF0YVjE1kwVsywYDmugu2qhEi7LiS8tgyaE5XqILRqvKXkZ-"
                           "1pFAAAABC_AV5-BE0fqsRa7Wo25ICoAQIwkrRnq993po4HbKnUzQuq90bg6wFf8w0ulx8kSxw_5osFUpDm5Ct4B4JeL"
                           "F1B4rpd3Cy4iAZT0msTxhwXVrAalAQIDJiABIVggwD4LMXnu6jGwvc-PwbT46HLfUFAp6flASQh4CuEsACIiWCDKyZP"
                           "LKFfXGZa--6Gjbp0dmq_fDIYWYVapphWk6WodBA"}
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data=data,
                                           headers=headers):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)

        # Trigger all 3 token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "hans", "pass": pin},
                                           headers=headers), patch(
            'privacyidea.lib.tokens.webauthntoken.WebAuthnTokenClass._get_nonce') as mock_nonce:
            mock_nonce.return_value = webauthn_b64_decode("Z1osHXV_kbmE0Jg5S2zkBWUKI3ZO6UYO-hkzBv-YypA")
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            j = res.json
            detail = j.get("detail")
            multichallenge = detail.get("multi_challenge")
            self.assertEqual(3, len(multichallenge))
            transaction_id = detail.get("transaction_id")

        # Remove the TokenCredentialIdHash and TokenInfo entries so the token has to be found via the transaction_id
        # This simulates the case of webauthn token that are present pre 3.11. When they are used in 3.11, they will
        # create these entries.
        credential_id = "jCStGer33emjgdsqdTNC6r3RuDrAV_zDS6XHyRLHD_miwVSkObkK3gHgl4sXUHiul3cLLiIBlPSaxPGHBdWsBg"
        credential_id_hash = hash_credential_id(credential_id)
        tcih = TokenCredentialIdHash.query.filter_by(credential_id_hash=credential_id_hash).one()
        self.assertTrue(tcih)
        tcih.delete()
        token_info_entry = (TokenInfo.query.filter(TokenInfo.Key == "credential_id_hash")
                            .filter(TokenInfo.Value == credential_id_hash).first())
        self.assertTrue(token_info_entry)
        token_info_entry.delete()

        data = {
            "authenticatordata": "1kwVsywYDmugu2qhEi7LiS8tgyaE5XqILRqvKXkZ-1oBAAAACA",
            "clientdata": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiWjFvc0hYVl9rYm1FMEpnNVMyemtCV1VLSTNaTzZVWU8t"
                          "aGt6QnYtWXlwQSIsIm9yaWdpbiI6Imh0dHBzOi8vcGkuZnJpdHouYm94OjUwMDAifQ",
            "credentialid": credential_id,
            "signaturedata": "MEYCIQDl9geJO2uBLoedFxpGLhOyxKIhp9CJXdFO0gAp56HgcQIhAO5MRvXN_ZOEl-M_fhIsVJCq4xeVrbME-Mw2C"
                             "AVK_1kh",
            "transaction_id": transaction_id,
            "username": "hans"
        }
        with self.app.test_request_context('/validate/check', method='POST', data=data, headers=headers):
            res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res)
        j = res.json
        self.assertTrue(j.get("result").get("status"))
        self.assertTrue(j.get("result").get("value"))

        delete_policy("challenge_response")
        remove_token(hotp.get_serial())
        remove_token(totp.get_serial())
        remove_token(webauthn_serial)

    def test_20_authenticate_other_token(self):
        # Ensure that a not readily enrolled WebAuthn token does not disturb the usage
        # of an HOTP token with challenge response.
        # First enrollment step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pin": self.pin,
                                                 "serial": self.serial,
                                                 "type": "webauthn",
                                                 "genkey": 1},
                                           headers={"authorization": self.at,
                                                    "Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            webauthn_request = data.get("detail").get("webAuthnRegisterRequest")
            self.assertEqual("Please confirm with your WebAuthn token", webauthn_request.get("message"))

        # The token is now in the client_wait rollout state. We do not do the 2nd enrollment step
        tokens = get_tokens(serial=self.serial)
        self.assertEqual(ROLLOUTSTATE.CLIENTWAIT, tokens[0].rollout_state)

        # Now we create the 2nd token of the user, an HOTP token
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pin": self.pin,
                                                 "otpkey": self.otpkey,
                                                 "type": "hotp",
                                                 "serial": "hotpX1"},
                                           headers={"authorization": self.at,
                                                    "Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))
        # We need a policy for HOTP trigger challenge
        set_policy(name="trigpol", scope=SCOPE.AUTH, action="{0!s}=hotp".format(ACTION.CHALLENGERESPONSE))
        # Check if the challenge is triggered for the HOTP token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pass": self.pin},
                                           headers={"Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            data = res.json
            transaction_id = data.get("detail").get("transaction_id")
            # The WebAuthn token is disabled because it is not enrolled completely, so there is no data of it
            # But there is a challenge-response message for the HOTP token
            messages = data.get("detail").get("messages")
            self.assertEqual(1, len(messages))
            self.assertIn("please enter otp: ", messages)
            self.assertEqual(1, len(data.get("detail").get("multi_challenge")))

        # Authenticate with HOTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": self.username,
                                                 "transaction_id": transaction_id,
                                                 "pass": self.valid_otp_values[0]},
                                           headers={"Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # check if the challenge is triggered for the HOTP token via triggerchallenge
        with self.app.test_request_context('/validate/triggerchallenge',
                                           method='POST',
                                           data={"user": self.username},
                                           headers={"authorization": self.at,
                                                    "Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            data = res.json
            transaction_id = data.get("detail").get("transaction_id")

        # Authenticate with HOTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": self.username,
                                                 "transaction_id": transaction_id,
                                                 "pass": self.valid_otp_values[1]},
                                           headers={"Host": "pi.example.com",
                                                    "Origin": "https://pi.example.com"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        delete_policy("trigpol")
        remove_token("hotpX1")
        remove_token(self.serial)


class WebAuthnOfflineTestCase(MyApiTestCase):
    """
    This Testcase simulates the enrollment and full authentication with a WebAuthn token.
    """

    username = "cornelius"
    pin = "webauthnpin"
    serial = "WAN0001D434"
    clientdata = "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiMGZueEhXNVIybWFPclZydUxK\r\nR3JFR0ZwRm1KSF" \
                 "I0alBFbWVkSjlQdDNoayIsIm9yaWdpbiI6Imh0dHBzOi8vcHVjay5vZmZpY2Uu\r\nbmV0a25pZ2h0cy5pdCIsImNyb3NzT" \
                 "3JpZ2luIjpmYWxzZX0"
    regdata = "o2NmbXRmcGFja2VkZ2F0dFN0bXSjY2FsZyZjc2lnWEcwRQIhAMjdckoGnrQ7mI4afrFD9Gf1eYKX\r\n1nij_v7PsyGb1RXBAiB" \
              "1XH98HGptKlcdtZtPxbL4WZKVOa5Enb09ZZQxycsCOGN4NWOBWQLAMIIC\r\nvDCCAaSgAwIBAgIEA63wEjANBgkqhkiG9w0BAQ" \
              "sFADAuMSwwKgYDVQQDEyNZdWJpY28gVTJGIFJv\r\nb3QgQ0EgU2VyaWFsIDQ1NzIwMDYzMTAgFw0xNDA4MDEwMDAwMDBaGA8yM" \
              "DUwMDkwNDAwMDAwMFow\r\nbTELMAkGA1UEBhMCU0UxEjAQBgNVBAoMCVl1YmljbyBBQjEiMCAGA1UECwwZQXV0aGVudGljYXRv" \
              "\r\nciBBdHRlc3RhdGlvbjEmMCQGA1UEAwwdWXViaWNvIFUyRiBFRSBTZXJpYWwgNjE3MzA4MzQwWTAT\r\nBgcqhkjOPQIBBgg" \
              "qhkjOPQMBBwNCAAQZnoecFi233DnuSkKgRhalswn-ygkvdr4JSPltbpXK5Mxl\r\nzVSgWc-9x8mzGysdbBhEecLAYfQYqpVLWW" \
              "osHPoXo2wwajAiBgkrBgEEAYLECgIEFTEuMy42LjEu\r\nNC4xLjQxNDgyLjEuNzATBgsrBgEEAYLlHAIBAQQEAwIEMDAhBgsrB" \
              "gEEAYLlHAEBBAQSBBD6K5nc\r\nnjlCV4-SSjDSPEEYMAwGA1UdEwEB_wQCMAAwDQYJKoZIhvcNAQELBQADggEBACjrs2f-0djw" \
              "4onr\r\nyp_22AdXxg6a5XyxcoybHDjKu72E2SN9qDGsIZSfDy38DDFr_bF1s25joiu7WA6tylKA0HmEDloe\r\nJXJiWjv7h2A" \
              "z2_siqWnJOLic4XE1lAChJS2XAqkSk9VFGelg3SLOiifrBet-ebdQwAL-2QFrcR7J\r\nrXRQG9kUy76O2VcSgbdPROsHfOYeyw" \
              "arhalyVSZ-6OOYK_Q_DLIaOC0jXrnkzm2ymMQFQlBAIysr\r\nYeEM1wxiFbwDt-lAcbcOEtHEf5ZlWi75nUzlWn8bSx_5FO4Tb" \
              "Z5hIEcUiGRpiIBEMRZlOIm4ZIbZ\r\nycn_vJOFRTVps0V0S4ygtDdoYXV0aERhdGFYxFLyPscdaSzo-TkwLG7jxyp-Etk6ein0" \
              "C_VjHUvB\r\nUOENQQAAAWP6K5ncnjlCV4-SSjDSPEEYAEBG4GUQidTvJywgtJPu7oChPut2o1iNJ_iOXPfzHXTf\r\njjEzZIe" \
              "W3Bu0HACkVidtBc7yDluCtviQWHU0SufOxPrEpQECAyYgASFYID-YUA3c7cOqFtNK6bfB\r\nL3H6BNN7ivKOfFnU5zOIA3X7Il" \
              "ggaKqMkh_8X6Vim6wj6GSq9_zeCvDUgJKeTuo-Nxk_jz0"

    rp_id = "netknights.it"

    recorded_allow_credentials = "RuBlEInU7ycsILST7u6AoT7rdqNYjSf4jlz38x10344xM2SHl" \
                                 "twbtBwApFYnbQXO8g5bgrb4kFh1NErnzsT6xA"

    recorded_challenge = "zphA4XzB8ZHkiGnsQAcqDRn8j8e4h9HcSAQ2mlt0o94"

    refilltokens = []
    user_agents = ["privacyidea-cp/1.1.1 Windows/Laptop-1231312", "privacyidea-cp/2.2.2 ComputerName/PC-ASDASDS"]

    def setUp(self):
        # Set up the WebAuthn Token from the lib test case
        super(MyApiTestCase, self).setUp()
        self.setUp_user_realms()

        set_policy("wan1", scope=SCOPE.ENROLL,
                   action=("webauthn_relying_party_id={0!s}".format(self.rp_id)))
        set_policy("wan2", scope=SCOPE.ENROLL,
                   action="webauthn_relying_party_name=privacyIDEA")

    def test_01_token_init(self):
        payload = {"genkey": 1,
                   "type": "webauthn",
                   "pin": self.pin,
                   "description": "my description",
                   "serial": self.serial,
                   "user": self.username}

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data=payload,
                                           headers={"authorization": self.at,
                                                    "Host": "puck.office.netknights.it",
                                                    "Origin": "https://puck.office.netknights.it"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            detail = data.get("detail")
            self.assertEqual(self.serial, detail.get("serial"))
            web_authn_request = data.get("detail").get("webAuthnRegisterRequest")
            self.assertEqual("Please confirm with your WebAuthn token", web_authn_request.get("message"))
            transaction_id = web_authn_request.get("transaction_id")
            self.assertEqual(web_authn_request.get("attestation"), "direct")

        # We need to change the nonce in the challenge database to use our recorded WebAuthN enrollment data
        recorded_nonce = "0fnxHW5R2maOrVruLJGrEGFpFmJHR4jPEmedJ9Pt3hk"
        recorded_nonce_hex = hexlify_and_unicode(webauthn_b64_decode(recorded_nonce))
        # Update the nonce in the challenge database.
        from privacyidea.lib.challenge import get_challenges
        chal = get_challenges(serial=self.serial, transaction_id=transaction_id)[0]
        chal.challenge = recorded_nonce_hex
        chal.save()

        # 2nd enrollment step
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": self.username,
                                                 "pin": self.pin,
                                                 "serial": self.serial,
                                                 "type": "webauthn",
                                                 "transaction_id": transaction_id,
                                                 "clientdata": self.clientdata,
                                                 "regdata": self.regdata},
                                           headers={"authorization": self.at,
                                                    "Host": "puck.office.netknights.it",
                                                    "Origin": "https://puck.office.netknights.it"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertEqual('my description',
                             data.get("detail").get("webAuthnRegisterResponse").get("subject"))

        # Test, if the token received the automatic description
        tok = get_one_token(serial=self.serial)
        self.assertEqual(tok.token.description, "my description")

        # Attach offline to WebAuthn
        mt = attach_token(self.serial, "offline")
        self.assertEqual("offline", mt.application)
        self.assertEqual(1, mt.id)

    def _trigger_and_modify_challenge(self, headers):
        payload = {"user": self.username,
                   "pass": self.pin}

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           environ_base={'REMOTE_ADDR': '10.0.0.17'},
                                           data=payload,
                                           headers=headers):
            res = self.app.full_dispatch_request()

            self.assertEqual(200, res.status_code)
            data = res.json
            self.assertTrue("transaction_id" in data.get("detail"))
            self.assertEqual(self.serial, data.get("detail").get("serial"))
            self.assertEqual("Please confirm with your WebAuthn token (my description)",
                             data.get("detail").get("message"))
            detail = data.get("detail")
            self.assertEqual("webauthn", detail.get("client_mode"))
            web_authn_sign_request = detail.get("attributes").get("webAuthnSignRequest")
            self.assertEqual("netknights.it", web_authn_sign_request.get("rpId"))
            allow_credentials = web_authn_sign_request.get("allowCredentials")
            self.assertEqual(1, len(allow_credentials))
            self.assertEqual(self.recorded_allow_credentials, allow_credentials[0].get("id"))
            transaction_id = detail.get("transaction_id")

            # Update the recorded challenge in the DB
            recorded_challenge_hex = hexlify_and_unicode(webauthn_b64_decode(self.recorded_challenge))
            # Update the nonce in the challenge database.
            from privacyidea.lib.challenge import get_challenges
            chal = get_challenges(serial=self.serial, transaction_id=transaction_id)[0]
            chal.challenge = recorded_challenge_hex
            chal.save()
            return transaction_id

    def _validate_check(self, headers, transaction_id):
        # 2nd authentication step
        payload = {
            "credentialid": "RuBlEInU7ycsILST7u6AoT7rdqNYjSf4jlz38x10344xM2SHltwbtBwApFYnbQXO8g5bgrb4kFh1NErnzsT6xA",
            "clientdata": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoienBoQTRYekI4WkhraUduc1FBY3FE\r\nUm44ajhl"
                          "NGg5SGNTQVEybWx0MG85NCIsIm9yaWdpbiI6Imh0dHBzOi8vcHVjay5vZmZpY2UubmV0\r\na25pZ2h0cy5pdCIs"
                          "ImNyb3NzT3JpZ2luIjpmYWxzZX0",
            "signaturedata": "MEYCIQCo7auEWVB0QitS6Hr2GnM9QU3R3ZFdnjVhSKgrbD52lAIhANmt2evYe9JP3MLMeIc1WXpG\r\n2NlUT"
                             "2MHQTQATDoyMdM3",
            "authenticatordata": "UvI-xx1pLOj5OTAsbuPHKn4S2Tp6KfQL9WMdS8FQ4Q0BAAABZQ",
            "user": self.username,
            "pass": "",
            "transaction_id": transaction_id
        }

        # We need the client IP (REMOTE_ADDR) to set the authitems in postpolicy.py:offline_info()
        with self.app.test_request_context('/validate/check',
                                           environ_base={'REMOTE_ADDR': '10.0.0.17'},
                                           method='POST',
                                           data=payload,
                                           headers=headers):
            return self.app.full_dispatch_request()

    def test_02_authenticate(self):
        headers = {"Host": "puck.office.netknights.it",
                   "Origin": "https://puck.office.netknights.it",
                   "User-Agent": self.user_agents[0]}

        for i in range(len(self.user_agents)):
            headers.update({"User-Agent": self.user_agents[i]})
            transaction_id = self._trigger_and_modify_challenge(headers)
            res = self._validate_check(headers, transaction_id)
            self.assertEqual(200, res.status_code)
            data = res.json
            detail = data.get("detail")
            result = data.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual("Found matching challenge", detail.get("message"))
            self.assertIn("serial", detail)
            self.assertIn("auth_items", data)
            auth_items = data.get("auth_items")
            """
            auth_items looks like this:

            {'offline': [
                {'user': 'cornelius',
                 'username': 'cornelius',
                 'refilltoken': '79906cc20567c6ca1e4b452500bb0662e107ce0fa14742c95b7e5c6a1417a519f829318622c1d569',
                 'response': {
                     'pubKey': 'a50102032620012158203f98500ddcedc3aa16d34ae9b7c12...ea3e37193f8f3d',
                     'credentialId': 'RuBlEInU7ycsILST7u6AoT7rdqN...4xM2SHltwbtBwApFYnbQXO8g5bgrb4kFh1NErnzsT6xA',
                     'rpId': 'netknights.it'},
                 'serial': 'WAN0001D434'}]}
            """
            response = auth_items.get("offline")[0].get("response")
            _refill_token = auth_items.get("offline")[0].get("refilltoken")
            # Offline returns the credential ID and the pub key
            self.assertEqual(self.recorded_allow_credentials, response.get("credentialId"))
            self.assertIn("pubKey", response)
            self.assertEqual(self.rp_id, response.get("rpId"))
            self.refilltokens.append(auth_items.get("offline")[0].get("refilltoken"))

            # Set the sign count back to be able to use the same data for authentication again
            token = get_one_token(serial=self.serial)
            if not token:
                self.fail(f"No token found for serial {self.serial}")
            token.set_otp_count(0)

        # Check that the refilltokens are NOT the same
        self.assertEqual(len(set(self.refilltokens)), len(self.user_agents))

    def test_03_authenticate_no_machine_name(self):
        token = get_one_token(serial=self.serial)
        if not token:
            self.fail("No token found for serial {0!s}".format(self.serial))
        # Set the sign count back to be able to use the same data for authentication again
        token.set_otp_count(0)

        headers = {"Host": "puck.office.netknights.it",
                   "Origin": "https://puck.office.netknights.it",
                   "User-Agent": "privacyidea-cp/1.1.1"}

        transaction_id = self._trigger_and_modify_challenge(headers)
        res = self._validate_check(headers, transaction_id)
        self.assertEqual(200, res.status_code)
        data = res.json
        detail = data.get("detail")
        result = data.get("result")
        self.assertTrue(result.get("status"))
        self.assertTrue(result.get("value"))
        self.assertEqual("Found matching challenge", detail.get("message"))
        # There should be no offline auth_items because the computer name is missing
        # but there is no error "blocking" the real result of the authentication
        self.assertIsNone(data.get("auth_items"))

    def _assert_err_905(self, res):
        self.assertEqual(400, res.status_code)
        data = res.json
        self.assertEqual(905, data.get("result").get("error").get("code"))
        self.assertFalse(data.get("result").get("status"))

    def test_04_refill_no_machine_name(self):
        headers = {"Host": "puck.office.netknights.it",
                   "Origin": "https://puck.office.netknights.it"}
        self.assertTrue(len(self.refilltokens) > 0)
        payload = {"refilltoken": self.refilltokens[0], "serial": self.serial, "pass": ""}
        with self.app.test_request_context('/validate/offlinerefill',
                                           environ_base={'REMOTE_ADDR': '10.0.0.17'},
                                           method='POST',
                                           data=payload,
                                           headers=headers):
            res = self.app.full_dispatch_request()
            # In case of offlinerefill, the response should be 400, because the requested operation did not succeed,
            # in contrast to the test above
            self._assert_err_905(res)

    def test_05_refill_per_machine(self):
        headers = {"Host": "puck.office.netknights.it",
                   "Origin": "https://puck.office.netknights.it",
                   "User-Agent": self.user_agents[0]}

        for i in range(len(self.user_agents)):
            payload = {"refilltoken": self.refilltokens[i], "serial": self.serial, "pass": ""}
            headers.update({"User-Agent": self.user_agents[i]})
            with self.app.test_request_context('/validate/offlinerefill',
                                               environ_base={'REMOTE_ADDR': '10.0.0.17'},
                                               method='POST',
                                               data=payload,
                                               headers=headers):
                res = self.app.full_dispatch_request()
                data = res.json
                self.assertEqual(200, res.status_code)
                self.assertTrue(data.get("result").get("status"))
                self.assertIsNotNone(data.get("auth_items"))
                self.assertEqual(self.serial, data.get("auth_items").get("offline")[0].get("serial"))
                self.refilltokens[i] = data.get("auth_items").get("offline")[0].get("refilltoken")

    def test_06_remove_machine(self):
        deleted_count = detach_token(self.serial, "offline")
        self.assertEqual(1, deleted_count)

        # An attempted refill for a detached token should result in an error
        headers = {"Host": "puck.office.netknights.it",
                   "Origin": "https://puck.office.netknights.it",
                   "User-Agent": self.user_agents[0]}

        for i in range(len(self.user_agents)):
            payload = {"refilltoken": self.refilltokens[i], "serial": self.serial, "pass": ""}
            headers.update({"User-Agent": self.user_agents[i]})
            with self.app.test_request_context('/validate/offlinerefill',
                                               environ_base={'REMOTE_ADDR': '10.0.0.17'},
                                               method='POST',
                                               data=payload,
                                               headers=headers):
                res = self.app.full_dispatch_request()
                self._assert_err_905(res)
