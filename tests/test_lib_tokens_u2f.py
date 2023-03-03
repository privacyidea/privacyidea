"""
This test file tests the lib.tokens.u2ftoken
This depends on lib.tokenclass
"""
from .base import MyTestCase
from privacyidea.lib.tokens.u2ftoken import U2fTokenClass
from privacyidea.lib.tokens.u2f import (check_registration_data,
                                        parse_registration_data, url_decode,
                                        check_response, parse_response_data)
from privacyidea.lib.token import init_token, remove_token, check_user_pass
from privacyidea.lib.user import User
from privacyidea.lib.policy import set_policy, SCOPE, ACTION, delete_policy
from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.utils import hexlify_and_unicode, to_bytes
from privacyidea.lib.error import TokenAdminError
from privacyidea.lib import _
import binascii
from hashlib import sha256
from OpenSSL import crypto
import base64


REG_DATA = "BQRFnd8XtfZzsTK68VPK64Bcjiog_ZzyYNuzjaaGwpPnSpifxaqQV4_4IMxVlGS3CLoQmNAR41MSMxZHG0dENLRmQGnk4OqRxGRHmUOOLmDkGgdIJycQe79JCERV1gqGnWAOFBg_bH4WFSxZwnX-IMRcl3zW_X442QNrrdFySvXrba4wggIcMIIBBqADAgECAgQ4Zt91MAsGCSqGSIb3DQEBCzAuMSwwKgYDVQQDEyNZdWJpY28gVTJGIFJvb3QgQ0EgU2VyaWFsIDQ1NzIwMDYzMTAgFw0xNDA4MDEwMDAwMDBaGA8yMDUwMDkwNDAwMDAwMFowKzEpMCcGA1UEAwwgWXViaWNvIFUyRiBFRSBTZXJpYWwgMTM4MzExNjc4NjEwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAAQ3jfx0DHOblHJO09Ujubh2gQZWwT3ob6-uzzjZD1XiyAob_gsw3FOzXefQRblty48r-U-o4LkDFjx_btwuSHtxoxIwEDAOBgorBgEEAYLECgEBBAAwCwYJKoZIhvcNAQELA4IBAQIaR2TKAInPkq24f6hIU45yzD79uzR5KUMEe4IWqTm69METVio0W2FHWXlpeUe85nGqanwGeW7U67G4_WAnGbcd6zz2QumNsdlmb_AebbdPRa95Z8BG1ub_S04JoxQYNLaa8WRlzN7POgqAnAqkmnsZQ_W9Tj2uO9zP3mpxOkkmnqz7P5zt4Lp5xrv7p15hGOIPD5V-ph7tUmiCJsq0LfeRA36X7aXi32Ap0rt_wyfnRef59YYr7SmwaMuXKjbIZSLesscZZTMzXd-uuLb6DbUCasqEVBkGGqTRfAcOmPov1nHUrNDCkOR0obR4PsJG4PiamIfApNeoXGYpGbok6nucMEYCIQC_yerJqB3mnuAJGfbdKuOIx-Flxr-VSQ2nAkUUE_50dQIhAJE2NL1Xs2oVEG4bFzEM86TfS7nkHxad89aYmUrII49V"
CLIENT_DATA_HASH = "eyJ0eXAiOiJuYXZpZ2F0b3IuaWQuZmluaXNoRW5yb2xsbWVudCIsImNoYWxsZW5nZSI6ImdXbndtYnFSMl9YOE91RFhId0dyQWNmUTBUajN4YTVfZ2RJMjBYcVlsdTg9Iiwib3JpZ2luIjoiaHR0cDovL2xvY2FsaG9zdDo1MDAwIiwiY2lkX3B1YmtleSI6IiJ9"
KEY_HANDLE_HEX = "61655467367048455a45655a51343475594f51614230676e4a78423776306b4952465857436f61645941345547443973666859564c466e436466346778467958664e6239666a6a5a4132757430584a4b396574747267"
APP_ID = "http://localhost:5000"


