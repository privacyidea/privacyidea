"""Base test configuration to set up/teardown tests."""
import pathlib
import unittest
import mock
from sqlalchemy import Sequence, select, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm.session import close_all_sessions

from privacyidea.app import create_app
from privacyidea.config import TestingConfig
from privacyidea.models import Token, db, save_config_timestamp
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.realm import set_realm
from privacyidea.lib.user import User
from privacyidea.lib.auth import create_db_admin
from privacyidea.lib.auditmodules.base import Audit
from privacyidea.lib.conditional_access.request_context import reset_ca_context
from privacyidea.lib.conditional_access.session import close_ca_session
from privacyidea.lib.lifecycle import call_finalizers


PWFILE = "tests/testdata/passwords"
PWFILE2 = "tests/testdata/passwd"


def force_expire_challenges(transaction_id):
    """Force every challenge with ``transaction_id`` to be expired, on
    whichever backend stores it, for tests that exercise the
    expired-challenge rejection path.

    A raw ``Challenge.query...update()`` only reaches the SQL backend and is a
    no-op when the challenge lives in Redis. Going through the challenge object
    doesn't help either: ``ChallengeDTO.save()`` deliberately refuses to write
    an already-expired challenge, so for the cache backend the stored hash
    field is rewritten directly (the key is still within its TTL, but
    ``is_valid()`` now returns False, which is what the rejection path checks).
    """
    from datetime import timedelta
    from privacyidea.models.utils import utc_now
    from privacyidea.lib.challenge import get_challenges
    from privacyidea.lib.cache import redis_feature_enabled

    past = utc_now() - timedelta(minutes=5)
    challenges = get_challenges(transaction_id=transaction_id)
    for challenge in challenges:
        challenge.expiration = past
    if redis_feature_enabled("challenges"):
        from privacyidea.lib.cache.redis import get_redis, _TXN_KEY
        redis_client = get_redis()
        for challenge in challenges:
            redis_client.hset(_TXN_KEY.format(challenge.transaction_id),
                              challenge.serial, challenge.to_payload())
    else:
        from privacyidea.models import db
        db.session.commit()


class FakeFlaskG(object):
    policy_object = None
    logged_in_user = {}
    audit_object = None
    client_ip = None
    request_headers = None
    serial = None

    def get(self, name, default=None):
        return self.__dict__.get(name, default)


class FakeAudit(Audit):

    def __init__(self):
        super(FakeAudit).__init__()
        self.audit_data = {}


class PristineSqliteFixtures:
    """
    Test-class mixin that keeps sqlite fixture files pristine.

    SQL-resolver tests create/update/delete users in their backing sqlite
    file, which would otherwise leave the committed fixture dirty in the
    working tree. List the files to protect in ``pristine_fixtures``; they are
    snapshotted in setUpClass and restored in tearDownClass, making the test
    run byte-neutral for those files.

    Place this mixin *first* in the base-class list so its setUpClass /
    tearDownClass run and chain to the TestCase via super(), e.g.::

        class FooTestCase(PristineSqliteFixtures, MyApiTestCase):
            pristine_fixtures = ["tests/testdata/testuser-api.sqlite"]
    """
    pristine_fixtures: list = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._pristine_fixture_backups = {}
        for path in cls.pristine_fixtures:
            with open(path, "rb") as fixture_file:
                cls._pristine_fixture_backups[path] = fixture_file.read()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        for path, data in getattr(cls, "_pristine_fixture_backups", {}).items():
            with open(path, "wb") as fixture_file:
                fixture_file.write(data)


def _declared_sequences() -> list:
    """Names of every ``Sequence`` the models attach to a primary key.

    privacyIDEA allocates ids from real database sequences rather than from
    AUTO_INCREMENT, so emptying the tables is not enough to make the next class
    start from id 1 again — the sequences have to be restarted too.
    """
    return sorted({column.default.name
                   for table in db.metadata.tables.values()
                   for column in table.columns
                   if isinstance(getattr(column, "default", None), Sequence)})


