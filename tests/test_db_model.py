# SPDX-FileCopyrightText: (C) 2024 Paul Lettich <paul.lettich@netknights.it>
# SPDX-FileCopyrightText: (C) 2015 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Info: https://privacyidea.org
#
# This code is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see <http://www.gnu.org/licenses/>.
"""Test the models of the privacyIDEA database."""
import os
from datetime import datetime
from datetime import timedelta

from mock import mock
from sqlalchemy import func, delete, select

from privacyidea.lib.policies.conditions import (PolicyConditionClass, ConditionSection,
                                                 ConditionHandleMissingData)
from privacyidea.lib.policy import set_policy_conditions
from privacyidea.lib.token import init_token, remove_token
from privacyidea.lib.tokengroup import delete_tokengroup
from privacyidea.lib.user import User
from privacyidea.lib.utils.compare import PrimaryComparators
from privacyidea.models import (Token,
                                Resolver,
                                ResolverRealm, NodeName,
                                TokenRealm,
                                ResolverConfig,
                                Realm,
                                Config,
                                Policy,
                                Challenge, PasswordReset, ClientApplication, UserCache,
                                EventCounter, MonitoringStats, PolicyCondition, db,
                                Tokengroup, TokenTokengroup, Serviceid, TokenInfo)
from .base import MyTestCase


