from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.error import ParameterError
from privacyidea.lib.realm import delete_realm, set_realm
from privacyidea.lib.resolver import delete_resolver, save_resolver
from tests import ldap3mock
from tests.base import MyTestCase
from privacyidea.lib.resolvers.LDAPIdResolver import IdResolver as LDAPResolver
from privacyidea.lib.riskbase import CONFIG_GROUPS_RISK_SCORES_KEY, CONFIG_IP_RISK_SCORES_KEY, CONFIG_SERVICES_RISK_SCORES_KEY, DEFAULT_IP_RISK, DEFAULT_SERVICE_RISK, DEFAULT_USER_RISK, _fetch_groups, _get_group_resolver,get_groups,LDAP_GROUP_RESOLVER_NAME_STR,LDAP_USER_GROUP_SEARCH_ATTR_STR,LDAP_USER_GROUP_DN_STR, get_ip_risk_score, get_risk_score, get_service_risk_score, get_user_groups, get_user_risk_score, remove_risk_score, sanitize_risk_score, save_risk_score, user_group_fetching_config_test


LDAPDirectory = [{"dn": "uid=jane.smith,ou=users,dc=example,dc=org",
                 "attributes": {'cn': 'jane',
                                "sn": "Smith",
                                "uid": "jane.smith",
                                'userPassword': 'janepassword',
                                "email": "jane@example.org",
                                "accountExpires": 131024988000000000,
                                "objectClass": ["top","person","organizationalPerson","inetOrgPerson"]
                                }},
                 {"dn": 'uid=john.doe,ou=users,dc=example,dc=org',
                  "attributes": {'cn': 'john',
                                 "sn": "doe",
                                 "uid": "john.doe",
                                 "email": "john@example.org",
                                 'userPassword': 'johnpassword',
                                 "accountExpires": 9223372036854775807,
                                 "objectClass": ["top","person","organizationalPerson","inetOrgPerson"]
                                 }},
                 {"dn": 'uid=test.test,ou=users,dc=example,dc=org',
                  "attributes": {'cn': 'test',
                                 "sn": "test",
                                 "email": "test.test@example.org",
                                 'userPassword': 'test',
                                 "accountExpires": 9223372036854775807,
                                 "objectClass": ["top","person","organizationalPerson","inetOrgPerson"]
                                 }},
                 #groups
                 {"dn": "cn=admin,ou=groups,dc=example,dc=org",
                  "attributes": {"cn": "admin",
                                 "member": ["uid=test.test,ou=users,dc=example,dc=org"],
                                 "objectClass": ["top","groupOfNames"]
                                 }},
                 {"dn": "cn=professor,ou=groups,dc=example,dc=org",
                  "attributes": {"cn": "professor",
                                 "member": ["uid=jane.smith,ou=users,dc=example,dc=org", "uid=john.doe,ou=users,dc=example,dc=org"],
                                 "objectClass": ["top","groupOfNames"]
                                 }},
                 {"dn": "cn=student,ou=groups,dc=example,dc=org",
                  "attributes": {"cn": "student",
                                 "member": ["uid=jane.smith,ou=users,dc=example,dc=org"],
                                 "objectClass": ["top","groupOfNames"]
                                 }}]

