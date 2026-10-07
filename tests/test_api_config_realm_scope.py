"""
Admin policies restricted to a realm also restrict the configuration of resolvers, realms and policies (issue #1732).
"""
from io import BytesIO

from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import set_policy, delete_policy, get_policies, export_policies, SCOPE
from privacyidea.lib.realm import set_realm, get_realms, set_default_realm, get_default_realm
from privacyidea.lib.resolver import save_resolver, get_resolver_list
from privacyidea.models import db, NodeName
from .base import MyApiTestCase, PWFILE

REALM_A = "realm_a"
REALM_B = "realm_b"
RESO_A = "reso_a"
RESO_B = "reso_b"
RESO_FREE = "reso_free"
NODE_UUID = "5b1e0f3c-7a43-4f0e-9a2d-1c6b8e2f4d71"
CONFIG_ACTIONS = ", ".join([PolicyAction.RESOLVERREAD, PolicyAction.RESOLVERWRITE, PolicyAction.RESOLVERDELETE,
                            PolicyAction.POLICYREAD, PolicyAction.POLICYWRITE, PolicyAction.POLICYDELETE])


class ConfigRealmScopeTestCase(MyApiTestCase):

    def setUp(self):
        super().setUp()
        for resolver in (RESO_A, RESO_B, RESO_FREE):
            save_resolver({"resolver": resolver, "type": "passwdresolver", "fileName": PWFILE})
        set_realm(REALM_A, [{"name": RESO_A}])
        set_realm(REALM_B, [{"name": RESO_B}])
        set_default_realm(REALM_A)

    def tearDown(self):
        for policy in get_policies():
            delete_policy(policy.get("name"))
        node = db.session.get(NodeName, NODE_UUID)
        if node:
            db.session.delete(node)
            db.session.commit()
        super().tearDown()

    def _request(self, url, method="GET", data=None, json=None):
        kwargs = {"json": json} if json is not None else {"data": data or {}}
        with self.app.test_request_context(url, method=method, headers={"Authorization": self.at}, **kwargs):
            return self.app.full_dispatch_request()

    def _restrict_to_realm_a(self):
        set_policy(name="admin_realm_a", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_A)

    def test_01_read_resolvers(self):
        # Without admin policies every resolver is listed
        res = self._request("/resolver/")
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue({RESO_A, RESO_B, RESO_FREE} <= set(res.json["result"]["value"]))

        # An admin policy for realm_a lists only the resolvers of realm_a
        self._restrict_to_realm_a()
        res = self._request("/resolver/")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({RESO_A}, set(res.json["result"]["value"]))
        res = self._request(f"/resolver/{RESO_B}")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({}, res.json["result"]["value"])

        # A policy naming a resolver grants it, even if it is part of no realm
        set_policy(name="admin_reso_free", scope=SCOPE.ADMIN, action=PolicyAction.RESOLVERREAD, resolver=RESO_FREE)
        res = self._request("/resolver/")
        self.assertEqual({RESO_A, RESO_FREE}, set(res.json["result"]["value"]))

        # A policy without any restriction grants every resolver
        set_policy(name="admin_all", scope=SCOPE.ADMIN, action=PolicyAction.RESOLVERREAD)
        res = self._request("/resolver/")
        self.assertTrue({RESO_A, RESO_B, RESO_FREE} <= set(res.json["result"]["value"]))

    def test_02_write_resolvers(self):
        self._restrict_to_realm_a()
        params = {"type": "passwdresolver", "fileName": PWFILE}
        res = self._request(f"/resolver/{RESO_A}", "POST", params)
        self.assertEqual(200, res.status_code, res.json)
        for resolver in (RESO_B, RESO_FREE, "reso_new"):
            res = self._request(f"/resolver/{resolver}", "POST", params)
            self.assertEqual(403, res.status_code, resolver)
        self.assertNotIn("reso_new", get_resolver_list())

        res = self._request(f"/resolver/{RESO_FREE}", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertIn(RESO_FREE, get_resolver_list())

        # Testing a stored resolver uses its stored password, so it needs the resolver to be granted
        res = self._request("/resolver/test", "POST", dict(params, resolver=RESO_B))
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/resolver/test", "POST", params)
        self.assertEqual(200, res.status_code, res.json)

    def test_03_realm_resolvers(self):
        self._restrict_to_realm_a()
        # Adding a resolver of another realm is refused
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": f"{RESO_A},{RESO_B}"})
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual([RESO_A], [r["name"] for r in get_realms(REALM_A)[REALM_A]["resolver"]])
        # Writing the realm unchanged is allowed
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": RESO_A})
        self.assertEqual(200, res.status_code, res.json)
        # Another realm is refused by its name
        res = self._request(f"/realm/{REALM_B}", "POST", {"resolvers": RESO_B})
        self.assertEqual(403, res.status_code, res.json)

        # A resolver of the realm belongs to it, so a policy for the realm grants it
        set_realm(REALM_A, [{"name": RESO_A}, {"name": RESO_FREE}])
        res = self._request("/resolver/")
        self.assertEqual({RESO_A, RESO_FREE}, set(res.json["result"]["value"]))

        # A policy narrowed to one resolver of the realm: the other one may stay in the realm, but not be removed
        set_policy(name="admin_realm_a", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_A, resolver=RESO_A)
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": RESO_A})
        self.assertEqual(403, res.status_code, res.json)
        for resolvers in (f"{RESO_A},{RESO_FREE}", f"{RESO_A}, {RESO_FREE}", f"{RESO_A},{RESO_FREE},"):
            res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": resolvers})
            self.assertEqual(200, res.status_code, resolvers)

        # Only the path names the realm and the node: a nodeid in the body or another spelling of the realm
        # does not hide the removal
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": RESO_A, "nodeid": "node_x"})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request(f"/realm/{REALM_A.upper()}", "POST", {"resolvers": RESO_A})
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual({RESO_A, RESO_FREE}, {r["name"] for r in get_realms(REALM_A)[REALM_A]["resolver"]})

        # The resolvers of a node are checked the same way
        set_policy(name="admin_realm_a", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_A, resolver="")
        db.session.add(NodeName(id=NODE_UUID, name="realm_scope_node"))
        db.session.commit()
        res = self._request(f"/realm/{REALM_A}/node/{NODE_UUID}", "POST", json={"resolver": [{"name": RESO_B}]})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request(f"/realm/{REALM_A}/node/{NODE_UUID}", "POST", json={"resolver": [{"name": RESO_A}]})
        self.assertEqual(200, res.status_code, res.json)
        # A resolver entry without a name is left to the endpoint, which refuses it
        res = self._request(f"/realm/{REALM_A}/node/{NODE_UUID}", "POST", json={"resolver": [{"priority": 1}]})
        self.assertEqual(400, res.status_code, res.json)

        # Another spelling of the realm keeps the resolvers the request does not set, also those the admin may not
        # administer
        set_realm(REALM_A, [{"name": RESO_A}, {"name": RESO_FREE, "node": NODE_UUID}])
        set_policy(name="admin_realm_a", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_A, resolver=RESO_A)
        expected = {(RESO_A, ""), (RESO_FREE, NODE_UUID)}
        res = self._request(f"/realm/{REALM_A.upper()}", "POST", {"resolvers": RESO_A})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(expected, {(r["name"], r.get("node") or "") for r in get_realms(REALM_A)[REALM_A]["resolver"]})
        set_policy(name="admin_realm_a", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_A, resolver="")
        res = self._request(f"/realm/{REALM_A.upper()}/node/{NODE_UUID}", "POST",
                            json={"resolver": [{"name": RESO_FREE}]})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(expected, {(r["name"], r.get("node") or "") for r in get_realms(REALM_A)[REALM_A]["resolver"]})

    def test_04_default_realm(self):
        self._restrict_to_realm_a()
        set_default_realm(REALM_B)
        res = self._request(f"/defaultrealm/{REALM_A}", "POST")
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/defaultrealm", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual(REALM_B, get_default_realm())

        set_default_realm(REALM_A)
        res = self._request(f"/defaultrealm/{REALM_B}", "POST")
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual(REALM_A, get_default_realm())
        res = self._request("/defaultrealm", "DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertIsNone(get_default_realm())

        # The default realm needs a policy for the whole realm, not for some of its resolvers
        set_default_realm(REALM_A)
        set_policy(name="admin_realm_a", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_A, resolver=RESO_A)
        res = self._request("/defaultrealm", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual(REALM_A, get_default_realm())

    def test_05_read_policies(self):
        set_policy(name="pol_a", scope=SCOPE.AUTH, action=PolicyAction.OTPPIN + "=userstore", realm=REALM_A)
        set_policy(name="pol_b", scope=SCOPE.AUTH, action=PolicyAction.OTPPIN + "=userstore", realm=REALM_B)
        set_policy(name="pol_all", scope=SCOPE.AUTH, action=PolicyAction.OTPPIN + "=userstore")
        set_policy(name="pol_ab", scope=SCOPE.AUTH, action=PolicyAction.OTPPIN + "=userstore",
                   realm=f"{REALM_A},{REALM_B}")
        self._restrict_to_realm_a()
        # The admin sees every policy that applies to a granted realm, also one for every realm
        res = self._request("/policy/")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({"pol_a", "pol_ab", "pol_all", "admin_realm_a"},
                         {p["name"] for p in res.json["result"]["value"]})
        res = self._request("/policy/pol_b")
        self.assertEqual([], res.json["result"]["value"])

        res = self._request("/policy/export/policies.cfg")
        self.assertEqual(200, res.status_code)
        exported = res.get_data(as_text=True)
        self.assertIn("[pol_a]", exported)
        self.assertIn("[pol_all]", exported)
        self.assertNotIn("[pol_b]", exported)

    def test_06_write_policies(self):
        auth_action = PolicyAction.OTPPIN + "=userstore"
        set_policy(name="pol_a", scope=SCOPE.AUTH, action=auth_action, realm=REALM_A)
        set_policy(name="pol_b", scope=SCOPE.AUTH, action=auth_action, realm=REALM_B)
        self._restrict_to_realm_a()

        # A policy of another realm can not be changed, renamed, toggled or deleted
        res = self._request("/policy/pol_b", "POST", {"scope": SCOPE.AUTH, "action": auth_action})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/policy/pol_b", "PATCH", {"name": "pol_renamed"})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/policy/disable/pol_b", "POST")
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/policy/pol_b", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        # Only the path names the policy: an own policy as old_name in the query or body does not grant another one
        res = self._request("/policy/pol_b?old_name=pol_a", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/policy/disable/pol_b", "POST", {"old_name": "pol_a"})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/policy/pol_b", "POST", {"scope": SCOPE.AUTH, "action": auth_action, "realm": REALM_A,
                                                      "old_name": "pol_a"})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/policy/pol_b", "POST", {"scope": SCOPE.AUTH, "action": PolicyAction.OTPPIN + "=none",
                                                      "old_name": "pol_a"})
        self.assertEqual(403, res.status_code, res.json)
        pol_b = get_policies(name="pol_b", active=True)[0]
        self.assertEqual([REALM_B], pol_b["realm"])
        self.assertEqual({PolicyAction.OTPPIN: "userstore"}, pol_b["action"])

        # A new policy needs a realm the admin may administer
        res = self._request("/policy/pol_new", "POST", {"scope": SCOPE.AUTH, "action": auth_action})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/policy/pol_new", "POST", {"scope": SCOPE.AUTH, "action": auth_action,
                                                        "realm": f"{REALM_A},{REALM_B}"})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/policy/pol_new", "POST", {"scope": SCOPE.AUTH, "action": auth_action,
                                                        "realm": REALM_A})
        self.assertEqual(200, res.status_code, res.json)

        # The own policies can be changed, keeping their realm or setting a granted one
        res = self._request("/policy/pol_a", "POST", {"scope": SCOPE.AUTH, "action": auth_action})
        self.assertEqual(200, res.status_code, res.json)
        res = self._request("/policy/pol_a", "POST", {"scope": SCOPE.AUTH, "action": auth_action, "realm": ""})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/policy/disable/pol_a", "POST")
        self.assertEqual(200, res.status_code, res.json)
        res = self._request("/policy/pol_a", "PATCH", {"name": "pol_a_renamed"})
        self.assertEqual(200, res.status_code, res.json)
        res = self._request("/policy/pol_a_renamed", "DELETE")
        self.assertEqual(200, res.status_code, res.json)

        # A policy of a granted and another realm also applies to the other realm, so it can not be changed at all
        set_policy(name="pol_ab", scope=SCOPE.AUTH, action=auth_action, realm=f"{REALM_A},{REALM_B}")
        for method, url, data in (("POST", "/policy/disable/pol_ab", None),
                                  ("POST", "/policy/pol_ab", {"scope": SCOPE.AUTH, "action": auth_action}),
                                  ("POST", "/policy/pol_ab", {"scope": SCOPE.AUTH, "action": auth_action,
                                                              "realm": REALM_A}),
                                  ("PATCH", "/policy/pol_ab", {"name": "pol_ab_renamed"}),
                                  ("DELETE", "/policy/pol_ab", None)):
            res = self._request(url, method, data)
            self.assertEqual(403, res.status_code, (method, url, data))
        pol_ab = get_policies(name="pol_ab", active=True)[0]
        self.assertEqual([REALM_A, REALM_B], sorted(pol_ab["realm"]))

    def test_07_unrestricted_admin(self):
        # An admin policy without a realm keeps the configuration unrestricted
        set_policy(name="admin_all", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS)
        set_policy(name="pol_b", scope=SCOPE.AUTH, action=PolicyAction.OTPPIN + "=userstore", realm=REALM_B)
        res = self._request("/resolver/")
        self.assertTrue({RESO_A, RESO_B, RESO_FREE} <= set(res.json["result"]["value"]))
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": f"{RESO_A},{RESO_B}"})
        self.assertEqual(200, res.status_code, res.json)
        res = self._request("/policy/")
        self.assertEqual({"admin_all", "pol_b"}, {p["name"] for p in res.json["result"]["value"]})
        res = self._request("/policy/pol_b", "DELETE")
        self.assertEqual(200, res.status_code, res.json)

    def test_08_import_policies(self):
        auth_action = PolicyAction.OTPPIN + "=userstore"
        set_policy(name="imp_a", scope=SCOPE.AUTH, action=auth_action, realm=REALM_A)
        set_policy(name="imp_b", scope=SCOPE.AUTH, action=auth_action, realm=REALM_A)
        set_policy(name="imp_c", scope=SCOPE.AUTH, action=auth_action, realm=REALM_B)
        set_policy(name="imp_all", scope=SCOPE.AUTH, action=auth_action)
        policy_file = export_policies([policy for name in ("imp_a", "imp_b", "imp_c", "imp_all")
                                       for policy in get_policies(name=name)])
        # Every realm but realm_b is realm_a today, but also every realm created later
        policy_file += (f"[imp_wildcard]\nscope = {SCOPE.AUTH}\naction = \"{{'{PolicyAction.OTPPIN}': 'userstore'}}\"\n"
                        f"realm = \"['*', '!{REALM_B}']\"\n")
        for name in ("imp_a", "imp_c", "imp_all"):
            delete_policy(name)
        # The file puts imp_b into realm_a, but the stored imp_b belongs to realm_b
        set_policy(name="imp_b", scope=SCOPE.AUTH, action=PolicyAction.OTPPIN + "=none", realm=REALM_B)
        self._restrict_to_realm_a()

        # As with tokens added to a container, the policies the admin may not write are skipped
        with self.app.test_request_context("/policy/import/policies.cfg", method="POST",
                                           data={"file": (BytesIO(policy_file.encode()), "policies.cfg")},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(1, res.json["result"]["value"])
        self.assertEqual({"imp_a", "imp_b"}, {p["name"] for p in get_policies() if p["name"].startswith("imp_")})
        imp_b = get_policies(name="imp_b")[0]
        self.assertEqual([REALM_B], imp_b["realm"])
        self.assertEqual({PolicyAction.OTPPIN: "none"}, imp_b["action"])

    def test_09_delete_realm(self):
        # Deleting a realm removes its resolvers, so each of them needs to be granted
        set_realm(REALM_A, [{"name": RESO_A}, {"name": RESO_FREE}])
        set_default_realm(REALM_B)
        set_policy(name="admin_realm_a", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_A, resolver=RESO_A)
        res = self._request(f"/realm/{REALM_A}", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertIn(REALM_A, get_realms())

        # Deleting a realm that is not the default realm does not need the right for the default realm
        set_policy(name="admin_realm_a", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_A, resolver="")
        res = self._request(f"/realm/{REALM_A}", "DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertNotIn(REALM_A, get_realms())
        self.assertEqual(REALM_B, get_default_realm())

        # Deleting the default realm needs the right for the whole realm
        set_realm(REALM_A, [{"name": RESO_A}])
        set_default_realm(REALM_A)
        set_policy(name="admin_realm_a", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_A, resolver=RESO_A)
        for spelling in (REALM_A, REALM_A.upper()):
            res = self._request(f"/realm/{spelling}", "DELETE")
            self.assertEqual(403, res.status_code, res.json)
        self.assertEqual(REALM_A, get_default_realm())
        set_policy(name="admin_realm_a", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_A, resolver="")
        res = self._request(f"/realm/{REALM_A}", "DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertNotIn(REALM_A, get_realms())

    def test_10_policies_without_realm_restriction(self):
        auth_action = PolicyAction.OTPPIN + "=userstore"
        set_policy(name="pol_b", scope=SCOPE.AUTH, action=auth_action, realm=REALM_B)
        set_policy(name="pol_all", scope=SCOPE.AUTH, action=auth_action)
        # An admin policy naming resolvers or users but no realm does not restrict the policies
        for restriction in ({"resolver": RESO_A, "user": ""}, {"resolver": "", "user": "operator"}):
            set_policy(name="admin_no_realm", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, **restriction)
            res = self._request("/policy/")
            self.assertEqual(200, res.status_code, res.json)
            self.assertEqual({"admin_no_realm", "pol_b", "pol_all"}, {p["name"] for p in res.json["result"]["value"]})
            res = self._request("/policy/pol_b", "POST", {"scope": SCOPE.AUTH, "action": auth_action})
            self.assertEqual(200, res.status_code, res.json)
            res = self._request("/policy/pol_new", "POST", {"scope": SCOPE.AUTH, "action": auth_action})
            self.assertEqual(200, res.status_code, res.json)
            res = self._request("/policy/pol_new", "DELETE")
            self.assertEqual(200, res.status_code, res.json)

        # The resolver configuration stays restricted to the named resolver
        set_policy(name="admin_no_realm", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, resolver=RESO_A, user="")
        res = self._request("/resolver/")
        self.assertEqual({RESO_A}, set(res.json["result"]["value"]))

    def test_11_realm_wildcard_and_empty_grant(self):
        auth_action = PolicyAction.OTPPIN + "=userstore"
        set_policy(name="pol_a", scope=SCOPE.AUTH, action=auth_action, realm=REALM_A)
        set_policy(name="pol_b", scope=SCOPE.AUTH, action=auth_action, realm=REALM_B)
        set_policy(name="pol_all", scope=SCOPE.AUTH, action=auth_action)

        # Every realm but realm_b grants the policies and resolvers of all other realms
        set_policy(name="admin_but_b", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=f"*,!{REALM_B}")
        res = self._request("/policy/")
        self.assertEqual({"pol_a", "pol_all", "admin_but_b"}, {p["name"] for p in res.json["result"]["value"]})
        res = self._request("/resolver/")
        self.assertEqual({RESO_A}, set(res.json["result"]["value"]))
        res = self._request("/policy/pol_b", "POST", {"scope": SCOPE.AUTH, "action": auth_action})
        self.assertEqual(403, res.status_code, res.json)

        # A realm field of nothing but an exclusion matches no realm, so it grants nothing
        set_policy(name="admin_but_b", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=f"!{REALM_B}")
        res = self._request("/policy/")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual([], res.json["result"]["value"])
        res = self._request("/resolver/")
        self.assertEqual({}, res.json["result"]["value"])
        res = self._request("/policy/pol_new", "POST", {"scope": SCOPE.AUTH, "action": auth_action,
                                                        "realm": REALM_A})
        self.assertEqual(403, res.status_code, res.json)