def _schema_present() -> bool:
    """Is the schema already built in this worker's database?

    Reads one row from the table every test touches. A failure means the tables
    are gone - either this is the first class on the worker, or a class in
    ``tests/cli`` dropped them - and leaves the transaction unusable on
    PostgreSQL, so it is rolled back before the caller builds the schema.
    """
    try:
        db.session.execute(select(Token.id).limit(1)).first()
        return True
    except DatabaseError:
        db.session.rollback()
        return False


def _reset_database() -> None:
    """Give the next test class an empty database without rebuilding the schema.

    ``db.create_all()`` over the ~57 tables and the matching ``db.drop_all()``
    cost about 1.9 s per test class against MariaDB, and there are ~325 classes,
    so the suite spent a fifth of its time recreating a schema that never
    changes. Creating it once per xdist worker and deleting the rows in between
    leaves each class with the same empty tables for about 45 ms.

    The schema is only built when it is actually missing, which one cheap query
    answers. It cannot simply be built once and remembered: several classes in
    ``tests/cli`` call ``db.drop_all()`` in their own teardown, and a remembered
    "already built" would leave every later class on that worker querying tables
    that no longer exist. Asking the database each time costs about a
    millisecond and stays correct however the tables went away, where calling
    ``create_all()`` unconditionally cost ~300 ms per class under parallel load.

    PostgreSQL is emptied with ``TRUNCATE`` rather than ``DELETE``. It is not
    only about speed: ``DELETE`` leaves the heap in place, and because an
    ``UPDATE`` writes a new tuple, a row updated after the wipe can end up
    physically behind a row inserted later. ``get_tokens()`` has no ``ORDER
    BY``, so tests that read ``tokens[0]`` then see the wrong token - the
    two-step push enrollment updates its row and stopped coming first.
    ``TRUNCATE`` recreates the heap, which is what dropping and rebuilding the
    table used to provide. MySQL/MariaDB cannot use it here, because
    privacyIDEA's sequences are SEQUENCE-engine tables and ``TRUNCATE`` refuses
    them; InnoDB returns rows in primary-key order anyway, so ``DELETE`` is
    equivalent there.

    Rows are deleted child-table first (``sorted_tables`` is parent-first) so
    foreign keys stay satisfied. MySQL/MariaDB additionally get the FK check
    switched off, because privacyIDEA has cycles that no single ordering
    satisfies.

    The sequences behind the primary keys are restarted as well, so a class
    still sees ids counting from 1 the way a freshly built schema gave it.
    Several tests assert on a specific id, and deleting rows alone leaves the
    sequences where the previous class left them. On SQLite there is nothing to
    do: ``Sequence`` is ignored there and an emptied table hands out rowid 1
    again by itself.
    """
    if not _schema_present():
        db.create_all()
    connection = db.session.connection()
    dialect = db.engine.dialect.name
    is_mysql = dialect in ("mysql", "mariadb")
    if is_mysql:
        connection.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    try:
        if dialect == "postgresql":
            table_list = ", ".join(f'"{table.name}"' for table in db.metadata.sorted_tables)
            connection.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"))
        else:
            for table in reversed(db.metadata.sorted_tables):
                connection.execute(table.delete())
        if dialect != "sqlite":
            for sequence_name in _declared_sequences():
                connection.execute(text(f"ALTER SEQUENCE {sequence_name} RESTART"))
    finally:
        if is_mysql:
            connection.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    db.session.commit()


