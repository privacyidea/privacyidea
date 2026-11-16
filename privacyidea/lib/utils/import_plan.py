# (c) NetKnights GmbH 2026,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
"""
This module compares configuration data to be imported (the format of
``pi-manage config export``) with the configuration of this system and plans
what an import changes: which entries are created, updated, left unchanged,
deleted (with ``replace``) or skipped.

The plan never contains or logs the value of a field, only the names of the
entries and of the changed fields, because the compared data holds secrets in
clear text.

It is tested in tests/test_lib_utils_import_plan.py
"""
import copy
import inspect
import logging
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Optional, Union

from privacyidea.lib import config  # noqa: F401 # registers the importer of the type 'config'
from privacyidea.lib.caconnector import delete_caconnector
from privacyidea.lib.crypto import is_censored
from privacyidea.lib.event import delete_event
from privacyidea.lib.machineresolver import delete_resolver as delete_machine_resolver
from privacyidea.lib.periodictask import delete_periodic_task
from privacyidea.lib.policy import delete_policy, filter_invalid_actions, SCOPE
from privacyidea.lib.privacyideaserver import delete_privacyideaserver
from privacyidea.lib.radiusserver import delete_radius
from privacyidea.lib.realm import delete_realm
from privacyidea.lib.resolver import delete_resolver
from privacyidea.lib.smsprovider.SMSProvider import delete_smsgateway
from privacyidea.lib.smtpserver import delete_smtpserver
from privacyidea.lib.utils import is_true
from privacyidea.lib.utils.export import EXPORT_FUNCTIONS, IMPORT_FUNCTIONS
from privacyidea.models import db
from privacyidea.models.policy import parse_action_string

log = logging.getLogger(__name__)

CREATE = "create"
UPDATE = "update"
UNCHANGED = "unchanged"
DELETE = "delete"
SKIP = "skip"

CONFIG_NOTE = "System settings (type 'config') are not replaced: keys missing from the import are kept."
ADMIN_POLICY_WARNING = ("Warning: after this import no active admin policy is left, "
                        "so every administrator may do everything.")

_MISSING = object()


@dataclass
class PlanEntry:
    """
    The planned action for one entry of a configuration type.

    ``key`` is the name of the entry, for ``event`` the tuple ``(name, handlermodule)``.
    ``changed_fields`` holds the sorted names of the changed fields of an update, never their values.
    ``target_name`` is the name under which this system stores the entry of a planned ``delete``, if it
    differs from ``key``.
    """
    action: str
    key: Union[str, tuple]
    changed_fields: list = field(default_factory=list)
    reason: Optional[str] = None
    target_id: Optional[int] = None
    target_name: Optional[str] = None


@dataclass
class TypePlan:
    """
    The plan of one configuration type.

    ``data`` holds the import data of the create and update entries (and of the
    skipped event handlers, so that the importer still reports them) in the
    format the importer of the type takes.
    """
    typ: str
    entries: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    data: Union[dict, list, None] = None


def _import_order() -> list:
    """The registered import types in the order the importers run (sorted by prio)."""
    return [typ for typ, _ in sorted(IMPORT_FUNCTIONS.items(), key=lambda item: item[1]["prio"])]