class U2FHelperFuncTestCase(MyTestCase):

    def test_01_check_reg_data(self):
        attestation_cert = "3082013c3081e4a003020102020a4790128000115595735230" \
                           "0a06082a8648ce3d0403023017311530130603550403130c" \
                           "476e756262792050696c6f74301e170d313230383134313" \
                           "8323933325a170d3133303831343138323933325a303131" \
                           "2f302d0603550403132650696c6f74476e756262792d302" \
                           "e342e312d34373930313238303030313135353935373335" \
                           "323059301306072a8648ce3d020106082a8648ce3d030107" \
                           "034200048d617e65c9508e64bcc5673ac82a6799da3c1446" \
                           "682c258c463fffdf58dfd2fa3e6c378b53d795c4a4dffb4" \
                           "199edd7862f23abaf0203b4b8911ba0569994e101300a06" \
                           "082a8648ce3d0403020347003044022060cdb6061e9c2226" \
                           "2d1aac1d96d8c70829b2366531dda268832cb836bcd30dfa" \
                           "0220631b1459f09e6330055722c8d89b7f48883b9089b88d" \
                           "60d1d9795902b30410df"

        cdata_str = """{"typ": "navigator.id.finishEnrollment",
                        "challenge": "vqrS6WXDe1JUs5_c3i4-LkKIHRr-3XVb3azuA5TifHo",
                        "cid_pubkey": {
                            "kty": "EC",
                            "crv": "P-256",
                            "x": "HzQwlfXX7Q4S5MtCCnZUNBw3RMzPO9tOyWjBqRl4tJ8",
                            "y": "XVguGFLIZx1fXg3wNqfdbn75hi4-_7-BxhMljw42Ht4"},
                        "origin": "http://example.com"}"""
        my_app_id = 'http://example.com'

        app_id_hash = hexlify_and_unicode(sha256(to_bytes(my_app_id)).digest())
        self.assertEqual(app_id_hash,
                         "f0e6a6a97042a4f1f1c87f5f7d44315b2d852c2df5c7991cc66241bf7072d1c4")
        attestation_cert = crypto.load_certificate(crypto.FILETYPE_ASN1,
                                                   binascii.unhexlify(attestation_cert))
        client_data_str = ''.join(cdata_str.split())
        client_data_hash = hexlify_and_unicode(sha256(to_bytes(client_data_str)).digest())
        self.assertEqual(client_data_hash,
                         "4142d21c00d94ffb9d504ada8f99b721f4b191ae4e37ca0140f696b6983cfacb")

        user_pub_key = "04b174bc49c7ca254b70d2e5c207cee9cf174820ebd77ea3c65508c26da51b657c1cc6b952f8621697936482da0a6d3d3826a59095daf6cd7c03e2e60385d2f6d9"
        key_handle = "2a552dfdb7477ed65fd84133f86196010b2215b57da75d315b7b9e8fe2e3925a6019551bab61d16591659cbaf00b4950f7abfe6660e2e006f76868b772d70c25"
        signature = "304502201471899bcc3987e62e8202c9b39c33c19033f7340352dba80fcab017db9230e402210082677d673d891933ade6f617e5dbde2e247e70423fd5ad7804a6d3d3961ef871"

        r = check_registration_data(attestation_cert, my_app_id, client_data_str,
                                    user_pub_key, key_handle, signature)
        self.assertEqual(r, True)

    def test_02_parse_reg_date(self):
        attestation_cert, user_pub_key, key_handle, signature, description \
            = parse_registration_data(REG_DATA)
        self.assertEqual(description, 'Yubico U2F EE Serial 13831167861')
        self.assertEqual(signature,
                     '3046022100bfc9eac9a81de69ee00919f6dd2ae388c7e165c6bf95490da702451413fe7475022100913634bd57b36a15106e1b17310cf3a4df4bb9e41f169df3d698994ac8238f55')
        self.assertEqual(key_handle, '69e4e0ea91c4644799438e2e60e41a07482727107bbf49084455d60a869d600e14183f6c7e16152c59c275fe20c45c977cd6fd7e38d9036badd1724af5eb6dae')
        self.assertEqual(user_pub_key, '04459ddf17b5f673b132baf153caeb805c8e2a20fd9cf260dbb38da686c293e74a989fc5aa90578ff820cc559464b708ba1098d011e353123316471b474434b466')

    def test_03_url_decode(self):
        dec = url_decode("SGFsbG8sIGRhcyBpc3QgZWluIFRlc3QuLi4")
        self.assertEqual(dec, b"Hallo, das ist ein Test...")

    def test_04_check_response(self):
        # According to
        # https://fidoalliance.org/specs/fido-u2f-v1.0-nfc-bt-amendment
        # -20150514/fido-u2f-raw-message-formats.html#authentication-example
        app_id = "https://gstatic.com/securitykey/a/example.com"
        user_pub_key = \
            "04d368f1b665bade3c33a20f1e429c7750d5033660c019119d29aa4ba7abc04aa7c80a46bbe11ca8cb5674d74f31f8a903f6bad105fb6ab74aefef4db8b0025e1d"
        cdata_str = """{"typ": "navigator.id.getAssertion",
                             "challenge": "opsXqUifDriAAmWclinfbS0e-USY0CgyJHe_Otd7z8o",
                             "cid_pubkey": {
                                 "kty": "EC",
                                 "crv": "P-256",
                                 "x": "HzQwlfXX7Q4S5MtCCnZUNBw3RMzPO9tOyWjBqRl4tJ8",
                                 "y": "XVguGFLIZx1fXg3wNqfdbn75hi4-_7-BxhMljw42Ht4"},
                             "origin": "http://example.com"}"""
        client_data_str = ''.join(cdata_str.split())
        counter = 1
        user_presence_byte = b'\x01'
        signature = "304402204b5f0cd17534cedd8c34ee09570ef542a353df4436030ce43d406de870b847780220267bb998fac9b7266eb60e7cb0b5eabdfd5ba9614f53c7b22272ec10047a923f"
        r = check_response(user_pub_key, app_id, client_data_str, signature,
                           counter, user_presence_byte)
        self.assertEqual(r, True)

    def test_05_parse_response(self):
        response = "0100000001304402204b5f0cd17534cedd8c34ee09570ef542a353df4436030ce43d406de870b847780220267bb998fac9b7266eb60e7cb0b5eabdfd5ba9614f53c7b22272ec10047a923f"
        up, count, sig = parse_response_data(response)
        self.assertTrue(up, "\x01")
        self.assertTrue(count, 1)
        self.assertTrue(sig, response[5:])


