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
        res = self._request("/resolver/")
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue({RESO_A, RESO_B, RESO_FREE} <= set(res.json["result"]["value"]))

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
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": f"{RESO_A},{RESO_B}"})
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual([RESO_A], [r["name"] for r in get_realms(REALM_A)[REALM_A]["resolver"]])
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": RESO_A})
        self.assertEqual(200, res.status_code, res.json)
        res = self._request(f"/realm/{REALM_B}", "POST", {"resolvers": RESO_B})
        self.assertEqual(403, res.status_code, res.json)

        # A resolver of the realm belongs to it, so a policy for the realm grants it
        set_realm(REALM_A, [{"name": RESO_A}, {"name": RESO_FREE}])
        res = self._request("/resolver/")
        self.assertEqual({RESO_A, RESO_FREE}, set(res.json["result"]["value"]))

        # A policy narrowed to one resolver of the realm changes nothing in it, not even a save that keeps it as it is
        set_policy(name="admin_realm_a", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_A, resolver=RESO_A)
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": RESO_A})
        self.assertEqual(403, res.status_code, res.json)
        for resolvers in (f"{RESO_A},{RESO_FREE}", f"{RESO_A}, {RESO_FREE}", f"{RESO_A},{RESO_FREE},"):
            res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": resolvers})
            self.assertEqual(403, res.status_code, resolvers)

        # Only the path names the realm and the node: a nodeid in the body or another spelling of the realm
        # does not hide the removal
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": RESO_A, "nodeid": "node_x"})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request(f"/realm/{REALM_A.upper()}", "POST", {"resolvers": RESO_A})
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual({RESO_A, RESO_FREE}, {r["name"] for r in get_realms(REALM_A)[REALM_A]["resolver"]})

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

        # Another spelling of the realm keeps the resolvers the request does not set
        set_realm(REALM_A, [{"name": RESO_A}, {"name": RESO_FREE, "node": NODE_UUID}])
        expected = {(RESO_A, ""), (RESO_FREE, NODE_UUID)}
        res = self._request(f"/realm/{REALM_A.upper()}", "POST", {"resolvers": RESO_A})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(expected, {(r["name"], r.get("node") or "") for r in get_realms(REALM_A)[REALM_A]["resolver"]})
        res = self._request(f"/realm/{REALM_A.upper()}/node/{NODE_UUID}", "POST",
                            json={"resolver": [{"name": RESO_FREE}]})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(expected, {(r["name"], r.get("node") or "") for r in get_realms(REALM_A)[REALM_A]["resolver"]})

    def test_04_default_realm(self):
        self._restrict_to_realm_a()
        res = self._request("/defaultrealm")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({REALM_A}, set(res.json["result"]["value"]))
        set_default_realm(REALM_B)
        res = self._request("/defaultrealm")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({}, res.json["result"]["value"])
        set_policy(name="admin_tokens_b", scope=SCOPE.ADMIN, action=PolicyAction.TOKENLIST, realm=REALM_B)
        res = self._request("/defaultrealm")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({}, res.json["result"]["value"])
        delete_policy("admin_tokens_b")
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

        check = f"user=someone&scope={SCOPE.AUTH}&action={PolicyAction.OTPPIN}"
        res = self._request(f"/policy/check?realm={REALM_A}&{check}")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({"pol_a", "pol_ab", "pol_all"}, {p["name"] for p in res.json["result"]["value"]["policy"]})
        # check_base_action reads only "realm", the endpoint any spelling of it
        for realms in (f"realm={REALM_B}", f"Realm={REALM_B}", f"realm={REALM_A}&Realm={REALM_B}",
                       f"realm={REALM_A},{REALM_B}"):
            res = self._request(f"/policy/check?{realms}&{check}")
            self.assertEqual(403, res.status_code, realms)

    def test_06_write_policies(self):
        auth_action = PolicyAction.OTPPIN + "=userstore"
        set_policy(name="pol_a", scope=SCOPE.AUTH, action=auth_action, realm=REALM_A)
        self._restrict_to_realm_a()

        # Policies apply to every realm, so a policy restricted to a realm does not grant writing them
        for method, url, data in (("POST", "/policy/pol_a", {"scope": SCOPE.AUTH, "action": auth_action}),
                                  ("POST", "/policy/pol_new", {"scope": SCOPE.AUTH, "action": auth_action,
                                                               "realm": REALM_A}),
                                  ("PATCH", "/policy/pol_a", {"name": "pol_a_renamed"}),
                                  ("POST", "/policy/disable/pol_a", None),
                                  ("POST", "/policy/enable/pol_a", None),
                                  ("DELETE", "/policy/pol_a", None)):
            res = self._request(url, method, data)
            self.assertEqual(403, res.status_code, (method, url, data))
        self.assertEqual(["pol_a"], [p["name"] for p in get_policies(scope=SCOPE.AUTH, active=True)])

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
        set_policy(name="imp_a", scope=SCOPE.AUTH, action=PolicyAction.OTPPIN + "=userstore", realm=REALM_A)
        policy_file = export_policies(get_policies(name="imp_a"))
        delete_policy("imp_a")
        self._restrict_to_realm_a()

        with self.app.test_request_context("/policy/import/policies.cfg", method="POST",
                                           data={"file": (BytesIO(policy_file.encode()), "policies.cfg")},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual([], get_policies(name="imp_a"))

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
        # An admin policy naming resolvers or users but no realm does not restrict reading the policies, but it does
        # not grant writing them
        for restriction in ({"resolver": RESO_A, "user": ""}, {"resolver": "", "user": "operator"}):
            set_policy(name="admin_no_realm", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, **restriction)
            res = self._request("/policy/")
            self.assertEqual(200, res.status_code, res.json)
            self.assertEqual({"admin_no_realm", "pol_b", "pol_all"}, {p["name"] for p in res.json["result"]["value"]})
            res = self._request("/policy/pol_b", "POST", {"scope": SCOPE.AUTH, "action": auth_action})
            self.assertEqual(403, res.status_code, res.json)

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
        res = self._request("/defaultrealm")
        self.assertEqual({REALM_A}, set(res.json["result"]["value"]))
        set_default_realm(REALM_B)
        res = self._request("/defaultrealm")
        self.assertEqual({}, res.json["result"]["value"])
        set_default_realm(REALM_A)
        res = self._request("/policy/pol_b", "POST", {"scope": SCOPE.AUTH, "action": auth_action})
        self.assertEqual(403, res.status_code, res.json)

        # A realm field of nothing but an exclusion matches no realm, so it grants nothing
        set_policy(name="admin_but_b", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=f"!{REALM_B}")
        res = self._request("/policy/")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual([], res.json["result"]["value"])
        res = self._request("/resolver/")
        self.assertEqual({}, res.json["result"]["value"])
        res = self._request("/defaultrealm")
        self.assertEqual({}, res.json["result"]["value"])
        res = self._request("/policy/pol_new", "POST", {"scope": SCOPE.AUTH, "action": auth_action,
                                                        "realm": REALM_A})
        self.assertEqual(403, res.status_code, res.json)

    def test_12_resolver_priority(self):
        set_realm(REALM_A, [{"name": RESO_A, "priority": 1}, {"name": RESO_FREE, "priority": 2}])
        set_policy(name="admin_realm_a", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_A, resolver=RESO_A)
        resolvers = f"{RESO_A},{RESO_FREE}"
        # The priority of a granted resolver decides whether it hides the users of the other one, so it may not be
        # changed either
        for priorities in ({f"priority.{RESO_A}": 1, f"priority.{RESO_FREE}": 3},
                           {f"priority.{RESO_A}": 1},
                           {f"priority.{RESO_A}": 3, f"priority.{RESO_FREE}": 2}):
            res = self._request(f"/realm/{REALM_A}", "POST", json=dict(priorities, resolvers=resolvers))
            self.assertEqual(403, res.status_code, priorities)
        self.assertEqual({RESO_A: 1, RESO_FREE: 2},
                         {r["name"]: r["priority"] for r in get_realms(REALM_A)[REALM_A]["resolver"]})

        set_policy(name="admin_realm_a", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_A, resolver="")
        res = self._request(f"/realm/{REALM_A}", "POST",
                            json={"resolvers": resolvers, f"priority.{RESO_A}": 3, f"priority.{RESO_FREE}": 2})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({RESO_A: 3, RESO_FREE: 2},
                         {r["name"]: r["priority"] for r in get_realms(REALM_A)[REALM_A]["resolver"]})

    def test_13_resolver_restricted_admin(self):
        realm_new = "realm_new"
        set_default_realm(REALM_B)
        set_policy(name="admin_reso_a", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, resolver=RESO_A)

        # A realm of granted resolvers only may be created and changed in every way
        res = self._request(f"/realm/{realm_new}", "POST", {"resolvers": RESO_A})
        self.assertEqual(200, res.status_code, res.json)
        res = self._request(f"/realm/{realm_new}", "POST", json={"resolvers": RESO_A, f"priority.{RESO_A}": 5})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({RESO_A: 5}, {r["name"]: r["priority"] for r in get_realms(realm_new)[realm_new]["resolver"]})
        res = self._request(f"/realm/{realm_new}", "POST", {"resolvers": f"{RESO_A},{RESO_B}"})
        self.assertEqual(403, res.status_code, res.json)

        # A realm with a resolver that is not granted can not be changed
        res = self._request(f"/realm/{REALM_B}", "POST", {"resolvers": f"{RESO_B},{RESO_A}"})
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual([RESO_B], [r["name"] for r in get_realms(REALM_B)[REALM_B]["resolver"]])

        # Also if the resolver that is not granted is part of the realm on another node only
        db.session.add(NodeName(id=NODE_UUID, name="realm_scope_node"))
        db.session.commit()
        set_realm(REALM_A, [{"name": RESO_A, "priority": 2}, {"name": RESO_FREE, "node": NODE_UUID}])
        res = self._request(f"/realm/{REALM_A}", "POST", json={"resolvers": RESO_A, f"priority.{RESO_A}": 1})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request(f"/realm/{REALM_A}", "POST", json={"resolvers": RESO_A, f"priority.{RESO_A}": 2})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request(f"/realm/{REALM_A}", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertIn(REALM_A, get_realms())

        res = self._request(f"/realm/{realm_new}", "DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertNotIn(realm_new, get_realms())
