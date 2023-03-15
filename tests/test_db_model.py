# coding: utf-8
from mock import mock
import os
from sqlalchemy import func

from privacyidea.models import (Token,
                                Resolver,
                                ResolverRealm,
                                TokenRealm,
                                ResolverConfig,
                                Realm,
                                Config,
                                Policy,
                                Challenge, MachineResolver,
                                MachineResolverConfig, MachineToken, Admin,
                                CAConnector, CAConnectorConfig, SMTPServer,
                                PasswordReset, EventHandlerOption,
                                EventHandler, SMSGatewayOption, SMSGateway,
                                EventHandlerCondition, PrivacyIDEAServer,
                                ClientApplication, Subscription, UserCache,
                                EventCounter, PeriodicTask, PeriodicTaskLastRun,
                                PeriodicTaskOption, MonitoringStats, PolicyCondition, db,
                                Tokengroup, TokenTokengroup, Serviceid)
from .base import MyTestCase
from dateutil.tz import tzutc
from datetime import datetime
from datetime import timedelta


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

        otpObj = t.get_otpkey()
        self.assertTrue(otpObj.getKey() == otpkey.encode('utf8'))
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
        t1.delete()
        t = Token.query.filter_by(id=tid).first()
        self.assertTrue(t is None)

    def test_01_create_a_token_with_a_realm(self):
        '''
        Create a token with a user and a tokenrealm in the database
        When we create a token with a user, the tokenrealm is filled in
        automatically.
        '''
        self.create_resolver_realm()
        # Now we have a user cornelius@realm1
        # userid=1009
        # resolver=resolver1
        # realm=realm1
        otpkey = "123456"

        # create token and also assign the user and realm
        tneu = Token(serial="serial2",
                     otpkey=otpkey,
                     userid=1009,
                     resolver="resolver1",
                     realm="realm1")
        t2 = Token.query\
                  .filter_by(serial="serial2")\
                  .first()
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
        self.assertTrue(type(token_dict) == dict)
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
        t2.set_info({"info": "value"})
        t3 = Token.query\
                  .filter_by(serial="serial2")\
                  .first()
        self.assertTrue(t3.count_window == 100)
        self.assertTrue(t3.otplen == 8)
        self.assertTrue(t3.description == "De scription")
        self.assertTrue(t3.info_list[0].Value == "value")
        t3info = t3.get_info()
        self.assertTrue(t3.get_info().get("info") == "value")

        # test the string represenative
        s = "{0!s}".format(t3)
        self.assertTrue(s == "serial2")

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

        # delete the token
        ret = t2.delete()
        self.assertTrue(ret)
        # check that the TokenRealm is deleted
        q = TokenRealm.query.all()
        self.assertTrue(len(q) == 0)

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

    def test_04_update_resolver_config(self):
        resolvername = "resolver2"
        r = Resolver(resolvername, "passwdresolver")
        rid = r.save()
        self.assertTrue(r.name is not None, r.name)
        self.assertTrue(r.rtype == "passwdresolver", r.rtype)
        # save first resolver config
        rc = ResolverConfig(resolver=resolvername,
                            Key="fileName",
                            Value="/etc/passwd")
        res_conf_id = rc.save()
        self.assertTrue(res_conf_id > 0, res_conf_id)
        # update resolver config
        rc = ResolverConfig(resolver=resolvername,
                            Key="fileName",
                            Value="/etc/secureusers")
        res_conf_id2 = rc.save()
        self.assertTrue(res_conf_id2 == res_conf_id,
                        res_conf_id2)
        # delete resolver and its config
        r.delete()
        # check that config is empty
        q = ResolverConfig.query.filter_by(resolver_id=rid).all()
        self.assertTrue(len(q) == 0, q)

    def test_05_get_set_realm(self):
        t1 = Token(serial="serial1123")
        t1.save()
        realms = t1.get_realms()
        self.assertTrue(len(realms) == 0)
        t1.set_realms(["realm1"])
        t1.save()
        realms = t1.get_realms()
        self.assertTrue(len(realms) == 1)

    def test_06_caconnector(self):
        connector_name = "testCA"
        # create a CA connector
        cacon = CAConnector(name=connector_name, catype="localCA")
        cacon.save()

        # try to create a CA connector, that already exist
        #cacon = CAConnector(name="testCA", catype="localCA")
        #self.assertRaises(Exception, cacon.save)

        # add config entries to the CA connector
        CAConnectorConfig(caconnector_id=1, Key="Key1",
                          Value="Value1").save()
        CAConnectorConfig(caconnector=connector_name, Key="Key2",
                          Value="Value2", Type="password").save()
        q = CAConnectorConfig.query.filter_by(caconnector_id=1).all()
        self.assertEqual(len(q), 2)
        self.assertEqual(q[0].Value, "Value1")
        self.assertEqual(q[1].Value, "Value2")

        # update config entries
        CAConnectorConfig(caconnector=connector_name, Key="Key2",
                          Value="Value3").save()
        q = CAConnectorConfig.query.filter_by(Key="Key2").all()
        self.assertEqual(len(q), 1)
        self.assertEqual(q[0].Value, "Value3")

        # delete config entries
        CAConnectorConfig.query.filter_by(Key="Key2").delete()
        q = CAConnectorConfig.query.filter_by(Key="Key2").all()
        self.assertEqual(q, [])

        # Delete the CA connector. Remaining Config entries will be deleted
        # automatically
        cacon = CAConnector.query.filter_by(name=connector_name).first()
        r = cacon.delete()
        self.assertEqual(r, 1)
        q = CAConnectorConfig.query.filter_by(Key="Key1").all()
        # FIXME: The last entry does not get deleted!
        #self.assertEqual(q, [])

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
        p3.set_conditions([("userinfo", "type", "==", "foobar", False),
                           ("request", "user_agent", "==", "abcd", True)])
        self.assertEqual(p3.get_conditions_tuples(),
                         [("userinfo", "type", "==", "foobar", False),
                          ("request", "user_agent", "==", "abcd", True)])
        self.assertEqual(p3.get()["conditions"],
                         [("userinfo", "type", "==", "foobar", False),
                          ("request", "user_agent", "==", "abcd", True)])
        self.assertEqual(PolicyCondition.query.count(), 2)

        p3.set_conditions([("userinfo", "type", "==", "baz", True)])
        p3.save()
        self.assertEqual(p3.get()["conditions"],
                         [("userinfo", "type", "==", "baz", True)])
        self.assertEqual(len(p3.conditions), 1)
        self.assertEqual(p3.conditions[0].Value, "baz")
        self.assertEqual(PolicyCondition.query.count(), 1)

        # Check that the change has been persisted to the database
        p3_reloaded1 = Policy.query.filter_by(name="pol3").one()
        self.assertEqual(p3_reloaded1.get()["pinode"], ["pinode3"])
        self.assertEqual(p3_reloaded1.get()["conditions"],
                         [("userinfo", "type", "==", "baz", True)])
        self.assertEqual(len(p3_reloaded1.conditions), 1)
        self.assertEqual(p3_reloaded1.conditions[0].Value, "baz")
        self.assertEqual(PolicyCondition.query.count(), 1)

        p3.set_conditions([])
        p3.save()
        self.assertEqual(p3.get()["conditions"], [])
        self.assertEqual(Policy.query.filter_by(name="pol3").one().get()["conditions"], [])
        self.assertEqual(PolicyCondition.query.count(), 0)

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
        self.assertTrue(len(c.transaction_id) == 20, c.transaction_id)
        self.assertTrue(len(c.get_transaction_id()) == 20, c.transaction_id)

        c.set_data("some data")
        self.assertTrue(c.data == "some data", c.data)
        self.assertTrue(c.get_data() == "some data", c.data)
        c.set_data({"some": "data"})
        self.assertTrue("some" in c.data, c.data)
        c.set_session("session")
        self.assertTrue(c.get_session() == "session", c.session)
        c.set_challenge("challenge")
        self.assertTrue(c.get_challenge() == "challenge", c.challenge)

        self.assertTrue("otp_received" in "{0!s}".format(c), "{0!s}".format(c))
        self.assertTrue("transaction_id" in "{0!s}".format(c), "{0!s}".format(c))
        self.assertTrue("timestamp" in "{0!s}".format(c), "{0!s}".format(c))

        # test with timestamp=True, which results in something like this:
        timestamp = '2014-11-29 21:56:43.057293'
        self.assertTrue(len(c.get(True).get("timestamp")) == len(timestamp),
                        c.get(True))
        # otp_status
        c.set_otp_status(valid=False)
        self.assertTrue(c.get_otp_status()[0], c.get_otp_status())
        self.assertFalse(c.get_otp_status()[1], c.get_otp_status())

    def test_13_machine_resolver(self):
        # create the machineresolver and a config entry
        mr = MachineResolver("mr1", "mrtype1")
        mr_id = mr.save()
        self.assertTrue(mr_id > 0, mr)
        mrc = MachineResolverConfig(resolver="mr1", Key="key1", Value="value1")
        mrc_id = mrc.save()
        self.assertTrue(mrc_id > 0, mrc)
        # check that the config entry exist
        db_mrconf = MachineResolverConfig.query.filter(
            MachineResolverConfig.resolver_id == mr_id).first()
        self.assertTrue(db_mrconf is not None)

        # add a config value by ID
        mrc = MachineResolverConfig(resolver_id=mr_id, Key="key2", Value="v2")
        mrc_id = mrc.save()
        self.assertTrue(mrc_id > 0)
        # update config
        MachineResolverConfig(resolver_id=mr_id, Key="key2",
                              Value="new value").save()
        # check if the value is updated.
        new_config = MachineResolverConfig.query.filter(
            MachineResolverConfig.Key=="key2").first()
        self.assertTrue(new_config.Value == "new value", new_config.Value)

        # Connect a machine to a token
        mt_id = MachineToken(machineresolver_id=mr_id, machine_id="client1",
                             serial="serial1123",
                             application="SSH").save()
        self.assertTrue(mt_id > 0, mt_id)
        # Connect another machine to a token
        token_id = Token.query.filter_by(serial="serial1123").first().id
        mt_id2 = MachineToken(machineresolver="mr1", machine_id="client2",
                             token_id=token_id,
                             application="LUKS").save()
        self.assertTrue(mt_id2 > mt_id, (mt_id2, mt_id))
        # get the token that contains the machines
        db_token = Token.query.filter_by(serial="serial1123").first()
        # check the length of the machine list of the token
        self.assertTrue(len(db_token.machine_list) == 2, db_token.machine_list)
        machine2 = db_token.machine_list[1].machine_id
        self.assertTrue(machine2 == "client2", (machine2,
                                                db_token.machine_list))

        # delete the machine resolver
        db_mr = MachineResolver.query.filter(MachineResolver.name ==
                                             "mr1").first()
        db_mr.delete()
        # check that there is no machine resolver and no config entry

        db_mr = MachineResolver.query.filter(MachineResolver.name ==
                                             "mr1").first()
        self.assertTrue(db_mr is None)
        db_mrconf = MachineResolverConfig.query.filter(
            MachineResolverConfig.resolver_id == mr_id).first()
        self.assertTrue(db_mrconf is None)

    def test_14_save_update_admin(self):
        # create an admin user
        adminname = Admin(username="admin", password="secret",
                          email="admin@privacyidea.org").save()
        self.assertEqual(adminname, "admin")
        password1 = Admin.query.filter_by(username="admin").first().password

        # update admin - change the password
        Admin(username="admin", password="supersecret").save()
        password2 = Admin.query.filter_by(username="admin").first().password
        self.assertTrue(password1 != password2, (password1, password2))

    def test_15_add_and_delete_tokeninfo(self):
        t1 = Token("serialTI")
        t1.save()

        t1.set_info({"key1": "value1",
                     "key2": "value2",
                     "key3": "value3"})
        t2 = Token.query.filter_by(serial="serialTI").first()
        t2info = t2.get_info()
        self.assertTrue(t2info.get("key2") == "value2", t2info)

        t2.del_info("key2")
        t2info = t2.get_info()
        self.assertTrue(t2info.get("key2") is None, t2info)

    def test_16_add_and_delete_tokeninfo_password(self):
        t1 = Token("serialTI2")
        t1.set_info({"key1": "value1",
                     "key1.type": "password"})

        t2 = Token.query.filter_by(serial="serialTI2").first()
        t2info = t2.get_info()

        self.assertTrue(t2info.get("key1.type") == "password",
                        t2info)

    def test_17_add_and_delete_smtpserver(self):
        s1 = SMTPServer(identifier="myserver", server="1.2.3.4")
        s1.save()
        s2 = SMTPServer.query.filter_by(identifier="myserver").first()
        self.assertTrue(s2.server, "1.2.3.4")

        # Update the server
        r = SMTPServer(identifier="myserver", server="100.2.3.4",
                       username="user", password="password", tls=True,
                       description="test", port=123).save()
        modified_server = SMTPServer.query.filter_by(
            identifier="myserver").first()

        self.assertEqual(modified_server.server, "100.2.3.4")
        self.assertEqual(modified_server.username, "user")

        # Delete the server
        s2.delete()
        # Try to find the server
        s2 = SMTPServer.query.filter_by(identifier="myserver").first()
        # The server does not exist anymore
        self.assertEqual(s2, None)

    def test_18_add_and_delete_password_reset(self):
        p1 = PasswordReset("recoverycode", "cornelius",
                           "realm", expiration=datetime.now() + timedelta(
                seconds=120))
        p1.save()
        p2 = PasswordReset.query.filter_by(username="cornelius",
                                           realm="realm").first()
        self.assertTrue(p2.recoverycode, "recoverycode")

    def test_19_add_update_delete_eventhandler(self):
        # Bind the module "usernotice" to the enroll event
        event = "enroll"
        event_update = "init"
        handlermodule = "usernotice"
        action = "email"
        condition = "always"
        options = {"mailserver": "blafoo",
                   "option2": "value2"}
        conditions = {"user_type": "admin"}
        eh1 = EventHandler("ev1", event, handlermodule=handlermodule,
                           action=action, condition=condition,
                           options=options, conditions=conditions)
        self.assertTrue(eh1)

        self.assertEqual(eh1.event, event)
        self.assertEqual(eh1.handlermodule, handlermodule)
        self.assertEqual(eh1.action, action)
        self.assertEqual(eh1.condition, condition)
        self.assertEqual(eh1.options[0].Key, "mailserver")
        self.assertEqual(eh1.options[0].Value, "blafoo")
        self.assertEqual(eh1.options[1].Key, "option2")
        self.assertEqual(eh1.options[1].Value, "value2")
        self.assertEqual(eh1.conditions[0].Key, "user_type")
        self.assertEqual(eh1.conditions[0].Value, "admin")

        id = eh1.id

        # update eventhandler
        eh2 = EventHandler("ev1", event_update, handlermodule=handlermodule,
                           action=action, condition=condition,
                           options=options, ordering=0, id=id)
        self.assertEqual(eh1.event, event_update)

        # Update option value
        EventHandlerOption(id, Key="mailserver", Value="mailserver")
        self.assertEqual(eh1.options[0].Value, "mailserver")

        # Add Option
        EventHandlerOption(id, Key="option3", Value="value3")
        self.assertEqual(eh1.options[2].Key, "option3")
        self.assertEqual(eh1.options[2].Value, "value3")

        # Update condition value
        EventHandlerCondition(id, Key="user_type", Value="user")
        self.assertEqual(eh1.conditions[0].Value, "user")

        # Add condition
        EventHandlerCondition(id, Key="result_value", Value="True")
        self.assertEqual(eh1.conditions[0].Key, "result_value")
        self.assertEqual(eh1.conditions[0].Value, "True")
        self.assertEqual(eh1.conditions[1].Key, "user_type")
        self.assertEqual(eh1.conditions[1].Value, "user")

        # Delete event handler
        eh1.delete()

    def test_20_add_update_delete_smsgateway(self):
        name = "myGateway"
        provider_module = "privacyidea.lib.smsprovider.httpbla"
        provider_module2 = "module2"
        gw = SMSGateway(name, provider_module, options={"k": "v"})

        self.assertTrue(gw)

        self.assertEqual(gw.identifier, name)
        self.assertEqual(gw.providermodule, provider_module)

        # update SMS gateway, key "k" should not exist anymore!
        SMSGateway(name, provider_module2,
                   options={"k1": "v1"})
        self.assertEqual(gw.providermodule, provider_module2)
        self.assertEqual(gw.options[0].Key, "k1")
        self.assertEqual(gw.options[0].Value, "v1")

        # Delete gateway
        gw.delete()

    def test_21_add_update_delete_clientapp(self):
        # MySQLs DATETIME type supports only seconds so we have to mock now()
        current_time = datetime(2018, 3, 4, 5, 6, 8)
        with mock.patch('privacyidea.models.datetime') as mock_dt:
            mock_dt.now.return_value = current_time

            ClientApplication(ip="1.2.3.4", hostname="host1",
                              clienttype="PAM", node="localnode").save()

        c = ClientApplication.query.filter(ClientApplication.ip == "1.2.3.4").first()
        self.assertEqual(c.hostname, "host1")
        self.assertEqual(c.ip, "1.2.3.4")
        self.assertEqual(c.clienttype, "PAM")
        t1 = c.lastseen

        self.assertIn("localnode", repr(c))

        ClientApplication(ip="1.2.3.4", hostname="host1",
                          clienttype="PAM", node="localnode").save()
        c = ClientApplication.query.filter(ClientApplication.ip == "1.2.3.4").first()
        self.assertGreater(c.lastseen, t1, c)

        ClientApplication.query.filter(ClientApplication.id == c.id).delete()
        c = ClientApplication.query.filter(ClientApplication.ip == "1.2.3.4").first()
        self.assertEqual(c, None)

    def test_22_subscription(self):
        sid = Subscription(application="otrs", for_name="customer",
                           for_email="customer@example.com", for_phone="12345",
                           by_name="provider", by_email="p@example.com",
                           level="Gold").save()
        s = Subscription.query.filter(Subscription.application == "otrs").first()
        self.assertEqual(s.application, "otrs")
        self.assertEqual(s.for_name, "customer")
        self.assertEqual(s.for_email, "customer@example.com")
        self.assertEqual(s.for_phone, "12345")
        self.assertEqual(s.by_name, "provider")
        self.assertEqual(s.by_email, "p@example.com")
        self.assertEqual(s.level, "Gold")

        # Update the entry
        sid = Subscription(application="otrs", for_phone="11111",
                           by_url="https://support.com",
                           signature="1234567890", level="Silver").save()
        s = Subscription.query.filter(
            Subscription.application == "otrs").first()
        self.assertEqual(s.application, "otrs")
        self.assertEqual(s.for_name, "customer")
        self.assertEqual(s.for_email, "customer@example.com")
        self.assertEqual(s.for_phone, "11111")
        self.assertEqual(s.by_name, "provider")
        self.assertEqual(s.by_email, "p@example.com")
        self.assertEqual(s.by_url, "https://support.com")
        self.assertEqual(s.level, "Silver")

        # delete entry
        Subscription.query.filter(Subscription.application == "otrs").delete()
        s = Subscription.query.filter(
            Subscription.application == "otrs").first()
        self.assertEqual(s, None)

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

    def test_24_add_and_delete_privacyideaserver(self):
        pi1 = PrivacyIDEAServer(identifier="myserver",
                                url="https://pi.example.com")
        pi1.save()
        pi2 = PrivacyIDEAServer.query.filter_by(identifier="myserver").first()
        self.assertEqual(pi2.url, "https://pi.example.com")
        self.assertFalse(pi2.tls)

        # Update the server
        r = PrivacyIDEAServer(identifier="myserver",
                              url="https://pi2.example.com", tls=True,
                              description="test").save()
        modified_server = PrivacyIDEAServer.query.filter_by(
            identifier="myserver").first()

        self.assertTrue(modified_server.tls, "100.2.3.4")
        self.assertEqual(modified_server.description, "test")
        self.assertEqual(modified_server.url, "https://pi2.example.com")

        # Delete the server
        pi2.delete()
        # Try to find the server
        pi2 = PrivacyIDEAServer.query.filter_by(identifier="myserver").first()
        # The server does not exist anymore
        self.assertEqual(pi2, None)

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
        self.assertEqual(counter6.counter_value, 4)
        self.assertEqual(counter6.node, "othernode")

        counter_value = db.session.query(func.sum(EventCounter.counter_value))\
            .filter(EventCounter.counter_name == "test_counter").one()[0]
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

    def test_26_periodictask(self):
        current_utc_time = datetime(2018, 3, 4, 5, 6, 8)
        with mock.patch('privacyidea.models.datetime') as mock_dt:
            mock_dt.utcnow.return_value = current_utc_time

            task1 = PeriodicTask("task1", False, "0 5 * * *", ["localhost"], "some.module", 2, {
                "key1": "value2",
                "KEY2": True,
                "key3": "öfføff",
            })
            task2 = PeriodicTask("some other task", True, "0 6 * * *", ["localhost"], "some.other.module", 1, {
                "foo": "bar"
            })


        self.assertEqual(PeriodicTask.query.filter_by(name="task1").one(), task1)
        self.assertEqual(PeriodicTask.query.filter_by(name="some other task").one(), task2)
        self.assertEqual(PeriodicTaskOption.query.filter_by(periodictask_id=task1.id, key="KEY2").one().value,
                         "True")
        # Values are converted to strings
        self.assertEqual(task1.get(), {
            "id": task1.id,
            "name": "task1",
            "active": False,
            "interval": "0 5 * * *",
            # we get a timezone-aware datetime here
            "last_update": current_utc_time.replace(tzinfo=tzutc()),
            "nodes": ["localhost"],
            "taskmodule": "some.module",
            "ordering": 2,
            "options": {
                "key1": "value2",
                "KEY2": "True",
                "key3": "öfføff",
            },
            "retry_if_failed": True,
            "last_runs": {}})

        # register a run
        task1.set_last_run("localhost", datetime(2018, 3, 4, 5, 6, 7))

        # assert we can update the task
        later_utc_time = current_utc_time + timedelta(seconds=1)
        with mock.patch('privacyidea.models.datetime') as mock_dt:
            mock_dt.utcnow.return_value = later_utc_time
            PeriodicTask("task one", True, "0 8 * * *", ["localhost", "otherhost"], "some.module", 3, {
                "KEY2": "value number 2",
                "key 4": 1234
            }, id=task1.id)
        # the first run for otherhost
        task1.set_last_run("otherhost", datetime(2018, 8, 9, 10, 11, 12))
        result = PeriodicTask.query.filter_by(name="task one").one().get()
        self.assertEqual(result,
                         {
                             "id": task1.id,
                             "active": True,
                             "name": "task one",
                             "interval": "0 8 * * *",
                             "last_update": later_utc_time.replace(tzinfo=tzutc()),
                             "nodes": ["localhost", "otherhost"],
                             "taskmodule": "some.module",
                             "ordering": 3,
                             "options": {"KEY2": "value number 2",
                                         "key 4": "1234"},
                             'retry_if_failed': True,
                             "last_runs": {
                                 "localhost": datetime(2018, 3, 4, 5, 6, 7, tzinfo=tzutc()),
                                 "otherhost": datetime(2018, 8, 9, 10, 11, 12, tzinfo=tzutc()),
                             }
                         })
        # assert all old options are removed
        self.assertEqual(PeriodicTaskOption.query.filter_by(periodictask_id=task1.id, key="key3").count(), 0)
        # the second run for localhost
        task1.set_last_run("localhost", datetime(2018, 3, 4, 5, 6, 8))
        result = PeriodicTask.query.filter_by(name="task one").one().get()
        self.assertEqual(result,
                         {
                             "id": task1.id,
                             "active": True,
                             "name": "task one",
                             "interval": "0 8 * * *",
                             "last_update": later_utc_time.replace(tzinfo=tzutc()),
                             "nodes": ["localhost", "otherhost"],
                             "taskmodule": "some.module",
                             "ordering": 3,
                             "options": {"KEY2": "value number 2",
                                         "key 4": "1234"},
                             'retry_if_failed': True,
                             "last_runs": {
                                 "localhost": datetime(2018, 3, 4, 5, 6, 8, tzinfo=tzutc()),
                                 "otherhost": datetime(2018, 8, 9, 10, 11, 12, tzinfo=tzutc()),
                             }
                         })

        # remove "localhost", assert the last run is removed
        PeriodicTask("task one", True, "0 8 * * *", ["otherhost"], "some.module", 4, {"foo": "bar"}, id=task1.id)
        self.assertEqual(PeriodicTaskOption.query.filter_by(periodictask_id=task1.id).count(), 1)
        self.assertEqual(PeriodicTaskLastRun.query.filter_by(periodictask_id=task1.id).one().node, "otherhost")
        # naive timestamp in the database
        self.assertEqual(PeriodicTaskLastRun.query.filter_by(periodictask_id=task1.id).one().timestamp,
                         datetime(2018, 8, 9, 10, 11, 12, tzinfo=None))
        self.assertEqual(PeriodicTaskLastRun.query.filter_by(periodictask_id=task1.id).one().aware_timestamp,
                         datetime(2018, 8, 9, 10, 11, 12, tzinfo=tzutc()))

        # remove the tasks, everything is removed
        task1.delete()
        self.assertEqual(PeriodicTaskOption.query.count(), 1) # from task2
        self.assertEqual(PeriodicTaskLastRun.query.count(), 0)
        task2.delete()
        self.assertEqual(PeriodicTaskOption.query.count(), 0)

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
        t = TokenTokengroup(token_id=tok1.id, tokengroupname="gruppe1").save()
        t = TokenTokengroup(token_id=tok1.id, tokengroupname="gruppe2").save()
        t = TokenTokengroup(token_id=tok2.id, tokengroup_id=tg2.id).save()
        ttg = TokenTokengroup.query.all()
        self.assertEqual(len(ttg), 3)
        # It does not change anything, if we try to save the same assignment!
        t = TokenTokengroup(token_id=tok2.id, tokengroup_id=tg2.id).save()
        ttg = TokenTokengroup.query.all()
        self.assertEqual(len(ttg), 3)

        ttg = TokenTokengroup.query.filter_by(token_id=tok1.id).all()
        self.assertEqual(len(ttg), 2)

        ttg = TokenTokengroup.query.filter_by(token_id=tok2.id).all()
        self.assertEqual(len(ttg), 1)

        self.assertEqual(len(tok1.tokengroup_list), 2)
        self.assertEqual(len(tok2.tokengroup_list), 1)

        self.assertEqual(tok2.tokengroup_list[0].tokengroup.name, "gruppe2")

        # remove tokengroups and check that tokentokengroups assignments are removed
        tg1.delete()
        ttg = TokenTokengroup.query.all()
        self.assertEqual(len(ttg), 2)

        tg2.delete()
        ttg = TokenTokengroup.query.all()
        self.assertEqual(len(ttg), 0)

        # cleanup
        tok1.delete()
        tok2.delete()


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