class U2FTokenTestCase(MyTestCase):

    def test_00_users(self):
        self.setUp_user_realms()

        set_privacyidea_config("u2f.appId", APP_ID)

    def test_01_create_token(self):
        pin = "test"
        # Init step1
        token = init_token({"type": "u2f",
                            "pin": pin})
        serial = token.token.serial

        self.assertEqual(token.type, "u2f")

        prefix = U2fTokenClass.get_class_prefix()
        self.assertEqual(prefix, "U2F")

        info = U2fTokenClass.get_class_info()
        self.assertEqual(info.get("type"), "u2f")

        info = U2fTokenClass.get_class_info("type")
        self.assertEqual(info, "u2f")

        idetail = token.get_init_detail()
        detail_serial = idetail.get("serial")
        self.assertEqual(serial, detail_serial)

        registerRequest = idetail.get("u2fRegisterRequest")
        version = registerRequest.get("version")
        self.assertEqual(version, "U2F_V2")
        challenge = registerRequest.get("challenge")
        self.assertEqual(len(challenge), 43)

        # Init step 2
        token = init_token({"type": "u2f",
                            "serial": serial,
                            "regdata": REG_DATA,
                            "clientdata": CLIENT_DATA_HASH})
        idetail = token.get_init_detail()
        subject = idetail.get("u2fRegisterResponse").get("subject")
        self.assertEqual(subject, 'Yubico U2F EE Serial 13831167861')

        # check the tokeninfo of the attestation certificate
        issuer = token.get_tokeninfo("attestation_issuer")
        subject = token.get_tokeninfo("attestation_subject")
        serial = token.get_tokeninfo("attestation_serial")
        self.assertEqual(issuer, "CN=Yubico U2F Root CA Serial 457200631")
        self.assertEqual(subject, "CN=Yubico U2F EE Serial 13831167861")
        self.assertEqual(serial, "946265973")

        #
        # Do some authentication
        #

        # challenge
        # check challenge
        is_chalrequest = token.is_challenge_request(pin)
        self.assertEqual(is_chalrequest, True)

        # create challenge
        res, message, t_id, reply_dict = token.create_challenge()
        attributes = reply_dict.get("attributes")
        self.assertTrue(res)
        expected_text = _("Please confirm with your U2F token ({0!s})").format("Yubico U2F EE Serial 13831167861")
        self.assertEqual(message, expected_text)
        self.assertEqual(len(t_id), 20)
        u2f_sign_request = attributes.get("u2fSignRequest")
        version = u2f_sign_request.get("version")
        self.assertEqual(version, "U2F_V2")
        key_handle = u2f_sign_request.get("keyHandle")
        key_handle_hex = hexlify_and_unicode(key_handle)
        self.assertTrue("appId" in u2f_sign_request, u2f_sign_request)
        self.assertTrue("challenge" in u2f_sign_request, u2f_sign_request)
        self.assertTrue("keyHandle" in u2f_sign_request, u2f_sign_request)
        self.assertEqual(key_handle_hex, KEY_HANDLE_HEX)
        self.assertEqual(u2f_sign_request.get("appId"), APP_ID)
        self.assertEqual(len(u2f_sign_request.get("challenge")), 43)

    def test_02_parse_regdata(self):
        client_data = "eyJ0eXAiOiJuYXZpZ2F0b3IuaWQuZmluaXNoRW5yb2xsbWVudCIsImNoYWxsZW5nZSI6IlNna3pUekdyYnNVREUyNEJSMV9kUTRYbXJtNTVqU2MzVml3Sm5DRjVmWm8iLCJvcmlnaW4iOiJodHRwczovL2RlbW8ueXViaWNvLmNvbSIsImNpZF9wdWJrZXkiOiJ1bnVzZWQifQ"
        reg_data = "BQT3NET2RTTcgzAiZRW5gkg3TT6mgQBepZl96iMtj-nXU25VdwBXCL1EjWOY-q1M76vT_iX9ebDhkZ1kvosbi3_AQGVopI2hcyIsc8q-KpzerJIZgWtN25bCy6g_hTk_M1khCjQGaiGJFwnk8GIn2OnkNOJRe7V00Q9PBZHn5mFwfFwwggJEMIIBLqADAgECAgRVYr6gMAsGCSqGSIb3DQEBCzAuMSwwKgYDVQQDEyNZdWJpY28gVTJGIFJvb3QgQ0EgU2VyaWFsIDQ1NzIwMDYzMTAgFw0xNDA4MDEwMDAwMDBaGA8yMDUwMDkwNDAwMDAwMFowKjEoMCYGA1UEAwwfWXViaWNvIFUyRiBFRSBTZXJpYWwgMTQzMjUzNDY4ODBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABEszH3c9gUS5mVy-RYVRfhdYOqR2I2lcvoWsSCyAGfLJuUZ64EWw5m8TGy6jJDyR_aYC4xjz_F2NKnq65yvRQwmjOzA5MCIGCSsGAQQBgsQKAgQVMS4zLjYuMS40LjEuNDE0ODIuMS41MBMGCysGAQQBguUcAgEBBAQDAgUgMAsGCSqGSIb3DQEBCwOCAQEArBbZs262s6m3bXWUs09Z9Pc-28n96yk162tFHKv0HSXT5xYU10cmBMpypXjjI-23YARoXwXn0bm-BdtulED6xc_JMqbK-uhSmXcu2wJ4ICA81BQdPutvaizpnjlXgDJjq6uNbsSAp98IStLLp7fW13yUw-vAsWb5YFfK9f46Yx6iakM3YqNvvs9M9EUJYl_VrxBJqnyLx2iaZlnpr13o8NcsKIJRdMUOBqt_ageQg3ttsyq_3LyoNcu7CQ7x8NmeCGm_6eVnZMQjDmwFdymwEN4OxfnM5MkcKCYhjqgIGruWkVHsFnJa8qjZXneVvKoiepuUQyDEJ2GcqvhU2YKY1zBFAiEAqqVKbLnZuWYyzjcsb1YnHEyuk-dmM77Q66iExrj8h2cCIHAvpisjLj-D2KvnZZcIQ_fFjFj9OX5jkfmJ65QVQ9bE"
        cert, user_pub_key, key_handle, signature, description = \
            parse_registration_data(reg_data)
        self.assertEqual(user_pub_key,
                         '04f73444f64534dc8330226515b98248374d3ea681005ea5997dea232d8fe9d7536e5577005708bd448d6398faad4cefabd3fe25fd79b0e1919d64be8b1b8b7fc0')
        self.assertEqual(key_handle,
                         '6568a48da173222c73cabe2a9cdeac9219816b4ddb96c2cba83f85393f3359210a34066a21891709e4f06227d8e9e434e2517bb574d10f4f0591e7e661707c5c')
        self.assertEqual(description, 'Yubico U2F EE Serial 1432534688')

        client_data_str = base64.b64decode(client_data+"==")
        r = check_registration_data(cert, "https://demo.yubico.com",
                                    client_data_str,
                                    user_pub_key, key_handle, signature)
        self.assertTrue(r)

        # modify signature
        broken_sig = 'ff' + signature[2:]
        with self.assertRaisesRegex(Exception,
                                    'Error checking the signature of the registration data.'):
            check_registration_data(cert, "https://demo.yubico.com", client_data_str,
                                    user_pub_key, key_handle, broken_sig)

    def test_03_missing_app_id(self):
        set_privacyidea_config("u2f.appId", '')
        pin = "test"
        token = init_token({"type": "u2f",
                            "pin": pin})
        with self.assertRaises(TokenAdminError):
            _detail = token.get_init_detail()

    def test_04_broken_reg_data(self):
        reg_data = 'BgT3NET2RTTcgzAiZRW5gkg3TT6mgQBepZl96iMtj-nXU25VdwBXCL1EjW' \
                   'OY-q1M76vT_iX9ebDhkZ1kvosbi3_AQGVopI2hcyIsc8q-KpzerJIZgWtN' \
                   '25bCy6g_hTk_M1khCjQGaiGJFwnk8GIn2OnkNOJRe7V00Q9PBZHn5mFwfF' \
                   'wwggJEMIIBLqADAgECAgRVYr6gMAsGCSqGSIb3DQEBCzAuMSwwKgYDVQQD' \
                   'EyNZdWJpY28gVTJGIFJvb3QgQ0EgU2VyaWFsIDQ1NzIwMDYzMTAgFw0xND' \
                   'A4MDEwMDAwMDBaGA8yMDUwMDkwNDAwMDAwMFowKjEoMCYGA1UEAwwfWXVi' \
                   'aWNvIFUyRiBFRSBTZXJpYWwgMTQzMjUzNDY4ODBZMBMGByqGSM49AgEGCC' \
                   'qGSM49AwEHA0IABEszH3c9gUS5mVy-RYVRfhdYOqR2I2lcvoWsSCyAGfLJ' \
                   'uUZ64EWw5m8TGy6jJDyR_aYC4xjz_F2NKnq65yvRQwmjOzA5MCIGCSsGAQ' \
                   'QBgsQKAgQVMS4zLjYuMS40LjEuNDE0ODIuMS41MBMGCysGAQQBguUcAgEB' \
                   'BAQDAgUgMAsGCSqGSIb3DQEBCwOCAQEArBbZs262s6m3bXWUs09Z9Pc-28' \
                   'n96yk162tFHKv0HSXT5xYU10cmBMpypXjjI-23YARoXwXn0bm-BdtulED6' \
                   'xc_JMqbK-uhSmXcu2wJ4ICA81BQdPutvaizpnjlXgDJjq6uNbsSAp98ISt' \
                   'LLp7fW13yUw-vAsWb5YFfK9f46Yx6iakM3YqNvvs9M9EUJYl_VrxBJqnyL' \
                   'x2iaZlnpr13o8NcsKIJRdMUOBqt_ageQg3ttsyq_3LyoNcu7CQ7x8NmeCG' \
                   'm_6eVnZMQjDmwFdymwEN4OxfnM5MkcKCYhjqgIGruWkVHsFnJa8qjZXneV' \
                   'vKoiepuUQyDEJ2GcqvhU2YKY1zBFAiEAqqVKbLnZuWYyzjcsb1YnHEyuk-' \
                   'dmM77Q66iExrj8h2cCIHAvpisjLj-D2KvnZZcIQ_fFjFj9OX5jkfmJ65QVQ9bE'
        with self.assertRaisesRegex(Exception,
                                    'The registration data is in a wrong format.'):
            parse_registration_data(reg_data)


