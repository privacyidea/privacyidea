# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
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
# SPDX-License-Identifier: AGPL-3.0-or-later
#
"""
Drive every API path that carries a credential with the whole privacyidea logger at DEBUG and
assert that the credential does not reach the log.

The check is deliberately end to end. Hiding a value correctly in one function proves nothing,
because the same request data is logged again by the next frame, by the audit log, by the request
URL and by the repr of the objects built from it. Only reading the whole log output for one request
shows whether a credential survived somewhere.

Each case sends its own unique secret, so output that arrives late from the previous request is
attributed instead of being counted against the current case.
"""
import io
import logging
import re

import pytest

from .base import MyApiTestCase

# A value shaped like a JWT is a session credential of whoever sent the request.
JWT_PATTERN = re.compile(r"eyJhbGciOiJ[A-Za-z0-9_\-]{5,}\.eyJ[A-Za-z0-9_\-]{10,}")

# The placeholder is replaced by a per-case unique value before the request is sent.
SECRET = "@SECRET@"

# (label, method, path, kind, data), where kind selects how the secret is transported:
# form body, JSON body, query string or request header.
CREDENTIAL_REQUESTS = [
    # enrollment, one per token type that takes a secret
    ("init/hotp-pin", "POST", "/token/init", "form", {"type": "hotp", "genkey": 1, "pin": SECRET}),
    ("init/hotp-otpkey", "POST", "/token/init", "form", {"type": "hotp", "otpkey": SECRET}),
    ("init/hotp-2step", "POST", "/token/init", "form", {"type": "hotp", "2stepinit": 1,
                                                        "otpkey": SECRET}),
    ("init/totp", "POST", "/token/init", "form", {"type": "totp", "genkey": 1, "pin": SECRET}),
    ("init/daypassword", "POST", "/token/init", "form", {"type": "daypassword", "genkey": 1,
                                                         "pin": SECRET}),
    ("init/motp", "POST", "/token/init", "form", {"type": "motp", "genkey": 1, "motppin": SECRET}),
    ("init/radius", "POST", "/token/init", "form", {"type": "radius", "radius.server": "1.2.3.4",
                                                    "radius.user": "u",
                                                    "radius.secret": SECRET}),
    ("init/remote", "POST", "/token/init", "form", {"type": "remote",
                                                    "remote.server": "https://1.2.3.4",
                                                    "remote.user": "u",
                                                    "remote.password": SECRET}),
    ("init/sms", "POST", "/token/init", "form", {"type": "sms", "phone": "123", "pin": SECRET}),
    ("init/email", "POST", "/token/init", "form", {"type": "email", "email": "a@b.c",
                                                   "pin": SECRET}),
    ("init/question", "POST", "/token/init", "form", {"type": "question",
                                                      "questions": '{"q1": "%s", "q2": "%s", '
                                                                   '"q3": "%s", "q4": "%s", '
                                                                   '"q5": "%s"}' % ((SECRET,) * 5)}),
    ("init/tan", "POST", "/token/init", "form", {"type": "tan", "tans": SECRET}),
    ("init/registration", "POST", "/token/init", "form", {"type": "registration", "pin": SECRET}),
    ("init/spass", "POST", "/token/init", "form", {"type": "spass", "pin": SECRET}),
    ("init/sshkey", "POST", "/token/init", "form", {"type": "sshkey",
                                                    "sshkey": f"ssh-rsa AAAAB3{SECRET} u@h"}),
    ("init/indexedsecret", "POST", "/token/init", "form", {"type": "indexedsecret",
                                                           "otpkey": SECRET}),
    ("init/yubikey", "POST", "/token/init", "form", {"type": "yubikey", "otpkey": "a" * 32,
                                                     "pin": SECRET}),
    ("init/yubico", "POST", "/token/init", "form", {"type": "yubico",
                                                    "yubico.tokenid": "c" * 12, "pin": SECRET}),
    ("init/paper", "POST", "/token/init", "form", {"type": "paper", "pin": SECRET}),
    ("init/applspec", "POST", "/token/init", "form", {"type": "applspec", "service_id": "s",
                                                      "pin": SECRET}),
    ("init/pw", "POST", "/token/init", "form", {"type": "pw", "otpkey": SECRET}),
    ("init/vasco", "POST", "/token/init", "form", {"type": "vasco", "otpkey": "0" * 496,
                                                   "pin": SECRET}),
    ("init/4eyes", "POST", "/token/init", "form", {"type": "4eyes", "4eyes": "realm1:1",
                                                   "pin": SECRET}),
    ("init/tiqr", "POST", "/token/init", "form", {"type": "tiqr", "user": "cornelius",
                                                  "realm": "realm1", "pin": SECRET}),
    ("init/ocra", "POST", "/token/init", "form", {"type": "ocra", "genkey": 1, "pin": SECRET}),
    ("init/push", "POST", "/token/init", "form", {"type": "push", "genkey": 1, "pin": SECRET}),
    ("init/certificate", "POST", "/token/init", "form", {"type": "certificate", "genkey": 1,
                                                         "pin": SECRET}),
    ("init/webauthn", "POST", "/token/init", "form", {"type": "webauthn", "user": "cornelius",
                                                      "realm": "realm1", "pin": SECRET}),
    ("init/passkey", "POST", "/token/init", "form", {"type": "passkey", "user": "cornelius",
                                                     "realm": "realm1", "pin": SECRET}),
    # the same credential in each transport, because the hiding must not depend on it
    ("init/json-body", "POST", "/token/init", "json", {"type": "hotp", "genkey": 1,
                                                       "pin": SECRET}),
    ("init/query-string", "POST", "/token/init", "query", {"type": "hotp", "genkey": 1,
                                                          "pin": SECRET}),
    # pin handling on existing tokens
    ("setpin/otppin", "POST", "/token/setpin", "form", {"serial": "LOGTEST01", "otppin": SECRET}),
    ("setpin/userpin", "POST", "/token/setpin", "form", {"serial": "LOGTEST01",
                                                         "userpin": SECRET}),
    ("setpin/sopin", "POST", "/token/setpin", "form", {"serial": "LOGTEST01", "sopin": SECRET}),
    ("setpin/query", "POST", "/token/setpin", "query", {"serial": "LOGTEST01", "otppin": SECRET}),
    ("assign", "POST", "/token/assign", "form", {"serial": "LOGTEST01", "user": "cornelius",
                                                 "realm": "realm1", "pin": SECRET}),
    ("resync", "POST", "/token/resync", "form", {"serial": "LOGTEST01", "otp1": SECRET,
                                                 "otp2": SECRET}),
    ("reset", "POST", "/token/reset", "form", {"serial": "LOGTEST01", "pin": SECRET}),
    ("token/set", "POST", "/token/set", "form", {"serial": "LOGTEST01", "password": SECRET}),
    ("token/load", "POST", "/token/load/x.xml", "form", {"password": SECRET, "type": "oathcsv"}),
    ("token/challenges", "GET", "/token/challenges/", "query", {"pass": SECRET}),
    # authentication
    ("validate/check-form", "POST", "/validate/check", "form", {"user": "cornelius",
                                                                "pass": SECRET}),
    ("validate/check-query", "GET", "/validate/check", "query", {"user": "cornelius",
                                                                 "pass": SECRET}),
    ("validate/check-json", "POST", "/validate/check", "json", {"user": "cornelius",
                                                                "pass": SECRET}),
    ("validate/check-serial", "POST", "/validate/check", "form", {"serial": "LOGTEST01",
                                                                  "pass": SECRET}),
    ("validate/samlcheck", "POST", "/validate/samlcheck", "form", {"user": "cornelius",
                                                                   "pass": SECRET}),
    ("validate/triggerchallenge", "POST", "/validate/triggerchallenge", "form",
     {"user": "cornelius", "pass": SECRET}),
    ("validate/radiuscheck", "POST", "/validate/radiuscheck", "form", {"user": "cornelius",
                                                                       "pass": SECRET}),
    ("auth/admin", "POST", "/auth", "form", {"username": "admin-probe", "password": SECRET}),
    ("auth/user", "POST", "/auth", "form", {"username": "cornelius", "realm": "realm1",
                                            "password": SECRET}),
    # user management
    ("user/post", "POST", "/user/", "form", {"user": "probeuser", "resolver": "resolver1",
                                             "password": SECRET, "email": "a@b.c"}),
    ("user/put", "PUT", "/user/", "form", {"user": "cornelius", "resolver": "resolver1",
                                           "password": SECRET}),
    # resolvers
    ("resolver/ldap", "POST", "/resolver/probeldap", "form", {"type": "ldapresolver",
                                                              "LDAPURI": "ldap://x",
                                                              "LDAPBASE": "o=x", "BINDDN": "cn=x",
                                                              "BINDPW": SECRET}),
    ("resolver/sql", "POST", "/resolver/probesql", "form", {"type": "sqlresolver",
                                                            "Driver": "sqlite", "Server": "/",
                                                            "Database": "x", "User": "u",
                                                            "Password": SECRET, "Table": "t",
                                                            "Map": "{}"}),
    ("resolver/http", "POST", "/resolver/probehttp", "form", {"type": "httpresolver",
                                                              "endpoint": "https://x",
                                                              "password": SECRET}),
    ("resolver/entra", "POST", "/resolver/probeentra", "form", {"type": "entraidresolver",
                                                                "client_secret": SECRET,
                                                                "tenant": "t", "client_id": "c"}),
    ("resolver/test", "POST", "/resolver/test", "form", {"type": "ldapresolver",
                                                         "LDAPURI": "ldap://x", "BINDDN": "cn=x",
                                                         "BINDPW": SECRET}),
    # peripheral servers and connectors
    ("smtpserver", "POST", "/smtpserver/probe", "form", {"identifier": "probe",
                                                         "server": "1.2.3.4", "username": "u",
                                                         "password": SECRET}),
    ("smtpserver/test", "POST", "/smtpserver/test_request", "form", {"identifier": "probe",
                                                                     "server": "1.2.3.4",
                                                                     "password": SECRET,
                                                                     "recipient": "a@b.c"}),
    ("radiusserver", "POST", "/radiusserver/probe", "form", {"identifier": "probe",
                                                             "server": "1.2.3.4",
                                                             "secret": SECRET}),
    ("radiusserver/test", "POST", "/radiusserver/test_request", "form", {"identifier": "probe",
                                                                         "server": "1.2.3.4",
                                                                         "secret": SECRET,
                                                                         "user": "u",
                                                                         "password": SECRET}),
    ("privacyideaserver", "POST", "/privacyideaserver/probe", "form", {"identifier": "probe",
                                                                       "url": "https://x",
                                                                       "password": SECRET}),
    ("caconnector", "POST", "/caconnector/probe", "form", {"type": "local", "cakey": SECRET,
                                                           "cacert": "x"}),
    ("machineresolver", "POST", "/machineresolver/probe", "form", {"type": "hosts",
                                                                   "filename": "/etc/hosts",
                                                                   "password": SECRET}),
    ("smsgateway", "POST", "/smsgateway", "form", {"name": "probe",
                                                   "module": "privacyidea.lib.smsprovider."
                                                             "HttpSMSProvider.HttpSMSProvider",
                                                   "option.PASSWORD": SECRET}),
    # configuration
    ("system/setconfig", "POST", "/system/setconfig", "form", {"probe.password": SECRET}),
    ("system/hsm", "POST", "/system/hsm", "form", {"password": SECRET}),
    # registration and recovery
    ("register", "POST", "/register", "form", {"username": "probereg", "givenname": "a",
                                               "surname": "b", "email": "a@b.c",
                                               "password": SECRET}),
    ("recover/reset", "POST", "/recover/reset", "form", {"user": "cornelius", "realm": "realm1",
                                                         "recoverycode": SECRET,
                                                         "password": SECRET}),
    # containers
    ("container/register", "POST", "/container/register/initialize", "form",
     {"container_serial": "CONT0001", "passphrase_response": SECRET}),
    # token type callback carrying the firebase credential
    ("ttype/push", "POST", "/ttype/push", "form", {"serial": "LOGTEST01", "fbtoken": SECRET}),
    # the session token, under both header names a client may use
    ("header/pi-authorization", "GET", "/token/", "header", {"PI-Authorization": SECRET}),
    ("header/authorization", "GET", "/token/", "header", {"Authorization": SECRET}),
]