class TokenModelTestCase(MyTestCase):
    """
    Test the token on the database level
    """

    def create_resolver_realm(self):
        r = Resolver("resolver1", "passwdresolver")
        r.save()
        self.assertTrue(r.name is not None, r.name)
        self.assertTrue(r.rtype is not None, r.rtype)
        # Add configuration to the resolver
        conf = ResolverConfig(r.id, "fileName", "tests/testdata/passwd")
        conf.save()

        # Read Resolver
        r1 = Resolver.query.filter_by(name="resolver1").first()
        self.assertTrue(r1.rtype == "passwdresolver", r1.rtype)

        realm = Realm("realm1")
        realm.save()
        # Put the resolver into the realm
        rrealm = ResolverRealm(resolver_name="resolver1",
                               realm_name="realm1")
        rrealm.save()

    def test_00_create_token(self):
        otpkey = "1234567890"
        t1 = Token(serial="serial1",
                   otpkey=otpkey,
                   tokentype="hmac")
        t1.set_description("myfirsttoken")
        t1.set_hashed_pin("1234")
        t1.otplen = 6
        tid = t1.save()

        userpin = "HalloDuda"
        t1.set_user_pin(userpin)
        t1.save()

        pin_object = t1.get_user_pin()
        self.assertTrue(pin_object.getPin() == userpin.encode('utf8'))

        t = Token.query.filter_by(id=tid).first()
        self.assertTrue(len(t.pin_hash) > 0)
        self.assertTrue(len(t.user_pin) > 0)

        otp_obj = t.get_otpkey()
        self.assertTrue(otp_obj.getKey() == otpkey.encode('utf8'))
        count = t.count
        self.assertTrue(count == 0)

        up = t.get_user_pin()
        self.assertTrue(up.getPin() == userpin.encode('utf8'))

        self.assertTrue(t.check_pin("1234"))

        t.set_user_pin(b'HalloDuDa')
        self.assertTrue(t.get_user_pin().getPin() == b'HalloDuDa')

        t.set_user_pin('HelloWörld')
        self.assertTrue(t.get_user_pin().getPin().decode('utf8') == 'HelloWörld')

        t.set_hashed_pin(b'1234')
        self.assertTrue(t.check_pin(b'1234'))

        t.set_hashed_pin('HelloWörld')
        self.assertTrue(t.check_pin('HelloWörld'))

        t.pin_hash = None
        self.assertTrue(t.check_pin(''))
        self.assertFalse(t.check_pin(None))
        self.assertFalse(t.check_pin('1234'))

        t.pin_hash = ''
        self.assertTrue(t.check_pin(''))
        self.assertFalse(t.check_pin('1234'))

        t.set_hashed_pin('')
        self.assertTrue(len(t.pin_hash) > 0)
        self.assertTrue(t.check_pin(''))
        self.assertFalse(t.check_pin('1234'))

        # Delete the token
        remove_token(t1.serial)
        t = Token.query.filter_by(id=tid).first()
        self.assertTrue(t is None)

    def test_01_create_a_token_with_a_realm(self):
        """
        Create a token with a user and a tokenrealm in the database
        When we create a token with a user, the tokenrealm is filled in
        automatically.
        """
        self.create_resolver_realm()
        # Now we have a user cornelius@realm1
        # userid=1009
        # resolver=resolver1
        # realm=realm1
        otpkey = "123456"

        # create token and also assign the user and realm
        init_token({"type": "hotp", "serial": "serial2"},
                   user=User(uid=1009, realm=self.realm1, resolver=self.resolvername1))
        t2 = Token.query.filter_by(serial="serial2").first()
        self.assertEqual(t2.first_owner.resolver, "resolver1")
        # check the realm list of the token
        realm_found = False
        for realm_entry in t2.realm_list:
            if realm_entry.realm.name == "realm1":
                realm_found = True
        self.assertTrue(realm_found)

        # set the pin in a hashed way
        t2.set_pin("thepin")
        t2.save()
        r = t2.check_pin("wrongpin")
        self.assertFalse(r)
        r = t2.check_pin("thepin")
        self.assertTrue(r)

        # save the pin in an encrypted way
        t2.set_pin("thepin", hashed=False)
        t2.save()
        r = t2.check_pin("wrongpin")
        self.assertTrue(r is False)
        r = t2.check_pin("thepin")
        self.assertTrue(r)
        pin = t2.get_pin()
        self.assertEqual("thepin", pin)
        t2.set_pin('pinwithä', hashed=False)
        self.assertEqual(t2.get_pin(), 'pinwithä')

        # set the so pin
        (enc, iv) = t2.set_so_pin("topsecret")
        self.assertTrue(len(enc) > 0)
        self.assertTrue(len(iv) > 0)

        (enc, iv) = t2.set_so_pin(b"topsecret")
        self.assertTrue(enc)
        self.assertTrue(iv)

        (enc, iv) = t2.set_so_pin("topsecrät")
        self.assertTrue(enc)
        self.assertTrue(iv)

        # get token information
        token_dict = t2.get()
        self.assertIsInstance(token_dict, dict)
        self.assertTrue(token_dict.get("resolver") == "resolver1")
        # THe realm list is contained in realms
        self.assertTrue("realm1" in token_dict.get("realms"))

        resolver = t2.get("resolver")
        self.assertTrue(resolver == "resolver1")

        # retrieve a value, that does not exist
        nonexist = t2.get("nonexist")
        self.assertTrue(nonexist is None)

        # setting normal values
        t2.count_window = 100
        t2.otplen = 8
        t2.set_description("De scription")
        t2.save()
        TokenInfo(t2.id, "info", "value").save()
        t3 = Token.query.filter_by(serial="serial2").first()
        self.assertEqual(100, t3.count_window)
        self.assertEqual(8, t3.otplen)
        self.assertEqual("De scription", t3.description)
        self.assertEqual("value", t3.get_info().get("info"))

        # test the string representation
        s = "{0!s}".format(t3)
        self.assertEqual("serial2", s)

        # update token type
        t2.update_type("totp")
        self.assertTrue(t2.get("tokentype") == "totp")

        old_key = t2.key_enc
        old_pin = t2.pin_hash
        t2.update_token(description="New Text", otpkey="1234",
                        pin="new pin")
        self.assertTrue(t2.get("description") == "New Text")
        # The key has changed
        self.assertTrue(t2.key_enc != old_key)
        self.assertTrue(t2.pin_hash != old_pin)

        t2.set_otpkey(b'12345')
        self.assertEqual(b'12345', t2.get_otpkey().getKey(), t2)
        t2.failcount = 5
        t2.set_otpkey('Hellö', reset_failcount=True)
        self.assertTrue(t2.failcount == 0, t2)
        self.assertEqual('Hellö', t2.get_otpkey().getKey().decode('utf8'), t2)

        # key too long
        k = os.urandom(1500)
        t2.set_otpkey(k)
        self.assertGreater(len(t2.key_enc), Token.key_enc.property.columns[0].type.length)

        # SQLite supports writing too long data, all others don't.
        if db.engine.name != 'sqlite':
            self.assertRaises(Exception, db.session.commit)
            db.session.rollback()

        # set an empty token description
        self.assertEqual(t2.set_description(desc=None), '')

    def test_02_config_model(self):
        c = Config("splitRealm", True,
                   Type="string", Description="something")

        cid = c.save()
        self.assertTrue(cid == "splitRealm", cid)
        self.assertTrue("{0!s}".format(c) == "<splitRealm (string)>", c)

        # delete the config
        config = Config.query.filter_by(Key="splitRealm").first()
        self.assertTrue(config.delete() == "splitRealm")
        q = Config.query.filter_by(Key="splitRealm").all()
        # the list is empty
        self.assertTrue(len(q) == 0, q)

    def test_03_create_and_delete_realm(self):
        realmname = "realm23"
        r = Realm(realmname)
        r.save()

        qr = Realm.query.filter_by(name=realmname).first()
        self.assertTrue(qr.name == realmname)

        # delete realm
        qr.delete()
        # no realm left
        q = Realm.query.filter_by(name=realmname).all()
        self.assertTrue(len(q) == 0)

    def test_05_get_set_realm(self):
        t1 = Token(serial="serial1123")
        t1.save()
        realms = t1.get_realms()
        self.assertTrue(len(realms) == 0)

        statement = select(Realm).filter_by(name="realm1")
        realm_db = db.session.execute(statement).scalar_one_or_none()
        token_realm = TokenRealm(token_id=t1.id, realm_id=realm_db.id)
        db.session.add(token_realm)
        db.session.commit()
        realms = t1.get_realms()
        self.assertTrue(len(realms) == 1)

    def test_10_delete_resolver_realm(self):
        resolvername = "res1"
        realmname = "r1"
        # create a resolver
        r = Resolver(resolvername, "passwdresolver")
        _rid = r.save()
        # create a realm with this resolver
        realm = Realm(realmname)
        _realm_id = realm.save()
        rr = ResolverRealm(realm_name=realmname,
                           resolver_name=resolvername)
        rr_id = rr.save()
        self.assertTrue(rr_id > 0, rr_id)
        # check how many resolvers are in the realm
        db_realm = Realm.query.filter_by(name=realmname).first()
        self.assertTrue(len(db_realm.resolver_list) == 1,
                        len(db_realm.resolver_list))
        # remove the resolver from the realm
        # we can do this by deleting rr_id
        rr.delete()
        # check how many resolvers are in the realm
        self.assertTrue(len(db_realm.resolver_list) == 0,
                        len(db_realm.resolver_list))
        # delete the realm
        db_realm.delete()

    def test_11_policy(self):
        p = Policy("pol1", active="true",
                   scope="selfservice", action="action1",
                   realm="*")
        p.save()
        self.assertTrue(p.action == "action1", p)
        self.assertTrue("action1" in p.get().get("action"), p)
        self.assertTrue("action1" in p.get("action"), p)
        self.assertEqual(p.get()["conditions"], [])

        p2 = Policy("pol1", active="false",
                    scope="selfservice", action="action1",
                    realm="*")
        self.assertFalse(p2.active, p2.active)

        # update
        self.assertTrue(p.user == "", p.user)
        p.user = "cornelius"
        p.resolver = "*"
        p.client = "0.0.0.0"
        p.time = "anytime"
        p.pinode = "pinode1, pinode2"
        p.save()
        self.assertTrue(p.user == "cornelius", p.user)
        self.assertEqual(p.pinode, "pinode1, pinode2")

        # save admin policy
        p3 = Policy("pol3", active="false", scope="admin",
                    adminrealm='superuser', action="*", pinode="pinode3")
        self.assertEqual(p3.adminrealm, "superuser")
        self.assertEqual(p3.pinode, "pinode3")
        p3.save()

        # set conditions
        conditions = [
            PolicyConditionClass(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "foobar", False),
            PolicyConditionClass(ConditionSection.HTTP_REQUEST_HEADER, "user_agent", PrimaryComparators.EQUALS,
                                 "abcd", True)]
        set_policy_conditions(conditions, p3)
        expected = [(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "foobar", False,
                     ConditionHandleMissingData.default().value),
                    (ConditionSection.HTTP_REQUEST_HEADER, "user_agent", PrimaryComparators.EQUALS, "abcd", True,
                     ConditionHandleMissingData.default().value)]
        self.assertEqual(expected, p3.get_conditions_tuples())
        self.assertEqual(expected, p3.get()["conditions"])
        self.assertEqual(2, PolicyCondition.query.count())

        set_policy_conditions(
            [PolicyConditionClass(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "baz", True)],
            p3)
        p3.save()
        self.assertEqual([(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "baz", True,
                           ConditionHandleMissingData.default().value)], p3.get()["conditions"])
        self.assertEqual(1, len(p3.conditions))
        self.assertEqual("baz", p3.conditions[0].Value)
        self.assertEqual(1, PolicyCondition.query.count())

        # Check that the change has been persisted to the database
        p3_reloaded1 = Policy.query.filter_by(name="pol3").one()
        self.assertEqual(["pinode3"], p3_reloaded1.get()["pinode"])
        self.assertEqual([("userinfo", "type", PrimaryComparators.EQUALS, "baz", True,
                           ConditionHandleMissingData.default().value)], p3_reloaded1.get()["conditions"])
        self.assertEqual(1, len(p3_reloaded1.conditions))
        self.assertEqual("baz", p3_reloaded1.conditions[0].Value)
        self.assertEqual(1, PolicyCondition.query.count())

        set_policy_conditions([], p3)
        p3.save()
        self.assertEqual([], p3.get()["conditions"])
        self.assertEqual([], Policy.query.filter_by(name="pol3").one().get()["conditions"])
        self.assertEqual(0, PolicyCondition.query.count())

        # Test policies with adminusers
        p = Policy("pol1admin", active="true",
                   scope="admin", action="action1",
                   adminuser="jan, hein, klaas, pit")
        r = p.save()
        adminusers = p.get("adminuser")
        self.assertEqual(["jan", "hein", "klaas", "pit"], adminusers)
        p2 = Policy.query.filter_by(id=r).one()
        self.assertEqual("jan, hein, klaas, pit", p2.adminuser)

    def test_12_challenge(self):
        c = Challenge("S123456")
        self.assertEqual(20, len(c.transaction_id), c.transaction_id)
        self.assertEqual(20, len(c.get_transaction_id()), c.transaction_id)

        c.set_data("some data")
        self.assertEqual("some data", c.data)
        self.assertEqual("some data", c.get_data(), c.data)
        c.set_data({"some": "data"})
        self.assertIn("some", c.data, c.data)
        c.set_session("session")
        self.assertEqual("session", c.get_session(), c.session)
        c.set_challenge("challenge")
        self.assertEqual("challenge", c.get_challenge(), c.challenge)

        self.assertIn("otp_received", f"{c}")
        self.assertIn("transaction_id", f"{c}")
        self.assertIn("timestamp", f"{c}")

        # test with timestamp=True, which results in something like this:
        timestamp = '2014-11-29 21:56:43.057293'
        self.assertEqual(len(timestamp), len(c.get(True).get("timestamp")), c.get(True))
        # otp_status
        c.set_otp_status(valid=False)
        self.assertTrue(c.get_otp_status()[0], c.get_otp_status())
        self.assertFalse(c.get_otp_status()[1], c.get_otp_status())

    def test_15_add_and_delete_tokeninfo(self):
        t1 = Token("serialTI")
        t1.save()

        token_info = {"key1": "value1",
                      "key2": "value2",
                      "key3": "value3"}
        for key, value in token_info.items():
            info = TokenInfo(t1.id, key, value)
            db.session.add(info)
        db.session.commit()

        t2 = Token.query.filter_by(serial="serialTI").first()
        t2info = t2.get_info()
        self.assertTrue(t2info.get("key2") == "value2", t2info)

        statement = delete(TokenInfo).where(TokenInfo.token_id == t2.id, TokenInfo.Key == "key2")
        db.session.execute(statement)
        db.session.commit()
        t2info = t2.get_info()
        self.assertTrue(t2info.get("key2") is None, t2info)

    def test_18_add_and_delete_password_reset(self):
        p1 = PasswordReset("recoverycode", "cornelius",
                           "realm",
                           expiration=datetime.now() + timedelta(seconds=120))
        p1.save()
        p2 = PasswordReset.query.filter_by(username="cornelius",
                                           realm="realm").first()
        self.assertTrue(p2.recoverycode, "recoverycode")

    def test_21_add_update_delete_clientapp(self):
        # MySQLs DATETIME type supports only seconds so we have to mock now()
        current_time = datetime(2018, 3, 4, 5, 6, 8)
        with mock.patch('privacyidea.models.subscription.datetime') as mock_dt:
            mock_dt.now.return_value = current_time

            app = ClientApplication(ip="1.2.3.4", hostname="host1",
                                    clienttype="PAM", node="localnode")
            db.session.add(app)
            db.session.flush()

        c = db.session.scalars(select(ClientApplication).where(ClientApplication.ip == "1.2.3.4")).first()
        self.assertEqual(c.hostname, "host1")
        self.assertEqual(c.ip, "1.2.3.4")
        self.assertEqual(c.clienttype, "PAM")

        self.assertIn("localnode", repr(c))

    def test_23_usercache(self):
        username = "cornelius"
        resolver = "resolver1"
        user_id = 1
        # we don't need a timestamp with microseconds here, the MySQL DATETIME
        # type doesn't support it out of the box anyway
        timestamp = datetime.now().replace(microsecond=0)

        # create a user in the cache
        cached_user = UserCache(username, username, resolver, user_id, timestamp)
        self.assertTrue(cached_user)
        cached_user.save()

        # search a user in the cache
        find_user = UserCache.query.filter(UserCache.username ==
                                           username).first()
        self.assertTrue(find_user)
        self.assertEqual(find_user.user_id, str(user_id))
        self.assertEqual(find_user.resolver, resolver)
        self.assertEqual(find_user.timestamp, timestamp)  # TODO: Sensible, or might we have a small loss of precision?

        # search the user by his used_login
        # search a user in the cache
        find_user = UserCache.query.filter(UserCache.used_login ==
                                           username).first()
        self.assertTrue(find_user)
        self.assertEqual(find_user.user_id, str(user_id))
        self.assertEqual(find_user.resolver, resolver)

        # delete the user from the cache
        r = find_user.delete()
        self.assertTrue(r)
        find_user = UserCache.query.filter(UserCache.username ==
                                           username).first()
        self.assertFalse(find_user)

    def test_25_eventcounter(self):
        counter = EventCounter("test_counter", 10)
        counter.save()
        counter2 = EventCounter.query.filter_by(counter_name="test_counter").first()
        self.assertEqual(counter2.counter_value, 10)
        self.assertEqual(counter2.node, "")

        counter2.increase()
        counter2.increase()

        counter3 = EventCounter.query.filter_by(counter_name="test_counter").first()
        self.assertEqual(counter3.counter_value, 12)

        counter3.decrease()

        counter4 = EventCounter.query.filter_by(counter_name="test_counter").first()
        self.assertEqual(counter4.counter_value, 11)

        counter4.decrease()

        counter5 = EventCounter.query.filter_by(counter_name="test_counter").first()
        self.assertEqual(counter5.counter_value, 10)

        counter6 = EventCounter("test_counter", 4, "othernode")
        counter6.save()
        self.assertEqual(counter6.counter_value, 4)
        self.assertEqual(counter6.node, "othernode")

        counter_value = db.session.query(func.sum(EventCounter.counter_value)).filter(
            EventCounter.counter_name == "test_counter").one()[0]
        self.assertEqual(counter_value, 14)

        counters7 = EventCounter.query.filter_by(counter_name="test_counter").all()
        self.assertEqual(len(counters7), 2)

        counter8 = EventCounter.query.filter_by(counter_name="test_counter", node="othernode")
        counter8.delete()

        counters9 = EventCounter.query.filter_by(counter_name="test_counter").all()
        self.assertEqual(len(counters9), 1)
        counters9[0].delete()

        counter10 = EventCounter.query.filter_by(counter_name="test_counter").first()
        self.assertEqual(counter10, None)

    def test_27_monitoring_stats(self):
        # Simple test to write data to the monitoring stats table
        key1 = "user_count"
        key2 = "successful_auth"
        utcnow = datetime.utcnow()
        MonitoringStats(utcnow - timedelta(seconds=1), key1, 15).save()
        MonitoringStats(utcnow, key1, 21).save()
        MonitoringStats(utcnow, key2, 123).save()

        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 2)
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key2).count(), 1)

        # Delete all entries
        MonitoringStats.query.delete()
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key1).count(), 0)
        self.assertEqual(MonitoringStats.query.filter_by(stats_key=key2).count(), 0)


