"""
This tests the module lib.utils.import_plan, which compares configuration data
to be imported (the format of ``pi-manage config export``) with the
configuration of this system and plans what an import changes.

API under test
--------------

``build_import_plan(data, types, name=None, replace=False, skip_invalid=False) -> list[TypePlan]``
    ``data`` is the parsed import data ``{typ: <exporter output>, ...}``, keys
    that are no registered import type (e.g. ``privacyIDEA_version``) are
    ignored. ``types`` is an iterable of type names, ``"all"`` in it selects
    every type. A ``TypePlan`` is returned for each type that is both selected
    and present in ``data`` (also when its value is empty), in import order
    (``IMPORT_FUNCTIONS`` sorted by ``prio``). ``name`` limits the plan to the
    entries with that name. ``data`` is not modified.

``TypePlan``
    * ``typ``: the type name, e.g. ``"policy"``
    * ``entries``: list of ``PlanEntry``
    * ``notes``: list of str, e.g. the note on ``config`` with ``replace=True``
    * ``warnings``: list of str, e.g. the admin policy warning on ``policy``
    * ``data``: the import data of the create and update entries, in the
      format the importer of the type takes (not asserted here)

``PlanEntry``
    * ``action``: one of ``"create"``, ``"update"``, ``"unchanged"``,
      ``"delete"``, ``"skip"``
    * ``key``: the name of the entry (dict key, ``name``, ``connectorname``
      or config key), for ``event`` the tuple ``(name, handlermodule)``
    * ``changed_fields``: sorted list of the names of the changed fields for
      ``update`` (nested as ``data.<KEY>``, ``options.<KEY>``), else empty
    * ``reason``: str for ``skip``, else None
    * ``target_id``: for a ``delete`` of an ``event`` or ``periodictask`` the
      id of the entry on this system, else None

    Without ``replace`` an entry that exists only on this system is not part of
    the plan. A value ``__CENSORED__`` counts as unchanged when the entry
    exists on this system.

``format_import_plan(plans) -> list[str]``
    One line per entry, no value of any field is ever printed::

          update smtpserver "smtp1": password, server
          create policy "newpol"
          unchanged realm "realm1"
          delete policy "oldpol"
          skip event "ev1" (UserNotification): 1 entry in the import, 2 on this system, use --replace

    i.e. ``"  {action} {typ} \\"{name}\\""``, for ``event`` followed by
    ``" ({handlermodule})"``, then ``": " + ", ".join(changed_fields)`` for an
    update with changed fields or ``": " + reason`` for a skip. Each note and
    each warning of a ``TypePlan`` is a line ``"  " + text``.

``DELETE_ORDER``
    Sequence of type names: the reverse import order, ``config`` may be left
    out (it is never deleted).
"""
import copy
from unittest import mock

from privacyidea.lib.caconnector import save_caconnector, delete_caconnector
from privacyidea.lib.config import set_privacyidea_config, delete_privacyidea_config
from privacyidea.lib.container import (init_container, set_container_realms, delete_container_by_serial,
                                       find_container_by_serial)
from privacyidea.lib.crypto import CENSORED
from privacyidea.lib.event import set_event, delete_event
from privacyidea.lib.machineresolver import (save_resolver as save_machine_resolver,
                                             delete_resolver as delete_machine_resolver)
from privacyidea.lib.periodictask import set_periodic_task, delete_periodic_task
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
from privacyidea.lib.privacyideaserver import add_privacyideaserver, delete_privacyideaserver
from privacyidea.lib.radiusserver import add_radius, delete_radius
from privacyidea.lib.realm import set_realm, delete_realm, get_default_realm, get_realms, set_default_realm
from privacyidea.lib.resolver import save_resolver, delete_resolver
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway, delete_smsgateway
from privacyidea.lib.smtpserver import add_smtpserver, delete_smtpserver
from privacyidea.lib.token import init_token, remove_token, get_realms_of_token
from privacyidea.lib.utils.export import EXPORT_FUNCTIONS, IMPORT_FUNCTIONS
from privacyidea.lib.utils.import_plan import (build_import_plan, format_import_plan, apply_import_plan,
                                               plan_has_changes, DELETE_ORDER, _ADAPTERS)
from privacyidea.models import Config, db
from .base import MyTestCase, PWFILE, PWFILE2

PREFIX = "imp-"
HTTP_SMS_PROVIDER = "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider"
REALM_RESOLVER = "imp-realmres"
CONFIG_NOTE = "System settings (type 'config') are not replaced: keys missing from the import are kept."
ADMIN_WARNING = ("Warning: after this import no active admin policy is left, "
                 "so every administrator may do everything.")
NO_DEFAULT_REALM_WARNING = ("Warning: after this import no realm is the default realm, "
                            "so a user who logs in without a realm is not found.")

# Exporters returning a list name their entries in this field, the others return a dict keyed by name.
LIST_NAME_FIELD = {"policy": "name", "event": "name", "periodictask": "name", "caconnector": "connectorname"}

# Order in which tearDown removes what the tests created (dependent objects first).
CLEANUP_ORDER = ["policy", "event", "periodictask", "privacyideaserver", "smsgateway", "caconnector",
                 "machineresolver", "smtpserver", "radiusserver", "realm", "config", "resolver"]


def _entry_name(typ, entry):
    return entry[LIST_NAME_FIELD[typ]]


def export(typ, names):
    """Export the entries of ``typ`` with the given names, as a deep copy safe to modify."""
    exported = copy.deepcopy(EXPORT_FUNCTIONS[typ]())
    if typ in LIST_NAME_FIELD:
        return [entry for entry in exported if _entry_name(typ, entry) in names]
    return {key: value for key, value in exported.items() if key in names}


def entry_of(typ, typ_data, name):
    """Return the entry with this name from the import data of one type."""
    if typ in LIST_NAME_FIELD:
        return next(entry for entry in typ_data if _entry_name(typ, entry) == name)
    return typ_data[name]


def delete_object(typ, name):
    """Delete the object of ``typ`` with this name from this system (all of them for event)."""
    if typ in ("event", "periodictask"):
        for entry in EXPORT_FUNCTIONS[typ]():
            if entry["name"] == name:
                (delete_event if typ == "event" else delete_periodic_task)(entry["id"])
        return
    {"policy": delete_policy,
     "privacyideaserver": delete_privacyideaserver,
     "smsgateway": delete_smsgateway,
     "caconnector": delete_caconnector,
     "machineresolver": delete_machine_resolver,
     "smtpserver": delete_smtpserver,
     "radiusserver": delete_radius,
     "realm": delete_realm,
     "config": delete_privacyidea_config,
     "resolver": delete_resolver}[typ](name)