class SecretsNotLoggedTestCase(MyApiTestCase):

    def setUp(self):
        self.log_stream = io.StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.root_logger = logging.getLogger()
        self.privacyidea_logger = logging.getLogger("privacyidea")
        self.previous_levels = [(logger, logger.level)
                                for logger in (self.root_logger, self.privacyidea_logger)]
        for logger in (self.root_logger, self.privacyidea_logger):
            logger.addHandler(self.handler)
            logger.setLevel(logging.DEBUG)

    def tearDown(self):
        for logger in (self.root_logger, self.privacyidea_logger):
            logger.removeHandler(self.handler)
        for logger, level in self.previous_levels:
            logger.setLevel(level)

    def send(self, method: str, path: str, kind: str, data: dict) -> str:
        """
        Send one request and return everything that was logged while handling it.

        :param method: HTTP method
        :param path: The endpoint path
        :param kind: How to transport the data: form, json, query or header
        :param data: The request data, containing the secret
        :return: The captured log output
        """
        self.log_stream.truncate(0)
        self.log_stream.seek(0)
        arguments = {"method": method, "headers": {"Authorization": self.at}}
        if kind == "form":
            arguments["data"] = data
        elif kind == "json":
            arguments["json"] = data
        elif kind == "query":
            arguments["query_string"] = data
        elif kind == "header":
            arguments["headers"].update(data)
        try:
            with self.app.test_request_context(path, **arguments):
                self.app.full_dispatch_request()
        except Exception:
            # A request may legitimately fail, for example because a parameter combination is
            # incomplete. What is logged on the way to the failure still must not contain a secret.
            pass
        return self.log_stream.getvalue()

    @staticmethod
    def specialize(value, secret: str):
        """Replace the placeholder in request data with this case's unique secret."""
        if isinstance(value, str):
            return value.replace(SECRET, secret)
        if isinstance(value, dict):
            return {key: SecretsNotLoggedTestCase.specialize(item, secret)
                    for key, item in value.items()}
        return value

    def test_01_credentials_are_not_written_to_the_log(self):
        with self.app.test_request_context("/token/init",
                                           data={"type": "hotp", "genkey": 1,
                                                 "serial": "LOGTEST01"},
                                           method="POST",
                                           headers={"Authorization": self.at}):
            self.app.full_dispatch_request()

        leaked = []
        leaked_session_token = []
        for index, (label, method, path, kind, data) in enumerate(CREDENTIAL_REQUESTS):
            secret = f"logtest-{index:03d}-secret"
            output = self.send(method, path, kind, self.specialize(data, secret))
            if secret in output:
                first_line = next(line for line in output.splitlines() if secret in line)
                leaked.append(f"{label}: {first_line[:300]}")
            # Every one of these requests is authenticated, so each is also a chance to log the
            # session token of the caller.
            if JWT_PATTERN.search(output) or self.at in output:
                leaked_session_token.append(label)
        self.assertEqual([], leaked, "\n\n".join(leaked))
        self.assertEqual([], leaked_session_token,
                         f"the auth token was logged during: {leaked_session_token}")

    @pytest.mark.xfail(reason="A generic key/value pair carries no name to recognise: the value is "
                              "a credential only because a sibling parameter says so. Not fixable "
                              "by matching key names.",
                       strict=True)
    def test_02_generic_key_value_pair(self):
        output = self.send("POST", "/user/attribute", "form",
                           {"user": "cornelius", "realm": "realm1", "key": "password",
                            "value": "logtest-keyvalue-secret"})
        self.assertNotIn("logtest-keyvalue-secret", output)

    @pytest.mark.xfail(reason="The credential sits inside a JSON string, so walking keys never "
                              "reaches it. Parsing arbitrary strings while formatting a log line "
                              "is not worth the cost.",
                       strict=True)
    def test_03_secret_inside_a_serialized_json_value(self):
        output = self.send("POST", "/periodictask/", "form",
                           {"name": "probe", "active": True, "interval": "0 0 * * *",
                            "nodes": "localnode", "taskmodule": "EventCounter", "ordering": 0,
                            "options": '{"password": "logtest-serialized-secret"}'})
        self.assertNotIn("logtest-serialized-secret", output)
