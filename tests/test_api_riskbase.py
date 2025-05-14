from privacyidea.lib.config import get_from_config
from privacyidea.lib.realm import delete_realm, set_realm
from privacyidea.lib.resolver import delete_resolver, save_resolver
from privacyidea.lib.riskbase import DEFAULT_IP_RISK, DEFAULT_SERVICE_RISK, DEFAULT_USER_RISK, LDAP_GROUP_RESOLVER_NAME_STR, LDAP_USER_GROUP_DN_STR, LDAP_USER_GROUP_SEARCH_ATTR_STR, get_ip_risk_score, get_service_risk_score, get_user_risk_score
from tests import ldap3mock
from tests.base import MyApiTestCase

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
                                 "member": ["test.test"], #the ldap3mock parser does not like filters with multiple "=", so we this instead of uid=test.test,ou=users,dc=example,dc=org
                                 "objectClass": ["top","groupOfNames"]
                                 }},
                 {"dn": "cn=professor,ou=groups,dc=example,dc=org",
                  "attributes": {"cn": "professor",
                                 "member": ["jane.smith", "john.doe"],
                                 "objectClass": ["top","groupOfNames"]
                                 }},
                 {"dn": "cn=student,ou=groups,dc=example,dc=org",
                  "attributes": {"cn": "student",
                                 "member": ["jane.smith"],
                                 "objectClass": ["top","groupOfNames"]
                                 }}]

