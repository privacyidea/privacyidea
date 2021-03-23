# -*- coding: utf-8 -*-

from .base import MyApiTestCase
import binascii
import struct
from hashlib import sha256
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

from privacyidea.lib.token import assign_token, remove_token
from privacyidea.lib.user import User
from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.tokens.u2f import (check_response, url_encode)
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
from privacyidea.lib.tokens.u2ftoken import U2FACTION
from privacyidea.models import Challenge
from privacyidea.lib.utils import hexlify_and_unicode, to_bytes
from privacyidea.lib.error import ERROR
from privacyidea.lib import _


PWFILE = "tests/testdata/passwords"
IMPORTFILE = "tests/testdata/import.oath"
IMPORTFILE2 = "tests/testdata/empty.oath"
YUBICOFILE = "tests/testdata/yubico-oath.csv"
OTPKEY = "3132333435363738393031323334353637383930"
OTPKEY2 = "010fe88d31948c0c2e3258a4b0f7b11956a258ef"
OTPVALUES2 = ["551536", "703671", "316522", "413789"]


def sign_challenge(user_priv_key, app_id, client_data, counter,
                   user_presence_byte=b'\x01'):
    """
    This creates a signature for the U2F data.
    Only used in test scenario

    The calculation of the signature is described here:
    https://fidoalliance.org/specs/fido-u2f-v1.0-nfc-bt-amendment-20150514/fido-u2f-raw-message-formats.html#authentication-response-message-success

    The input_data is a concatenation of:
        * AppParameter: sha256(app_id)
        * The user presence [1byte]
        * counter [4byte]
        * ChallengeParameter: sha256(client_data)

    :param user_priv_key: The private key
    :type user_priv_key: hex string
    :param app_id: The application id
    :type app_id: str
    :param client_data: the stringified JSON
    :type client_data: str
    :param counter: the authentication counter
    :type counter: int
    :param user_presence_byte: one byte 0x01
    :type user_presence_byte: char
    :return: The DER encoded signature
    :rtype: hex string
    """
    app_id_hash = sha256(to_bytes(app_id)).digest()
    client_data_hash = sha256(to_bytes(client_data)).digest()
    counter_bin = struct.pack(">L", counter)
    input_data = app_id_hash + user_presence_byte + counter_bin + client_data_hash

    sk = ec.derive_private_key(int(user_priv_key, 16), ec.SECP256R1())
    signature = sk.sign(input_data, ec.ECDSA(hashes.SHA256()))
    return hexlify_and_unicode(signature)


