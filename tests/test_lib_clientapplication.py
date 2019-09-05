"""
This test file tests the lib.clientapplicaton.py
"""
import mock
from datetime import datetime, timedelta
from contextlib import contextmanager

from privacyidea.models import ClientApplication
from .base import MyTestCase
from privacyidea.lib.clientapplication import (get_clientapplication,
                                               save_clientapplication)


class ClientApplicationTestCase(MyTestCase):
    """
    Test the ClientApplication functions
    """
    def test_01_save_and_get(self):
        save_clientapplication("1.2.3.4", "PAM")
        save_clientapplication("1.2.3.4", "RADIUS")
        save_clientapplication("1.2.3.4", "OTRS")
        save_clientapplication("1.2.3.4", "SAML")
        save_clientapplication("10.1.1.1", "SAML")

        r = get_clientapplication()
        self.assertEqual(len(r), 4)

        r = get_clientapplication(group_by="ip")
        self.assertEqual(len(r), 2)

        r = get_clientapplication(clienttype="SAML")
        self.assertEqual(len(r), 1)
        self.assertEqual(len(r.get("SAML")), 2)

        r = get_clientapplication(ip="1.2.3.4")
        self.assertEqual(len(r), 4)

        r = get_clientapplication(ip="1.2.3.4")
        # 4 clienttypes in IP 1.2.3.4
        self.assertEqual(len(r), 4)
        self.assertEqual(r["OTRS"][0]["ip"], "1.2.3.4")
        self.assertEqual(r["PAM"][0]["ip"], "1.2.3.4")
        self.assertTrue(r["RADIUS"][0]["lastseen"] < datetime.now())
        self.assertTrue(r["SAML"][0]["lastseen"] < datetime.now())

    def test_02_multiple_nodes(self):
        @contextmanager
        def _set_node(node):
            """ context manager that sets the current node name """
            with mock.patch("privacyidea.lib.clientapplication.get_privacyidea_node") as mock_node:
                mock_node.return_value = node
                yield

        @contextmanager
        def _fake_time(t):
            """ context manager that fakes the current time that is written to the ``lastseen`` column """
            with mock.patch("privacyidea.models.datetime") as mock_dt:
                mock_dt.now.return_value = t
                yield

        # remove all rows first
        ClientApplication.query.delete()

        # create some fake timestamps
        t1 = datetime.now()
        t2 = t1 + timedelta(minutes=5)
        t3 = t2 + timedelta(minutes=5)

        with _fake_time(t1):
            with _set_node("pinode1"):
                save_clientapplication("1.2.3.4", "PAM")
            with _set_node("pinode2"):
                save_clientapplication("1.2.3.4", "RADIUS")
                save_clientapplication("2.3.4.5", "PAM")

        # check that the rows are written correctly
        row1 = ClientApplication.query.filter_by(ip="1.2.3.4", clienttype="PAM").one()
        self.assertEqual(row1.lastseen, t1)
        self.assertEqual(row1.node, "pinode1")
        row2 = ClientApplication.query.filter_by(ip="1.2.3.4", clienttype="RADIUS").one()
        self.assertEqual(row2.lastseen, t1)
        self.assertEqual(row2.node, "pinode2")
        row3 = ClientApplication.query.filter_by(ip="2.3.4.5", clienttype="PAM").one()
        self.assertEqual(row3.lastseen, t1)
        self.assertEqual(row3.node, "pinode2")

        # check that the apps are returned correctly
        apps = get_clientapplication(clienttype="PAM")
        self.assertEqual(list(apps.keys()), ["PAM"])
        self.assertEqual(len(apps["PAM"]), 2)
        self.assertIn({"ip": "1.2.3.4", "hostname": None, "lastseen": t1}, apps["PAM"])
        self.assertIn({"ip": "2.3.4.5", "hostname": None, "lastseen": t1}, apps["PAM"])

        with _fake_time(t2):
            with _set_node("pinode1"):
                save_clientapplication("1.2.3.4", "RADIUS")
            with _set_node("pinode2"):
                save_clientapplication("1.2.3.4", "PAM")

        # check that the rows are written correctly
        # 1.2.3.4 + PAM was last seen on pinode1 at t1 ...
        row1 = ClientApplication.query.filter_by(ip="1.2.3.4", clienttype="PAM", node="pinode1").one()
        self.assertEqual(row1.lastseen, t1)
        # but on pinode2, it was t2!
        row2 = ClientApplication.query.filter_by(ip="1.2.3.4", clienttype="PAM", node="pinode2").one()
        self.assertEqual(row2.lastseen, t2)
        # 1.2.3.4 + RADIUS was last seen on pinode1 at t2 ...
        row3 = ClientApplication.query.filter_by(ip="1.2.3.4", clienttype="RADIUS", node="pinode1").one()
        self.assertEqual(row3.lastseen, t2)
        # ... but on pinode2, it was t1!
        row4 = ClientApplication.query.filter_by(ip="1.2.3.4", clienttype="RADIUS", node="pinode2").one()
        self.assertEqual(row4.lastseen, t1)

        # check that the apps are returned correctly
        apps = get_clientapplication(ip="1.2.3.4")
        self.assertEqual(set(apps.keys()), {"PAM", "RADIUS"})
        self.assertEqual(apps["PAM"], [{"ip": "1.2.3.4", "hostname": None, "lastseen": t2}])
        self.assertEqual(apps["RADIUS"], [{"ip": "1.2.3.4", "hostname": None, "lastseen": t2}])

        apps = get_clientapplication(group_by="ip")
        self.assertEqual(set(apps.keys()), {"1.2.3.4", "2.3.4.5"})
        self.assertEqual(len(apps["1.2.3.4"]), 2)
        self.assertIn({"clienttype": "PAM", "hostname": None, "lastseen": t2}, apps["1.2.3.4"])
        self.assertIn({"clienttype": "RADIUS", "hostname": None, "lastseen": t2}, apps["1.2.3.4"])
        self.assertEqual(apps["2.3.4.5"], [{"clienttype": "PAM", "hostname": None, "lastseen": t1}])