class RiskbaseTestCase(MyApiTestCase):
    def test_00_group_connection_config(self):
        #test with no parameters
        with self.app.test_request_context("/riskbase/groups",
                                           method="POST",
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,400)
            self.assertEqual(res.json["result"]["error"]["message"],"ERR905: Missing parameter: 'resolver_name'")
        
        #empty resolver
        with self.app.test_request_context("/riskbase/groups",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"resolver_name": ""}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,400)
            self.assertEqual(res.json["result"]["error"]["message"],"ERR905: Parameter 'resolver_name' must not be empty")
        
        #test with resolver and defaults
        with self.app.test_request_context("/riskbase/groups",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"resolver_name": "ldapresolver"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = get_from_config(LDAP_GROUP_RESOLVER_NAME_STR)
            self.assertEqual(r,"ldapresolver")
            r = get_from_config(LDAP_USER_GROUP_DN_STR)
            self.assertEqual(r,None)
            r = get_from_config(LDAP_USER_GROUP_SEARCH_ATTR_STR)
            self.assertEqual(r,None)
        
        #change resolver
        with self.app.test_request_context("/riskbase/groups",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"resolver_name": "AA"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = get_from_config(LDAP_GROUP_RESOLVER_NAME_STR)
            self.assertEqual(r,"AA")
            r = get_from_config(LDAP_USER_GROUP_DN_STR)
            self.assertEqual(r,None)
            r = get_from_config(LDAP_USER_GROUP_SEARCH_ATTR_STR)
            self.assertEqual(r,None)
        
        #add dn and attr
        with self.app.test_request_context("/riskbase/groups",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"resolver_name": "MyResolver",
                                                 "user_to_group_search_attr": "attr",
                                                 "user_to_group_dn": "myDN"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = get_from_config(LDAP_GROUP_RESOLVER_NAME_STR)
            self.assertEqual(r,"MyResolver")
            r = get_from_config(LDAP_USER_GROUP_DN_STR)
            self.assertEqual(r,"myDN")
            r = get_from_config(LDAP_USER_GROUP_SEARCH_ATTR_STR)
            self.assertEqual(r,"attr")
        
        #change dn
        with self.app.test_request_context("/riskbase/groups",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"resolver_name": "MyResolver",
                                                 "user_to_group_search_attr": "attr",
                                                 "user_to_group_dn": "DNChanged"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = get_from_config(LDAP_GROUP_RESOLVER_NAME_STR)
            self.assertEqual(r,"MyResolver")
            r = get_from_config(LDAP_USER_GROUP_DN_STR)
            self.assertEqual(r,"DNChanged")
            r = get_from_config(LDAP_USER_GROUP_SEARCH_ATTR_STR)
            self.assertEqual(r,"attr")
        
        #delete dn
        with self.app.test_request_context("/riskbase/groups",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"resolver_name": "MyResolver",
                                                 "user_to_group_search_attr": "attr"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = get_from_config(LDAP_GROUP_RESOLVER_NAME_STR)
            self.assertEqual(r,"MyResolver")
            r = get_from_config(LDAP_USER_GROUP_DN_STR)
            self.assertEqual(r,None)
            r = get_from_config(LDAP_USER_GROUP_SEARCH_ATTR_STR)
            self.assertEqual(r,"attr")
            
        #delete attr
        with self.app.test_request_context("/riskbase/groups",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"resolver_name": "MyResolver"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = get_from_config(LDAP_GROUP_RESOLVER_NAME_STR)
            self.assertEqual(r,"MyResolver")
            r = get_from_config(LDAP_USER_GROUP_DN_STR)
            self.assertEqual(r,None)
            r = get_from_config(LDAP_USER_GROUP_SEARCH_ATTR_STR)
            self.assertEqual(r,None)
            
    def test_01_risks(self):
        #user risk
        with self.app.test_request_context("/riskbase/user",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"user_group": "groupA","risk_score": 10}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = get_user_risk_score(["groupA"])
            self.assertEqual(r,10)
        
        #service risk
        with self.app.test_request_context("/riskbase/service",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"service": "myService","risk_score": 11}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = get_service_risk_score("myService")
            self.assertEqual(r,11)
        
        #invalid ip
        with self.app.test_request_context("/riskbase/ip",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"ip": "192.168.3.0/16","risk_score": 3}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,400)
            error = res.json["result"]["error"]
            self.assertEqual(error["message"],"ERR905: Invalid IP address or network")
        
        #subnet with mask 24
        with self.app.test_request_context("/riskbase/ip",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"ip": "192.168.1.0/24","risk_score": 5}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = get_ip_risk_score("192.168.1.1")
            self.assertEqual(r,5)
        
        #ip without mask
        with self.app.test_request_context("/riskbase/ip",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"ip": "192.168.3.3","risk_score":12}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = get_ip_risk_score("192.168.3.3")
            self.assertEqual(r,12)
        
        #check
        with self.app.test_request_context("/riskbase/check",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"user": "groupA"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = res.json
            self.assertEqual(r["result"]["value"],10 + DEFAULT_IP_RISK + DEFAULT_SERVICE_RISK)
            
        with self.app.test_request_context("/riskbase/check",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"service": "myService"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = res.json
            self.assertEqual(r["result"]["value"],DEFAULT_USER_RISK + DEFAULT_IP_RISK + 11)
            
        with self.app.test_request_context("/riskbase/check",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"ip": "192.168.3.3"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = res.json
            self.assertEqual(r["result"]["value"],DEFAULT_USER_RISK + DEFAULT_SERVICE_RISK + 12)
            
        with self.app.test_request_context("/riskbase/check",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"ip": "192.168.3.3","user": "groupA", "service": "myService"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = res.json
            self.assertEqual(r["result"]["value"],10 + 11 + 12)
        
        
        #delete user risk
        with self.app.test_request_context("/riskbase/user/delete",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"identifier": "groupA"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = get_user_risk_score(["groupA"])
            self.assertEqual(r,DEFAULT_USER_RISK)
        
        #delete service risk
        with self.app.test_request_context("/riskbase/service/delete",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"identifier": "myService"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = get_service_risk_score("myService")
            self.assertEqual(r,DEFAULT_SERVICE_RISK)
        
        #delete ip risk
        with self.app.test_request_context("/riskbase/ip/delete",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"identifier": "192.168.3.3/32"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = get_ip_risk_score("192.168.3.3")
            self.assertEqual(r,DEFAULT_IP_RISK)
            
        #further check the values have been deleted
        with self.app.test_request_context("/riskbase/check",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"ip": "192.168.3.3","user": "groupA", "service": "myService"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = res.json
            self.assertEqual(r["result"]["value"],DEFAULT_USER_RISK + DEFAULT_SERVICE_RISK + DEFAULT_IP_RISK)
            
    @ldap3mock.activate
    def test_02_test_fetch_user_group(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        params = ({'LDAPURI': 'ldap://localhost',
                   'LDAPBASE': 'dc=example,dc=org',
                   'BINDDN': 'uid=john.doe,ou=users,dc=example,dc=org',
                   'BINDPW': 'johnpassword',
                   'LOGINNAMEATTRIBUTE': 'cn',
                   'LDAPSEARCHFILTER': '(objectClass=groupOfNames)', 
                   'UIDTYPE': 'DN',
                   'USERINFO': '{ "member": "member" }',
                   'MULTIVALUEATTRIBUTES': '["member"]',
                   })
        resolver_name = "groups"
        params["resolver"] = resolver_name
        params["type"] = "ldapresolver"
        rid = save_resolver(params)
        self.assertTrue(rid > 0)
        (added, failed) = set_realm("ldap", [{'name': resolver_name}])
        self.assertEqual(len(added), 1)
        self.assertEqual(len(failed), 0)
        
        #non-existing resolver
        with self.app.test_request_context("/riskbase/groups/test",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"resolver_name": "my resolver",
                                                 "user_dn": "jane.smith"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            groups = res.json["result"]["value"]
            self.assertEqual(len(groups),0,groups)
            
        #non-existing user
        with self.app.test_request_context("/riskbase/groups/test",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"resolver_name": resolver_name,
                                                 "user_dn": "my.user"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            groups = res.json["result"]["value"]
            self.assertEqual(len(groups),0,groups)
            
        #existing resolver and user
        with self.app.test_request_context("/riskbase/groups/test",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"resolver_name": resolver_name,
                                                 "user_dn": "jane.smith"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            groups = res.json["result"]["value"]
            self.assertEqual(len(groups),2,groups)
        
        delete_realm("ldap")
        delete_resolver(resolver_name)
        
        