class TokenModelTestCaseDeleting(MyTestCase):

    def test_01_create_and_delete_resolver(self):
        r = Resolver("try_delete", "passwdresolver")
        rid = r.save()
        self.assertTrue(r.name is not None, r.name)
        self.assertTrue(r.rtype is not None, r.rtype)
        # Add configuration to the resolver
        conf = ResolverConfig(r.id, "fileName", "this_very_specific_file_try_delete")
        conf.save()

        # Read Resolver
        r1 = Resolver.query.filter_by(name="try_delete").first()
        self.assertTrue(r1.rtype == "passwdresolver", r1.rtype)
        self.assertEqual(rid, r1.id)

        # Get the option
        rc = ResolverConfig.query.filter_by(Value="this_very_specific_file_try_delete").first()
        self.assertTrue(rc)
        self.assertEqual(rc.resolver_id, rid)

        # Now delete the Resolver and check, if there is no config left
        reso = Resolver.query.filter_by(name="try_delete").first()
        reso.delete()
        rc = ResolverConfig.query.filter_by(Value="this_very_specific_file_try_delete").first()
        self.assertIsNone(rc)


class TokengroupTestCase(MyTestCase):

    def test_01_create_update_delete_tokengroup(self):
        tg = Tokengroup("gruppe1", "coolest group ever")
        self.assertIsInstance(tg, Tokengroup)
        rid = tg.save()
        self.assertGreaterEqual(rid, 1)

        # Test, if it does exist
        r = Tokengroup.query.filter_by(name="gruppe1").all()
        self.assertEqual(len(r), 1)
        self.assertIsInstance(r[0], Tokengroup)

        # delete
        r = tg.delete()
        self.assertEqual(r, rid)

        # Test, if it is gone
        r = Tokengroup.query.filter_by(name="gruppe1").all()
        self.assertEqual(len(r), 0)

    def test_02_assign_tokens_to_tokengroup(self):
        # create token groups
        tg1 = Tokengroup("gruppe1", "coolest group ever")
        self.assertIsInstance(tg1, Tokengroup)
        rid = tg1.save()
        self.assertGreaterEqual(rid, 1)
        tg2 = Tokengroup("gruppe2", "2nd group")
        self.assertIsInstance(tg2, Tokengroup)
        rid = tg2.save()
        self.assertGreaterEqual(rid, 1)

        # create tokens
        tok1 = Token(tokentype="spass", serial="tok1")
        tok1.save()
        tok2 = Token(tokentype="spass", serial="tok2")
        tok2.save()
        self.assertEqual(tok1.serial, "tok1")
        self.assertEqual(tok2.serial, "tok2")

        # assign tokens to token groups
        TokenTokengroup(token_id=tok1.id, tokengroupname="gruppe1").save()
        TokenTokengroup(token_id=tok1.id, tokengroupname="gruppe2").save()
        TokenTokengroup(token_id=tok2.id, tokengroup_id=tg2.id).save()
        ttg = TokenTokengroup.query.all()
        self.assertEqual(len(ttg), 3)

        ttg = TokenTokengroup.query.filter_by(token_id=tok1.id).all()
        self.assertEqual(len(ttg), 2)

        ttg = TokenTokengroup.query.filter_by(token_id=tok2.id).all()
        self.assertEqual(len(ttg), 1)

        self.assertEqual(len(tok1.tokengroup_list), 2)
        self.assertEqual(len(tok2.tokengroup_list), 1)

        self.assertEqual(tok2.tokengroup_list[0].name, "gruppe2")

        # cleanup
        remove_token(tok1.serial)
        remove_token(tok2.serial)
        delete_tokengroup(tg1.name)
        delete_tokengroup(tg2.name)