class APIU2fTestCase(MyApiTestCase):

    serial = "U2F001"

    def test_000_setup_realms(self):
        self.setUp_user_realms()
        # U2F is not configured yet
        with self.app.test_request_context('/ttype/u2f',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400)

        set_privacyidea_config("u2f.appId", "http://localhost:5000")

    def test_00_sign_check(self):
        # Test the low level functions
        # Values taken from
        # https://fidoalliance.org/specs/fido-u2f-v1.0-nfc-bt-amendment-20150514/fido-u2f-raw-message-formats.html#authentication-example
        pass
        privkey = "ffa1e110dde5a2f8d93c4df71e2d4337b7bf5ddb60c75dc2b6b81433b54dd3c0"
        pubkey = "04d368f1b665bade3c33a20f1e429c7750d5033660c019119d29aa4ba7abc04aa7c80a46bbe11ca8cb5674d74f31f8a903f6bad105fb6ab74aefef4db8b0025e1d"
        app_id = "https://gstatic.com/securitykey/a/example.com"
        cdata = """{"typ":"navigator.id.getAssertion",
                    "challenge":"opsXqUifDriAAmWclinfbS0e-USY0CgyJHe_Otd7z8o",
                    "cid_pubkey":{
                        "kty":"EC",
                        "crv":"P-256",
                        "x":"HzQwlfXX7Q4S5MtCCnZUNBw3RMzPO9tOyWjBqRl4tJ8",
                        "y":"XVguGFLIZx1fXg3wNqfdbn75hi4-_7-BxhMljw42Ht4"},
                    "origin":"http://example.com"}"""
        client_data = ''.join(cdata.split())
        counter = 1
        signature = sign_challenge(privkey, app_id,
                                   client_data, counter)

        r = check_response(pubkey, app_id, client_data, signature, counter)
        self.assertEqual(r, 1)

    def test_01_register_u2f(self):
        # step 1
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "u2f",
                                                 "serial": self.serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = res.json
            result = response.get("result")
            details = response.get("detail")
            self.assertEqual(result.get("value"), True)

            serial = details.get("serial")
            self.assertEqual(serial[:3], "U2F")
            self.assertEqual(details.get("u2fRegisterRequest").get(
                "version"), "U2F_V2")
            challenge = details.get("u2fRegisterRequest").get("challenge")
            self.assertTrue(len(challenge) > 20)

        # step 2
        # We need to send back regData and clientData.
        # from the registration example
        reg_data = "BQRFnd8XtfZzsTK68VPK64Bcjiog_ZzyYNuzjaaGwpPnSpifxaqQV4_4IMxVlGS3CLoQmNAR41MSMxZHG0dENLRmQGnk4OqRxGRHmUOOLmDkGgdIJycQe79JCERV1gqGnWAOFBg_bH4WFSxZwnX-IMRcl3zW_X442QNrrdFySvXrba4wggIcMIIBBqADAgECAgQ4Zt91MAsGCSqGSIb3DQEBCzAuMSwwKgYDVQQDEyNZdWJpY28gVTJGIFJvb3QgQ0EgU2VyaWFsIDQ1NzIwMDYzMTAgFw0xNDA4MDEwMDAwMDBaGA8yMDUwMDkwNDAwMDAwMFowKzEpMCcGA1UEAwwgWXViaWNvIFUyRiBFRSBTZXJpYWwgMTM4MzExNjc4NjEwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAAQ3jfx0DHOblHJO09Ujubh2gQZWwT3ob6-uzzjZD1XiyAob_gsw3FOzXefQRblty48r-U-o4LkDFjx_btwuSHtxoxIwEDAOBgorBgEEAYLECgEBBAAwCwYJKoZIhvcNAQELA4IBAQIaR2TKAInPkq24f6hIU45yzD79uzR5KUMEe4IWqTm69METVio0W2FHWXlpeUe85nGqanwGeW7U67G4_WAnGbcd6zz2QumNsdlmb_AebbdPRa95Z8BG1ub_S04JoxQYNLaa8WRlzN7POgqAnAqkmnsZQ_W9Tj2uO9zP3mpxOkkmnqz7P5zt4Lp5xrv7p15hGOIPD5V-ph7tUmiCJsq0LfeRA36X7aXi32Ap0rt_wyfnRef59YYr7SmwaMuXKjbIZSLesscZZTMzXd-uuLb6DbUCasqEVBkGGqTRfAcOmPov1nHUrNDCkOR0obR4PsJG4PiamIfApNeoXGYpGbok6nucMEYCIQC_yerJqB3mnuAJGfbdKuOIx-Flxr-VSQ2nAkUUE_50dQIhAJE2NL1Xs2oVEG4bFzEM86TfS7nkHxad89aYmUrII49V"
        client_data = "eyJ0eXAiOiJuYXZpZ2F0b3IuaWQuZmluaXNoRW5yb2xsbWVudCIsImNoYWxsZW5nZSI6ImdXbndtYnFSMl9YOE91RFhId0dyQWNmUTBUajN4YTVfZ2RJMjBYcVlsdTg9Iiwib3JpZ2luIjoiaHR0cDovL2xvY2FsaG9zdDo1MDAwIiwiY2lkX3B1YmtleSI6IiJ9"
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"serial": serial,
                                                 "type": "u2f",
                                                 "regdata": reg_data,
                                                 "clientdata": client_data},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = res.json
            result = response.get("result")
            self.assertEqual(result.get("value"), True)

    def test_02_validate(self):
        # assign token to user
        r = assign_token(self.serial, User("cornelius", self.realm1),
                         pin="u2f")
        self.assertEqual(r, True)

        # Issue challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@"+self.realm1,
                                                 "pass": "u2f"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("value"), False)
            transaction_id = detail.get("transaction_id")
            self.assertEqual(len(transaction_id), len('01350277175811850842'))
            self.assertEqual(detail.get("message"), detail.get("message"),
                            _("Please confirm with your U2F token ({0!s})").format("Yubico U2F EE Serial 13831167861"))
            attributes = detail.get("attributes")
            u2f_sign_request = attributes.get("u2fSignRequest")
            self.assertTrue("appId" in u2f_sign_request)
            app_id = u2f_sign_request.get("appId")
            self.assertTrue("challenge" in u2f_sign_request)
            challenge = u2f_sign_request.get("challenge")
            self.assertTrue("keyHandle" in u2f_sign_request)
            key_handle = u2f_sign_request.get("keyHandle")
            self.assertEqual(u2f_sign_request.get("version"), "U2F_V2")

        # private key from the registration example
        privkey = "9a9684b127c5e3a706d618c86401c7cf6fd827fd0bc18d24b0eb842e36d16df1"
        counter = 1
        cdata = """{{"typ":"navigator.id.getAssertion",
                    "challenge":"{0!s}",
                    "cid_pubkey":{{
                        "kty":"EC",
                        "crv":"P-256",
                        "x":"HzQwlfXX7Q4S5MtCCnZUNBw3RMzPO9tOyWjBqRl4tJ8",
                        "y":"XVguGFLIZx1fXg3wNqfdbn75hi4-_7-BxhMljw42Ht4"}},
                    "origin":"{1!s}"}}"""
        client_data = cdata.format(challenge, app_id)
        client_data_str = ''.join(client_data.split())
        signature_hex = sign_challenge(privkey, app_id, client_data_str, counter)
        signature_data_hex = "0100000001" + signature_hex
        signature_data_url = url_encode(binascii.unhexlify(signature_data_hex))
        client_data_url = url_encode(client_data_str)
        # Send the response. Unfortunately it does not fit to the
        # registration, so we create a BadSignatureError
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "clientdata": client_data_url,
                                                 "signaturedata":
                                                     signature_data_url}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertEqual(result.get("status"), True)
            self.assertEqual(result.get("value"), False)

    def test_03_facet_list(self):
        with self.app.test_request_context('/ttype/u2f',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            data = res.json
            self.assertTrue("trustedFacets" in data)

        set_policy(name="facet1", scope=SCOPE.AUTH,
                   action="{0!s}=host1 host2 host3".format(U2FACTION.FACETS))

        with self.app.test_request_context('/ttype/u2f',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            data = res.json
            self.assertTrue("trustedFacets" in data)
            facets = data["trustedFacets"][0]
            ids = facets["ids"]
            self.assertTrue("https://host1" in ids)
            self.assertTrue("https://host2" in ids)
            self.assertTrue("https://host3" in ids)

        delete_policy("facet1")

    def test_04_create_token_validate(self):
        # test data taken from
        # https://fidoalliance.org/specs/fido-u2f-v1.0-ps-20141009/fido-u2f-raw-message-formats-ps-20141009.html#examples
        serial = "U2F0010BF6F"
        set_privacyidea_config("u2f.appId",
                               "https://puck.az.intern")
        # Registration data
        client_data = "eyJ0eXAiOiJuYXZpZ2F0b3IuaWQuZmluaXNoRW5yb2xsbWVudCIsImNoYWxsZW5nZSI6ImpIakIxaEM2VjA3dDl4ZnNNaDRfOEQ3U1JuSHRFY1BqUTdsaVl3cWxkX009Iiwib3JpZ2luIjoiaHR0cHM6Ly9wdWNrLmF6LmludGVybiIsImNpZF9wdWJrZXkiOiJ1bnVzZWQifQ"
        reg_data = "BQRHjwxEYFCkLHz3xdrmifKOHl2h17BmRJQ_S1Y9PRAhS2R186T391YE-ryqWis9HSmdp0XpRqUaKk9L8lxJTPpTQF_xFJ_LAsKkPTzKIwUlPIjGZDsLmv0en2Iya17Yz8X8OS89fuxwZOvEok-NQOKUTJP3att_RVe3dEAbq_iOtyAwggJEMIIBLqADAgECAgRVYr6gMAsGCSqGSIb3DQEBCzAuMSwwKgYDVQQDEyNZdWJpY28gVTJGIFJvb3QgQ0EgU2VyaWFsIDQ1NzIwMDYzMTAgFw0xNDA4MDEwMDAwMDBaGA8yMDUwMDkwNDAwMDAwMFowKjEoMCYGA1UEAwwfWXViaWNvIFUyRiBFRSBTZXJpYWwgMTQzMjUzNDY4ODBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABEszH3c9gUS5mVy-RYVRfhdYOqR2I2lcvoWsSCyAGfLJuUZ64EWw5m8TGy6jJDyR_aYC4xjz_F2NKnq65yvRQwmjOzA5MCIGCSsGAQQBgsQKAgQVMS4zLjYuMS40LjEuNDE0ODIuMS41MBMGCysGAQQBguUcAgEBBAQDAgUgMAsGCSqGSIb3DQEBCwOCAQEArBbZs262s6m3bXWUs09Z9Pc-28n96yk162tFHKv0HSXT5xYU10cmBMpypXjjI-23YARoXwXn0bm-BdtulED6xc_JMqbK-uhSmXcu2wJ4ICA81BQdPutvaizpnjlXgDJjq6uNbsSAp98IStLLp7fW13yUw-vAsWb5YFfK9f46Yx6iakM3YqNvvs9M9EUJYl_VrxBJqnyLx2iaZlnpr13o8NcsKIJRdMUOBqt_ageQg3ttsyq_3LyoNcu7CQ7x8NmeCGm_6eVnZMQjDmwFdymwEN4OxfnM5MkcKCYhjqgIGruWkVHsFnJa8qjZXneVvKoiepuUQyDEJ2GcqvhU2YKY1zBFAiEA4ZkIXXyjEPExcMGtW6kJXqYv7UHgjxJR5h3H9w9FV7gCIFGdhxZDqwCQKplDi-LU4WJ45OyCpNK6lGa72eZqUR_k"
        # Authentication data
        transaction_id = "05871369157706202013"
        challenge = "1616515928c389ba9e028d83eb5f63782cbf351ca6abbc81aeb0dddd4895b609"
        client_data_auth = "eyJ0eXAiOiJuYXZpZ2F0b3IuaWQuZ2V0QXNzZXJ0aW9uIiwiY2hhbGxlbmdlIjoiRmhaUldTakRpYnFlQW8yRDYxOWplQ3lfTlJ5bXE3eUJyckRkM1VpVnRnayIsIm9yaWdpbiI6Imh0dHBzOi8vcHVjay5hei5pbnRlcm4iLCJjaWRfcHVia2V5IjoidW51c2VkIn0"
        signature_data = "AQAAAAMwRQIgU8d6waOIRVVydg_AXxediEZGkfFioUjd6FG3OxH2wUMCIQDpxzavJyxRlMwgNmD1Kw-iw_oP2egdshU9hrpxFHTRzQ"

        # step 1
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "u2f",
                                                 "serial": serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertEqual(result.get("status"), True)
            self.assertEqual(result.get("value"), True)

        # Init step 2
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "u2f",
                                                 "serial": serial,
                                                 "regdata": reg_data,
                                                 "clientdata": client_data},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertEqual(result.get("status"), True)
            self.assertEqual(result.get("value"), True)

        # create a challenge in the database
        db_challenge = Challenge(serial,
                                 transaction_id=transaction_id,
                                 challenge=challenge,
                                 data=None)
        db_challenge.save()

        set_policy(name="u2f01", scope=SCOPE.AUTHZ,
                   action="{0!s}=issuer/.*Yubico.*/".format(U2FACTION.REQ) )

        # Successful C/R authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": serial,
                                                 "pass": "",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "clientdata":
                                                     client_data_auth,
                                                 "signaturedata":
                                                     signature_data}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertEqual(result.get("status"), True)
            self.assertEqual(result.get("value"), True)

        delete_policy("u2f01")
        remove_token(serial)

    def test_05_u2f_auth_fails_wrong_issuer(self):
        # test data taken from
        # https://fidoalliance.org/specs/fido-u2f-v1.0-ps-20141009/fido-u2f-raw-message-formats-ps-20141009.html#examples
        serial = "U2F0010BF6F"
        set_privacyidea_config("u2f.appId",
                               "https://puck.az.intern")
        # Registration data
        client_data = "eyJ0eXAiOiJuYXZpZ2F0b3IuaWQuZmluaXNoRW5yb2xsbWVudCIsImNoYWxsZW5nZSI6ImpIakIxaEM2VjA3dDl4ZnNNaDRfOEQ3U1JuSHRFY1BqUTdsaVl3cWxkX009Iiwib3JpZ2luIjoiaHR0cHM6Ly9wdWNrLmF6LmludGVybiIsImNpZF9wdWJrZXkiOiJ1bnVzZWQifQ"
        reg_data = "BQRHjwxEYFCkLHz3xdrmifKOHl2h17BmRJQ_S1Y9PRAhS2R186T391YE-ryqWis9HSmdp0XpRqUaKk9L8lxJTPpTQF_xFJ_LAsKkPTzKIwUlPIjGZDsLmv0en2Iya17Yz8X8OS89fuxwZOvEok-NQOKUTJP3att_RVe3dEAbq_iOtyAwggJEMIIBLqADAgECAgRVYr6gMAsGCSqGSIb3DQEBCzAuMSwwKgYDVQQDEyNZdWJpY28gVTJGIFJvb3QgQ0EgU2VyaWFsIDQ1NzIwMDYzMTAgFw0xNDA4MDEwMDAwMDBaGA8yMDUwMDkwNDAwMDAwMFowKjEoMCYGA1UEAwwfWXViaWNvIFUyRiBFRSBTZXJpYWwgMTQzMjUzNDY4ODBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABEszH3c9gUS5mVy-RYVRfhdYOqR2I2lcvoWsSCyAGfLJuUZ64EWw5m8TGy6jJDyR_aYC4xjz_F2NKnq65yvRQwmjOzA5MCIGCSsGAQQBgsQKAgQVMS4zLjYuMS40LjEuNDE0ODIuMS41MBMGCysGAQQBguUcAgEBBAQDAgUgMAsGCSqGSIb3DQEBCwOCAQEArBbZs262s6m3bXWUs09Z9Pc-28n96yk162tFHKv0HSXT5xYU10cmBMpypXjjI-23YARoXwXn0bm-BdtulED6xc_JMqbK-uhSmXcu2wJ4ICA81BQdPutvaizpnjlXgDJjq6uNbsSAp98IStLLp7fW13yUw-vAsWb5YFfK9f46Yx6iakM3YqNvvs9M9EUJYl_VrxBJqnyLx2iaZlnpr13o8NcsKIJRdMUOBqt_ageQg3ttsyq_3LyoNcu7CQ7x8NmeCGm_6eVnZMQjDmwFdymwEN4OxfnM5MkcKCYhjqgIGruWkVHsFnJa8qjZXneVvKoiepuUQyDEJ2GcqvhU2YKY1zBFAiEA4ZkIXXyjEPExcMGtW6kJXqYv7UHgjxJR5h3H9w9FV7gCIFGdhxZDqwCQKplDi-LU4WJ45OyCpNK6lGa72eZqUR_k"
        # Authentication data
        transaction_id = "05871369157706202013"
        challenge = "1616515928c389ba9e028d83eb5f63782cbf351ca6abbc81aeb0dddd4895b609"
        client_data_auth = "eyJ0eXAiOiJuYXZpZ2F0b3IuaWQuZ2V0QXNzZXJ0aW9uIiwiY2hhbGxlbmdlIjoiRmhaUldTakRpYnFlQW8yRDYxOWplQ3lfTlJ5bXE3eUJyckRkM1VpVnRnayIsIm9yaWdpbiI6Imh0dHBzOi8vcHVjay5hei5pbnRlcm4iLCJjaWRfcHVia2V5IjoidW51c2VkIn0"
        signature_data = "AQAAAAMwRQIgU8d6waOIRVVydg_AXxediEZGkfFioUjd6FG3OxH2wUMCIQDpxzavJyxRlMwgNmD1Kw-iw_oP2egdshU9hrpxFHTRzQ"

        # step 1
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "u2f",
                                                 "user": "cornelius",
                                                 "realm": self.realm1,
                                                 "serial": serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertEqual(result.get("status"), True)
            self.assertEqual(result.get("value"), True)

        # Init step 2
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "u2f",
                                                 "serial": serial,
                                                 "regdata": reg_data,
                                                 "clientdata": client_data},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertEqual(result.get("status"), True)
            self.assertEqual(result.get("value"), True)

        # create a challenge in the database
        db_challenge = Challenge(serial,
                                 transaction_id=transaction_id,
                                 challenge=challenge,
                                 data=None)
        db_challenge.save()

        set_policy(name="u2f01", scope=SCOPE.AUTHZ,
                   action="{0!s}=issuer/.*Plugup.*/".format(U2FACTION.REQ))

        # Successful C/R authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": serial,
                                                 "pass": "",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "clientdata":
                                                     client_data_auth,
                                                 "signaturedata":
                                                     signature_data}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json.get("result")
            self.assertEqual(result.get("status"), False)
            self.assertEqual(result.get("error").get("code"), ERROR.POLICY)
            self.assertEqual(result.get("error").get("message"),
                             u'The U2F device is not allowed to authenticate '
                             u'due to policy restriction.')

        delete_policy("u2f01")
        remove_token(serial)

    def test_06_u2f_enrollment_fails_wrong_issuer(self):
        # test data taken from
        # https://fidoalliance.org/specs/fido-u2f-v1.0-ps-20141009/fido-u2f-raw-message-formats-ps-20141009.html#examples
        serial = "U2F0010BF6F"
        set_privacyidea_config("u2f.appId",
                               "https://puck.az.intern")
        # Registration data
        client_data = "eyJ0eXAiOiJuYXZpZ2F0b3IuaWQuZmluaXNoRW5yb2xsbWVudCIsImNoYWxsZW5nZSI6ImpIakIxaEM2VjA3dDl4ZnNNaDRfOEQ3U1JuSHRFY1BqUTdsaVl3cWxkX009Iiwib3JpZ2luIjoiaHR0cHM6Ly9wdWNrLmF6LmludGVybiIsImNpZF9wdWJrZXkiOiJ1bnVzZWQifQ"
        reg_data = "BQRHjwxEYFCkLHz3xdrmifKOHl2h17BmRJQ_S1Y9PRAhS2R186T391YE-ryqWis9HSmdp0XpRqUaKk9L8lxJTPpTQF_xFJ_LAsKkPTzKIwUlPIjGZDsLmv0en2Iya17Yz8X8OS89fuxwZOvEok-NQOKUTJP3att_RVe3dEAbq_iOtyAwggJEMIIBLqADAgECAgRVYr6gMAsGCSqGSIb3DQEBCzAuMSwwKgYDVQQDEyNZdWJpY28gVTJGIFJvb3QgQ0EgU2VyaWFsIDQ1NzIwMDYzMTAgFw0xNDA4MDEwMDAwMDBaGA8yMDUwMDkwNDAwMDAwMFowKjEoMCYGA1UEAwwfWXViaWNvIFUyRiBFRSBTZXJpYWwgMTQzMjUzNDY4ODBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABEszH3c9gUS5mVy-RYVRfhdYOqR2I2lcvoWsSCyAGfLJuUZ64EWw5m8TGy6jJDyR_aYC4xjz_F2NKnq65yvRQwmjOzA5MCIGCSsGAQQBgsQKAgQVMS4zLjYuMS40LjEuNDE0ODIuMS41MBMGCysGAQQBguUcAgEBBAQDAgUgMAsGCSqGSIb3DQEBCwOCAQEArBbZs262s6m3bXWUs09Z9Pc-28n96yk162tFHKv0HSXT5xYU10cmBMpypXjjI-23YARoXwXn0bm-BdtulED6xc_JMqbK-uhSmXcu2wJ4ICA81BQdPutvaizpnjlXgDJjq6uNbsSAp98IStLLp7fW13yUw-vAsWb5YFfK9f46Yx6iakM3YqNvvs9M9EUJYl_VrxBJqnyLx2iaZlnpr13o8NcsKIJRdMUOBqt_ageQg3ttsyq_3LyoNcu7CQ7x8NmeCGm_6eVnZMQjDmwFdymwEN4OxfnM5MkcKCYhjqgIGruWkVHsFnJa8qjZXneVvKoiepuUQyDEJ2GcqvhU2YKY1zBFAiEA4ZkIXXyjEPExcMGtW6kJXqYv7UHgjxJR5h3H9w9FV7gCIFGdhxZDqwCQKplDi-LU4WJ45OyCpNK6lGa72eZqUR_k"

        # step 1
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "u2f",
                                                 "user": "cornelius",
                                                 "realm": self.realm1,
                                                 "serial": serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(result.get("status"), True)
            self.assertEqual(result.get("value"), True)

        set_policy(name="u2f01", scope=SCOPE.ENROLL,
                   action="{0!s}=issuer/.*Plugup.*/".format(U2FACTION.REQ))

        # Init step 2
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "u2f",
                                                 "serial": serial,
                                                 "regdata": reg_data,
                                                 "clientdata": client_data},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json.get("result")
            self.assertEqual(result.get("status"), False)
            self.assertEqual(result.get("error").get("message"),
                             u'The U2F device is not allowed to be registered '
                             u'due to policy restriction.')

        delete_policy("u2f01")
        remove_token(serial)

# TODO: check wrong challenge
# TODO: check wrong type (navigator.id)
# TODO: check for old counter (these might also be checked in test_lib_tokens_u2f)