class RiskbaseTestCase(MyTestCase):
    @ldap3mock.activate
    def test_00_get_groups(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        params = ({'LDAPURI': 'ldap://localhost',
                   'LDAPBASE': 'dc=example,dc=org',
                   'BINDDN': 'uid=john.doe,ou=users,dc=example,dc=org',
                   'BINDPW': 'johnpassword',
                   'LOGINNAMEATTRIBUTE': 'cn',
                   'LDAPSEARCHFILTER': '(objectClass=groupOfNames)', 
                   'UIDTYPE': 'DN',
                   })
        params["resolver"] = "ldapresolver"
        params["type"] = "ldapresolver"
        rid = save_resolver(params)
        self.assertTrue(rid > 0)
        (added, failed) = set_realm("ldap", [{'name': "ldapresolver"}])
        self.assertEqual(len(added), 1)
        self.assertEqual(len(failed), 0)
        
        set_privacyidea_config(LDAP_GROUP_RESOLVER_NAME_STR,"ldapresolver")
        groups = get_groups()
        self.assertEqual(len(groups),3,len(groups))
        self.assertIn("professor",groups,"Professor was not fetched")
        self.assertIn("student",groups,"Student was not fetched")
        self.assertIn("admin",groups,"Admin was not fetched")
        
        delete_realm("ldap")
        delete_resolver("ldapresolver")
        
    @ldap3mock.activate
    #NOT WORKING
    def test_01_test_user_group_fetch(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        paramsGroup = ({'LDAPURI': 'ldap://localhost',
                   'LDAPBASE': 'dc=example,dc=org',
                   'BINDDN': 'uid=john.doe,ou=users,dc=example,dc=org',
                   'BINDPW': 'johnpassword',
                   'LOGINNAMEATTRIBUTE': 'cn',
                   'LDAPSEARCHFILTER': '(objectClass=groupOfNames)', 
                   'UIDTYPE': 'DN',
                   'USERINFO': '{ "member": "member" }',
                   'MULTIVALUEATTRIBUTES': '["member"]',
                   })
        paramsGroup["resolver"] = "ldapresolver"
        paramsGroup["type"] = "ldapresolver"
        rid = save_resolver(paramsGroup)
        self.assertTrue(rid > 0)
        
        (added, failed) = set_realm("ldap", [{'name': "ldapresolver"}])
        self.assertEqual(len(added), 1)
        self.assertEqual(len(failed), 0)
        
        #use defaults
        re = _get_group_resolver("ldapresolver")
        g = re.getUserList({"member": "uid=jane.smith,ou=users,dc=example,dc=org"})
        print(g)
        # g = _fetch_groups("groupOfNames",re,re.basedn,"objectClass")
        # re._search(re.basedn,"(&objectClass=groupOfNames)",re.loginname_attribute)
        # self.assertEqual("",None,g)
        # groups = user_group_fetching_config_test("uid=jane.smith,ou=users,dc=example,dc=org","groups",None,None)
        # self.assertEqual(len(groups),1,groups)
        
        delete_realm("ldap")
        delete_resolver("ldapresolver")
        
    @ldap3mock.activate
    #NOT WORKING
    def test_02_get_user_groups(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        params = ({'LDAPURI': 'ldap://localhost',
                   'LDAPBASE': 'dc=example,dc=org',
                   'BINDDN': 'uid=john.doe,ou=users,dc=example,dc=org',
                   'BINDPW': 'johnpassword',
                   'LOGINNAMEATTRIBUTE': 'cn',
                   'LDAPSEARCHFILTER': '(objectClass=groupOfNames)', 
                   'UIDTYPE': 'DN',
                   })
        params["resolver"] = "ldapresolver"
        params["type"] = "ldapresolver"
        rid = save_resolver(params)
        self.assertTrue(rid > 0)
        (added, failed) = set_realm("ldap", [{'name': "ldapresolver"}])
        self.assertEqual(len(added), 1)
        self.assertEqual(len(failed), 0)
        
        set_privacyidea_config(LDAP_GROUP_RESOLVER_NAME_STR,"ldapresolver")
        
        g = get_user_groups("uid=john.doe,ou=users,dc=example,dc=org")
        print(g)

        delete_realm("ldap")
        delete_resolver("ldapresolver")
        
    def test_03_get_save_remove_risk_scores(self):
        key = "myKey"
        
        r = get_risk_score(key,CONFIG_SERVICES_RISK_SCORES_KEY)
        self.assertEqual(r,None,f"risk score was not none: {r}")
        
        save_risk_score(key,5,CONFIG_SERVICES_RISK_SCORES_KEY)
        r = get_risk_score("nonExistingKey",CONFIG_SERVICES_RISK_SCORES_KEY)
        self.assertEqual(r,None,f"risk score was not none: {r}")
        
        r = get_risk_score(key,CONFIG_SERVICES_RISK_SCORES_KEY)
        self.assertEqual(r,5,f"risk score was not the same: {r}")
        
        key2 = "myKey2"
        save_risk_score(key2,10,CONFIG_SERVICES_RISK_SCORES_KEY)
        r = get_risk_score(key,CONFIG_SERVICES_RISK_SCORES_KEY)
        self.assertEqual(r,5,f"risk score was not the same: {r}")
        
        r = get_risk_score(key2,CONFIG_SERVICES_RISK_SCORES_KEY)
        self.assertEqual(r,10,f"risk score was not the same: {r}")
        
        #try to override
        with self.assertRaises(ParameterError):
            save_risk_score(key,3,CONFIG_SERVICES_RISK_SCORES_KEY)
            
        remove_risk_score(key,CONFIG_SERVICES_RISK_SCORES_KEY)
        r = get_risk_score(key,CONFIG_SERVICES_RISK_SCORES_KEY)
        self.assertEqual(r,None,f"risk score was not none: {r}")
        
        #try to remove unexisting risk score
        with self.assertRaises(ParameterError):
            remove_risk_score(key,CONFIG_SERVICES_RISK_SCORES_KEY)
    
        
    def test_04_get_ip_risk_score(self):
        ip = "192.168.1.10"
        
        #test default IP risk score
        risk = get_ip_risk_score(ip)
        self.assertEqual(risk,DEFAULT_IP_RISK,"Default IP risk not the same")
        
        #change default IP risk
        set_privacyidea_config("DefaultIPRiskScore",10)
        risk = get_ip_risk_score(ip)
        self.assertEqual(risk,10,"Default IP risk did not changed")
        
        #test with no IP
        risk = get_ip_risk_score(None)
        self.assertEqual(risk,10,"Risk score for null IP was not the expected")
        
        #test subnet
        save_risk_score("192.168.0.0/16",5,CONFIG_IP_RISK_SCORES_KEY)
        risk = get_ip_risk_score(ip)
        self.assertEqual(risk,5,"IP does not have the correct risk score")
        
        #test with another subnet
        save_risk_score("192.168.1.0/24",7,CONFIG_IP_RISK_SCORES_KEY)
        risk = get_ip_risk_score(ip)
        self.assertEqual(risk,7,"IP does not have the correct risk score")
        
        #set risk score for the IP
        save_risk_score(f"{ip}/32",3,CONFIG_IP_RISK_SCORES_KEY)
        risk = get_ip_risk_score(ip)
        self.assertEqual(risk,3,"IP does not have the correct risk score")
        
        #test with different IP
        risk = get_ip_risk_score("127.0.0.1")
        self.assertEqual(risk,10,"IP risk was not the default")
        
    def test_05_get_service_risk_score(self):
        service = "https://example.com"
        
        #test default
        risk = get_service_risk_score(service)
        self.assertEqual(risk,DEFAULT_SERVICE_RISK,"Default service risk not the same")
        
        #change default
        set_privacyidea_config("DefaultServiceRiskScore",10)
        risk = get_service_risk_score(service)
        self.assertEqual(risk,10,"Default service risk did not changed")
        
        #test with no service
        risk = get_service_risk_score(None)
        self.assertEqual(risk,10,"Risk score for null service was not the expected")
        
        #test with service risk score
        save_risk_score(service,3,CONFIG_SERVICES_RISK_SCORES_KEY)
        risk = get_service_risk_score(service)
        self.assertEqual(risk,3,"Service does not have the correct risk score")
        
    def test_06_get_user_risk_score(self):
        group = ["groupA"]
        
        #test default
        risk = get_user_risk_score(group)
        self.assertEqual(risk,DEFAULT_USER_RISK,"Default user risk not the same")
        
        #change default
        set_privacyidea_config("DefaultUserRiskScore",10)
        risk = get_user_risk_score(group)
        self.assertEqual(risk,10,"Default user risk did not changed")
        
        #test with no group
        risk = get_user_risk_score(None)
        self.assertEqual(risk,10,"Risk for null group was not the expected")
        
        #test with risk score
        save_risk_score("groupA",3,CONFIG_GROUPS_RISK_SCORES_KEY)
        risk = get_user_risk_score(group)
        self.assertEqual(risk,3,"Group does not have the correct risk score")
        
        #assign risk score for the other group
        save_risk_score("groupB",5,CONFIG_GROUPS_RISK_SCORES_KEY)
        risk = get_user_risk_score(group)
        self.assertEqual(risk,3,"Group does not have the correct risk score")
        
        group.append("groupB")
        risk = get_user_risk_score(group)
        self.assertEqual(risk,5,"Group does not have the correct risk score")
        
    def test_07_sanitize_risk_score(self):
        risk = 3
        
        r = sanitize_risk_score(risk)
        self.assertEqual(risk,r,"Not the same")
        
        r = sanitize_risk_score(str(risk))
        self.assertEqual(risk,r,"Not the same")
        
        with self.assertRaises(ParameterError):
            sanitize_risk_score(-10)
            
        with self.assertRaises(ParameterError):
            sanitize_risk_score("-10") 
        
        with self.assertRaises(ParameterError):
            r = sanitize_risk_score("AA")
            
        with self.assertRaises(ParameterError):
            sanitize_risk_score(None)
            
        