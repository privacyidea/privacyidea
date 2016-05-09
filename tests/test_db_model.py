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
                                EventHandler)
from .base import MyTestCase
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
        self.assertTrue(pin_object.getPin() == userpin)
        
        t = Token.query.filter_by(id=tid).first()
        self.assertTrue(len(t.pin_hash) > 0)
        self.assertTrue(len(t.user_pin) > 0)
        
        otpObj = t.get_otpkey()
        self.assertTrue(otpObj.getKey() == otpkey)
        count = t.count
        self.assertTrue(count == 0)
        
        up = t.get_user_pin()
        self.assertTrue(up.getPin() == userpin)
        
        self.assertTrue(t.check_hashed_pin("1234"))
        
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
        self.assertTrue(t2.resolver == "resolver1")
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
        self.assertTrue(r is False)
        r = t2.check_pin("thepin")
        self.assertTrue(r)

        # call split_pin_pass
        res, pin, otp = t2.split_pin_pass("pin123456")
        self.assertTrue(res)
        self.assertTrue(pin == "pin", pin)
        self.assertTrue(otp == "123456", otp)
        res, pin, otp = t2.split_pin_pass("123456pin", prepend=False)
        self.assertTrue(res)
        self.assertTrue(pin == "pin", pin)
        self.assertTrue(otp == "123456", otp)

        # save the pin in an encrypted way
        t2.set_pin("thepin", hashed=False)
        t2.save()
        r = t2.check_pin("wrongpin")
        self.assertTrue(r is False)
        r = t2.check_pin("thepin")
        self.assertTrue(r)
        pin = t2.get_pin()
        self.assertTrue(pin == "thepin")
        
        # set the so pin
        (enc, iv) = t2.set_so_pin("topsecret")
        self.assertTrue(len(enc) > 0)
        self.assertTrue(len(iv) > 0)
        
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
        self.assertTrue(u"{0!s}".format(c) == "<splitRealm (string)>", c)
        
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
        p.save()
        self.assertTrue(p.user == "cornelius", p.user)

        # save admin policy
        p3 = Policy("pol3", active="false", scope="admin",
                    adminrealm='superuser', action="*")
        self.assertEqual(p3.adminrealm, "superuser")
        
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
        self.assertTrue(mr_id > 0, mr_id)
        mrc = MachineResolverConfig(resolver="mr1", Key="key1", Value="value1")
        mrc.save()
        self.assertTrue(mrc > 0)
        # check that the config entry exist
        db_mrconf = MachineResolverConfig.query.filter(
            MachineResolverConfig.resolver_id == mr_id).first()
        self.assertTrue(db_mrconf is not None)

        # add a config value by ID
        mrc = MachineResolverConfig(resolver_id=mr_id, Key="key2", Value="v2")
        mrc.save()
        self.assertTrue(mrc > 0)
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
        eh1 = EventHandler(event, handlermodule=handlermodule,
                           action=action, condition=condition,
                           options=options)
        self.assertTrue(eh1)

        self.assertEqual(eh1.event, event)
        self.assertEqual(eh1.handlermodule, handlermodule)
        self.assertEqual(eh1.action, action)
        self.assertEqual(eh1.condition, condition)
        self.assertEqual(eh1.option_list[0].Key, "mailserver")
        self.assertEqual(eh1.option_list[0].Value, "blafoo")
        self.assertEqual(eh1.option_list[1].Key, "option2")
        self.assertEqual(eh1.option_list[1].Value, "value2")

        id = eh1.id

        # update eventhandler
        eh2 = EventHandler(event_update, handlermodule=handlermodule,
                           action=action, condition=condition,
                           options=options, ordering=0, id=id)
        self.assertEqual(eh1.event, event_update)

        # Update option value
        EventHandlerOption(id, Key="mailserver", Value="mailserver")
        self.assertEqual(eh1.option_list[0].Value, "mailserver")

        # Add value
        EventHandlerOption(id, Key="option3", Value="value3")
        self.assertEqual(eh1.option_list[2].Key, "option3")
        self.assertEqual(eh1.option_list[2].Value, "value3")

        # Delete event handler
        eh1.delete()


