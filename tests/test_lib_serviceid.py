# -*- coding: utf-8 -*-
"""
This test file tests the lib.serviceid methods.

This tests the token functions on an interface level
"""
from .base import MyTestCase
from privacyidea.lib.error import privacyIDEAError, ResourceNotFoundError

from privacyidea.lib.serviceid import set_serviceid, delete_serviceid, get_serviceids
from privacyidea.models import Serviceid

WEBSERVER = "webserver"
MAILSERVER = "mailserver"


class TokenTestCase(MyTestCase):

    def test_01_create_serviceid(self):

        r = set_serviceid(WEBSERVER, "all cool light machines")
        self.assertGreaterEqual(r, 1)
        si = Serviceid.query.filter_by(id=r).first()
        self.assertEqual(si.Description, "all cool light machines")

        # Update
        r = set_serviceid(WEBSERVER, "all heavy httpd machines")
        self.assertGreaterEqual(r, 1)
        si = Serviceid.query.filter_by(id=r).first()
        self.assertEqual(si.Description, "all heavy httpd machines")

    def test_02_delete_serviceid(self):
        r = set_serviceid(WEBSERVER, "HTTP")
        self.assertGreaterEqual(r, 1)

        delete_serviceid(WEBSERVER)
        si = Serviceid.query.filter_by(name=WEBSERVER).all()
        self.assertEqual(len(si), 0)

        r = set_serviceid("webserver", "other machines")
        self.assertGreaterEqual(r, 1)

        self.assertRaises(privacyIDEAError,
                          delete_serviceid, sid=(r + 1), name=WEBSERVER)

        delete_serviceid(sid=r)
        si = Serviceid.query.filter_by(name=WEBSERVER).all()
        self.assertEqual(len(si), 0)

        self.assertRaises(ResourceNotFoundError, delete_serviceid)

    def test_03_get_serviceids(self):
        r1 = set_serviceid(WEBSERVER, "httpd")
        self.assertGreaterEqual(r1, 1)

        r2 = set_serviceid(MAILSERVER, "smtpd")
        self.assertGreater(r2, r1)

        sis = get_serviceids()
        self.assertEqual(len(sis), 2)

        sis = get_serviceids(name=WEBSERVER)
        self.assertEqual(len(sis), 1)

        sis = get_serviceids(id=r2)
        self.assertEqual(len(sis), 1)
        self.assertEqual(sis[0].name, MAILSERVER)