class MyTestCase(unittest.TestCase):
    app = None
    app_context = None
    resolvername1 = "resolver1"
    resolvername2 = "Resolver2"
    resolvername3 = "reso3"
    realm1 = "realm1"
    realm2 = "realm2"
    realm3 = "realm3"
    realm4 = "realm4"
    testadmin = 'testadmin'
    testadminpw = 'testpw'
    testadminmail = "admin@test.tld"
    serials = ["SE1", "SE2", "SE3"]
    otpkey = "3132333435363738393031323334353637383930"
    valid_otp_values = ["755224",
                        "287082",
                        "359152",
                        "969429",
                        "338314",
                        "254676",
                        "287922",
                        "162583",
                        "399871",
                        "520489"]

    @classmethod
    def setUpClass(cls):
        # Avoid warning when creating Flask-App without path to a config file
        # (And do not use the default config file here).
        cls.app = create_app('testing', pathlib.Path.cwd() / "tests/testdata/test_pi.cfg")
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        _reset_database()

        # save the current timestamp to the database to avoid hanging cached data
        save_config_timestamp()
        db.session.commit()
        # Create an admin for tests.
        create_db_admin(cls.testadmin, cls.testadminmail, cls.testadminpw)

    def set_default_g_variables(self):
        # Set values to g to avoid attribute errors in tests
        self.app_context.g.policy_object = None
        self.app_context.g.logged_in_user = {}
        self.app_context.g.audit_object = None
        self.app_context.g.client_ip = None
        self.app_context.g.request_headers = None
        self.app_context.g.serial = None
        self.app_context.g.policies = {}

    def reset_flask_g(self):
        """Remove everything from ``g``, so the next request starts from the state a real one would see.

        The app context is pushed once per test class, hence ``g`` outlives the individual requests a test
        dispatches. Leftovers let a blueprint that never initializes its own request-local state pass its
        tests on values another request left behind. Call this before dispatching a request, and between
        requests if a test dispatches several.
        """
        for key in list(iter(self.app_context.g)):
            self.app_context.g.pop(key)

    def pin_to_database(self, *features: str) -> None:
        """Keep the named Redis workloads off for this test class.

        Some tests are *about* the database representation - they assert rows,
        or they mock the user store the cache sits in front of - and a cache
        that answers before the database or the mock is reached makes them
        assert the cache instead of what they were written for. Those tests say
        so here, and the dedicated cache tests cover the Redis side.

        Call from ``setUp``. The app is built per test class, so this stays
        within the class that asks for it.

        :param features: workload names as used in ``PI_REDIS_CACHE_<NAME>``,
            e.g. ``"auth"`` or ``"users"``
        """
        for feature in features:
            self.app.config[f"PI_REDIS_CACHE_{feature.upper()}"] = False

    def tearDown(self):
        # Closes the conditional-access session, mirroring what a real request does at teardown: with one app
        # context shared across a whole test class, an unclosed session would outlive its test and serve stale
        # rows next time (SQLite reuses deleted rows' primary keys); staged events are cleared for the same reason.
        close_ca_session()
        reset_ca_context()
        # Rollback uncommitted changes to the DB and close the session to
        # avoid breaking following tests due to unfinished transactions
        try:
            db.session.commit()
        finally:
            db.session.rollback()
        db.session.close()

    def setUp_user_realms(self):
        # create user realm
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm1, [{'name': self.resolvername1}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        user = User(login="root",
                    realm=self.realm1,
                    resolver=self.resolvername1)

        user_str = "{0!s}".format(user)
        self.assertTrue(user_str == "<root.resolver1@realm1>", user_str)

        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        user_repr = "{0!r}".format(user)
        expected = "User(login='root', realm='realm1', resolver='resolver1')"
        self.assertTrue(user_repr == expected, user_repr)

    def setUp_user_realm2(self):
        # create user realm
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm2,
                                    [{'name': self.resolvername1}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        user = User(login="root",
                    realm=self.realm2,
                    resolver=self.resolvername1)

        user_str = "{0!s}".format(user)
        self.assertTrue(user_str == "<root.resolver1@realm2>", user_str)

        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        user_repr = "{0!r}".format(user)
        expected = "User(login='root', realm='realm2', resolver='resolver1')"
        self.assertTrue(user_repr == expected, user_repr)

    def setUp_user_realm3(self):
        # create user realm
        rid = save_resolver({"resolver": self.resolvername3,
                             "type": "passwdresolver",
                             "fileName": PWFILE2})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm3,
                                    [{'name': self.resolvername3}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        user = User(login="root",
                    realm=self.realm3,
                    resolver=self.resolvername3)

        user_str = "{0!s}".format(user)
        self.assertTrue(user_str == "<root.reso3@realm3>", user_str)

        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        user_repr = "{0!r}".format(user)
        expected = "User(login='root', realm='realm3', resolver='reso3')"
        self.assertTrue(user_repr == expected, user_repr)

    def setUp_user_realm4_with_2_resolvers(self):
        # create user realm
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)
        rid = save_resolver({"resolver": self.resolvername3,
                             "type": "passwdresolver",
                             "fileName": PWFILE2})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm4,
                                    [{'name': self.resolvername1, 'priority': 1},
                                     {'name': self.resolvername3, 'priority': 2}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 2)

        user = User(login="root",
                    realm=self.realm4,
                    resolver=self.resolvername3)

        user_str = "{0!s}".format(user)
        self.assertTrue(user_str == "<root.reso3@realm4>", user_str)

        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        user_repr = "{0!r}".format(user)
        expected = "User(login='root', realm='realm4', resolver='reso3')"
        self.assertTrue(user_repr == expected, user_repr)

    def setUp_sqlite_resolver_realm(self, sqlite_file, realm):
        parameters = {'resolver': "sqlite_resolver",
                      "type": "sqlresolver",
                      'Driver': 'sqlite',
                      'Server': '/tests/testdata/',
                      'Database': sqlite_file,
                      'Table': 'users',
                      'Encoding': 'utf8',
                      'Editable': True,
                      'Map': """{ "username": "username",
                        "userid" : "id",
                        "email" : "email",
                        "surname" : "name",
                        "givenname" : "givenname",
                        "password" : "password",
                        "phone": "phone",
                        "mobile": "mobile"}"""
                      }
        r = save_resolver(parameters)
        self.assertTrue(r)
        success, fail = set_realm(realm, [{'name': "sqlite_resolver"}])
        self.assertEqual(len(success), 1)
        self.assertEqual(len(fail), 0)

    @classmethod
    def tearDownClass(cls):
        call_finalizers()
        close_all_sessions()
        db.engine.dispose()
        cls.app_context.pop()

    def authenticate(self):
        with self.app.test_request_context('/auth',
                                           data={"username": self.testadmin,
                                                 "password": self.testadminpw},
                                           method='POST'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            self.at = result.get("value").get("token")

    def authenticate_selfservice_user(self):
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            self.at_user = result.get("value").get("token")
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "user", result)
            self.assertEqual(result.get("value").get("realm"), "realm1")

    def find_most_recent_audit_entry(self, **filter_data):
        """
        Given audit log entry filters, return the most recent entry matching the criteria,
        or raise an IndexError if there is no such entry.
        This is useful for testing the audit log behavior.
        """
        sorted_filter = filter_data.copy()
        sorted_filter["sortorder"] = "desc"
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data=sorted_filter,
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.data)
            self.assertTrue(res.is_json, res)
            result = res.json['result']
            self.assertIn('auditdata', result['value'])
            # return the last entry
            return res.json["result"]["value"]["auditdata"][0]


class OverrideConfigTestCase(MyTestCase):
    """
    helper class that allows to modify the app config processed by ``create_app``.
    This can be useful if config values need to be adjusted *for app creation*.
    For that, just override the inner ``Config`` class.
    """
    class Config(TestingConfig):
        pass

    @classmethod
    def setUpClass(cls):
        """ override privacyidea.config.config["testing"] with the inner config class """
        with mock.patch.dict("privacyidea.config.config", {"testing": cls.Config}):
            MyTestCase.setUpClass()


class MyApiTestCase(MyTestCase):
    @classmethod
    def cls_auth(cls, app):
        with app.test_request_context('/auth', data={"username": cls.testadmin,
                                                     "password": cls.testadminpw},
                                      method='POST'):
            res = app.full_dispatch_request()
            assert res.status_code == 200
            result = res.json.get("result")
            assert result.get("status")
            cls.at = result.get("value").get("token")

    @classmethod
    def setUpClass(cls):
        super(MyApiTestCase, cls).setUpClass()
        cls.cls_auth(cls.app)
