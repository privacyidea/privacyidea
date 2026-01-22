from privacyidea.lib.realm import delete_realm, set_realm
from privacyidea.lib.resolver import delete_resolver, save_resolver
from privacyidea.lib.riskbase import DEFAULT_IP_RISK, DEFAULT_SERVICE_RISK, DEFAULT_USER_RISK, get_group_resolvers, get_ip_risk_score, get_service_risk_score, get_user_risk_score
from tests import ldap3mock
from tests.base import MyApiTestCase

LDAPDirectory = [{"dn": 'uid=john.doe,ou=users,dc=example,dc=org',
                  "attributes": {'cn': 'john',
                                 "sn": "doe",
                                 "uid": "john.doe",
                                 "email": "john@example.org",
                                 'userPassword': 'johnpassword',
                                 "accountExpires": 9223372036854775807,
                                 "objectClass": ["top","person","organizationalPerson","inetOrgPerson"]
                                 }},
                 #groups
                 {"dn": "cn=admin,ou=groups,dc=example,dc=org",
                  "attributes": {"cn": "admin",
                                 "member": ["test.test"], #the ldap3mock parser does not like filters with multiple "=", so we use this instead of uid=test.test,ou=users,dc=example,dc=org
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
    @ldap3mock.activate
    def test_00_attach_group_resolver(self):
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
        
        group_resolver_name = "groups"
        paramsGroup["resolver"] = group_resolver_name
        paramsGroup["type"] = "ldapresolver"
        rid = save_resolver(paramsGroup)
        self.assertTrue(rid > 0)
        
        paramsUsers = ({'LDAPURI': 'ldap://localhost',
                   'LDAPBASE': 'dc=example,dc=org',
                   'BINDDN': 'uid=john.doe,ou=users,dc=example,dc=org',
                   'BINDPW': 'johnpassword',
                   'LOGINNAMEATTRIBUTE': 'cn',
                   'LDAPSEARCHFILTER': '(objectClass=inetOrgPerson)', 
                   'UIDTYPE': 'DN',
                   })
        
        user_resolver_name = "users"

        paramsUsers["resolver"] = user_resolver_name
        paramsUsers["type"] = "ldapresolver"
        rid = save_resolver(paramsUsers)
        self.assertTrue(rid > 0)
        
        (added, failed) = set_realm("ldap", [{'name': group_resolver_name},{"name": user_resolver_name}])
        self.assertEqual(len(added), 2)
        self.assertEqual(len(failed), 0)
        
        with self.app.test_request_context("/riskbase/groups",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"group_resolver_name": group_resolver_name,
                                                 "user_resolver_name": user_resolver_name}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            resolvers = get_group_resolvers()
            self.assertEqual(len(resolvers),1,resolvers)
            r = resolvers[0]
            self.assertEqual(r[0],user_resolver_name,r[0])
            self.assertEqual(r[1],group_resolver_name,r[1])

        with self.app.test_request_context("/riskbase/groups/delete",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"group_resolver_name": group_resolver_name,
                                                 "user_resolver_name": user_resolver_name}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            resolvers = get_group_resolvers()
            self.assertEqual(len(resolvers),0,resolvers)
            
        with self.app.test_request_context("/riskbase/groups",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"group_resolver_name": group_resolver_name,
                                                 "user_resolver_name": group_resolver_name}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,400)
            self.assertEqual(res.json["result"]["error"]["message"],"ERR905: Group resolver and User resolver cannot be the same")
            
        with self.app.test_request_context("/riskbase/groups",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"group_resolver_name": group_resolver_name,
                                                 "user_resolver_name": "AA"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,400)
            self.assertEqual(res.json["result"]["error"]["message"],"ERR905: User resolver does not exist")
            
        with self.app.test_request_context("/riskbase/groups",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"group_resolver_name": "AA",
                                                 "user_resolver_name": user_resolver_name}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,400)
            self.assertEqual(res.json["result"]["error"]["message"],"ERR905: Group resolver does not exist")
            
        delete_realm("ldap")
        delete_resolver(group_resolver_name)
        delete_resolver(user_resolver_name)
                   
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
            
        with self.app.test_request_context("/riskbase/ip/delete",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"identifier": "192.168.1.0/24"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            r = get_ip_risk_score("192.168.1.0/24")
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
    def test_02_get_config(self):
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
        
        group_resolver_name = "groups"
        paramsGroup["resolver"] = group_resolver_name
        paramsGroup["type"] = "ldapresolver"
        rid = save_resolver(paramsGroup)
        self.assertTrue(rid > 0)
        
        paramsUsers = ({'LDAPURI': 'ldap://localhost',
                   'LDAPBASE': 'dc=example,dc=org',
                   'BINDDN': 'uid=john.doe,ou=users,dc=example,dc=org',
                   'BINDPW': 'johnpassword',
                   'LOGINNAMEATTRIBUTE': 'cn',
                   'LDAPSEARCHFILTER': '(objectClass=inetOrgPerson)', 
                   'UIDTYPE': 'DN',
                   })
        
        user_resolver_name = "users"

        paramsUsers["resolver"] = user_resolver_name
        paramsUsers["type"] = "ldapresolver"
        rid = save_resolver(paramsUsers)
        self.assertTrue(rid > 0)
        
        (added, failed) = set_realm("ldap", [{'name': group_resolver_name},{"name": user_resolver_name}])
        self.assertEqual(len(added), 2)
        self.assertEqual(len(failed), 0)
        
        with self.app.test_request_context("/riskbase/groups",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"group_resolver_name": group_resolver_name,
                                                 "user_resolver_name": user_resolver_name}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
        
        with self.app.test_request_context("/riskbase/user",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"user_group": "groupA","risk_score": 10}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
        
        with self.app.test_request_context("/riskbase/ip",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"ip": "192.168.3.3","risk_score":12}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
        
        
        with self.app.test_request_context("/riskbase/service",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"service": "myService","risk_score": 11}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
        
        with self.app.test_request_context("/riskbase/",method="GET",
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            values = res.json["result"]["value"]
            
            self.assertIn("group_resolvers",values)
            self.assertIn("user_risk",values)
            self.assertIn("service_risk",values)
            self.assertIn("ip_risk",values)
            
            self.assertEqual(values["group_resolvers"],[{"user_resolver": user_resolver_name, "group_resolver": group_resolver_name}],values["group_resolvers"])
            self.assertEqual(values["user_risk"],[{"group": "groupA", "risk_score": str(float(10))}],values["user_risk"])
            self.assertEqual(values["service_risk"],[{"name": "myService", "risk_score": str(float(11))}],values["service_risk"])
            self.assertEqual(values["ip_risk"],[{"ip": "192.168.3.3/32", "risk_score": str(float(12))}],values["ip_risk"])
            
        #clear risk scores
        with self.app.test_request_context("/riskbase/ip/delete",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"identifier": "192.168.3.3/32"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)        
            
        with self.app.test_request_context("/riskbase/service/delete",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"identifier": "myService"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            
        with self.app.test_request_context("/riskbase/user/delete",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"identifier": "groupA"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            
        #clear user and group attach
        with self.app.test_request_context("/riskbase/groups/delete",method="POST",
                                           headers={"Authorization": self.at},
                                           data={"group_resolver_name": group_resolver_name,
                                                 "user_resolver_name": user_resolver_name}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
    
        #check everything is clear
        with self.app.test_request_context("/riskbase/",method="GET",
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code,200)
            values = res.json["result"]["value"]
            
            self.assertNotIn("group_resolvers",values)
            self.assertNotIn("user_risk",values)
            self.assertNotIn("service_risk",values)
            self.assertNotIn("ip_risk",values)
            
    
        delete_realm("ldap")
        delete_resolver(group_resolver_name)
        delete_resolver(user_resolver_name)
        