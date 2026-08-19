"""
This test file tests the lib.clientapplicaton.py
"""
import mock
from datetime import datetime, timedelta
from contextlib import contextmanager

import time

from sqlalchemy import event
from sqlalchemy.engine import Engine

from privacyidea.lib.framework import get_app_local_store
from privacyidea.models import ClientApplication, db
from .base import MyTestCase
from privacyidea.lib.clientapplication import (_LAST_WRITE_KEY, _MAX_TRACKED_CLIENTS,
                                               _write_interval_seconds, get_clientapplication,
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
        now = datetime.now()
        for client_type, apps in r.items():
            if client_type == "SAML":
                self.assertEqual(2, len(apps))
            else:
                self.assertEqual(1, len(apps))
            for app in apps:
                self.assertAlmostEqual(now, app.get("lastseen"), delta=timedelta(seconds=5))

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
            with mock.patch("privacyidea.lib.clientapplication.datetime") as mock_dt:
                mock_dt.now.return_value = t
                yield

        # remove all rows first
        ClientApplication.query.delete()

        # create some fake timestamps
        t1 = datetime.now()
        t2 = t1 + timedelta(minutes=5)

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


class ClientApplicationWriteThrottleTestCase(MyTestCase):
    """
    ``save_clientapplication`` runs on every /validate/check request, so it does
    not rewrite a row it has just written.
    """

    @contextmanager
    def _write_interval(self, seconds):
        """Set how long a row may keep its old lastseen before being rewritten."""
        key = "PI_CLIENTAPPLICATION_WRITE_INTERVAL"
        had_key = key in self.app.config
        old_value = self.app.config.get(key)
        self.app.config[key] = seconds
        try:
            yield
        finally:
            if had_key:
                self.app.config[key] = old_value
            else:
                self.app.config.pop(key, None)

    def _statements(self):
        """Count the statements a save costs, so the test states the actual point."""
        statements = []

        def on_execute(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        return statements, on_execute

    def setUp(self):
        super().setUp()
        ClientApplication.query.delete()
        db.session.commit()

    def test_01_the_first_write_always_happens(self):
        with self._write_interval(60):
            save_clientapplication("1.2.3.4", "PAM")
        row = ClientApplication.query.filter_by(ip="1.2.3.4", clienttype="PAM").one()
        self.assertIsNotNone(row.lastseen)

    def test_02_a_repeated_save_within_the_interval_is_skipped(self):
        with self._write_interval(60):
            with mock.patch("privacyidea.lib.clientapplication.datetime") as mock_dt:
                first_seen = datetime.now()
                mock_dt.now.return_value = first_seen
                save_clientapplication("1.2.3.4", "PAM")
                # A second later the same client is back. Its row already says
                # it was around, so there is nothing worth writing
                mock_dt.now.return_value = first_seen + timedelta(seconds=1)
                save_clientapplication("1.2.3.4", "PAM")
        row = ClientApplication.query.filter_by(ip="1.2.3.4", clienttype="PAM").one()
        self.assertEqual(first_seen, row.lastseen)

    def test_03_the_skipped_save_costs_no_statement(self):
        # The reason for the throttle is the SELECT, the UPDATE and the COMMIT
        # that every request would otherwise pay
        with self._write_interval(60):
            save_clientapplication("1.2.3.4", "PAM")
            statements, on_execute = self._statements()
            event.listen(Engine, "before_cursor_execute", on_execute)
            try:
                save_clientapplication("1.2.3.4", "PAM")
            finally:
                event.remove(Engine, "before_cursor_execute", on_execute)
        self.assertEqual([], statements)

    def test_04_a_save_after_the_interval_writes_again(self):
        with self._write_interval(60):
            with mock.patch("privacyidea.lib.clientapplication.datetime") as mock_dt:
                first_seen = datetime.now()
                mock_dt.now.return_value = first_seen
                save_clientapplication("1.2.3.4", "PAM")
                # Move the worker's clock past the interval rather than sleeping
                with mock.patch("privacyidea.lib.clientapplication.time.monotonic",
                                return_value=time.monotonic() + 61):
                    later = first_seen + timedelta(seconds=61)
                    mock_dt.now.return_value = later
                    save_clientapplication("1.2.3.4", "PAM")
        row = ClientApplication.query.filter_by(ip="1.2.3.4", clienttype="PAM").one()
        self.assertEqual(later, row.lastseen)

    def test_05_clients_are_throttled_one_by_one(self):
        with self._write_interval(60):
            with mock.patch("privacyidea.lib.clientapplication.datetime") as mock_dt:
                first_seen = datetime.now()
                mock_dt.now.return_value = first_seen
                save_clientapplication("1.2.3.4", "PAM")
                # A different address, and a different client type on the same
                # address, are both clients of their own
                save_clientapplication("1.2.3.4", "RADIUS")
                save_clientapplication("10.1.1.1", "PAM")
        self.assertEqual(3, ClientApplication.query.count())

    def test_06_an_interval_of_zero_writes_every_time(self):
        with self._write_interval(0):
            with mock.patch("privacyidea.lib.clientapplication.datetime") as mock_dt:
                first_seen = datetime.now()
                mock_dt.now.return_value = first_seen
                save_clientapplication("1.2.3.4", "PAM")
                later = first_seen + timedelta(seconds=1)
                mock_dt.now.return_value = later
                save_clientapplication("1.2.3.4", "PAM")
        row = ClientApplication.query.filter_by(ip="1.2.3.4", clienttype="PAM").one()
        self.assertEqual(later, row.lastseen)

    def test_07_a_malformed_interval_falls_back_to_the_default(self):
        with self._write_interval("not a number"):
            self.assertEqual(60, _write_interval_seconds())
        with self._write_interval(-5):
            self.assertEqual(0, _write_interval_seconds())

    def test_08_the_tracked_clients_do_not_grow_without_end(self):
        # A server reached from very many addresses must not accumulate one
        # entry per address forever
        with self._write_interval(60):
            save_clientapplication("1.2.3.4", "PAM")
            last_writes = get_app_local_store()[_LAST_WRITE_KEY]
            # Fill it past the cap with clients last written long ago
            long_ago = time.monotonic() - 3600
            for index in range(_MAX_TRACKED_CLIENTS + 10):
                last_writes[("node", f"10.0.{index // 256}.{index % 256}", "PAM")] = long_ago
            save_clientapplication("10.1.1.1", "PAM")
        self.assertLessEqual(len(get_app_local_store()[_LAST_WRITE_KEY]), _MAX_TRACKED_CLIENTS)
        # The client that was just written is still remembered
        self.assertIn(("10.1.1.1", "PAM"),
                      [(key[1], key[2]) for key in get_app_local_store()[_LAST_WRITE_KEY]])