def _plain(value):
    """Turn tuples into lists recursively, so that exported and JSON-parsed data compare equal."""
    if isinstance(value, dict):
        return {key: _plain(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(val) for val in value]
    return value


def _differs(import_value, target_value) -> bool:
    """A censored import value keeps the stored one of an existing entry, so it is never a change."""
    if is_censored(import_value):
        return False
    return import_value != target_value


def _changed_fields(import_entry: dict, target_entry: dict, subset_fields: tuple = ()) -> list:
    """
    Return the sorted names of the fields that differ. Only the fields of the
    import entry are compared. A dict field in ``subset_fields`` is compared
    for its keys in the import entry only (the setter keeps missing keys),
    any other dict field as a whole (the setter removes missing keys).
    """
    changed = []
    for name, import_value in import_entry.items():
        target_value = target_entry.get(name, _MISSING)
        if isinstance(import_value, dict) and isinstance(target_value, dict):
            keys = import_value if name in subset_fields else set(import_value) | set(target_value)
            changed.extend(f"{name}.{key}" for key in keys
                           if _differs(import_value.get(key, _MISSING), target_value.get(key, _MISSING)))
        elif _differs(import_value, target_value):
            changed.append(name)
    return sorted(changed)


def _without(entry: dict, keys) -> dict:
    return {key: value for key, value in entry.items() if key not in keys}


# Normalizers turn an import entry or an exported entry of this system into the
# form that is compared. They work on deep copies and apply the same renames
# as the importers, and they drop the fields that are specific to an instance.

def _normalize_resolver(entry: dict) -> dict:
    return _without(entry, ("censor_keys",))


def _normalize_realm(entry: dict) -> dict:
    result = _without(entry, ("id",))
    if "default" in result:
        result["default"] = is_true(result["default"])
    if isinstance(result.get("resolver"), list):
        # set_realm only uses name, priority and node of each resolver, the order does not matter
        resolvers = [{"name": res.get("name"), "priority": res.get("priority"), "node": str(res.get("node") or "")}
                     for res in result["resolver"] if isinstance(res, dict)]
        result["resolver"] = sorted(resolvers, key=lambda res: (str(res["name"]), res["node"]))
    return result


def _normalize_policy(entry: dict) -> dict:
    result = dict(entry)
    if isinstance(result.get("action"), str):
        result["action"] = parse_action_string(result["action"]) if result["action"] else {}
    return result


def _normalize_config(entry: dict) -> dict:
    result = dict(entry)
    if "Value" in result and result["Value"] is not None and not is_censored(result["Value"]):
        result["Value"] = str(result["Value"])
    return result


def _normalize_radiusserver(entry: dict) -> dict:
    result = dict(entry)
    # import_radiusserver maps the legacy 'password' key onto 'secret'
    legacy_secret = result.pop("password", None)
    if legacy_secret is not None and "secret" not in result:
        result["secret"] = legacy_secret
    return result


def _normalize_smtpserver(entry: dict) -> dict:
    # import_smtpserver drops 'enqueue_job' of exports of privacyIDEA 3.14 and older
    return _without(entry, ("enqueue_job",))


def _normalize_periodictask(entry: dict) -> dict:
    return _without(entry, ("id", "last_update", "last_runs"))


def _normalize_event(entry: dict) -> dict:
    # import_event ignores the id of the exporting system and the unused 'condition'
    return _without(entry, ("id", "condition"))


@dataclass
class _TypeAdapter:
    """
    How to plan one configuration type.

    ``name_field`` is the field that names an entry of a type exported as a
    list, None for a type exported as a dict keyed by name. ``delete`` removes
    an entry from this system with the existing lib function, without forcing.
    ``fold_name`` turns a name into the form in which the setter of the type finds
    an existing entry, so that the plan matches names like the setter does.
    """
    name_field: Optional[str] = None
    normalize: Callable[[dict], dict] = dict
    subset_fields: tuple = ()
    delete: Optional[Callable[[PlanEntry], object]] = None
    fold_name: Callable[[str], str] = str


def _fold_realm_name(name: str) -> str:
    """The name under which ``set_realm`` stores a realm."""
    return name.lower().strip().replace(" ", "-")


def _fold_case(name: str) -> str:
    """The setters of resolvers and machine resolvers find an existing one without regard to the case."""
    return name.lower()


_ADAPTERS = {
    "resolver": _TypeAdapter(normalize=_normalize_resolver, subset_fields=("data",), fold_name=_fold_case,
                             delete=lambda entry: delete_resolver(entry.target_name or entry.key)),
    "config": _TypeAdapter(normalize=_normalize_config),
    "realm": _TypeAdapter(normalize=_normalize_realm, fold_name=_fold_realm_name,
                          delete=lambda entry: delete_realm(entry.key, delete_custom_attributes=False,
                                                            confirm_ca_policies=False)),
    "policy": _TypeAdapter(name_field="name", normalize=_normalize_policy,
                           delete=lambda entry: delete_policy(entry.key)),
    "event": _TypeAdapter(name_field="name", normalize=_normalize_event,
                          delete=lambda entry: delete_event(entry.target_id)),
    "periodictask": _TypeAdapter(name_field="name", normalize=_normalize_periodictask,
                                 delete=lambda entry: delete_periodic_task(entry.target_id)),
    "machineresolver": _TypeAdapter(subset_fields=("data",), fold_name=_fold_case,
                                    delete=lambda entry: delete_machine_resolver(entry.target_name or entry.key)),
    "caconnector": _TypeAdapter(name_field="connectorname", subset_fields=("data",),
                                delete=lambda entry: delete_caconnector(entry.key)),
    "privacyideaserver": _TypeAdapter(delete=lambda entry: delete_privacyideaserver(entry.key)),
    "radiusserver": _TypeAdapter(normalize=_normalize_radiusserver,
                                 delete=lambda entry: delete_radius(entry.key)),
    "smtpserver": _TypeAdapter(normalize=_normalize_smtpserver,
                               delete=lambda entry: delete_smtpserver(entry.key)),
    "smsgateway": _TypeAdapter(delete=lambda entry: delete_smsgateway(entry.key)),
}

# Deleting runs in the reverse import order, so that dependent entries (policies,
# event handlers) go before realms and realms before resolvers. config is never deleted.
DELETE_ORDER = tuple(typ for typ in reversed(_import_order()) if typ != "config")


def delete_plan_entry(typ: str, entry: PlanEntry):
    """
    Delete the entry of a planned ``delete`` from this system with the existing
    lib function of the type. Nothing is forced: e.g. a realm with assigned
    tokens or a resolver used by a realm raises the error of the lib function.

    :return: the result of the lib delete function
    """
    if entry.action != DELETE:
        raise ValueError(f"Plan entry {entry.key!r} of type {typ!r} is not planned for deletion.")
    return _ADAPTERS[typ].delete(entry)


def _keyed(adapter: _TypeAdapter, typ_data) -> dict:
    """Map the name of each entry to the entry, for data in the exporter format of the type."""
    if adapter.name_field:
        return {entry.get(adapter.name_field): entry for entry in typ_data or []}
    return dict(typ_data or {})


def _fold_names(adapter: _TypeAdapter, entries: dict) -> dict:
    """Key the entries by the name under which the setter of the type finds them."""
    return {adapter.fold_name(key) if isinstance(key, str) else key: entry for key, entry in entries.items()}


def _to_importer_format(adapter: _TypeAdapter, entries: dict):
    if adapter.name_field:
        return list(entries.values())
    return entries


def _target_entries(typ: str) -> dict:
    """The entries of this system, as a deep copy since exporters may return cached objects."""
    return _keyed(_ADAPTERS[typ], copy.deepcopy(EXPORT_FUNCTIONS[typ]()))


def _has_active_admin_policy(policies) -> bool:
    return any(policy.get("scope") == SCOPE.ADMIN and is_true(policy.get("active", True))
               for policy in policies)


def _admin_policy_warning(import_entries: dict, target: dict, entries: list) -> list:
    """Warn when this system has an active admin policy now but none after the import."""
    if not _has_active_admin_policy(target.values()):
        return []
    after = dict(target)
    for entry in entries:
        if entry.action == DELETE:
            after.pop(entry.key, None)
        elif entry.action in (CREATE, UPDATE):
            # set_policy writes every field, a missing 'active' becomes the default True
            after[entry.key] = import_entries[entry.key]
    return [] if _has_active_admin_policy(after.values()) else [ADMIN_POLICY_WARNING]


def _plan_name_keyed(typ: str, typ_data, name: Optional[str], replace: bool, skip_invalid: bool) -> TypePlan:
    adapter = _ADAPTERS[typ]
    if typ == "resolver" and isinstance(typ_data, list):
        # old style export, import_resolver takes it as well
        typ_data = {entry.get("resolvername"): entry for entry in typ_data}
    import_entries = _keyed(adapter, typ_data)
    if typ == "config":
        # keys starting with __ (e.g. __timestamp__) are specific to the instance
        import_entries = {key: value for key, value in import_entries.items() if not str(key).startswith("__")}
    if name is not None:
        # the importer compares the name unchanged, so the filter does the same
        import_entries = {key: value for key, value in import_entries.items() if key == name}
    import_entries = _fold_names(adapter, import_entries)
    stored_targets = _target_entries(typ)
    stored_names = {adapter.fold_name(key) if isinstance(key, str) else key: key for key in stored_targets}
    all_targets = _fold_names(adapter, stored_targets)
    targets = all_targets
    if typ == "config":
        targets = {key: value for key, value in targets.items() if not str(key).startswith("__")}
    if name is not None:
        folded_name = adapter.fold_name(name)
        targets = {key: value for key, value in targets.items() if key == folded_name}

    plan = TypePlan(typ=typ)
    to_import = {}
    for key, entry in import_entries.items():
        if typ == "policy" and skip_invalid:
            cleaned, dropped = filter_invalid_actions(entry.get("scope"), entry.get("action", {}))
            if dropped:
                log.warning(f'Policy "{key}": {len(dropped)} actions are not valid for this version '
                            f'and are dropped.')
                entry["action"] = cleaned
                if not cleaned:
                    plan.entries.append(PlanEntry(SKIP, key, reason="no valid action is left for this version"))
                    continue
        target = targets.get(key)
        if typ == "config" and is_censored(entry.get("Value")) and target is None:
            # import_config skips a censored entry that does not exist on this system
            plan.entries.append(PlanEntry(SKIP, key, reason="the value is censored and there is no value to keep"))
            continue
        if target is None:
            plan.entries.append(PlanEntry(CREATE, key))
            to_import[key] = entry
            continue
        changed = _changed_fields(_plain(adapter.normalize(entry)), _plain(adapter.normalize(target)),
                                  adapter.subset_fields)
        if changed:
            plan.entries.append(PlanEntry(UPDATE, key, changed_fields=changed))
            to_import[key] = entry
        else:
            plan.entries.append(PlanEntry(UNCHANGED, key))

    if replace and typ == "config":
        plan.notes.append(CONFIG_NOTE)
    elif replace:
        plan.entries.extend(PlanEntry(DELETE, key, target_id=target.get("id") if typ == "periodictask" else None,
                                      target_name=stored_names.get(key))
                            for key, target in targets.items() if key not in import_entries)
    if typ == "policy":
        plan.warnings.extend(_admin_policy_warning(import_entries, all_targets, plan.entries))
    plan.data = _to_importer_format(adapter, to_import)
    return plan


def _entry_count(count: int) -> str:
    return f"{count} entry" if count == 1 else f"{count} entries"


def _plan_event(typ_data, name: Optional[str], replace: bool) -> TypePlan:
    """
    Plan the event handlers grouped by (name, handlermodule) like import_event:
    the n handlers of a group in the import replace the m handlers of this
    system in the order of their ids. With n < m the group is skipped, with
    ``replace`` the first n are updated and the other m - n deleted.
    """
    adapter = _ADAPTERS["event"]
    imported = defaultdict(list)
    without_name = []
    for entry in typ_data or []:
        if name is not None and entry.get("name") != name:
            continue
        if entry.get("name"):
            imported[(entry["name"], entry.get("handlermodule"))].append(entry)
        else:
            without_name.append(entry)
    existing = defaultdict(list)
    for target in sorted(copy.deepcopy(EXPORT_FUNCTIONS["event"]()), key=lambda target: target["id"]):
        if name is None or target.get("name") == name:
            existing[(target.get("name"), target.get("handlermodule"))].append(target)

    plan = TypePlan(typ="event")
    to_import = []
    for key, entries in imported.items():
        targets = existing.get(key, [])
        if not targets:
            plan.entries.append(PlanEntry(CREATE, key))
            to_import.extend(entries)
            continue
        if len(entries) < len(targets) and not replace:
            plan.entries.append(PlanEntry(SKIP, key, reason=f"{_entry_count(len(entries))} in the import, "
                                                            f"{len(targets)} on this system, use --replace"))
            # import_event reports the skipped group, so it gets the entries as well
            to_import.extend(entries)
            continue
        changed = set()
        for entry, target in zip(entries, targets):
            changed.update(_changed_fields(_plain(adapter.normalize(entry)), _plain(adapter.normalize(target))))
        if changed or len(entries) > len(targets):
            plan.entries.append(PlanEntry(UPDATE, key, changed_fields=sorted(changed)))
            to_import.extend(entries)
        else:
            plan.entries.append(PlanEntry(UNCHANGED, key))
        plan.entries.extend(PlanEntry(DELETE, key, target_id=target["id"]) for target in targets[len(entries):])
    for entry in without_name:
        plan.entries.append(PlanEntry(SKIP, (entry.get("name") or "", entry.get("handlermodule")),
                                      reason="the event handler has no name"))
        to_import.append(entry)
    if replace:
        for key, targets in existing.items():
            if key not in imported:
                plan.entries.extend(PlanEntry(DELETE, key, target_id=target["id"]) for target in targets)
    plan.data = to_import
    return plan


def build_import_plan(data: dict, types, name: Optional[str] = None, replace: bool = False,
                      skip_invalid: bool = False) -> list:
    """
    Compare the configuration data to be imported with this system.

    :param data: The parsed import data ``{typ: <exporter output>, ...}``, keys
        that are no registered import type are ignored. It is not modified.
    :param types: The type names to plan, ``"all"`` selects every type
    :param name: Only plan the entries with this name
    :param replace: Plan to delete the entries of a planned type that are
        missing from the import (never for ``config``)
    :param skip_invalid: Drop policy actions that are not valid for this version
        before comparing, as ``import_policy`` does
    :return: a ``TypePlan`` for each selected type in ``data``, in import order
    """
    types = set(types)
    data = copy.deepcopy(data)
    plans = []
    for typ in _import_order():
        if typ not in data or ("all" not in types and typ not in types) or typ not in _ADAPTERS:
            continue
        if typ == "event":
            plan = _plan_event(data[typ], name, replace)
        else:
            plan = _plan_name_keyed(typ, data[typ], name, replace, skip_invalid)
        counts = defaultdict(int)
        for entry in plan.entries:
            counts[entry.action] += 1
        log.debug(f"Import plan for type '{typ}': {dict(counts)}")
        plans.append(plan)
    return plans


def _format_entry(typ: str, entry: PlanEntry) -> str:
    if typ == "event":
        line = f'  {entry.action} {typ} "{entry.key[0]}" ({entry.key[1]})'
    else:
        line = f'  {entry.action} {typ} "{entry.key}"'
    if entry.action == UPDATE and entry.changed_fields:
        line += ": " + ", ".join(entry.changed_fields)
    elif entry.action == SKIP and entry.reason:
        line += ": " + entry.reason
    return line


def format_import_plan(plans: list) -> list:
    """
    Return the plan as text lines, one per entry followed by the notes and
    warnings of each type. Only names of entries and fields are printed,
    never the value of a field.
    """
    lines = []
    for plan in plans:
        lines.extend(_format_entry(plan.typ, entry) for entry in plan.entries)
        lines.extend(f"  {text}" for text in plan.notes + plan.warnings)
    return lines


def _surplus_event_deletes(plan: TypePlan) -> list:
    """
    The planned deletions of event handlers of a group that is also in the
    import: they have to go before import_event, which skips a group with
    more handlers on this system than in the import.
    """
    if plan.typ != "event":
        return []
    imported_keys = {entry.key for entry in plan.entries if entry.action != DELETE}
    return [entry for entry in plan.entries if entry.action == DELETE and entry.key in imported_keys]


def apply_import_plan(plans: list, name: Optional[str] = None, skip_invalid: bool = False,
                      on_import: Optional[Callable[[str], None]] = None,
                      on_error: Optional[Callable[[str, Optional[PlanEntry], Exception], None]] = None) -> list:
    """
    Apply an import plan of :func:`build_import_plan` to this system.

    The importers of the types run in import order with the data of the
    create and update entries only, so unchanged entries are not written
    again. Afterwards the planned deletions run in ``DELETE_ORDER``. The
    surplus event handlers of a group that is also in the import are deleted
    right before the event handlers are imported.

    A failing importer or deletion is rolled back, reported with ``on_error``
    and the type is marked as failed. The remaining types and deletions are
    still applied, but the planned deletions of a type whose importer failed
    are not.

    :param plans: the list of ``TypePlan`` objects
    :param name: passed to the importers, only the entries with this name are imported
    :param skip_invalid: passed to the importers that support it
    :param on_import: called with the type before its importer runs
    :param on_error: called with the type, the plan entry of a failed deletion
        (None for a failed importer) and the exception
    :return: the failed types in the order they failed, without duplicates
    """
    failed = []
    import_failed = set()

    def fail(typ, entry, exx):
        db.session.rollback()
        log.warning(f"Import of configuration type '{typ}' failed: {exx!r}")
        log.debug(traceback.format_exc())
        if typ not in failed:
            failed.append(typ)
        if on_error:
            on_error(typ, entry, exx)

    def delete(typ, entry):
        try:
            delete_plan_entry(typ, entry)
        except Exception as exx:  # noqa: Any error of a delete function is reported, the others go on
            fail(typ, entry, exx)

    for plan in plans:
        surplus = _surplus_event_deletes(plan)
        if not plan.data and not surplus:
            continue
        if on_import:
            on_import(plan.typ)
        for entry in surplus:
            delete(plan.typ, entry)
        if not plan.data:
            continue
        func = IMPORT_FUNCTIONS[plan.typ]["func"]
        kwargs = {"name": name}
        if "skip_invalid" in inspect.signature(func).parameters:
            kwargs["skip_invalid"] = skip_invalid
        try:
            func(plan.data, **kwargs)
        except Exception as exx:  # noqa: Any error of an importer is reported, the other types go on
            import_failed.add(plan.typ)
            fail(plan.typ, None, exx)

    by_type = {plan.typ: plan for plan in plans}
    for typ in DELETE_ORDER:
        plan = by_type.get(typ)
        if not plan or typ in import_failed:
            # The entries of a type whose importer failed are kept, so that the type is not left half replaced.
            continue
        surplus = {id(entry) for entry in _surplus_event_deletes(plan)}
        for entry in plan.entries:
            if entry.action == DELETE and id(entry) not in surplus:
                delete(typ, entry)
    return failed