class ServiceidTestCase(MyTestCase):

    def test_01_create_update_delete_servicid(self):
        si = Serviceid("webserver", "The group of all our webservers")
        self.assertIsInstance(si, Serviceid)
        rid = si.save()
        self.assertGreaterEqual(rid, 1)

        # Test, if it does exist
        r = Serviceid.query.filter_by(name="webserver").all()
        self.assertEqual(len(r), 1)
        self.assertIsInstance(r[0], Serviceid)
        self.assertEqual("The group of all our webservers", r[0].Description)

        # update the description
        r[0].Description = "New description"
        r[0].save()

        # Check it:
        r = Serviceid.query.filter_by(name="webserver").all()
        self.assertEqual(len(r), 1)
        self.assertIsInstance(r[0], Serviceid)
        self.assertEqual("New description", r[0].Description)

        # delete
        r = si.delete()
        self.assertEqual(r, rid)

        # Test, if it is gone
        r = Serviceid.query.filter_by(name="webserver").all()
        self.assertEqual(len(r), 0)


class ResolverRealmTestCase(MyTestCase):

    def test_01_resolver_realm_with_nodes(self):
        nd1_uuid = "8e4272a9-9037-40df-8aa3-976e4a04b5a9"
        nd2_uuid = "d1d7fde6-330f-4c12-88f3-58a1752594bf"
        node1 = NodeName(id=nd1_uuid, name="Node1")
        node2 = NodeName(id=nd2_uuid, name="Node2")
        db.session.add_all([node1, node2])

        res = Resolver("resolver1", "passwdresolver")
        res.save()
        # Add configuration to the resolver
        ResolverConfig(res.id, "fileName", "tests/testdata/passwd").save()

        re1 = Realm("realm1")
        re1.save()

        # Put the resolver into the realm by name
        ResolverRealm(resolver_name="resolver1",
                      realm_name="realm1").save()

        self.assertIn(res.id, [x.resolver.id for x in re1.resolver_list])
        self.assertEqual(re1.resolver_list[0].node_uuid, "", re1.resolver_list[0])
        re1.delete()

        re2 = Realm("realm2")
        re2.save()
        ResolverRealm(resolver_name="resolver1",
                      realm_name="realm2", node_uuid=nd1_uuid).save()
        self.assertIn(res.id, [x.resolver.id for x in re2.resolver_list])
        self.assertEqual(re2.resolver_list[0].node_uuid, nd1_uuid, re1.resolver_list[0])
        re2.delete()

        db.session.delete(node1)
        db.session.delete(node2)

    # TODO: add resolver realm config with ids and different nodes
    # TODO: same nodes with different timestamps