class MultipleU2FTokenTestCase(MyTestCase):
    app_id = 'https://localhost:5000'
    reg_data1 = ("BQSUSmNE4buL5xIqMlaRyJSMHhSvr37LpTT2e-zxyVoY21dzl1gZwcTws9I8r"
                 "CCKwHV-j9dt3NsWIPypid8PsKWsQMU-IQlPNvVsMXxXyhMLjBoUvdiDZShlo5"
                 "w-P6_i_bT2mDF9O07q2lMW-AXGyIKKSrlsh-1oJBklRUYQ0sbfyEgwggK8MII"
                 "BpKADAgECAgQDrfASMA0GCSqGSIb3DQEBCwUAMC4xLDAqBgNVBAMTI1l1Ymlj"
                 "byBVMkYgUm9vdCBDQSBTZXJpYWwgNDU3MjAwNjMxMCAXDTE0MDgwMTAwMDAwM"
                 "FoYDzIwNTAwOTA0MDAwMDAwWjBtMQswCQYDVQQGEwJTRTESMBAGA1UECgwJWX"
                 "ViaWNvIEFCMSIwIAYDVQQLDBlBdXRoZW50aWNhdG9yIEF0dGVzdGF0aW9uMSY"
                 "wJAYDVQQDDB1ZdWJpY28gVTJGIEVFIFNlcmlhbCA2MTczMDgzNDBZMBMGByqG"
                 "SM49AgEGCCqGSM49AwEHA0IABBmeh5wWLbfcOe5KQqBGFqWzCf7KCS92vglI-"
                 "W1ulcrkzGXNVKBZz73HybMbKx1sGER5wsBh9BiqlUtZaiwc-hejbDBqMCIGCS"
                 "sGAQQBgsQKAgQVMS4zLjYuMS40LjEuNDE0ODIuMS43MBMGCysGAQQBguUcAgE"
                 "BBAQDAgQwMCEGCysGAQQBguUcAQEEBBIEEPormdyeOUJXj5JKMNI8QRgwDAYD"
                 "VR0TAQH_BAIwADANBgkqhkiG9w0BAQsFAAOCAQEAKOuzZ_7R2PDiievKn_bYB"
                 "1fGDprlfLFyjJscOMq7vYTZI32oMawhlJ8PLfwMMWv9sXWzbmOiK7tYDq3KUo"
                 "DQeYQOWh4lcmJaO_uHYDPb-yKpack4uJzhcTWUAKElLZcCqRKT1UUZ6WDdIs6"
                 "KJ-sF6355t1DAAv7ZAWtxHsmtdFAb2RTLvo7ZVxKBt09E6wd85h7LBquFqXJV"
                 "Jn7o45gr9D8Msho4LSNeueTObbKYxAVCUEAjKyth4QzXDGIVvAO36UBxtw4S0"
                 "cR_lmVaLvmdTOVafxtLH_kU7hNtnmEgRxSIZGmIgEQxFmU4ibhkhtnJyf-8k4"
                 "VFNWmzRXRLjKC0NzBEAiBcVPalM6D9t0JFcDFEJW4OiMr945SDuiJFaxlwi9M"
                 "SawIgdpy0pATSpLXaiFfUqxoFXaMfo-oSqssdZdcWIlWGCpI")
    client_data1 = ('eyJjaGFsbGVuZ2UiOiJJeF9HbWo1SkVFYktDR3k0QV9BVVZFYWRGTWNJam'
                    'hBOC1meTJha1ZFaUFRIiwib3JpZ2luIjoiaHR0cHM6Ly9sb2NhbGhvc3Q6'
                    'NTAwMCIsInR5cCI6Im5hdmlnYXRvci5pZC5maW5pc2hFbnJvbGxtZW50In0')

    reg_data2 = ('BQREKCB4dlbzcqkU7T1talLdlX8pV-aJa0ijSpM2JIXg490mvhXVRquJuSkhr'
                 'iz0YFrBsB0FjtbTejlsHeKO5de2QKfcG86b738Bq_RntwwH9Nf1VrsFHrdHnh'
                 '57-9-z7dTGKVD57W_LQch2QtjgZcPslUq19kbz-PXs-WJxgRNhMMUwggK8MII'
                 'BpKADAgECAgQDrfASMA0GCSqGSIb3DQEBCwUAMC4xLDAqBgNVBAMTI1l1Ymlj'
                 'byBVMkYgUm9vdCBDQSBTZXJpYWwgNDU3MjAwNjMxMCAXDTE0MDgwMTAwMDAwM'
                 'FoYDzIwNTAwOTA0MDAwMDAwWjBtMQswCQYDVQQGEwJTRTESMBAGA1UECgwJWX'
                 'ViaWNvIEFCMSIwIAYDVQQLDBlBdXRoZW50aWNhdG9yIEF0dGVzdGF0aW9uMSY'
                 'wJAYDVQQDDB1ZdWJpY28gVTJGIEVFIFNlcmlhbCA2MTczMDgzNDBZMBMGByqG'
                 'SM49AgEGCCqGSM49AwEHA0IABBmeh5wWLbfcOe5KQqBGFqWzCf7KCS92vglI-'
                 'W1ulcrkzGXNVKBZz73HybMbKx1sGER5wsBh9BiqlUtZaiwc-hejbDBqMCIGCS'
                 'sGAQQBgsQKAgQVMS4zLjYuMS40LjEuNDE0ODIuMS43MBMGCysGAQQBguUcAgE'
                 'BBAQDAgQwMCEGCysGAQQBguUcAQEEBBIEEPormdyeOUJXj5JKMNI8QRgwDAYD'
                 'VR0TAQH_BAIwADANBgkqhkiG9w0BAQsFAAOCAQEAKOuzZ_7R2PDiievKn_bYB'
                 '1fGDprlfLFyjJscOMq7vYTZI32oMawhlJ8PLfwMMWv9sXWzbmOiK7tYDq3KUo'
                 'DQeYQOWh4lcmJaO_uHYDPb-yKpack4uJzhcTWUAKElLZcCqRKT1UUZ6WDdIs6'
                 'KJ-sF6355t1DAAv7ZAWtxHsmtdFAb2RTLvo7ZVxKBt09E6wd85h7LBquFqXJV'
                 'Jn7o45gr9D8Msho4LSNeueTObbKYxAVCUEAjKyth4QzXDGIVvAO36UBxtw4S0'
                 'cR_lmVaLvmdTOVafxtLH_kU7hNtnmEgRxSIZGmIgEQxFmU4ibhkhtnJyf-8k4'
                 'VFNWmzRXRLjKC0NzBFAiEAgx6TM_lyZE6SQx05Wlot-hMK-Cp2p8itseOPNp_'
                 'xtu4CIDpSYJYOb10vM32rjrBNDd-AoKJWbIQRtAwjVEZjXwz6')

    client_data2 = ('eyJjaGFsbGVuZ2UiOiJUdU84MDVPTEQzdXpUNmNnalZ6blRJSjRrZXg4N'
                    'WlremlUTG1aNC1jQnBvIiwib3JpZ2luIjoiaHR0cHM6Ly9sb2NhbGhvc3'
                    'Q6NTAwMCIsInR5cCI6Im5hdmlnYXRvci5pZC5maW5pc2hFbnJvbGxtZW5'
                    '0In0')

    def setUp(self):
        self.setUp_user_realms()
        self.user = User(login='cornelius', resolver=self.resolvername1,
                         realm=self.realm1)
        set_privacyidea_config("u2f.appId", self.app_id)
        # init step 1
        self.token1 = init_token({'type': 'u2f'})
        self.serial1 = self.token1.token.serial
        # finish init step 1
        res = self.token1.get_init_detail()
        # init step 2
        self.token1 = init_token({"type": "u2f",
                                  "serial": self.serial1,
                                  "regdata": self.reg_data1,
                                  "clientdata": self.client_data1},
                                 user=self.user)
        # Token 2
        # init step 1
        self.token2 = init_token({'type': 'u2f'})
        self.serial2 = self.token2.token.serial
        # finish init step 1
        res = self.token2.get_init_detail()
        # init step 2
        self.token2 = init_token({"type": "u2f",
                                  "serial": self.serial2,
                                  "regdata": self.reg_data2,
                                  "clientdata": self.client_data2},
                                 user=self.user)

    def tearDown(self):
        remove_token(serial=self.serial1)
        remove_token(serial=self.serial2)

    # TODO: also test challenge-response with different tokens (u2f + totp)
    def test_01_multiple_token(self):
        set_policy("otppin", scope=SCOPE.AUTH, action="{0!s}=none".format(ACTION.OTPPIN))
        res, reply = check_user_pass(self.user, '')
        self.assertFalse(res)
        self.assertIn('transaction_id', reply, reply)
        tid = reply['transaction_id']
        self.assertIn('multi_challenge', reply, reply)
        self.assertEqual(len(reply['multi_challenge']), 2, reply['multi_challenge'])
        self.assertIn('messages', reply, reply)
        self.assertEqual(len(reply['messages']), 2, reply['messages'])
        # check that the serials of the challenges are different
        chal1 = reply['multi_challenge'][0]
        chal2 = reply['multi_challenge'][1]
        self.assertNotEqual(chal1['serial'], chal2['serial'],
                            reply['multi_challenge'])
        self.assertEqual(chal1['transaction_id'], chal2['transaction_id'],
                         reply['multi_challenge'])
        # Now make sure that the requests contain the same challenge
        self.assertEqual(chal1['attributes']['u2fSignRequest']['challenge'],
                         chal2['attributes']['u2fSignRequest']['challenge'],
                         reply['multi_challenge'])
        # check that we have two challenges in the db with the same challenge
        chals = get_challenges(transaction_id=tid)
        self.assertEqual(len(chals), 2, chals)
        self.assertEqual(chals[0].challenge, chals[1].challenge, chals)

        delete_policy('otppin')
