"""
Admin policies restricted to realms or resolvers also restrict the configuration of resolvers, realms and the default
realm. Reading the policies is not restricted by them.
"""
from flask import Response

from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import set_policy, delete_policy, get_policies, SCOPE
from privacyidea.lib.realm import set_realm, get_realms, set_default_realm, get_default_realm, delete_realm
from privacyidea.lib.resolver import save_resolver, get_resolver_list, delete_resolver
from privacyidea.models import db, NodeName
from .base import MyApiTestCase, PWFILE

REALM_A = "realm_a"
REALM_B = "realm_b"
REALM_NEW = "realm_new"
REALM_DASHED = "realm-c"
RESO_A = "reso_a"
RESO_B = "reso_b"
RESO_FREE = "reso_free"
RESO_NEW = "reso_new"
NODE_UUID = "5b1e0f3c-7a43-4f0e-9a2d-1c6b8e2f4d71"
CONFIG_ACTIONS = ", ".join([PolicyAction.RESOLVERREAD, PolicyAction.RESOLVERWRITE, PolicyAction.RESOLVERDELETE,
                            PolicyAction.POLICYREAD, PolicyAction.POLICYWRITE, PolicyAction.POLICYDELETE])
AUTH_ACTION = PolicyAction.OTPPIN + "=userstore"
RESOLVER_CONFIG = {"type": "passwdresolver", "fileName": PWFILE}


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
        for realm in (REALM_NEW, REALM_DASHED):
            if realm in get_realms():
                delete_realm(realm)
        if RESO_NEW in get_resolver_list():
            set_realm(REALM_A, [{"name": RESO_A}])
            set_realm(REALM_B, [{"name": RESO_B}])
            delete_resolver(RESO_NEW)
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

    def _resolver_names(self, url: str = "/resolver/") -> set[str]:
        res = self._request(url)
        self.assertEqual(200, res.status_code, res.json)
        return set(res.json["result"]["value"])

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
        self.assertTrue({RESO_A, RESO_B, RESO_FREE} <= self._resolver_names())

    def test_02_resolver_list_shows_resolvers_of_granted_realm_and_without_realm(self) -> None:
        self._restrict_to_realm_a()
        self.assertEqual({RESO_A, RESO_FREE}, self._resolver_names())
        self.assertEqual(set(), self._resolver_names(f"/resolver/{RESO_B}"))

    def test_03_resolver_list_shows_resolver_added_to_granted_realm(self) -> None:
        self._restrict_to_realm_a()
        set_realm(REALM_A, [{"name": RESO_A}, {"name": RESO_B}])
        self.assertEqual({RESO_A, RESO_B, RESO_FREE}, self._resolver_names())

    def test_04_resolver_list_shows_resolver_named_without_realm(self) -> None:
        self._restrict_to_realm_a()
        set_policy(name="admin_reso_b", scope=SCOPE.ADMIN, action=PolicyAction.RESOLVERREAD, resolver=RESO_B)
        self.assertEqual({RESO_A, RESO_B, RESO_FREE}, self._resolver_names())

    def test_05_resolver_list_with_admin_policy_without_target_shows_every_resolver(self) -> None:
        self._restrict_to_realm_a()
        set_policy(name="admin_all", scope=SCOPE.ADMIN, action=PolicyAction.RESOLVERREAD)
        self.assertTrue({RESO_A, RESO_B, RESO_FREE} <= self._resolver_names())

    def test_06_resolver_grant_ignores_users_of_admin_policy(self) -> None:
        # The configuration of a user store is not bound to its users, so the policy grants what it grants without them
        self._grant(realm=REALM_A, user="*, !admin")
        self.assertEqual({RESO_A, RESO_FREE}, self._resolver_names())
        self.assertEqual({RESO_A}, self._resolver_names(f"/resolver/{RESO_A}"))
        res = self._request(f"/resolver/{RESO_A}", "POST", RESOLVER_CONFIG)
        self.assertEqual(200, res.status_code, res.json)
        res = self._request(f"/resolver/{RESO_B}", "POST", RESOLVER_CONFIG)
        self.assertEqual(403, res.status_code, res.json)
        self._grant(user="operator")
        self.assertTrue({RESO_A, RESO_B, RESO_FREE} <= self._resolver_names())

    def test_07_write_resolver_of_granted_realm(self) -> None:
        self._restrict_to_realm_a()
        res = self._request(f"/resolver/{RESO_A}", "POST", RESOLVER_CONFIG)
        self.assertEqual(200, res.status_code, res.json)

    def test_08_write_resolver_of_other_realm_refused(self) -> None:
        self._restrict_to_realm_a()
        # save_resolver updates a stored resolver whose name differs only in case
        for resolver in (RESO_B, RESO_B.upper()):
            res = self._request(f"/resolver/{resolver}", "POST", RESOLVER_CONFIG)
            self.assertEqual(403, res.status_code, resolver)
        self.assertNotIn(RESO_B.upper(), get_resolver_list())

    def test_09_realm_admin_creates_resolver_and_adds_it_to_granted_realm(self) -> None:
        self._restrict_to_realm_a()
        res = self._request(f"/resolver/{RESO_NEW}", "POST", RESOLVER_CONFIG)
        self.assertEqual(200, res.status_code, res.json)
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": f"{RESO_A},{RESO_NEW}"})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({RESO_A, RESO_NEW}, self._resolvers_of(REALM_A))
        res = self._request(f"/resolver/{RESO_NEW}", "POST", RESOLVER_CONFIG)
        self.assertEqual(200, res.status_code, res.json)

    def test_10_realm_admin_administers_resolver_without_realm(self) -> None:
        # A resolver that is part of no realm serves no user of another realm
        self._restrict_to_realm_a()
        res = self._request(f"/resolver/{RESO_FREE}", "POST", RESOLVER_CONFIG)
        self.assertEqual(200, res.status_code, res.json)
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": f"{RESO_A},{RESO_FREE}"})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({RESO_A, RESO_FREE}, self._resolvers_of(REALM_A))
        set_realm(REALM_B, [{"name": RESO_B}, {"name": RESO_FREE}])
        res = self._request(f"/resolver/{RESO_FREE}", "POST", RESOLVER_CONFIG)
        self.assertEqual(403, res.status_code, res.json)

    def test_11_delete_resolver_of_other_realm_refused(self) -> None:
        self._restrict_to_realm_a()
        res = self._request(f"/resolver/{RESO_B}", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertIn(RESO_B, get_resolver_list())

    def test_12_test_stored_resolver_needs_resolver_grant(self) -> None:
        # Testing a stored resolver uses its stored password
        self._restrict_to_realm_a()
        res = self._request("/resolver/test", "POST", dict(RESOLVER_CONFIG, resolver=RESO_B))
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/resolver/test", "POST", RESOLVER_CONFIG)
        self.assertEqual(200, res.status_code, res.json)

    def test_13_write_resolver_shared_with_other_realm_refused(self) -> None:
        set_realm(REALM_B, [{"name": RESO_B}, {"name": RESO_A}])
        self._restrict_to_realm_a()
        res = self._request(f"/resolver/{RESO_A}", "POST", RESOLVER_CONFIG)
        self.assertEqual(403, res.status_code, res.json)

    def test_14_resolver_wildcard_with_exclusion_creates_resolver(self) -> None:
        self._grant(resolver=f"*,!{RESO_B}")
        for _ in range(2):
            res = self._request(f"/resolver/{RESO_NEW}", "POST", RESOLVER_CONFIG)
            self.assertEqual(200, res.status_code, res.json)
        res = self._request(f"/resolver/{RESO_B}", "POST", RESOLVER_CONFIG)
        self.assertEqual(403, res.status_code, res.json)

    def test_15_realm_and_resolver_policy_adds_its_resolver_to_its_realm(self) -> None:
        self._grant(realm=REALM_A, resolver=f"{RESO_A},{RESO_FREE}")
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": f"{RESO_A},{RESO_FREE}"})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({RESO_A, RESO_FREE}, self._resolvers_of(REALM_A))
        # A named resolver of another realm is not granted by naming it for this realm
        set_realm(REALM_A, [{"name": RESO_A}])
        self._grant(realm=REALM_A, resolver=f"{RESO_A},{RESO_B}")
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": f"{RESO_A},{RESO_B}"})
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual({RESO_A}, self._resolvers_of(REALM_A))

    # Realms

    def test_16_realm_change_needs_realm_grant(self) -> None:
        self._restrict_to_realm_a()
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": RESO_A})
        self.assertEqual(200, res.status_code, res.json)
        res = self._request(f"/realm/{REALM_B}", "POST", {"resolvers": RESO_B})
        self.assertEqual(403, res.status_code, res.json)

    def test_17_realm_change_adding_resolver_of_other_realm_refused(self) -> None:
        self._restrict_to_realm_a()
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": f"{RESO_A},{RESO_B}"})
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual({RESO_A}, self._resolvers_of(REALM_A))

    def test_18_realm_change_refused_while_realm_has_resolver_not_granted(self) -> None:
        set_realm(REALM_A, [{"name": RESO_A}, {"name": RESO_FREE}])
        self._grant(realm=REALM_A, resolver=RESO_A)
        for resolvers in (RESO_A, f"{RESO_A},{RESO_FREE}", f"{RESO_A}, {RESO_FREE}", f"{RESO_A},{RESO_FREE},"):
            res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": resolvers})
            self.assertEqual(403, res.status_code, resolvers)
        self.assertEqual({RESO_A, RESO_FREE}, self._resolvers_of(REALM_A))

    def test_19_realm_change_reads_realm_and_node_from_path(self) -> None:
        set_realm(REALM_A, [{"name": RESO_A}, {"name": RESO_FREE}])
        self._grant(realm=REALM_A, resolver=RESO_A)
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": RESO_A, "nodeid": "node_x"})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request(f"/realm/{REALM_A.upper()}", "POST", {"resolvers": RESO_A})
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual({RESO_A, RESO_FREE}, self._resolvers_of(REALM_A))

    def test_20_excluded_realm_in_other_spelling_refused(self) -> None:
        # A realm is stored lowercase with "-" for every space, so "Realm C" is the realm "realm-c"
        self._add_node()
        set_realm(REALM_DASHED, [{"name": RESO_A}])
        self._grant(realm=f"*,!{REALM_DASHED}")
        for spelling in (REALM_DASHED, "realm%20c", "Realm%20C"):
            res = self._request(f"/realm/{spelling}", "POST", {"resolvers": f"{RESO_A},{RESO_FREE}"})
            self.assertEqual(403, res.status_code, spelling)
            res = self._request(f"/realm/{spelling}/node/{NODE_UUID}", "POST", json={"resolver": [{"name": RESO_FREE}]})
            self.assertEqual(403, res.status_code, spelling)
            res = self._request(f"/realm/{spelling}", "DELETE")
            self.assertEqual(403, res.status_code, spelling)
        self.assertEqual({(RESO_A, "")}, self._resolvers_with_node(REALM_DASHED))

    def test_21_realm_node_change_needs_resolver_grant(self) -> None:
        self._restrict_to_realm_a()
        self._add_node()
        url = f"/realm/{REALM_A}/node/{NODE_UUID}"
        res = self._request(url, "POST", json={"resolver": [{"name": RESO_B}]})
        self.assertEqual(403, res.status_code, res.json)
        res = self._request(url, "POST", json={"resolver": [{"name": RESO_A}]})
        self.assertEqual(200, res.status_code, res.json)

    def test_22_realm_node_change_without_resolver_name_refused_by_endpoint(self) -> None:
        self._restrict_to_realm_a()
        self._add_node()
        res = self._request(f"/realm/{REALM_A}/node/{NODE_UUID}", "POST", json={"resolver": [{"priority": 1}]})
        self.assertEqual(400, res.status_code, res.json)

    def test_23_realm_change_in_other_spelling_keeps_resolvers_of_other_node(self) -> None:
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

    def test_24_only_realm_becomes_default_realm_with_whole_realm_grant(self) -> None:
        # set_realm makes the only realm the default realm
        delete_realm(REALM_B)
        set_default_realm(None)
        self._grant(realm=REALM_A, resolver=RESO_A)
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": RESO_A})
        self.assertEqual(403, res.status_code, res.json)
        self.assertIsNone(get_default_realm())
        self._restrict_to_realm_a()
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": RESO_A})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(REALM_A, get_default_realm())

    def test_25_delete_realm_needs_grant_of_every_resolver(self) -> None:
        set_realm(REALM_A, [{"name": RESO_A}, {"name": RESO_FREE}])
        set_default_realm(REALM_B)
        self._grant(realm=REALM_A, resolver=RESO_A)
        res = self._request(f"/realm/{REALM_A}", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertIn(REALM_A, get_realms())

    def test_26_delete_realm_that_is_not_default_realm(self) -> None:
        set_default_realm(REALM_B)
        self._restrict_to_realm_a()
        res = self._request(f"/realm/{REALM_A}", "DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertNotIn(REALM_A, get_realms())
        self.assertEqual(REALM_B, get_default_realm())

    def test_27_delete_default_realm_needs_whole_realm_grant(self) -> None:
        self._grant(realm=REALM_A, resolver=RESO_A)
        for spelling in (REALM_A, REALM_A.upper()):
            res = self._request(f"/realm/{spelling}", "DELETE")
            self.assertEqual(403, res.status_code, res.json)
        self.assertEqual(REALM_A, get_default_realm())
        self._restrict_to_realm_a()
        set_policy(name="admin_write_b", scope=SCOPE.ADMIN, action=PolicyAction.RESOLVERWRITE, realm=REALM_B)
        res = self._request(f"/realm/{REALM_A}", "DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertNotIn(REALM_A, get_realms())

    def test_28_delete_default_realm_refused_when_promoted_realm_not_writable(self) -> None:
        self._restrict_to_realm_a()
        res = self._request(f"/realm/{REALM_A}", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertIn(REALM_A, get_realms())
        self.assertEqual(REALM_A, get_default_realm())

    def test_29_delete_realm_without_default_realm_promotes_remaining_realm(self) -> None:
        # delete_realm also makes the only remaining realm the default realm if there was none
        set_default_realm(None)
        self._restrict_to_realm_a()
        res = self._request(f"/realm/{REALM_A}", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertIn(REALM_A, get_realms())
        set_policy(name="admin_write_b", scope=SCOPE.ADMIN, action=PolicyAction.RESOLVERWRITE, realm=REALM_B)
        res = self._request(f"/realm/{REALM_A}", "DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(REALM_B, get_default_realm())

    def test_30_delete_realm_in_other_spelling(self) -> None:
        res = self._request(f"/realm/{REALM_B.upper()}", "DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertNotIn(REALM_B, get_realms())

    # Default realm

    def test_31_default_realm_shown_to_every_admin(self) -> None:
        self._restrict_to_realm_a()
        for default_realm in (REALM_A, REALM_B):
            set_default_realm(default_realm)
            res = self._request("/defaultrealm")
            self.assertEqual(200, res.status_code, res.json)
            self.assertEqual({default_realm}, set(res.json["result"]["value"]))

    def test_32_default_realm_change_needs_grant_of_current_default_realm(self) -> None:
        self._restrict_to_realm_a()
        set_default_realm(REALM_B)
        res = self._request(f"/defaultrealm/{REALM_A}", "POST")
        self.assertEqual(403, res.status_code, res.json)
        res = self._request("/defaultrealm", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual(REALM_B, get_default_realm())

    def test_33_default_realm_set_to_realm_not_granted_refused(self) -> None:
        self._restrict_to_realm_a()
        res = self._request(f"/defaultrealm/{REALM_B}", "POST")
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual(REALM_A, get_default_realm())

    def test_34_default_realm_delete_with_realm_grant(self) -> None:
        self._restrict_to_realm_a()
        res = self._request("/defaultrealm", "DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertIsNone(get_default_realm())

    def test_35_default_realm_delete_needs_whole_realm_grant(self) -> None:
        self._grant(realm=REALM_A, resolver=RESO_A)
        res = self._request("/defaultrealm", "DELETE")
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual(REALM_A, get_default_realm())

    def test_36_default_realm_set_to_partly_granted_realm_refused(self) -> None:
        self._restrict_to_realm_a()
        set_policy(name="admin_reso_b", scope=SCOPE.ADMIN, action=CONFIG_ACTIONS, realm=REALM_B, resolver=RESO_B)
        res = self._request(f"/defaultrealm/{REALM_B}", "POST")
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual(REALM_A, get_default_realm())

    def test_37_default_realm_name_read_as_stored_and_not_empty(self) -> None:
        res = self._request("/defaultrealm/%20", "POST")
        self.assertEqual(400, res.status_code, res.json)
        self.assertEqual(REALM_A, get_default_realm())
        set_realm(REALM_DASHED, [{"name": RESO_A}])
        for spelling, realm in ((REALM_B.upper(), REALM_B), ("Realm%20C", REALM_DASHED)):
            res = self._request(f"/defaultrealm/{spelling}", "POST")
            self.assertEqual(200, res.status_code, res.json)
            self.assertEqual(realm, get_default_realm())

    # Policies

    def test_38_policy_read_is_not_restricted_by_admin_policy_target(self) -> None:
        self._set_policies_of_realms()
        for target in ({"realm": REALM_A}, {"realm": f"!{REALM_B}"}, {"resolver": RESO_A}, {"user": "operator"}):
            self._grant(**target)
            self.assertEqual({"admin_config", "pol_a", "pol_b", "pol_all"}, self._policy_names(), target)
            res = self._request("/policy/pol_b")
            self.assertEqual(["pol_b"], [p["name"] for p in res.json["result"]["value"]], target)
            res = self._request("/policy/export/policies.cfg")
            self.assertEqual(200, res.status_code, target)
            self.assertIn("[pol_b]", res.get_data(as_text=True), target)

    def test_39_policy_check_in_granted_realm(self) -> None:
        self._set_policies_of_realms()
        set_policy(name="pol_ab", scope=SCOPE.AUTH, action=AUTH_ACTION, realm=f"{REALM_A},{REALM_B}")
        self._restrict_to_realm_a()
        res = self._request(f"/policy/check?realm={REALM_A}&user=someone&scope={SCOPE.AUTH}"
                            f"&action={PolicyAction.OTPPIN}")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({"pol_a", "pol_ab", "pol_all"}, {p["name"] for p in res.json["result"]["value"]["policy"]})

    # Admin policies without a target, with wildcards or with exclusions

    def test_40_admin_policy_without_target_is_unrestricted(self) -> None:
        self._grant()
        set_policy(name="pol_b", scope=SCOPE.AUTH, action=AUTH_ACTION, realm=REALM_B)
        self.assertTrue({RESO_A, RESO_B, RESO_FREE} <= self._resolver_names())
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": f"{RESO_A},{RESO_B}"})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual({"admin_config", "pol_b"}, self._policy_names())
        res = self._request("/policy/pol_b", "DELETE")
        self.assertEqual(200, res.status_code, res.json)

    def test_41_realm_wildcard_with_exclusion_grants_every_other_realm(self) -> None:
        self._grant(realm=f"*,!{REALM_B}")
        self.assertEqual({RESO_A, RESO_FREE}, self._resolver_names())
        res = self._request(f"/realm/{REALM_A}", "POST", {"resolvers": f"{RESO_A},{RESO_FREE}"})
        self.assertEqual(200, res.status_code, res.json)
        res = self._request(f"/realm/{REALM_B}", "POST", {"resolvers": RESO_B})
        self.assertEqual(403, res.status_code, res.json)

    def test_42_realm_field_of_exclusions_grants_nothing(self) -> None:
        self._grant(realm=f"!{REALM_B}")
        self.assertEqual(set(), self._resolver_names())
        res = self._request(f"/resolver/{RESO_FREE}", "POST", RESOLVER_CONFIG)
        self.assertEqual(403, res.status_code, res.json)

    # Admin policies that name resolvers only

    def test_43_resolver_admin_sees_granted_resolvers(self) -> None:
        self._grant(resolver=RESO_A)
        self.assertEqual({RESO_A}, self._resolver_names())

    def test_44_resolver_admin_changes_realm_of_granted_resolvers(self) -> None:
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

    def test_45_resolver_admin_cannot_change_realm_with_other_resolver(self) -> None:
        set_default_realm(REALM_B)
        self._grant(resolver=RESO_A)
        res = self._request(f"/realm/{REALM_B}", "POST", {"resolvers": f"{RESO_B},{RESO_A}"})
        self.assertEqual(403, res.status_code, res.json)
        self.assertEqual({RESO_B}, self._resolvers_of(REALM_B))

    def test_46_resolver_admin_cannot_change_realm_with_other_resolver_on_other_node(self) -> None:
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

    def test_47_resolver_admin_deletes_realm_of_granted_resolvers(self) -> None:
        set_default_realm(REALM_B)
        set_realm(REALM_NEW, [{"name": RESO_A}])
        self._grant(resolver=RESO_A)
        res = self._request(f"/realm/{REALM_NEW}", "DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertNotIn(REALM_NEW, get_realms())