def names_on_system(typ):
    exported = EXPORT_FUNCTIONS[typ]()
    if typ in LIST_NAME_FIELD:
        return {_entry_name(typ, entry) for entry in exported}
    return set(exported)


def names_folded_to(typ: str, name: str) -> set[str]:
    """The names on this system that a setter of ``typ`` takes for ``name`` (case-insensitive, as stored)."""
    return {stored for stored in names_on_system(typ) if stored.lower() == name.lower()}


def _set_realm(name):
    set_realm(name, resolvers=[{"name": REALM_RESOLVER}])


def _set_periodic_task(name):
    set_periodic_task(name, "*/5 * * * *", ["pi1"], "SimpleStats", options={"total_tokens": "True"})


def _change(container, key, value, field):
    container[key] = value
    return field


# The 11 types matched by name: how to create an entry on this system and how to change one in the
# import data. The change function returns the name of the changed field as the plan reports it.
NAME_KEYED_TYPES = {
    "resolver": (
        lambda n: save_resolver({"resolver": n, "type": "passwdresolver", "fileName": PWFILE}),
        lambda e: _change(e["data"], "fileName", PWFILE2, "data.fileName")),
    "realm": (
        _set_realm,
        lambda e: _change(e["resolver"][0], "priority", 7, "resolver")),
    "policy": (
        lambda n: set_policy(n, scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU),
        lambda e: _change(e, "priority", 5, "priority")),
    "periodictask": (
        _set_periodic_task,
        lambda e: _change(e, "interval", "*/10 * * * *", "interval")),
    "smtpserver": (
        lambda n: add_smtpserver(n, server="mail.example.org", password="smtp-pw"),
        lambda e: _change(e, "port", 587, "port")),
    "radiusserver": (
        lambda n: add_radius(n, server="radius.example.org", secret="radius-secret"),
        lambda e: _change(e, "port", 1645, "port")),
    "privacyideaserver": (
        lambda n: add_privacyideaserver(n, url="https://pi.example.org"),
        lambda e: _change(e, "url", "https://pi2.example.org", "url")),
    "smsgateway": (
        lambda n: set_smsgateway(n, HTTP_SMS_PROVIDER, options={"URL": "https://sms.example.org"}),
        lambda e: _change(e, "description", "changed by the import", "description")),
    "caconnector": (
        lambda n: save_caconnector({"caconnector": n, "type": "local",
                                    "cakey": "/opt/imp/key.pem", "cacert": "/opt/imp/cert.pem"}),
        lambda e: _change(e["data"], "cakey", "/opt/imp/other-key.pem", "data.cakey")),
    "machineresolver": (
        lambda n: save_machine_resolver({"name": n, "type": "hosts", "filename": "tests/testdata/hosts"}),
        lambda e: _change(e["data"], "filename", "/etc/imp-hosts", "data.filename")),
    "config": (
        lambda n: set_privacyidea_config(n, "value-1"),
        lambda e: _change(e, "Value", "value-2", "Value")),
}


def plain_name_types() -> list[str]:
    """The types whose plan compares names unchanged and which can be renamed by an import with --replace."""
    return [typ for typ, adapter in _ADAPTERS.items()
            if adapter.fold_name is str and typ in NAME_KEYED_TYPES and typ not in ("config", "caconnector")]


def rename_entry(typ: str, typ_data: list | dict, name: str, new_name: str) -> dict:
    """Give the entry with this name in the import data of one type the new name, return the entry."""
    entry = entry_of(typ, typ_data, name)
    if typ in LIST_NAME_FIELD:
        entry[LIST_NAME_FIELD[typ]] = new_name
    else:
        typ_data[new_name] = typ_data.pop(name)
    return entry


def add_entries(typ: str, typ_data: list | dict, more: list | dict) -> None:
    if typ in LIST_NAME_FIELD:
        typ_data.extend(more)
    else:
        typ_data.update(more)


def import_directly(typ: str, typ_data: list | dict) -> None:
    """Store the import data of one type with its importer, without a plan."""
    IMPORT_FUNCTIONS[typ]["func"](copy.deepcopy(typ_data))


