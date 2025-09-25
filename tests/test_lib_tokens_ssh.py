"""
This test file tests the lib.tokens.sshkeytoken
This depends on lib.tokenclass
"""
from privacyidea.lib.error import TokenAdminError
from privacyidea.lib.token import init_token, import_tokens, get_tokens
from privacyidea.lib.tokenclass import ROLLOUTSTATE
from privacyidea.lib.tokens.sshkeytoken import SSHkeyTokenClass
from privacyidea.models import Token
from .base import MyTestCase


class SSHTokenTestCase(MyTestCase):
    otppin = "topsecret"
    serial1 = "ser1"
    serial2 = "ser2"
    serial3 = "ser3"
    serial4 = "ser4"
    sshkey = "ssh-rsa " \
             "AAAAB3NzaC1yc2EAAAADAQABAAACAQDJy0rLoxqc8SsY8DVAFijMsQyCv" \
             "hBu4K40hdZOacXK4O6OgnacnSKN56MP6pzz2+4svzvDzwvkFsvf34pbsgD" \
             "F67PPSCsimmjEQjf0UfamBKh0cl181CbPYsph3UTBOCgHh3FFDXBduPK4DQz" \
             "EVQpmqe80h+lsvQ81qPYagbRW6fpd0uWn9H7a/qiLQZsiKLL07HGB+NwWue4os" \
             "0r9s4qxeG76K6QM7nZKyC0KRAz7CjAf+0X7YzCOu2pzyxVdj/T+KArFcMmq8V" \
             "dz24mhcFFXTzU3wveas1A9rwamYWB+Spuohh/OrK3wDsrryStKQv7yofgnPMs" \
             "TdaL7XxyQVPCmh2jVl5ro9BPIjTXsre9EUxZYFVr3EIECRDNWy3xEnUHk7Rzs" \
             "734Rp6XxGSzcSLSju8/MBzUVe35iXfXDRcqTcoA0700pIb1ANYrPUO8Up05v4" \
             "EjIyBeU61b4ilJ3PNcEVld6FHwP3Z7F068ef4DXEC/d7pibrp4Up61WYQIXV/" \
             "utDt3NDg/Zf3iqoYcJNM/zIZx2j1kQQwqtnbGqxJMrL6LtClmeWteR4420uZx" \
             "afLE9AtAL4nnMPuubC87L0wJ88un9teza/N02KJMHy01Yz3iJKt3Ou9eV6kqO" \
             "ei3kvLs5dXmriTHp6g9whtnN6/Liv9SzZPJTs8YfThi34Wccrw== " \
             "NetKnights GmbH Descröption"
    unsupported_keytype = "ssh-something AAAAA comment"
    sshkey_ecdsa = "ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzd" \
                   "HAyNTYAAABBBHGCdIk0pO1HFr/mF4oLb43ZRyQJ4K7ICLrAhAiQERVa0tUvyY5TE" \
                   "zurWTqxSMx203rY77t6xnHLZBMPPpv8rk0= cornelius@puck"
    sshkey_ed25519 = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC38dIb3tM6nPrT" \
                     "3j1UfsQxOCBbf3JogwsKeVPM893Pi cornelius@puck"
    ecdsa_sk = "sk-ecdsa-sha2-nistp256@openssh.com AAAAInNrLWVjZHNhLXNoYTItbmlz" \
               "dHAyNTZAb3BlbnNzaC5jb20AAAAIbmlzdHAyNTYAAABBBOStamg+GO4TSgtoWjc82p" \
               "OKZIDuOeAt/8PU/jbzEmth6VuNhghRTCPqPMFtR6mB3Pb12yMDRiLH/t1VwkvWWYIA" \
               "AAAEc3NoOg=="
    wrong_sshkey = """---- BEGIN SSH2 PUBLIC KEY ----
    AAAAB3NzaC1kc3MAAACBAKrFC6uDvuxl9vnYL/Fu/Vq+12KJF4
    RyMSQe4mn8oHJma2VzepBRBpLt7Q==
    ---- END SSH2 PUBLIC KEY ----"""
    INVALID_SSH = "ssh-rsa"

    def test_01_create_token(self):
        db_token = Token(self.serial1, tokentype="sshkey")
        db_token.save()
        token = SSHkeyTokenClass(db_token)

        # An invalid key, raises an exception
        self.assertRaises(TokenAdminError, token.update, {"sshkey": "InvalidKey"})
        self.assertEqual(token.rollout_state, ROLLOUTSTATE.BROKEN)

        # An invalid key, raises an exception
        self.assertRaises(TokenAdminError, token.update, {"sshkey": self.INVALID_SSH})
        self.assertEqual(token.rollout_state, ROLLOUTSTATE.BROKEN)

        # An invalid key, raises an exception
        self.assertRaises(TokenAdminError, token.update, {"sshkey": self.wrong_sshkey})
        self.assertEqual(token.rollout_state, ROLLOUTSTATE.BROKEN)

        # An unsupported keytype
        self.assertRaises(TokenAdminError, token.update, {"sshkey": self.unsupported_keytype})
        self.assertEqual(token.rollout_state, ROLLOUTSTATE.BROKEN)

        # Set valid key
        token.update({"sshkey": self.sshkey})
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "sshkey",
                        token.token.tokentype)
        self.assertTrue(token.type == "sshkey", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "SSHK", class_prefix)
        self.assertTrue(token.get_class_type() == "sshkey", token)

        # ecdsa
        db_token = Token(self.serial2, tokentype="sshkey")
        db_token.save()
        token = SSHkeyTokenClass(db_token)
        token.update({"sshkey": self.sshkey_ecdsa})

        # ed25519
        db_token = Token(self.serial3, tokentype="sshkey")
        db_token.save()
        token = SSHkeyTokenClass(db_token)
        token.update({"sshkey": self.sshkey_ed25519})

        # ecdsa_sk
        db_token = Token(self.serial4, tokentype="sshkey")
        db_token.save()
        token = SSHkeyTokenClass(db_token)
        token.update({"sshkey": self.ecdsa_sk})

    def test_02_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = SSHkeyTokenClass(db_token)

        info = token.get_class_info()
        self.assertTrue(info.get("title") == "SSHkey Token",
                        "{0!s}".format(info.get("title")))

        info = token.get_class_info("title")
        self.assertTrue(info == "SSHkey Token", info)

    def test_03_get_sshkey(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = SSHkeyTokenClass(db_token)
        sshkey = token.get_sshkey()
        self.assertTrue(sshkey == self.sshkey, sshkey)
        self.assertIsInstance(sshkey, str)

        db_token = Token.query.filter(Token.serial == self.serial2).first()
        token = SSHkeyTokenClass(db_token)
        sshkey = token.get_sshkey()
        self.assertTrue(sshkey == self.sshkey_ecdsa, sshkey)
        self.assertIsInstance(sshkey, str)

        db_token = Token.query.filter(Token.serial == self.serial3).first()
        token = SSHkeyTokenClass(db_token)
        sshkey = token.get_sshkey()
        self.assertTrue(sshkey == self.sshkey_ed25519, sshkey)
        self.assertIsInstance(sshkey, str)

        db_token = Token.query.filter(Token.serial == self.serial4).first()
        token = SSHkeyTokenClass(db_token)
        sshkey = token.get_sshkey()
        self.assertEqual(self.ecdsa_sk, sshkey)
        self.assertIsInstance(sshkey, str)

    def test_04_ssh_token_export(self):
        # Set up the SSHTokenClass for testing
        token = init_token({"type": "sshkey",
                            "serial": self.serial1,
                            "sshkey": self.sshkey,
                            "description": "this is a ssh token export test",
                            "issuer": "privacyIDEA"})

        # Test that all expected keys are present in the exported dictionary
        exported_data = token.export_token()
        expected_keys = ["serial", "type", "description", "issuer"]
        self.assertTrue(set(expected_keys).issubset(exported_data.keys()))

        expected_tokeninfo_keys = ["tokenkind", "ssh_key", "ssh_type", "ssh_comment"]
        self.assertTrue(set(expected_tokeninfo_keys).issubset(exported_data["info_list"].keys()))

        # Test that the exported values match the token's data
        self.assertEqual(exported_data["serial"], "ser1")
        self.assertEqual(exported_data["type"], "sshkey")
        self.assertEqual(exported_data["description"], "this is a ssh token export test")
        self.assertEqual(exported_data["info_list"]["tokenkind"], "software")
        self.assertEqual(exported_data["issuer"], "privacyIDEA")
        self.assertEqual(exported_data["info_list"]["ssh_key"], self.sshkey[8:-28])  # ss_key without type and comment
        self.assertEqual(exported_data["info_list"]["ssh_type"], "ssh-rsa")
        self.assertEqual(exported_data["info_list"]["ssh_comment"], "NetKnights GmbH Descröption")

        # Clean up
        token.delete_token()

    def test_05_ssh_token_import(self):
        # Define the token data to be imported
        token_data = [{'description': 'this is a registration token export test',
                       'issuer': 'privacyIDEA',
                       'serial': 'newserial',
                       'type': 'sshkey',
                       'info_list': {'ssh_comment': 'NetKnights GmbH Descröption',
                                     'ssh_key': self.sshkey[8:-28],  # ss_key without type and comment
                                     'ssh_key.type': 'password',
                                     'ssh_type': 'ssh-rsa',
                                     'tokenkind': 'software'}
                       }]

        # Import the token
        import_tokens(token_data)

        # Retrieve the imported token
        token = get_tokens(serial=token_data[0]["serial"])[0]

        # Verify that the token data matches the imported data
        self.assertEqual(token.token.serial, token_data[0]["serial"])
        self.assertEqual(token.type, token_data[0]["type"])
        self.assertEqual(token.token.description, token_data[0]["description"])
        self.assertEqual(token.get_tokeninfo("tokenkind"), "software")
        self.assertEqual(token.get_tokeninfo("ssh_key"), self.sshkey[8:-28])
        self.assertEqual(token.get_tokeninfo("ssh_type"), "ssh-rsa")

        # Clean up
        token.delete_token()
