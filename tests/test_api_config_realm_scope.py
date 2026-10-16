"""
Admin policies restricted to a realm also restrict the configuration of resolvers, realms and policies.
"""
from io import BytesIO

from flask import Response

from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import set_policy, delete_policy, get_policies, export_policies, SCOPE
from privacyidea.lib.realm import set_realm, get_realms, set_default_realm, get_default_realm, delete_realm
from privacyidea.lib.resolver import save_resolver, get_resolver_list
from privacyidea.models import db, NodeName
from .base import MyApiTestCase, PWFILE

REALM_A = "realm_a"
REALM_B = "realm_b"
REALM_NEW = "realm_new"
RESO_A = "reso_a"
RESO_B = "reso_b"
RESO_FREE = "reso_free"
NODE_UUID = "5b1e0f3c-7a43-4f0e-9a2d-1c6b8e2f4d71"
CONFIG_ACTIONS = ", ".join([PolicyAction.RESOLVERREAD, PolicyAction.RESOLVERWRITE, PolicyAction.RESOLVERDELETE,
                            PolicyAction.POLICYREAD, PolicyAction.POLICYWRITE, PolicyAction.POLICYDELETE])
AUTH_ACTION = PolicyAction.OTPPIN + "=userstore"


class ConfigRealmScopeTestCase(MyApiTestCase):

    def setUp(self) -> None:
        super().setUp()
        for resolver in (RESO_A, RESO_B, RESO_FREE):
            save_resolver({"resolver": resolver, "type": "passwdresolver", "fileName": PWFILE})
        set_realm(REALM_A, [{"name": RESO_A}])
        set_realm(REALM_B, [{"name": RESO_B}])
        set_default_realm(REALM_A)

    def tearDown(self) -> None:
        for policy in get_policies():
            delete_policy(policy.get("name"))
        if REALM_NEW in get_realms():
            delete_realm(REALM_NEW)
        node = db.session.get(NodeName, NODE_UUID)
        if node:
            db.session.delete(node)
            db.session.commit()
        super().tearDown()

    def _request(self, url: str, method: str = "GET", data: dict | None = None,
                 json: dict | None = None) -> Response:
        kwargs = {"json": json} if json is not None else {"data": data or {}}
        with self.app.test_request_context(url, method=method, headers={"Authorization": self.at}, **kwargs):
            return self.app.full_dispatch_request()

    def _grant(self, **target: str) -> None:
        set_policy(name="admin_config", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS,
                   **{"realm": "", "resolver": "", "user": "", **target})

    def _restrict_to_realm_a(self) -> None:
        self._grant(realm=REALM_A)

    def _add_node(self) -> None:
        db.session.add(NodeName(id=NODE_UUID, name="realm_scope_node"))
        db.session.commit()

    def _resolvers_of(self, realm: str) -> set[str]:
        return {r["name"] for r in get_realms(realm)[realm]["resolver"]}

    def _resolvers_with_node(self, realm: str) -> set[tuple[str, str]]:
        return {(r["name"], r.get("node") or "") for r in get_realms(realm)[realm]["resolver"]}

    def _policy_names(self) -> set[str]:
        res = self._request("/policy/")
        self.assertEqual(200, res.status_code, res.json)
        return {p["name"] for p in res.json["result"]["value"]}

    def _set_policies_of_realms(self) -> None:
        set_policy(name="pol_a", scope=SCOPE.AUTH, action=AUTH_ACTION, realm=REALM_A)
        set_policy(name="pol_b", scope=SCOPE.AUTH, action=AUTH_ACTION, realm=REALM_B)
        set_policy(name="pol_all", scope=SCOPE.AUTH, action=AUTH_ACTION)

    # Resolvers

    def test_01_resolver_list_without_admin_policy_shows_every_resolver(self) -> None:
        res = self._request("/resolver/")
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue({RESO_A, RESO_B, RESO_FREE} <= set(res.json["result"]["value"]))

    def test_02_resolver_list_shows_resolvers_of_granted_realm(self) -> None:
        self._restrict_to_realm_a()
        res = self._request("/resolver/")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({RESO_A}, set(res.json["result"]["value"]))
        res = self._request(f"/resolver/{RESO_B}")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({}, res.json["result"]["value"])

    def test_03_resolver_list_shows_resolver_added_to_granted_realm(self) -> None:
        self._restrict_to_realm_a()
        set_realm(REALM_A, [{"name": RESO_A}, {"name": RESO_FREE}])
        res = self._request("/resolver/")
        self.assertEqual({RESO_A, RESO_FREE}, set(res.json["result"]["value"]))

    def test_04_resolver_list_shows_resolver_named_without_realm(self) -> None:
        self._restrict_to_realm_a()
        set_policy(name="admin_reso_free", scope=SCOPE.ADMIN, action=PolicyAction.RESOLVERREAD, resolver=RESO_FREE)
        res = self._request("/resolver/")
        self.assertEqual({RESO_A, RESO_FREE}, set(res.json["result"]["value"]))

    def test_05_resolver_list_with_admin_policy_without_target_shows_every_resolver(self) -> None:
        self._restrict_to_realm_a()
        set_policy(name="admin_all", scope=SCOPE.ADMIN, action=PolicyAction.RESOLVERREAD)
        res = self._request("/resolver/")
        self.assertTrue({RESO_A, RESO_B, RESO_FREE} <= set(res.json["result"]["value"]))

    def test_06_write_resolver_of_granted_realm(self) -> None:
        self._restrict_to_realm_a()
        res = self._request(f"/resolver/{RESO_A}", "POST", {"type": "passwdresolver", "fileName": PWFILE})
        self.assertEqual(200, res.status_code, res.json)

    def test_07_write_resolver_outside_granted_realm_refused(self) -> None:
        self._restrict_to_realm_a()
        for resolver in (RESO_B, RESO_FREE, "reso_new"):
            res = self._request(f"/resolver/{resolver}", "POST", {"type": "passwdresolver", "fileName": PWFILE})
            self.assertEqual(403, res.status_code, resolver)
        self.assertNotIn("reso_new", get_resolver_list())

    def test_08_delete_resolver_outside_granted_realm_refused(self) -> None:
        self._restrict_to_realm_a()
        res = self._request(f"/resolver/{RESO_FREE}", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertIn(RESO_FREE, get_resolver_list())

    def test_09_test_stored_resolver_needs_resolver_grant(self) -> None:
        # Testing a stored resolver uses its stored password
        self._restrict_to_realm_a()
        params = {"type": "passwdresolver", "fileName": PWFILE}
        res = self._request("/resolver/test", "POST", dict(params, resolver=RESO_B))
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/resolver/test", "POST", params)
        self.assertEqual(200, res.status_code, res.json)

    # Realms

    def test_10_realm_change_needs_realm_grant(self) -> None:
        self._restrict_to_realm_a()
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": RESO_A})
        self.assertEqual(200, res.status_code, res.json)
        res = self._request(f"/realm/{REALM_B}", "POST", {"resolvers": RESO_B})
        self.assertEqual(403, res.status_code, res.json)

    def test_11_realm_change_adding_resolver_of_other_realm_refused(self) -> None:
        self._restrict_to_realm_a()
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": f"{RESO_A},{RESO_B}"})
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual({RESO_A}, self._resolvers_of(REALM_A))

    def test_12_realm_change_refused_while_realm_has_resolver_not_granted(self) -> None:
        set_realm(REALM_A, [{"name": RESO_A}, {"name": RESO_FREE}])
        self._grant(realm=REALM_A, resolver=RESO_A)
        for resolvers in (RESO_A, f"{RESO_A},{RESO_FREE}", f"{RESO_A}, {RESO_FREE}", f"{RESO_A},{RESO_FREE},"):
            res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": resolvers})
            self.assertEqual(403, res.status_code, resolvers)
        self.assertEqual({RESO_A, RESO_FREE}, self._resolvers_of(REALM_A))

    def test_13_realm_change_reads_realm_and_node_from_path(self) -> None:
        set_realm(REALM_A, [{"name": RESO_A}, {"name": RESO_FREE}])
        self._grant(realm=REALM_A, resolver=RESO_A)
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": RESO_A, "nodeid": "node_x"})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request(f"/realm/{REALM_A.upper()}", "POST", {"resolvers": RESO_A})
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual({RESO_A, RESO_FREE}, self._resolvers_of(REALM_A))

    def test_14_realm_node_change_needs_resolver_grant(self) -> None:
        self._restrict_to_realm_a()
        self._add_node()
        url = f"/realm/{REALM_A}/node/{NODE_UUID}"
        res = self._request(url, "POST", json={"resolver": [{"name": RESO_B}]})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request(url, "POST", json={"resolver": [{"name": RESO_A}]})
        self.assertEqual(200, res.status_code, res.json)

    def test_15_realm_node_change_without_resolver_name_refused_by_endpoint(self) -> None:
        self._restrict_to_realm_a()
        self._add_node()
        res = self._request(f"/realm/{REALM_A}/node/{NODE_UUID}", "POST", json={"resolver": [{"priority": 1}]})
        self.assertEqual(400, res.status_code, res.json)

    def test_16_realm_change_in_other_spelling_keeps_resolvers_of_other_node(self) -> None:
        self._restrict_to_realm_a()
        self._add_node()
        set_realm(REALM_A, [{"name": RESO_A}, {"name": RESO_FREE, "node": NODE_UUID}])
        expected = {(RESO_A, ""), (RESO_FREE, NODE_UUID)}
        res = self._request(f"/realm/{REALM_A.upper()}", "POST", {"resolvers": RESO_A})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(expected, self._resolvers_with_node(REALM_A))
        res = self._request(f"/realm/{REALM_A.upper()}/node/{NODE_UUID}", "POST",
                            json={"resolver": [{"name": RESO_FREE}]})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(expected, self._resolvers_with_node(REALM_A))

    def test_17_delete_realm_needs_grant_of_every_resolver(self) -> None:
        set_realm(REALM_A, [{"name": RESO_A}, {"name": RESO_FREE}])
        set_default_realm(REALM_B)
        self._grant(realm=REALM_A, resolver=RESO_A)
        res = self._request(f"/realm/{REALM_A}", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertIn(REALM_A, get_realms())

    def test_18_delete_realm_that_is_not_default_realm(self) -> None:
        set_default_realm(REALM_B)
        self._restrict_to_realm_a()
        res = self._request(f"/realm/{REALM_A}", "DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertNotIn(REALM_A, get_realms())
        self.assertEqual(REALM_B, get_default_realm())

    def test_19_delete_default_realm_needs_whole_realm_grant(self) -> None:
        self._grant(realm=REALM_A, resolver=RESO_A)
        for spelling in (REALM_A, REALM_A.upper()):
            res = self._request(f"/realm/{spelling}", "DELETE")
            self.assertEqual(403, res.status_code, res.json)
        self.assertEqual(REALM_A, get_default_realm())
        self._restrict_to_realm_a()
        res = self._request(f"/realm/{REALM_A}", "DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertNotIn(REALM_A, get_realms())

    # Default realm

    def test_20_default_realm_shown_if_granted(self) -> None:
        self._restrict_to_realm_a()
        res = self._request("/defaultrealm")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({REALM_A}, set(res.json["result"]["value"]))

    def test_21_default_realm_hidden_without_resolverread_for_it(self) -> None:
        self._restrict_to_realm_a()
        set_default_realm(REALM_B)
        res = self._request("/defaultrealm")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({}, res.json["result"]["value"])
        set_policy(name="admin_tokens_b", scope=SCOPE.ADMIN, action=PolicyAction.TOKENLIST, realm=REALM_B)
        res = self._request("/defaultrealm")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({}, res.json["result"]["value"])

    def test_22_default_realm_change_needs_grant_of_current_default_realm(self) -> None:
        self._restrict_to_realm_a()
        set_default_realm(REALM_B)
        res = self._request(f"/defaultrealm/{REALM_A}", "POST")
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/defaultrealm", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual(REALM_B, get_default_realm())

    def test_23_default_realm_set_to_realm_not_granted_refused(self) -> None:
        self._restrict_to_realm_a()
        res = self._request(f"/defaultrealm/{REALM_B}", "POST")
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual(REALM_A, get_default_realm())

    def test_24_default_realm_delete_with_realm_grant(self) -> None:
        self._restrict_to_realm_a()
        res = self._request("/defaultrealm", "DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertIsNone(get_default_realm())

    def test_25_default_realm_delete_needs_whole_realm_grant(self) -> None:
        self._grant(realm=REALM_A, resolver=RESO_A)
        res = self._request("/defaultrealm", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual(REALM_A, get_default_realm())

    # Policies

    def test_26_policy_list_shows_policies_of_granted_realm(self) -> None:
        self._set_policies_of_realms()
        set_policy(name="pol_ab", scope=SCOPE.AUTH, action=AUTH_ACTION, realm=f"{REALM_A},{REALM_B}")
        self._restrict_to_realm_a()
        self.assertEqual({"pol_a", "pol_ab", "pol_all", "admin_config"}, self._policy_names())
        res = self._request("/policy/pol_b")
        self.assertEqual([], res.json["result"]["value"])

    def test_27_policy_export_contains_policies_of_granted_realm(self) -> None:
        self._set_policies_of_realms()
        self._restrict_to_realm_a()
        res = self._request("/policy/export/policies.cfg")
        self.assertEqual(200, res.status_code)
        exported = res.get_data(as_text=True)
        self.assertIn("[pol_a]", exported)
        self.assertIn("[pol_all]", exported)
        self.assertNotIn("[pol_b]", exported)

    def test_28_policy_check_in_granted_realm(self) -> None:
        self._set_policies_of_realms()
        set_policy(name="pol_ab", scope=SCOPE.AUTH, action=AUTH_ACTION, realm=f"{REALM_A},{REALM_B}")
        self._restrict_to_realm_a()
        res = self._request(f"/policy/check?realm={REALM_A}&user=someone&scope={SCOPE.AUTH}"
                            f"&action={PolicyAction.OTPPIN}")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({"pol_a", "pol_ab", "pol_all"}, {p["name"] for p in res.json["result"]["value"]["policy"]})

    def test_29_policy_check_in_other_realm_refused(self) -> None:
        self._restrict_to_realm_a()
        # check_base_action reads only "realm", the endpoint any spelling of it
        for realms in (f"realm={REALM_B}", f"Realm={REALM_B}", f"realm={REALM_A}&Realm={REALM_B}",
                       f"realm={REALM_A},{REALM_B}"):
            res = self._request(f"/policy/check?{realms}&user=someone&scope={SCOPE.AUTH}"
                                f"&action={PolicyAction.OTPPIN}")
            self.assertEqual(403, res.status_code, realms)

    def test_30_policy_write_refused_for_realm_admin(self) -> None:
        set_policy(name="pol_a", scope=SCOPE.AUTH, action=AUTH_ACTION, realm=REALM_A)
        self._restrict_to_realm_a()
        for method, url, data in (("POST", "/policy/pol_a", {"scope": SCOPE.AUTH, "action": AUTH_ACTION}),
                                  ("POST", "/policy/pol_new", {"scope": SCOPE.AUTH, "action": AUTH_ACTION,
                                                               "realm": REALM_A}),
                                  ("PATCH", "/policy/pol_a", {"name": "pol_a_renamed"}),
                                  ("POST", "/policy/disable/pol_a", None),
                                  ("POST", "/policy/enable/pol_a", None),
                                  ("DELETE", "/policy/pol_a", None)):
            res = self._request(url, method, data)
            self.assertEqual(403, res.status_code, (method, url, data))
        self.assertEqual(["pol_a"], [p["name"] for p in get_policies(scope=SCOPE.AUTH, active=True)])

    def test_31_policy_import_refused_for_realm_admin(self) -> None:
        set_policy(name="imp_a", scope=SCOPE.AUTH, action=AUTH_ACTION, realm=REALM_A)
        policy_file = export_policies(get_policies(name="imp_a"))
        delete_policy("imp_a")
        self._restrict_to_realm_a()
        with self.app.test_request_context("/policy/import/policies.cfg", method="POST",
                                           data={"file": (BytesIO(policy_file.encode()), "policies.cfg")},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual([], get_policies(name="imp_a"))

    def test_32_policy_list_with_admin_policy_without_realm(self) -> None:
        set_policy(name="pol_b", scope=SCOPE.AUTH, action=AUTH_ACTION, realm=REALM_B)
        set_policy(name="pol_all", scope=SCOPE.AUTH, action=AUTH_ACTION)
        for target in ({"resolver": RESO_A}, {"user": "operator"}):
            self._grant(**target)
            self.assertEqual({"admin_config", "pol_b", "pol_all"}, self._policy_names(), target)

    def test_33_policy_write_refused_for_admin_policy_without_realm(self) -> None:
        set_policy(name="pol_b", scope=SCOPE.AUTH, action=AUTH_ACTION, realm=REALM_B)
        for target in ({"resolver": RESO_A}, {"user": "operator"}):
            self._grant(**target)
            res = self._request("/policy/pol_b", "POST", {"scope": SCOPE.AUTH, "action": AUTH_ACTION})
            self.assertEqual(403, res.status_code, target)

    # Admin policies without a target, with wildcards or with exclusions

    def test_34_admin_policy_without_target_is_unrestricted(self) -> None:
        self._grant()
        set_policy(name="pol_b", scope=SCOPE.AUTH, action=AUTH_ACTION, realm=REALM_B)
        res = self._request("/resolver/")
        self.assertTrue({RESO_A, RESO_B, RESO_FREE} <= set(res.json["result"]["value"]))
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": f"{RESO_A},{RESO_B}"})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({"admin_config", "pol_b"}, self._policy_names())
        res = self._request("/policy/pol_b", "DELETE")
        self.assertEqual(200, res.status_code, res.json)

    def test_35_realm_wildcard_with_exclusion_grants_every_other_realm(self) -> None:
        self._set_policies_of_realms()
        self._grant(realm=f"*,!{REALM_B}")
        self.assertEqual({"pol_a", "pol_all", "admin_config"}, self._policy_names())
        res = self._request("/resolver/")
        self.assertEqual({RESO_A}, set(res.json["result"]["value"]))
        res = self._request("/defaultrealm")
        self.assertEqual({REALM_A}, set(res.json["result"]["value"]))
        set_default_realm(REALM_B)
        res = self._request("/defaultrealm")
        self.assertEqual({}, res.json["result"]["value"])

    def test_36_realm_wildcard_with_exclusion_does_not_grant_policy_write(self) -> None:
        set_policy(name="pol_b", scope=SCOPE.AUTH, action=AUTH_ACTION, realm=REALM_B)
        self._grant(realm=f"*,!{REALM_B}")
        res = self._request("/policy/pol_b", "POST", {"scope": SCOPE.AUTH, "action": AUTH_ACTION})
        self.assertEqual(403, res.status_code, res.json)

    def test_37_realm_field_of_exclusions_grants_nothing(self) -> None:
        self._set_policies_of_realms()
        self._grant(realm=f"!{REALM_B}")
        self.assertEqual(set(), self._policy_names())
        res = self._request("/resolver/")
        self.assertEqual({}, res.json["result"]["value"])
        res = self._request("/defaultrealm")
        self.assertEqual({}, res.json["result"]["value"])
        res = self._request("/policy/pol_new", "POST", {"scope": SCOPE.AUTH, "action": AUTH_ACTION,
                                                        "realm": REALM_A})
        self.assertEqual(403, res.status_code, res.json)

    # Admin policies that name resolvers only

    def test_38_resolver_admin_sees_granted_resolvers(self) -> None:
        self._grant(resolver=RESO_A)
        res = self._request("/resolver/")
        self.assertEqual({RESO_A}, set(res.json["result"]["value"]))

    def test_39_resolver_admin_changes_realm_of_granted_resolvers(self) -> None:
        set_default_realm(REALM_B)
        self._grant(resolver=RESO_A)
        res = self._request(f"/realm/{REALM_NEW}", "POST", {"resolvers": RESO_A})
        self.assertEqual(200, res.status_code, res.json)
        res = self._request(f"/realm/{REALM_NEW}", "POST", json={"resolvers": RESO_A, f"priority.{RESO_A}": 5})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({RESO_A: 5},
                         {r["name"]: r["priority"] for r in get_realms(REALM_NEW)[REALM_NEW]["resolver"]})
        res = self._request(f"/realm/{REALM_NEW}", "POST", {"resolvers": f"{RESO_A},{RESO_B}"})
        self.assertEqual(403, res.status_code, res.json)

    def test_40_resolver_admin_cannot_change_realm_with_other_resolver(self) -> None:
        set_default_realm(REALM_B)
        self._grant(resolver=RESO_A)
        res = self._request(f"/realm/{REALM_B}", "POST", {"resolvers": f"{RESO_B},{RESO_A}"})
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual({RESO_B}, self._resolvers_of(REALM_B))

    def test_41_resolver_admin_cannot_change_realm_with_other_resolver_on_other_node(self) -> None:
        set_default_realm(REALM_B)
        self._grant(resolver=RESO_A)
        self._add_node()
        set_realm(REALM_A, [{"name": RESO_A, "priority": 2}, {"name": RESO_FREE, "node": NODE_UUID}])
        for priority in (1, 2):
            res = self._request(f"/realm/{REALM_A}", "POST", json={"resolvers": RESO_A, f"priority.{RESO_A}": priority})
            self.assertEqual(403, res.status_code, priority)
        res = self._request(f"/realm/{REALM_A}", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertIn(REALM_A, get_realms())

    def test_42_resolver_admin_deletes_realm_of_granted_resolvers(self) -> None:
        set_default_realm(REALM_B)
        set_realm(REALM_NEW, [{"name": RESO_A}])
        self._grant(resolver=RESO_A)
        res = self._request(f"/realm/{REALM_NEW}", "DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertNotIn(REALM_NEW, get_realms())

    def test_43_default_realm_set_to_partly_granted_realm_refused(self) -> None:
        self._restrict_to_realm_a()
        set_policy(name="admin_reso_b", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_B, resolver=RESO_B)
        res = self._request(f"/defaultrealm/{REALM_B}", "POST")
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual(REALM_A, get_default_realm())

    def test_44_write_resolver_shared_with_other_realm_refused(self) -> None:
        set_realm(REALM_B, [{"name": RESO_B}, {"name": RESO_A}])
        self._restrict_to_realm_a()
        res = self._request(f"/resolver/{RESO_A}", "POST", {"type": "passwdresolver", "fileName": PWFILE})
        self.assertEqual(403, res.status_code, res.json)

    def test_45_policy_list_for_resolver_admin_shows_policies_of_granted_resolver(self) -> None:
        self._set_policies_of_realms()
        set_policy(name="pol_reso_a", scope=SCOPE.AUTH, action=AUTH_ACTION, resolver=RESO_A)
        set_policy(name="pol_reso_b", scope=SCOPE.AUTH, action=AUTH_ACTION, resolver=RESO_B)
        self._grant(resolver=RESO_A)
        self.assertEqual({"admin_config", "pol_a", "pol_b", "pol_all", "pol_reso_a"}, self._policy_names())

    def test_46_policy_list_for_user_admin_shows_every_policy(self) -> None:
        set_policy(name="pol_b", scope=SCOPE.AUTH, action=AUTH_ACTION, realm=REALM_B)
        set_policy(name="pol_reso_b", scope=SCOPE.AUTH, action=AUTH_ACTION, resolver=RESO_B)
        self._grant(user="operator")
        self.assertEqual({"admin_config", "pol_b", "pol_reso_b"}, self._policy_names())