class ImportPlanTestCase(MyTestCase):

    def tearDown(self):
        # Remove everything a test created, the database is shared by all tests of this class.
        for typ in CLEANUP_ORDER:
            for name in names_on_system(typ):
                if name.startswith(PREFIX):
                    delete_object(typ, name)
        super().tearDown()

    def _type_plan(self, plans, typ):
        matching = [plan for plan in plans if plan.typ == typ]
        self.assertEqual(1, len(matching), [plan.typ for plan in plans])
        return matching[0]

    def _by_key(self, type_plan):
        """Map key to entry, the keys of the entries must be unique."""
        entries = {entry.key: entry for entry in type_plan.entries}
        self.assertEqual(len(type_plan.entries), len(entries), type_plan.entries)
        return entries

    def test_01_plan_create_update_unchanged(self):
        save_resolver({"resolver": REALM_RESOLVER, "type": "passwdresolver", "fileName": PWFILE})
        for typ, (create, change) in NAME_KEYED_TYPES.items():
            with self.subTest(typ=typ):
                name_a, name_b, name_c = f"imp-{typ}-a", f"imp-{typ}-b", f"imp-{typ}-c"
                for name in (name_a, name_b, name_c):
                    create(name)
                data = {typ: export(typ, {name_a, name_b, name_c})}
                delete_object(typ, name_c)
                changed_field = change(entry_of(typ, data[typ], name_a))
                data_before = copy.deepcopy(data)

                plans = build_import_plan(data, [typ])
                self.assertEqual([typ], [plan.typ for plan in plans])
                entries = self._by_key(plans[0])
                self.assertEqual({name_a, name_b, name_c}, set(entries))
                self.assertEqual("update", entries[name_a].action)
                self.assertEqual([changed_field], entries[name_a].changed_fields)
                self.assertEqual("unchanged", entries[name_b].action)
                self.assertEqual([], entries[name_b].changed_fields)
                self.assertEqual("create", entries[name_c].action)
                # planning does not touch the import data
                self.assertEqual(data_before, data)

                # "all" selects the type as well
                self.assertEqual([typ], [plan.typ for plan in build_import_plan(data, ["all"])])

                # name limits the plan to this entry
                plans = build_import_plan(data, [typ], name=name_c)
                self.assertEqual([typ], [plan.typ for plan in plans])
                self.assertEqual([(name_c, "create")], [(e.key, e.action) for e in plans[0].entries])

                for name in (name_a, name_b):
                    delete_object(typ, name)

    def test_02_plan_event_groups_by_name_and_module(self):
        for name in ("imp-ev-same", "imp-ev-changed", "imp-ev-new", "imp-ev-multi", "imp-ev-ambig", "imp-ev-ambig"):
            set_event(name, ["token_init"], "UserNotification", "sendmail", conditions={})
        set_event("imp-ev-multi", ["token_init"], "Token", "set description", conditions={},
                  options={"description": "imp"})
        names = {"imp-ev-same", "imp-ev-changed", "imp-ev-new", "imp-ev-multi", "imp-ev-ambig"}
        exported = export("event", names)
        token_handler = next(e for e in exported if e["handlermodule"] == "Token")
        ambiguous_ids = sorted(e["id"] for e in exported if e["name"] == "imp-ev-ambig")
        self.assertEqual(2, len(ambiguous_ids))
        # The import holds the first of the two ambiguous handlers only, changed.
        data = {"event": [e for e in exported if e["id"] != ambiguous_ids[1]]}
        for entry in data["event"]:
            if entry["name"] == "imp-ev-changed":
                entry["ordering"] = 3
            if entry["name"] == "imp-ev-ambig":
                entry["ordering"] = 4
        # New on this system: imp-ev-new and the Token handler of imp-ev-multi
        delete_object("event", "imp-ev-new")
        delete_event(token_handler["id"])

        plans = build_import_plan(data, ["event"])
        self.assertEqual(["event"], [plan.typ for plan in plans])
        entries = self._by_key(plans[0])
        self.assertEqual({("imp-ev-same", "UserNotification"),
                          ("imp-ev-changed", "UserNotification"),
                          ("imp-ev-new", "UserNotification"),
                          ("imp-ev-multi", "UserNotification"),
                          ("imp-ev-multi", "Token"),
                          ("imp-ev-ambig", "UserNotification")}, set(entries))
        self.assertEqual("unchanged", entries[("imp-ev-same", "UserNotification")].action)
        changed = entries[("imp-ev-changed", "UserNotification")]
        self.assertEqual("update", changed.action)
        self.assertEqual(["ordering"], changed.changed_fields)
        self.assertEqual("create", entries[("imp-ev-new", "UserNotification")].action)
        # same name, other handler module: separate groups
        self.assertEqual("unchanged", entries[("imp-ev-multi", "UserNotification")].action)
        self.assertEqual("create", entries[("imp-ev-multi", "Token")].action)
        # 1 entry in the import, 2 on this system: skipped without replace
        ambiguous = entries[("imp-ev-ambig", "UserNotification")]
        self.assertEqual("skip", ambiguous.action)
        self.assertIn("use --replace", ambiguous.reason)

        lines = format_import_plan(plans)
        self.assertIn('  unchanged event "imp-ev-same" (UserNotification)', lines)
        self.assertIn('  update event "imp-ev-changed" (UserNotification): ordering', lines)
        self.assertIn('  create event "imp-ev-new" (UserNotification)', lines)
        self.assertIn('  unchanged event "imp-ev-multi" (UserNotification)', lines)
        self.assertIn('  create event "imp-ev-multi" (Token)', lines)
        self.assertIn('  skip event "imp-ev-ambig" (UserNotification): '
                      '1 entry in the import, 2 on this system, use --replace', lines)

        # With replace the first handler is updated and the second one deleted.
        plans = build_import_plan(data, ["event"], replace=True)
        type_plan = self._type_plan(plans, "event")
        ambiguous = [e for e in type_plan.entries if e.key == ("imp-ev-ambig", "UserNotification")]
        self.assertEqual(["delete", "update"], sorted(e.action for e in ambiguous))
        update = next(e for e in ambiguous if e.action == "update")
        self.assertEqual(["ordering"], update.changed_fields)
        delete = next(e for e in ambiguous if e.action == "delete")
        self.assertEqual(ambiguous_ids[1], delete.target_id)
        # every other group is in the import, nothing else is deleted or skipped
        others = {e.key: e.action for e in type_plan.entries if e.key[0] != "imp-ev-ambig"}
        self.assertEqual({("imp-ev-same", "UserNotification"): "unchanged",
                          ("imp-ev-changed", "UserNotification"): "update",
                          ("imp-ev-new", "UserNotification"): "create",
                          ("imp-ev-multi", "UserNotification"): "unchanged",
                          ("imp-ev-multi", "Token"): "create"}, others)
        lines = format_import_plan(plans)
        self.assertIn('  update event "imp-ev-ambig" (UserNotification): ordering', lines)
        self.assertIn('  delete event "imp-ev-ambig" (UserNotification)', lines)

    def test_03_plan_text_never_contains_values(self):
        save_resolver({"resolver": "imp-sec-ldap", "type": "ldapresolver",
                       "LDAPURI": "ldap://ldap.example.org", "LDAPBASE": "o=test",
                       "BINDDN": "cn=manager,ou=example,o=test", "BINDPW": "old-bindpw-4711",
                       "LOGINNAMEATTRIBUTE": "cn", "LDAPSEARCHFILTER": "(cn=*)",
                       "USERINFO": '{"username": "cn"}', "UIDTYPE": "DN"})
        add_smtpserver("imp-sec-smtp", server="mail.example.org", password="old-smtp-4711")
        add_radius("imp-sec-radius", server="radius.example.org", secret="old-radius-4711")
        set_smsgateway("imp-sec-sms", HTTP_SMS_PROVIDER,
                       options={"URL": "https://sms.example.org", "PASSWORD": "old-sms-4711"})
        set_privacyidea_config("imp-sec-config", "old-config-4711", typ="password")

        data = {"resolver": export("resolver", {"imp-sec-ldap"}),
                "smtpserver": export("smtpserver", {"imp-sec-smtp"}),
                "radiusserver": export("radiusserver", {"imp-sec-radius"}),
                "smsgateway": export("smsgateway", {"imp-sec-sms"}),
                "config": export("config", {"imp-sec-config"})}
        # the export holds the old secrets in clear text, so the plan has them to compare
        self.assertEqual("old-bindpw-4711", data["resolver"]["imp-sec-ldap"]["data"]["BINDPW"])
        self.assertEqual("old-config-4711", data["config"]["imp-sec-config"]["Value"])
        data["resolver"]["imp-sec-ldap"]["data"]["BINDPW"] = "new-bindpw-4712"
        data["smtpserver"]["imp-sec-smtp"]["password"] = "new-smtp-4712"
        data["radiusserver"]["imp-sec-radius"]["secret"] = "new-radius-4712"
        data["smsgateway"]["imp-sec-sms"]["options"]["PASSWORD"] = "new-sms-4712"
        data["config"]["imp-sec-config"]["Value"] = "new-config-4712"

        plans = build_import_plan(data, ["all"])
        expected = {"resolver": ("imp-sec-ldap", "data.BINDPW"),
                    "smtpserver": ("imp-sec-smtp", "password"),
                    "radiusserver": ("imp-sec-radius", "secret"),
                    "smsgateway": ("imp-sec-sms", "options.PASSWORD"),
                    "config": ("imp-sec-config", "Value")}
        self.assertEqual(set(expected), {plan.typ for plan in plans})
        lines = format_import_plan(plans)
        for typ, (name, field) in expected.items():
            entry = self._by_key(self._type_plan(plans, typ))[name]
            self.assertEqual("update", entry.action, typ)
            self.assertEqual([field], entry.changed_fields, typ)
            self.assertIn(f'  update {typ} "{name}": {field}', lines)
        text = "\n".join(lines)
        for secret in ("bindpw", "smtp-47", "radius-47", "sms-47", "config-47", "4711", "4712"):
            self.assertNotIn(secret, text)

        # A censored secret keeps the stored one, so it counts as unchanged.
        data["smtpserver"]["imp-sec-smtp"]["password"] = CENSORED
        data["radiusserver"]["imp-sec-radius"]["secret"] = CENSORED
        plans = build_import_plan(data, ["smtpserver", "radiusserver"])
        self.assertEqual("unchanged", self._by_key(self._type_plan(plans, "smtpserver"))["imp-sec-smtp"].action)
        self.assertEqual("unchanged",
                         self._by_key(self._type_plan(plans, "radiusserver"))["imp-sec-radius"].action)
        self.assertNotIn(CENSORED, "\n".join(format_import_plan(plans)))

    def test_04_replace_plans_deletes(self):
        # Deleting runs in reverse import order: policies and event handlers before realms,
        # realms before resolvers.
        self.assertLess(DELETE_ORDER.index("policy"), DELETE_ORDER.index("realm"))
        self.assertLess(DELETE_ORDER.index("event"), DELETE_ORDER.index("realm"))
        self.assertLess(DELETE_ORDER.index("realm"), DELETE_ORDER.index("resolver"))
        import_order = [typ for typ, _ in sorted(IMPORT_FUNCTIONS.items(), key=lambda item: item[1]["prio"])]
        self.assertEqual([typ for typ in reversed(import_order) if typ != "config"],
                         [typ for typ in DELETE_ORDER if typ != "config"])

        for name in ("imp-rep-keep", "imp-rep-drop", "imp-rep-drop2"):
            set_policy(name, scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU)
        save_resolver({"resolver": "imp-rep-res", "type": "passwdresolver", "fileName": PWFILE})
        set_privacyidea_config("imp-rep-cfg", "kept")
        policies = export("policy", {"imp-rep-keep"})

        # Every entry of an imported type that is missing from the import is deleted.
        plans = build_import_plan({"policy": policies}, ["all"], replace=True)
        self.assertEqual(["policy"], [plan.typ for plan in plans])
        self.assertEqual({"imp-rep-keep": "unchanged", "imp-rep-drop": "delete", "imp-rep-drop2": "delete"},
                         {e.key: e.action for e in plans[0].entries})
        lines = format_import_plan(plans)
        self.assertIn('  delete policy "imp-rep-drop"', lines)
        self.assertIn('  delete policy "imp-rep-drop2"', lines)
        self.assertIn('  unchanged policy "imp-rep-keep"', lines)

        # Without replace nothing is deleted.
        plans = build_import_plan({"policy": policies}, ["all"])
        self.assertEqual({"imp-rep-keep": "unchanged"}, {e.key: e.action for e in plans[0].entries})

        # An empty import of a type deletes all of its entries ...
        plans = build_import_plan({"policy": policies, "resolver": {}}, ["all"], replace=True)
        self.assertEqual({"imp-rep-res": "delete"},
                         {e.key: e.action for e in self._type_plan(plans, "resolver").entries})
        # ... but only if the type is selected.
        plans = build_import_plan({"policy": policies, "resolver": {}}, ["policy"], replace=True)
        self.assertEqual(["policy"], [plan.typ for plan in plans])
        plans = build_import_plan({"policy": policies}, ["resolver"], replace=True)
        self.assertEqual([], plans)

        # config is never replaced, the plan says so.
        config = export("config", {"imp-rep-cfg"})
        plans = build_import_plan({"config": config}, ["all"], replace=True)
        type_plan = self._type_plan(plans, "config")
        self.assertEqual({"imp-rep-cfg": "unchanged"}, {e.key: e.action for e in type_plan.entries})
        self.assertIn(CONFIG_NOTE, type_plan.notes)
        self.assertIn(f"  {CONFIG_NOTE}", format_import_plan(plans))
        plans = build_import_plan({"config": config}, ["all"])
        self.assertNotIn(CONFIG_NOTE, self._type_plan(plans, "config").notes)

        # name limits the deletion to this entry, and only if it is missing from the import.
        plans = build_import_plan({"policy": policies}, ["policy"], name="imp-rep-drop", replace=True)
        self.assertEqual([("imp-rep-drop", "delete")], [(e.key, e.action) for e in plans[0].entries])
        plans = build_import_plan({"policy": policies}, ["policy"], name="imp-rep-keep", replace=True)
        self.assertEqual([("imp-rep-keep", "unchanged")], [(e.key, e.action) for e in plans[0].entries])

        # Planning does not delete anything.
        self.assertEqual({"imp-rep-keep", "imp-rep-drop", "imp-rep-drop2"},
                         {n for n in names_on_system("policy") if n.startswith(PREFIX)})
        self.assertIn("imp-rep-res", names_on_system("resolver"))

    def test_05_plan_warns_when_no_active_admin_policy_remains(self):
        set_policy("imp-adm-pol", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE)
        admin_policy = export("policy", {"imp-adm-pol"})

        def warnings(data, replace):
            plans = build_import_plan(data, ["policy"], replace=replace)
            lines = format_import_plan(plans)
            warned = ADMIN_WARNING in self._type_plan(plans, "policy").warnings
            self.assertEqual(warned, f"  {ADMIN_WARNING}" in lines, lines)
            return warned

        # Deleting the last active admin policy opens the admin area: warn.
        self.assertTrue(warnings({"policy": []}, replace=True))
        # The admin policy is part of the import: no warning.
        self.assertFalse(warnings({"policy": admin_policy}, replace=True))
        # Without replace nothing is deleted: no warning.
        self.assertFalse(warnings({"policy": []}, replace=False))
        # Deactivating the last active admin policy: warn, also without replace.
        inactive = copy.deepcopy(admin_policy)
        inactive[0]["active"] = False
        self.assertTrue(warnings({"policy": inactive}, replace=False))
        self.assertTrue(warnings({"policy": inactive}, replace=True))

        # A system without an active admin policy has nothing to lose: no warning.
        delete_policy("imp-adm-pol")
        set_policy("imp-adm-auth", scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU)
        self.assertFalse(warnings({"policy": []}, replace=True))

    def test_06_replace_keeps_the_entries_of_a_type_whose_importer_failed(self):
        set_policy("imp-oldpol", scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU)
        add_smtpserver("imp-oldsmtp", server="mail.example.org")
        set_policy("imp-newpol", scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU)
        add_smtpserver("imp-newsmtp", server="mail2.example.org")
        data = {"policy": export("policy", {"imp-newpol"}),
                "smtpserver": export("smtpserver", {"imp-newsmtp"})}
        delete_policy("imp-newpol")
        delete_smtpserver("imp-newsmtp")

        plans = build_import_plan(data, ["policy", "smtpserver"], replace=True)
        errors = []

        def failing_importer(*args, **kwargs):
            raise Exception("importer failed")

        with mock.patch.dict(IMPORT_FUNCTIONS["policy"], {"func": failing_importer}):
            failed = apply_import_plan(plans, on_error=lambda typ, entry, exx: errors.append(typ))

        self.assertEqual(["policy"], failed)
        self.assertEqual(["policy"], errors)
        # The failed type is not replaced, so nothing of it is lost ...
        self.assertIn("imp-oldpol", names_on_system("policy"))
        self.assertNotIn("imp-newpol", names_on_system("policy"))
        # ... while a type whose importer worked is still replaced.
        self.assertNotIn("imp-oldsmtp", names_on_system("smtpserver"))
        self.assertIn("imp-newsmtp", names_on_system("smtpserver"))

    def test_07_failed_importer_is_rolled_back_before_the_next_type(self):
        data = {"config": {"imp-leakkey": {"Value": "v", "Type": "", "Description": ""}},
                "smtpserver": {"imp-leaksmtp": {"server": "mail.example.org"}}}
        plans = build_import_plan(data, ["config", "smtpserver"])

        def leaking_importer(*args, **kwargs):
            db.session.add(Config(Key="imp-leak", Value="x"))
            raise Exception("importer failed after a write")

        with mock.patch.dict(IMPORT_FUNCTIONS["config"], {"func": leaking_importer}):
            failed = apply_import_plan(plans)

        self.assertEqual(["config"], failed)
        # The commit of the smtpserver importer must not store the write of the failed importer.
        self.assertIn("imp-leaksmtp", names_on_system("smtpserver"))
        leaked = db.session.execute(db.select(Config).where(Config.Key == "imp-leak")).scalars().all()
        self.assertEqual([], leaked)

    def test_08_names_are_matched_like_the_setters_match_them(self):
        # The setters store a realm lowercase with "-" for blanks and find a resolver or machine
        # resolver case-insensitively, so the plan must match the import entries the same way.
        # Otherwise replace plans a create for the variant and a delete for the existing object.
        cases = [("realm", "imp-case-realm", lambda n: n.upper()),
                 ("realm", "imp-case-realm2", lambda n: n.replace("-", " ")),
                 ("resolver", "imp-case-resolver", lambda n: n.upper()),
                 ("machineresolver", "imp-case-machres", lambda n: n.upper())]
        for typ, name, make_variant in cases:
            with self.subTest(typ=typ, variant=make_variant(name)):
                if typ == "realm":
                    save_resolver({"resolver": REALM_RESOLVER, "type": "passwdresolver", "fileName": PWFILE})
                create, change = NAME_KEYED_TYPES[typ]
                create(name)
                # the import contains everything of this system, the entry under test with a variant key
                data = {typ: export(typ, names_on_system(typ))}
                entry = data[typ].pop(name)
                change(entry)
                variant = make_variant(name)
                self.assertNotEqual(name, variant)
                data[typ][variant] = entry

                plans = build_import_plan(data, [typ], replace=True)
                actions = [(e.key, e.action) for e in self._type_plan(plans, typ).entries]
                self.assertEqual(1, len([a for _, a in actions if a == "update"]), actions)
                self.assertEqual([], [key for key, a in actions if a == "delete"], actions)

                apply_import_plan(plans)
                self.assertIn(name, names_on_system(typ))

    def test_09_replace_deletes_entries_with_a_mixed_case_name(self):
        # The delete functions of resolvers find an object by its stored name, so the plan has to hand them that
        # name and not the folded one it matches with.
        for typ, name in (("resolver", "imp-MixedCase-Res"), ("machineresolver", "imp-MixedCase-Machres")):
            with self.subTest(typ=typ):
                NAME_KEYED_TYPES[typ][0](name)
                self.assertIn(name, names_on_system(typ))
                keep = names_on_system(typ) - {name}
                plans = build_import_plan({typ: export(typ, keep)}, [typ], replace=True)

                failed = apply_import_plan(plans)

                self.assertEqual([], failed)
                self.assertNotIn(name, names_on_system(typ))

    def _default_realm_scenario(self, import_default: bool) -> dict:
        """Create the default realm a and the realm b, return import data holding only b."""
        save_resolver({"resolver": REALM_RESOLVER, "type": "passwdresolver", "fileName": PWFILE})
        _set_realm("imp-default-a")
        _set_realm("imp-default-b")
        set_default_realm("imp-default-a")
        data = {"realm": export("realm", {"imp-default-b"})}
        entry_of("realm", data["realm"], "imp-default-b")["default"] = import_default
        return data

    def test_10_replace_makes_the_default_realm_follow_the_import(self):
        data = self._default_realm_scenario(import_default=False)
        self.assertEqual("imp-default-a", get_default_realm())

        for run in (1, 2):
            with self.subTest(run=run):
                plans = build_import_plan(data, ["realm"], replace=True)
                lines = format_import_plan(plans)
                if run == 1:
                    self.assertIn('  default realm: "imp-default-a" -> none', lines)
                    self.assertIn(f"  {NO_DEFAULT_REALM_WARNING}", lines)
                if run == 2:
                    self.assertEqual({"imp-default-b": "unchanged"},
                                     {e.key: e.action for e in self._type_plan(plans, "realm").entries})
                    # there is no default realm to lose any more
                    self.assertNotIn(f"  {NO_DEFAULT_REALM_WARNING}", lines)
                self.assertEqual([], apply_import_plan(plans))
                self.assertNotIn("imp-default-a", get_realms())
                self.assertIn("imp-default-b", get_realms())
                self.assertFalse(get_default_realm())

    def test_11_replace_keeps_the_default_realm_of_the_import(self):
        data = self._default_realm_scenario(import_default=True)

        for run in (1, 2):
            with self.subTest(run=run):
                plans = build_import_plan(data, ["realm"], replace=True)
                self.assertEqual([], apply_import_plan(plans))
                self.assertNotIn("imp-default-a", get_realms())
                self.assertEqual("imp-default-b", get_default_realm())

    def test_12_import_without_replace_leaves_the_default_realm(self):
        data = self._default_realm_scenario(import_default=False)

        for run in (1, 2):
            with self.subTest(run=run):
                plans = build_import_plan(data, ["realm"])
                self.assertEqual({"imp-default-b": "unchanged"},
                                 {e.key: e.action for e in self._type_plan(plans, "realm").entries})
                self.assertEqual([], apply_import_plan(plans))
                self.assertIn("imp-default-a", get_realms())
                self.assertEqual("imp-default-a", get_default_realm())

    def test_13_name_filter_matches_the_folded_name(self):
        # The setters find a resolver or machine resolver case-insensitively and store a realm lowercase with "-"
        # for blanks, so a name given to limit the import has to select the entry of the import the same way.
        save_resolver({"resolver": REALM_RESOLVER, "type": "passwdresolver", "fileName": PWFILE})
        cases = [("resolver", "imp-N-Res", "imp-n-res"),
                 ("resolver", "imp-N-Res", "IMP-N-RES"),
                 ("realm", "imp-n-realm", "IMP-N-Realm"),
                 ("realm", "imp-n-realm", " imp n realm"),
                 ("machineresolver", "imp-N-Mres", "imp-n-mres")]
        for typ, stored, name in cases:
            with self.subTest(typ=typ, name=name):
                NAME_KEYED_TYPES[typ][0](stored)
                data = {typ: export(typ, {stored})}
                delete_object(typ, stored)
                self.assertEqual(set(), names_folded_to(typ, stored))

                plans = build_import_plan(data, [typ], name=name)
                self.assertEqual(["create"], [e.action for e in self._type_plan(plans, typ).entries])
                self.assertEqual([], apply_import_plan(plans, name=name))
                self.assertEqual({stored}, names_folded_to(typ, stored))
                delete_object(typ, stored)

    def test_14_replace_with_a_folded_name_keeps_the_entry_of_the_import(self):
        save_resolver({"resolver": REALM_RESOLVER, "type": "passwdresolver", "fileName": PWFILE})
        for typ, stored, name in (("resolver", "imp-N-Res", "imp-n-res"), ("realm", "imp-n-realm", "IMP-N-Realm")):
            with self.subTest(typ=typ, name=name):
                NAME_KEYED_TYPES[typ][0](stored)
                data = {typ: export(typ, {stored})}

                plans = build_import_plan(data, [typ], name=name, replace=True)
                self.assertEqual(["unchanged"], [e.action for e in self._type_plan(plans, typ).entries])
                self.assertEqual([], apply_import_plan(plans, name=name))
                self.assertEqual({stored}, names_folded_to(typ, stored))

    def _assert_one_entry_as_imported(self, typ: str, data: dict, name: str, field: str) -> None:
        """Exactly one entry named like ``name`` regardless of case is left, and importing again changes nothing."""
        stored = names_folded_to(typ, name)
        self.assertEqual(1, len(stored), stored)
        stored_entry = entry_of(typ, export(typ, stored), next(iter(stored)))
        self.assertEqual(entry_of(typ, data[typ], name)[field], stored_entry[field])
        plans = build_import_plan(copy.deepcopy(data), [typ], replace=True)
        actions = [(e.key, e.action) for e in self._type_plan(plans, typ).entries]
        self.assertEqual({"unchanged"}, {action for _, action in actions}, actions)

    def test_15_replace_with_a_case_variant_of_a_name_keeps_one_entry(self):
        # On databases that compare names case-insensitively the setter updates the stored entry for the variant,
        # so a planned delete of the stored name would remove the entry that was just imported.
        for typ in plain_name_types():
            with self.subTest(typ=typ):
                create, change = NAME_KEYED_TYPES[typ]
                stored, variant = f"imp-variant-{typ}", f"imp-Variant-{typ}"
                create(stored)
                data = {typ: export(typ, names_on_system(typ))}
                field = change(rename_entry(typ, data[typ], stored, variant))

                plans = build_import_plan(copy.deepcopy(data), [typ], replace=True)
                self.assertEqual([], apply_import_plan(plans))
                self._assert_one_entry_as_imported(typ, data, variant, field)

    def test_16_replace_with_one_of_two_case_variants_keeps_the_imported_one(self):
        # Where the database allows both names, the entry that differs from the import only in case is a
        # different entry and has to go, where it does not, both names are the same entry.
        for typ in plain_name_types():
            with self.subTest(typ=typ):
                create, change = NAME_KEYED_TYPES[typ]
                lower, upper = f"imp-pair-{typ}", f"imp-Pair-{typ}"
                create(lower)
                upper_data = export(typ, {lower})
                rename_entry(typ, upper_data, lower, upper)
                lower_data = export(typ, {lower})
                change(entry_of(typ, lower_data, lower))
                import_directly(typ, lower_data)
                import_directly(typ, upper_data)

                data = {typ: export(typ, names_on_system(typ) - names_folded_to(typ, lower))}
                imported = copy.deepcopy(upper_data)
                field = change(entry_of(typ, imported, upper))
                add_entries(typ, data[typ], imported)

                plans = build_import_plan(copy.deepcopy(data), [typ], replace=True)
                self.assertEqual([], apply_import_plan(plans))
                self._assert_one_entry_as_imported(typ, data, upper, field)

    def test_17_replace_with_a_folded_name_deletes_only_the_named_entry(self):
        save_resolver({"resolver": REALM_RESOLVER, "type": "passwdresolver", "fileName": PWFILE})
        cases = [("resolver", "imp-Gone-Res", "IMP-GONE-RES"),
                 ("realm", "imp-gone-realm", "IMP-Gone-Realm"),
                 ("realm", "imp-gone-realm", " imp gone realm"),
                 ("machineresolver", "imp-Gone-Mres", "imp-gone-MRES")]
        for typ, stored, name in cases:
            with self.subTest(typ=typ, name=name):
                create = NAME_KEYED_TYPES[typ][0]
                kept = f"imp-stays-{typ}"
                create(stored)
                create(kept)
                data = {typ: export(typ, names_on_system(typ) - {stored, kept})}

                plans = build_import_plan(data, [typ], name=name, replace=True)
                self.assertEqual(["delete"], [e.action for e in self._type_plan(plans, typ).entries])
                self.assertEqual([], apply_import_plan(plans, name=name))
                self.assertEqual(set(), names_folded_to(typ, stored))
                self.assertEqual({kept}, names_folded_to(typ, kept))
                delete_object(typ, kept)

    def test_18_folded_name_updates_the_stored_entry(self):
        save_resolver({"resolver": REALM_RESOLVER, "type": "passwdresolver", "fileName": PWFILE})
        changed_value = {"resolver": lambda e: e["data"]["fileName"],
                         "realm": lambda e: e["resolver"][0]["priority"],
                         "machineresolver": lambda e: e["data"]["filename"]}
        cases = [("resolver", "imp-Upd-Res", "IMP-UPD-res"),
                 ("realm", "imp-upd-realm", "Imp-Upd-REALM"),
                 ("realm", "imp-upd-realm", "imp upd realm "),
                 ("machineresolver", "imp-Upd-Mres", "IMP-upd-mres")]
        for typ, stored, name in cases:
            with self.subTest(typ=typ, name=name):
                create, change = NAME_KEYED_TYPES[typ]
                create(stored)
                data = {typ: export(typ, {stored})}
                imported = entry_of(typ, data[typ], stored)
                field = change(imported)

                plans = build_import_plan(copy.deepcopy(data), [typ], name=name)
                entries = self._type_plan(plans, typ).entries
                self.assertEqual([("update", [field])], [(e.action, e.changed_fields) for e in entries])
                self.assertEqual([], apply_import_plan(plans, name=name))
                on_system = names_folded_to(typ, stored)
                self.assertEqual(1, len(on_system), on_system)
                stored_entry = entry_of(typ, export(typ, on_system), next(iter(on_system)))
                self.assertEqual(changed_value[typ](imported), changed_value[typ](stored_entry))
                delete_object(typ, next(iter(on_system)))

    def test_19_realm_not_marked_as_default_keeps_its_default(self):
        # Only --replace without -n removes the default realm. A plain import, or one limited with -n, of the
        # default realm marked as not default must not leave the system without a default realm.
        save_resolver({"resolver": REALM_RESOLVER, "type": "passwdresolver", "fileName": PWFILE})
        _set_realm("imp-default-a")
        _set_realm("imp-default-b")
        set_default_realm("imp-default-a")
        data = {"realm": export("realm", {"imp-default-a"})}
        entry = entry_of("realm", data["realm"], "imp-default-a")
        entry["default"] = False
        cases = [(None, False), ("imp-default-a", False), ("IMP-Default-A", False), ("imp-default-a", True)]
        for priority, (name, replace) in enumerate(cases, start=3):
            with self.subTest(name=name, replace=replace):
                # a changed resolver priority makes the importer of the realm run
                entry["resolver"][0]["priority"] = priority

                plans = build_import_plan(data, ["realm"], name=name, replace=replace)
                type_plan = self._type_plan(plans, "realm")
                self.assertEqual([("imp-default-a", "update", ["resolver"])],
                                 [(e.key, e.action, e.changed_fields) for e in type_plan.entries])
                lines = format_import_plan(plans)
                self.assertEqual([], [line for line in lines if "default realm" in line], lines)
                self.assertEqual([], apply_import_plan(plans, name=name))
                self.assertEqual("imp-default-a", get_default_realm())

    def test_20_realm_marked_as_default_becomes_the_default_realm(self):
        # Also without --replace and with -n. The importer does not run for the unchanged realm, so the plan sets
        # the default realm itself.
        data = self._default_realm_scenario(import_default=True)
        for name in (None, "imp-default-b"):
            with self.subTest(name=name):
                set_default_realm("imp-default-a")

                plans = build_import_plan(data, ["realm"], name=name)
                self.assertEqual({"imp-default-b": "unchanged"},
                                 {e.key: e.action for e in self._type_plan(plans, "realm").entries})
                self.assertIn('  default realm: "imp-default-a" -> "imp-default-b"', format_import_plan(plans))
                self.assertTrue(plan_has_changes(plans))
                self.assertEqual([], apply_import_plan(plans, name=name))
                self.assertEqual("imp-default-b", get_default_realm())
                self.assertIn("imp-default-a", get_realms())

                # the same import again changes nothing
                self.assertFalse(plan_has_changes(build_import_plan(data, ["realm"], name=name)))

    def test_21_default_realm_on_a_system_without_realms(self):
        # set_realm() makes the first realm the default realm, so the plan shows it, also if the file marks no
        # realm as default. With --replace the default realm follows the file, so no realm is the default realm.
        save_resolver({"resolver": REALM_RESOLVER, "type": "passwdresolver", "fileName": PWFILE})
        resolvers = [{"name": REALM_RESOLVER, "priority": None, "node": ""}]
        data = {"realm": {"imp-first-a": {"default": False, "resolver": resolvers},
                          "imp-first-b": {"default": False, "resolver": resolvers}}}

        for replace, default_realm in ((False, "imp-first-a"), (True, None)):
            with self.subTest(replace=replace):
                self.assertEqual({}, get_realms())
                plans = build_import_plan(data, ["realm"], replace=replace)
                lines = format_import_plan(plans)
                if default_realm:
                    self.assertIn(f'  default realm: none -> "{default_realm}"', lines)
                else:
                    # The system has no default realm before and after the import, so the plan has no line and no
                    # warning about it.
                    self.assertEqual([], [line for line in lines if "default realm" in line], lines)
                self.assertEqual([], apply_import_plan(plans))
                self.assertEqual(default_realm, get_default_realm() or None)
                self.assertFalse(plan_has_changes(build_import_plan(data, ["realm"], replace=replace)))
                for name in data["realm"]:
                    delete_realm(name)

    def test_22_replace_keeps_a_realm_that_contains_tokens_or_containers(self):
        # delete_realm() only refuses a realm whose users own tokens or containers. The import keeps a realm that
        # contains other tokens or containers as well, they would lose the realm.
        save_resolver({"resolver": REALM_RESOLVER, "type": "passwdresolver", "fileName": PWFILE})
        for name in ("imp-tok-realm", "imp-cont-realm", "imp-keep-realm"):
            _set_realm(name)
        init_token({"type": "spass", "serial": "IMP-TOK-1"}, tokenrealms=["imp-tok-realm"])
        self.addCleanup(remove_token, "IMP-TOK-1")
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.addCleanup(delete_container_by_serial, container_serial)
        set_container_realms(container_serial, ["imp-cont-realm"])
        data = {"realm": export("realm", {"imp-keep-realm"})}

        plans = build_import_plan(data, ["realm"], replace=True)
        self.assertEqual({"imp-keep-realm": "unchanged", "imp-tok-realm": "delete", "imp-cont-realm": "delete"},
                         {e.key: e.action for e in self._type_plan(plans, "realm").entries})
        errors = {}
        failed = apply_import_plan(plans, on_error=lambda typ, entry, exx: errors.update({entry.key: str(exx)}))

        self.assertEqual(["realm"], failed)
        self.assertIn("still contains tokens", errors["imp-tok-realm"])
        self.assertIn("still contains containers", errors["imp-cont-realm"])
        self.assertEqual(["imp-tok-realm"], get_realms_of_token("IMP-TOK-1"))
        container_realms = find_container_by_serial(container_serial).realms
        self.assertEqual(["imp-cont-realm"], [realm.name for realm in container_realms])

    def test_23_failed_event_import_keeps_the_surplus_event_handlers(self):
        # With --replace the surplus handler of a group is deleted in the transaction of the event import, so a
        # failed import does not leave the group with fewer handlers and without the update.
        for event in ("token_assign", "token_revoke"):
            set_event("imp-ev-surplus", [event], "UserNotification", "sendmail", conditions={})
        exported = export("event", {"imp-ev-surplus"})
        first = copy.deepcopy(min(exported, key=lambda e: e["id"]))
        first["ordering"] = 4
        data = {"event": [first]}

        plans = build_import_plan(data, ["event"], replace=True)
        self.assertEqual(["delete", "update"], sorted(e.action for e in self._type_plan(plans, "event").entries))
        with mock.patch("privacyidea.lib.event._stage_event", side_effect=RuntimeError("database connection lost")):
            self.assertEqual(["event"], apply_import_plan(plans))
        self.assertEqual(sorted((e["id"], e["ordering"]) for e in exported),
                         sorted((e["id"], e["ordering"]) for e in export("event", {"imp-ev-surplus"})))

        # without the failure the first handler is updated and the surplus one deleted
        self.assertEqual([], apply_import_plan(build_import_plan(data, ["event"], replace=True)))
        self.assertEqual([(first["id"], 4)],
                         [(e["id"], e["ordering"]) for e in export("event", {"imp-ev-surplus"})])

    def test_24_policy_without_description_removes_the_stored_one(self):
        # A policy without a description exports None. The import must remove a stored description, else the plan
        # reports the same update on every run.
        set_policy("imp-desc-pol", scope=SCOPE.AUTH, action=PolicyAction.PASSTHRU, description="old description")
        data = {"policy": export("policy", {"imp-desc-pol"})}
        entry_of("policy", data["policy"], "imp-desc-pol")["description"] = None

        plans = build_import_plan(data, ["policy"])
        entry = self._by_key(self._type_plan(plans, "policy"))["imp-desc-pol"]
        self.assertEqual(("update", ["description"]), (entry.action, entry.changed_fields))
        self.assertEqual([], apply_import_plan(plans))
        self.assertFalse(entry_of("policy", export("policy", {"imp-desc-pol"}), "imp-desc-pol")["description"])
        plans = build_import_plan(data, ["policy"])
        self.assertEqual("unchanged", self._by_key(self._type_plan(plans, "policy"))["imp-desc-pol"].action)

    def test_25_every_import_type_has_an_adapter(self):
        self.assertEqual(set(IMPORT_FUNCTIONS), set(_ADAPTERS))
        # A selected type without an adapter stops the plan instead of being left out without a message
        new_type = {"imp-newtype": {"prio": 99, "func": lambda data, name=None: None}}
        with mock.patch.dict(IMPORT_FUNCTIONS, new_type):
            with self.assertRaises(ValueError):
                build_import_plan({"imp-newtype": {}}, ["all"])
            self.assertEqual([], build_import_plan({"imp-newtype": {}}, ["policy"]))

    def test_26_kept_default_realm_stays_the_default_realm(self):
        # With --replace and a file that marks no realm as default, the import keeps a default realm that still
        # contains tokens. The realm stays as it was, so it also stays the default realm. A realm that was not the
        # default realm does not become the default realm, also if delete_realm() makes the last realm that is
        # left the default realm.
        save_resolver({"resolver": REALM_RESOLVER, "type": "passwdresolver", "fileName": PWFILE})
        _set_realm("imp-default-a")
        _set_realm("imp-default-b")
        init_token({"type": "spass", "serial": "IMP-TOK-DEFAULT"}, tokenrealms=["imp-default-a"])
        self.addCleanup(remove_token, "IMP-TOK-DEFAULT")
        file_with_b = {"realm": export("realm", {"imp-default-b"})}
        entry_of("realm", file_with_b["realm"], "imp-default-b")["default"] = False
        cases = [("imp-default-a", file_with_b, {"imp-default-a": "delete", "imp-default-b": "unchanged"}),
                 (None, {"realm": {}}, {"imp-default-a": "delete", "imp-default-b": "delete"})]

        for default_before, data, actions in cases:
            with self.subTest(default_before=default_before):
                set_default_realm(default_before)
                plans = build_import_plan(data, ["realm"], replace=True)
                self.assertEqual(actions, {e.key: e.action for e in self._type_plan(plans, "realm").entries})
                errors = {}
                failed = apply_import_plan(plans,
                                           on_error=lambda typ, entry, exx: errors.update({entry.key: str(exx)}))
                self.assertEqual(["realm"], failed)
                self.assertEqual(["imp-default-a"], list(errors))
                self.assertIn("imp-default-a", get_realms())
                self.assertEqual(default_before, get_default_realm() or None)
