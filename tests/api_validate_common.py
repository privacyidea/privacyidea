# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared constants and helpers extracted from test_api_validate.py.

Imported by test_api_validate*.py modules. Not collected by pytest.
"""
import responses

from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway

HOSTSFILE = "tests/testdata/hosts"
DICT_FILE = "tests/testdata/dictionary"

LDAPDirectory = [{"dn": "cn=alice,ou=example,o=test",
                  "attributes": {'cn': 'alice',
                                 "sn": "Cooper",
                                 "givenName": "Alice",
                                 'userPassword': 'alicepw',
                                 'oid': "2",
                                 "homeDirectory": "/home/alice",
                                 "email": "alice@test.com",
                                 "memberOf": ["cn=admins,o=test", "cn=users,o=test"],
                                 "accountExpires": 131024988000000000,
                                 "objectGUID": '\xef6\x9b\x03\xc0\xe7\xf3B'
                                               '\x9b\xf9\xcajl\rM1',
                                 'mobile': ["1234", "45678"]}},
                 {"dn": 'cn=bob,ou=example,o=test',
                  "attributes": {'cn': 'bob',
                                 "sn": "Marley",
                                 "givenName": "Robert",
                                 "email": "bob@example.com",
                                 "memberOf": ["cn=users,o=test"],
                                 "mobile": "123456",
                                 "homeDirectory": "/home/bob",
                                 'userPassword': 'bobpwééé',
                                 "accountExpires": 9223372036854775807,
                                 "objectGUID": '\xef6\x9b\x03\xc0\xe7\xf3B'
                                               '\x9b\xf9\xcajl\rMw',
                                 'oid': "3"}},
                 {"dn": 'cn=manager,ou=example,o=test',
                  "attributes": {'cn': 'manager',
                                 "givenName": "Corny",
                                 "sn": "keule",
                                 "email": "ck@o",
                                 "memberOf": ["cn=helpdesk,o=test", "cn=users,o=test"],
                                 "mobile": "123354",
                                 'userPassword': 'ldaptest',
                                 "accountExpires": 9223372036854775807,
                                 "objectGUID": '\xef6\x9b\x03\xc0\xe7\xf3B'
                                               '\x9b\xf9\xcajl\rMT',
                                 'oid': "1"}},
                 {"dn": 'cn=frank,ou=sales,o=test',
                  "attributes": {'cn': 'frank',
                                 "givenName": "Frank",
                                 "sn": "Hause",
                                 "email": "fh@o",
                                 "memberOf": ["cn=users,o=test"],
                                 "mobile": "123354",
                                 'userPassword': 'ldaptest',
                                 "accountExpires": 9223372036854775807,
                                 "objectGUID": '\xef7\x9b\x03\xc0\xe7\xf3B'
                                               '\x9b\xf9\xcajl\rMT',
                                 'oid': "5"}}
                 ]

OTPs = ["755224",
        "287082",
        "359152",
        "969429",
        "338314",
        "254676",
        "287922",
        "162583",
        "399871",
        "520489"]


def setup_sms_gateway():
    post_url = "http://smsgateway.com/sms_send_api.cgi"
    success_body = "ID 12345"

    identifier = "myGW"
    provider_module = "privacyidea.lib.smsprovider.HttpSMSProvider" \
                      ".HttpSMSProvider"
    id = set_smsgateway(identifier, provider_module, description="test",
                        options={"HTTP_METHOD": "POST",
                                 "URL": post_url,
                                 "RETURN_SUCCESS": "ID",
                                 "text": "{otp}",
                                 "phone": "{phone}"})
    assert (id > 0)
    # set config sms.identifier = myGW
    r = set_privacyidea_config("sms.identifier", identifier)
    assert (r in ["insert", "update"])
    responses.add(responses.POST,
                  post_url,
                  body=success_body)
