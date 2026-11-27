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
from typing import Any
from collections.abc import Callable, Iterable

from sqlalchemy import select

from privacyidea.lib import config  # noqa: F401 # registers the importer of the type 'config'
from privacyidea.lib.caconnector import delete_caconnector
from privacyidea.lib.crypto import is_censored
from privacyidea.lib.error import ConfigAdminError, UserError
from privacyidea.lib.event import delete_event, inline_webhook_defect, inline_webhook_link
from privacyidea.lib.machineresolver import delete_resolver as delete_machine_resolver
from privacyidea.lib.periodictask import delete_periodic_task
from privacyidea.lib.policy import delete_policy, filter_invalid_actions, SCOPE
from privacyidea.lib.privacyideaserver import delete_privacyideaserver
from privacyidea.lib.radiusserver import delete_radius
from privacyidea.lib.realm import delete_realm, get_default_realm, set_default_realm
from privacyidea.lib.resolver import delete_resolver
from privacyidea.lib.smsprovider.SMSProvider import delete_smsgateway
from privacyidea.lib.smtpserver import delete_smtpserver
from privacyidea.lib.utils import is_true
from privacyidea.lib.utils.export import EXPORT_FUNCTIONS, IMPORT_FUNCTIONS
from privacyidea.lib.webhook import delete_webhook
from privacyidea.models import (db, ConditionalAccessPolicy, ConditionalAccessPolicyStage,
                                ConditionalAccessStageAction, EventHandler, EventHandlerOption, PeriodicTask, Policy,
                                PrivacyIDEAServer, RADIUSServer, Realm, SMSGateway, SMTPServer, TokenContainerRealm,
                                TokenRealm, Webhook)
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
NO_DEFAULT_REALM_WARNING = ("Warning: after this import no realm is the default realm, "
                            "so a user who logs in without a realm is not found.")

_MISSING = object()
NO_DEFAULT_REALM_PLAN = object()


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
    key: str | tuple
    changed_fields: list = field(default_factory=list)
    reason: str | None = None
    target_id: int | None = None
    target_name: str | None = None


@dataclass
class TypePlan:
    """
    The plan of one configuration type.

    ``data`` holds the import data of the create and update entries (and of the
    skipped event handlers, so that the importer still reports them) in the
    format the importer of the type takes.

    ``webhooks_in_use`` holds, for the type ``event``, the identifiers of the
    webhooks that the event handlers use after the import.
    """
    typ: str
    entries: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    data: dict | list | None = None
    # name of the realm that is the default after the import (None: no default), NO_DEFAULT_REALM_PLAN: not planned
    default_realm: str | None | object = NO_DEFAULT_REALM_PLAN
    webhooks_in_use: set = field(default_factory=set)


def _import_order() -> list:
    """The registered import types in the order the importers run (sorted by prio)."""
    return [typ for typ, _ in sorted(IMPORT_FUNCTIONS.items(), key=lambda item: item[1]["prio"])]


def _plain(value: Any) -> Any:
    """Turn tuples into lists recursively, so that exported and JSON-parsed data compare equal."""
    if isinstance(value, dict):
        return {key: _plain(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(val) for val in value]
    return value


def _differs(import_value: Any, target_value: Any) -> bool:
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


def _without(entry: dict, keys: Iterable[str]) -> dict:
    return {key: value for key, value in entry.items() if key not in keys}


# Normalizers turn an import entry or an exported entry of this system into the
# form that is compared. They work on deep copies and apply the same renames
# as the importers, and they drop the fields that are specific to an instance.

def _normalize_resolver(entry: dict) -> dict:
    return _without(entry, ("censor_keys",))


def _normalize_realm(entry: dict) -> dict:
    # The default realm is a setting of the system and not of one realm. The plan of the type realm holds it in
    # TypePlan.default_realm, because import_realms() only sets the default and never takes it away.
    result = _without(entry, ("id", "default"))
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
    if "description" in result:
        # import_policy stores None as "", and Oracle reads "" back as None
        result["description"] = result["description"] or None
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


def _normalize_webhook(entry: dict) -> dict:
    result = dict(entry)
    # set_webhook only checks whether a header is in the list, and the export lists them in no fixed order
    if isinstance(result.get("secret_headers"), (list, tuple)):
        result["secret_headers"] = sorted(result["secret_headers"])
    return result


@dataclass
class _TypeAdapter:
    """
    How to plan one configuration type.

    ``name_field`` is the field that names an entry of a type exported as a
    list, None for a type exported as a dict keyed by name. ``delete`` removes
    an entry from this system with the existing lib function, without forcing.
    ``fold_name`` turns a name into the form in which the setter of the type finds
    an existing entry, so that the plan matches names like the setter does.
    ``stored_name`` returns the name of the entry on this system that the setter
    of the type finds for a name with its database lookup, or None. Depending on
    the collation of the database this can be an entry whose name differs in
    case. ``setter_renames`` tells whether the setter then writes the imported
    name to that entry (else it keeps the name stored on this system).
    """
    name_field: str | None = None
    normalize: Callable[[dict], dict] = dict
    subset_fields: tuple = ()
    delete: Callable[[PlanEntry], object] | None = None
    fold_name: Callable[[str], str] = str
    stored_name: Callable[[str], str | None] | None = None
    setter_renames: bool = False


def _fold_realm_name(name: str) -> str:
    """The name under which ``set_realm`` stores a realm."""
    return name.lower().strip().replace(" ", "-")


def _fold_case(name: str) -> str:
    """The setters of resolvers and machine resolvers find an existing one without regard to the case."""
    return name.lower()


def _delete_realm(entry: PlanEntry) -> int:
    """
    Delete a realm that is missing from the import. delete_realm() only refuses a realm whose users own tokens or
    containers, and it takes the realm away from all other tokens and containers. The import keeps such a realm.
    """
    realm_id = db.session.scalar(select(Realm.id).where(Realm.name == entry.key))
    if realm_id is not None:
        if db.session.scalar(select(TokenRealm.id).where(TokenRealm.realm_id == realm_id).limit(1)) is not None:
            raise UserError(f"Realm '{entry.key}' is not deleted, because it still contains tokens.")
        container_stmt = select(TokenContainerRealm.container_id).where(TokenContainerRealm.realm_id == realm_id)
        if db.session.scalar(container_stmt.limit(1)) is not None:
            raise UserError(f"Realm '{entry.key}' is not deleted, because it still contains containers.")
    return delete_realm(entry.key, delete_custom_attributes=False, confirm_ca_policies=False)


def _ca_policies_by_webhook() -> dict:
    """
    Return the names of the conditional access policies whose ``WEBHOOK`` actions name a webhook, by webhook.

    The configuration import does not carry conditional access policies, so all of them stay after an import.

    :return: dict of webhook identifier -> sorted list of policy names
    """
    rows = db.session.execute(
        select(ConditionalAccessPolicy.name, ConditionalAccessStageAction.action_value)
        .join(ConditionalAccessPolicyStage, ConditionalAccessPolicyStage.policy_id == ConditionalAccessPolicy.id)
        .join(ConditionalAccessStageAction, ConditionalAccessStageAction.stage_id == ConditionalAccessPolicyStage.id)
        .where(ConditionalAccessStageAction.action_type == "WEBHOOK")).all()
    policies = defaultdict(set)
    for policy_name, action_value in rows:
        if isinstance(action_value, dict) and action_value.get("webhook"):
            policies[action_value["webhook"]].add(policy_name)
    return {identifier: sorted(names) for identifier, names in policies.items()}


def _ca_policy_use(policy_names: list) -> str:
    """Say which conditional access policies use a webhook, for a note or an error."""
    if len(policy_names) > 1:
        return f"the conditional access policies {policy_names} use it"
    return f"the conditional access policy {policy_names[0]!r} uses it"


def _delete_unused_webhook(entry: PlanEntry) -> int:
    """
    Delete the webhook of a planned delete, unless an event handler or a conditional access policy uses it.

    The plan keeps the webhooks that the event handlers and the conditional access policies use after the import.
    This check covers a handler that the import creates: its id, and with it the webhook that an inline handler is
    linked to, is known only when it is written.

    :raises ConfigAdminError: if an event handler or a conditional access policy uses the webhook
    """
    identifier = entry.target_name or entry.key
    users = db.session.scalars(
        select(EventHandler.name)
        .join(EventHandlerOption, EventHandlerOption.eventhandler_id == EventHandler.id)
        .where(EventHandler.handlermodule == "WebHook", EventHandlerOption.Key == "webhook",
               EventHandlerOption.Value == identifier)).all()
    if users:
        raise ConfigAdminError(f"The webhook is not deleted, because the event handlers "
                               f"{sorted(name or '' for name in users)} use it.")
    policy_names = _ca_policies_by_webhook().get(identifier)
    if policy_names:
        raise ConfigAdminError(f"The webhook is not deleted, because {_ca_policy_use(policy_names)}.")
    return delete_webhook(identifier)


def _stored_name_lookup(column: Any) -> Callable[[str], str | None]:
    """Find a stored name with the comparison of the setter, which follows the collation of the database."""
    def lookup(name: str) -> str | None:
        return db.session.scalars(select(column).where(column == name)).first()
    return lookup


_ADAPTERS = {
    "resolver": _TypeAdapter(normalize=_normalize_resolver, subset_fields=("data",), fold_name=_fold_case,
                             delete=lambda entry: delete_resolver(entry.target_name or entry.key)),
    "config": _TypeAdapter(normalize=_normalize_config),
    "realm": _TypeAdapter(normalize=_normalize_realm, fold_name=_fold_realm_name, delete=_delete_realm),
    "policy": _TypeAdapter(name_field="name", normalize=_normalize_policy,
                           delete=lambda entry: delete_policy(entry.key),
                           stored_name=_stored_name_lookup(Policy.name)),
    "event": _TypeAdapter(name_field="name", normalize=_normalize_event,
                          delete=lambda entry: delete_event(entry.target_id)),
    "periodictask": _TypeAdapter(name_field="name", normalize=_normalize_periodictask,
                                 delete=lambda entry: delete_periodic_task(entry.target_id),
                                 stored_name=_stored_name_lookup(PeriodicTask.name), setter_renames=True),
    "machineresolver": _TypeAdapter(subset_fields=("data",), fold_name=_fold_case,
                                    delete=lambda entry: delete_machine_resolver(entry.target_name or entry.key)),
    "caconnector": _TypeAdapter(name_field="connectorname", subset_fields=("data",),
                                delete=lambda entry: delete_caconnector(entry.key)),
    "privacyideaserver": _TypeAdapter(delete=lambda entry: delete_privacyideaserver(entry.key),
                                      stored_name=_stored_name_lookup(PrivacyIDEAServer.identifier)),
    "radiusserver": _TypeAdapter(normalize=_normalize_radiusserver,
                                 delete=lambda entry: delete_radius(entry.key),
                                 stored_name=_stored_name_lookup(RADIUSServer.identifier)),
    "smtpserver": _TypeAdapter(normalize=_normalize_smtpserver,
                               delete=lambda entry: delete_smtpserver(entry.key),
                               stored_name=_stored_name_lookup(SMTPServer.identifier)),
    "smsgateway": _TypeAdapter(delete=lambda entry: delete_smsgateway(entry.key),
                               stored_name=_stored_name_lookup(SMSGateway.identifier)),
    "webhook": _TypeAdapter(normalize=_normalize_webhook, delete=_delete_unused_webhook,
                            stored_name=_stored_name_lookup(Webhook.identifier)),
}

# Deleting runs in the reverse import order, so that dependent entries (policies,
# event handlers) go before realms and realms before resolvers. config is never deleted.
DELETE_ORDER = tuple(typ for typ in reversed(_import_order()) if typ != "config")


def delete_plan_entry(typ: str, entry: PlanEntry) -> Any:
    """
    Delete the entry of a planned ``delete`` from this system with the existing
    lib function of the type. Nothing is forced: e.g. a realm that contains
    tokens or containers or a resolver used by a realm raises an error.

    :return: the result of the lib delete function
    """
    if entry.action != DELETE:
        raise ValueError(f"Plan entry {entry.key!r} of type {typ!r} is not planned for deletion.")
    return _ADAPTERS[typ].delete(entry)


def _keyed(adapter: _TypeAdapter, typ_data: dict | list | None) -> dict:
    """Map the name of each entry to the entry, for data in the exporter format of the type."""
    if adapter.name_field:
        return {entry.get(adapter.name_field): entry for entry in typ_data or []}
    return dict(typ_data or {})


def _fold_names(adapter: _TypeAdapter, entries: dict) -> dict:
    """Key the entries by the name under which the setter of the type finds them."""
    return {adapter.fold_name(key) if isinstance(key, str) else key: entry for key, entry in entries.items()}


def _to_importer_format(adapter: _TypeAdapter, entries: dict) -> list | dict:
    if adapter.name_field:
        return list(entries.values())
    return entries


def _target_entries(typ: str) -> dict:
    """The entries of this system, as a deep copy since exporters may return cached objects."""
    return _keyed(_ADAPTERS[typ], copy.deepcopy(EXPORT_FUNCTIONS[typ]()))


def _has_active_admin_policy(policies: Iterable[dict]) -> bool:
    return any(policy.get("scope") == SCOPE.ADMIN and is_true(policy.get("active", True))
               for policy in policies)


def _admin_policy_warning(import_entries: dict, target: dict, entries: list, hits: dict) -> list:
    """
    Warn when this system has an active admin policy now but none after the import.
    ``hits`` maps an imported name to the stored name of the entry that the setter updates instead.
    """
    if not _has_active_admin_policy(target.values()):
        return []
    after = dict(target)
    for entry in entries:
        if entry.action == DELETE:
            after.pop(entry.key, None)
        elif entry.action in (CREATE, UPDATE):
            after.pop(hits.get(entry.key), None)
            # set_policy writes every field, a missing 'active' becomes the default True
            after[entry.key] = import_entries[entry.key]
    return [] if _has_active_admin_policy(after.values()) else [ADMIN_POLICY_WARNING]


def _stored_name_hits(adapter: _TypeAdapter, import_entries: dict, stored_entries: dict) -> dict:
    """
    Map each imported name without an entry of the same name on this system to the
    stored name of the entry that the setter of the type finds for it, if there is one.
    """
    if adapter.stored_name is None:
        return {}
    hits = {}
    for key in import_entries:
        if not isinstance(key, str) or key in stored_entries:
            continue
        stored = adapter.stored_name(key)
        if stored is not None and stored != key and stored in stored_entries:
            hits[key] = stored
    return hits


def _plan_name_keyed(typ: str, typ_data: dict | list | None, name: str | None, replace: bool,
                      skip_invalid: bool) -> TypePlan:
    adapter = _ADAPTERS[typ]
    if typ == "resolver" and isinstance(typ_data, list):
        # old style export, import_resolver takes it as well
        typ_data = {entry.get("resolvername"): entry for entry in typ_data}
    import_entries = _keyed(adapter, typ_data)
    if typ == "config":
        # keys starting with __ (e.g. __timestamp__) are specific to the instance
        import_entries = {key: value for key, value in import_entries.items() if not str(key).startswith("__")}
    if name is not None:
        # the names of folded types (e.g. realm) match regardless of case, so the filter compares folded names
        import_entries = {key: value for key, value in import_entries.items()
                          if (adapter.fold_name(key) if isinstance(key, str) else key) == adapter.fold_name(name)}
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

    hits = _stored_name_hits(adapter, import_entries, all_targets)
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
        if key in hits:
            target = all_targets[hits[key]]
            if adapter.name_field and not adapter.setter_renames:
                target = {**target, adapter.name_field: key}
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
                            for key, target in targets.items()
                            if key not in import_entries and key not in hits.values())
    if typ == "policy":
        plan.warnings.extend(_admin_policy_warning(import_entries, all_targets, plan.entries, hits))
    if typ == "realm":
        plan.default_realm = _plan_default_realm(import_entries, all_targets, plan.entries,
                                                 replace_all=replace and name is None)
        if plan.default_realm is None and get_default_realm():
            plan.warnings.append(NO_DEFAULT_REALM_WARNING)
    plan.data = _to_importer_format(adapter, to_import)
    return plan


def _plan_default_realm(import_entries: dict, stored_realms: dict, entries: list,
                        replace_all: bool) -> str | None | object:
    """
    Return the name of the default realm after the import, None for no default
    realm, or NO_DEFAULT_REALM_PLAN if the import does not change the default.

    A realm of the import that is marked as default becomes the default realm.
    If the import replaces all realms, the default realm follows the import, also
    if no realm of the import is marked as default. Else set_realm() makes the
    first realm that it creates on a system without realms the default realm.
    """
    marked = next((key for key, entry in import_entries.items() if is_true(entry.get("default"))), None)
    if marked is not None or replace_all:
        return marked
    if not stored_realms:
        return next((entry.key for entry in entries if entry.action == CREATE), NO_DEFAULT_REALM_PLAN)
    return NO_DEFAULT_REALM_PLAN


def _entry_count(count: int) -> str:
    return f"{count} entry" if count == 1 else f"{count} entries"


def _stored_event_handlers() -> list:
    """The event handlers of this system in the order of their ids, as a deep copy."""
    return sorted(copy.deepcopy(EXPORT_FUNCTIONS["event"]()), key=lambda handler: handler["id"])


def _as_imported(entry: dict, target_id: int) -> dict:
    """
    Return an event handler definition as import_event writes it over the stored handler with this id: a WebHook
    handler in the pre-3.15 inline shape gets the ``webhook`` option that links it to its webhook.
    """
    identifier = inline_webhook_link(entry, target_id)
    if identifier is None:
        return entry
    return {**entry, "options": {**entry["options"], "webhook": identifier}}


def _webhook_in_use(handler: dict, target_id: int | None = None) -> str | None:
    """
    Return the identifier of the webhook that an event handler uses, or None.

    :param handler: a stored event handler, or an imported definition
    :param target_id: for an imported definition, the id of the stored handler that import_event writes it over. None
        for a stored handler and for a new one: a new handler gets its id, and an inline one with it the name of its
        webhook, only when it is written.
    """
    if handler.get("handlermodule") != "WebHook":
        return None
    identifier = (handler.get("options") or {}).get("webhook")
    if identifier or target_id is None:
        return identifier or None
    return inline_webhook_link(handler, target_id)


def _webhooks_in_use(stored: list, replaced_ids: set, written: list) -> set:
    """
    Return the identifiers of the webhooks that the event handlers use after the import.

    :param stored: the event handlers of this system
    :param replaced_ids: the ids of the stored handlers that the import writes over or deletes
    :param written: the imported definitions that the import writes, each with the id of the stored handler that it
        is written over (None for a new handler)
    """
    in_use = {_webhook_in_use(handler) for handler in stored if handler["id"] not in replaced_ids}
    in_use.update(_webhook_in_use(entry, target_id) for entry, target_id in written)
    in_use.discard(None)
    return in_use


def _keep_webhooks_in_use(plan: TypePlan, in_use: dict) -> None:
    """
    Remove the planned deletions of the webhooks that are in use after the import, and add a note for each.

    :param plan: the plan of the type ``webhook``
    :param in_use: dict of webhook identifier -> what uses it, for the note (for example "an event handler uses it")
    """
    kept = [entry for entry in plan.entries if entry.action == DELETE and (entry.target_name or entry.key) in in_use]
    if not kept:
        return
    plan.entries = [entry for entry in plan.entries if not any(entry is kept_entry for kept_entry in kept)]
    plan.notes.extend(f'Webhook "{entry.target_name or entry.key}" is not deleted: '
                      f'{in_use[entry.target_name or entry.key]}.' for entry in kept)


def _plan_event(typ_data: list | None, name: str | None, replace: bool) -> TypePlan:
    """
    Plan the event handlers grouped by (name, handlermodule) like import_event:
    the n handlers of a group in the import replace the m handlers of this
    system in the order of their ids. With n < m the group is skipped, with
    ``replace`` the first n are updated and the other m - n deleted.

    A WebHook handler in the pre-3.15 inline shape is compared in the form that
    import_event writes, that is with the link to its webhook. One that
    import_event does not convert to a webhook is skipped and does not count for
    its group. With ``replace`` the handlers of this system with its name and
    handler module are kept, as a policy is kept whose import is skipped.
    """
    adapter = _ADAPTERS["event"]
    imported = defaultdict(list)
    without_name = []
    defective = []
    for entry in typ_data or []:
        if name is not None and entry.get("name") != name:
            continue
        if not entry.get("name"):
            without_name.append(entry)
            continue
        defect = inline_webhook_defect(entry)
        if defect:
            defective.append((entry, defect))
            continue
        imported[(entry["name"], entry.get("handlermodule"))].append(entry)
    stored = _stored_event_handlers()
    existing = defaultdict(list)
    for target in stored:
        if name is None or target.get("name") == name:
            existing[(target.get("name"), target.get("handlermodule"))].append(target)

    plan = TypePlan(typ="event")
    to_import = []
    # The ids of the stored handlers that the import writes over or deletes, and the definitions that it writes, each
    # with the id of the stored handler that it is written over (None for a new handler)
    replaced_ids = set()
    written = []
    for key, entries in imported.items():
        targets = existing.get(key, [])
        if not targets:
            plan.entries.append(PlanEntry(CREATE, key))
            to_import.extend(entries)
            written.extend((entry, None) for entry in entries)
            continue
        if len(entries) < len(targets) and not replace:
            plan.entries.append(PlanEntry(SKIP, key, reason=f"{_entry_count(len(entries))} in the import, "
                                                            f"{len(targets)} on this system, use --replace"))
            # import_event reports the skipped group, so it gets the entries as well
            to_import.extend(entries)
            continue
        changed = set()
        for entry, target in zip(entries, targets):
            changed.update(_changed_fields(_plain(adapter.normalize(_as_imported(entry, target["id"]))),
                                           _plain(adapter.normalize(target))))
        if changed or len(entries) > len(targets):
            plan.entries.append(PlanEntry(UPDATE, key, changed_fields=sorted(changed)))
            to_import.extend(entries)
            target_ids = [target["id"] for target in targets]
            replaced_ids.update(target_ids)
            written.extend((entry, target_ids[index] if index < len(target_ids) else None)
                           for index, entry in enumerate(entries))
        else:
            plan.entries.append(PlanEntry(UNCHANGED, key))
        surplus = targets[len(entries):]
        plan.entries.extend(PlanEntry(DELETE, key, target_id=target["id"]) for target in surplus)
        replaced_ids.update(target["id"] for target in surplus)
    for entry in without_name:
        plan.entries.append(PlanEntry(SKIP, (entry.get("name") or "", entry.get("handlermodule")),
                                      reason="the event handler has no name"))
        to_import.append(entry)
    defective_keys = set()
    for entry, defect in defective:
        key = (entry["name"], entry.get("handlermodule"))
        defective_keys.add(key)
        plan.entries.append(PlanEntry(SKIP, key, reason=defect))
        # import_event reports the definition, or skips it with skip_invalid
        to_import.append(entry)
    if replace:
        for key, targets in existing.items():
            if key not in imported and key not in defective_keys:
                plan.entries.extend(PlanEntry(DELETE, key, target_id=target["id"]) for target in targets)
                replaced_ids.update(target["id"] for target in targets)
    plan.data = to_import
    plan.webhooks_in_use = _webhooks_in_use(stored, replaced_ids, written)
    return plan


def build_import_plan(data: dict, types: Iterable[str], name: str | None = None, replace: bool = False,
                      skip_invalid: bool = False) -> list:
    """
    Compare the configuration data to be imported with this system.

    :param data: The parsed import data ``{typ: <exporter output>, ...}``, keys
        that are no registered import type are ignored. It is not modified.
    :param types: The type names to plan, ``"all"`` selects every type
    :param name: Only plan the entries with this name
    :param replace: Plan to delete the entries of a planned type that are
        missing from the import (never for ``config``, and never a webhook that
        an event handler or a conditional access policy uses after the import)
    :param skip_invalid: Drop policy actions that are not valid for this version
        before comparing, as ``import_policy`` does
    :return: a ``TypePlan`` for each selected type in ``data``, in import order
    :raises ValueError: if a selected type in ``data`` has no adapter in ``_ADAPTERS``, so that the import does
        not leave out the type without a message
    """
    types = set(types)
    data = copy.deepcopy(data)
    plans = []
    for typ in _import_order():
        if typ not in data or ("all" not in types and typ not in types):
            continue
        if typ not in _ADAPTERS:
            raise ValueError(f"The configuration type '{typ}' can not be compared with this system.")
        if typ == "event":
            plans.append(_plan_event(data[typ], name, replace))
        else:
            plans.append(_plan_name_keyed(typ, data[typ], name, replace, skip_invalid))

    by_type = {plan.typ: plan for plan in plans}
    webhook_plan = by_type.get("webhook")
    if webhook_plan and any(entry.action == DELETE for entry in webhook_plan.entries):
        # The webhooks are planned before the event handlers, which decide which webhooks are still in use
        event_plan = by_type.get("event")
        used_by_event_handlers = (event_plan.webhooks_in_use if event_plan
                                  else _webhooks_in_use(_stored_event_handlers(), set(), []))
        in_use = {identifier: "an event handler uses it" for identifier in used_by_event_handlers}
        for identifier, policy_names in _ca_policies_by_webhook().items():
            in_use.setdefault(identifier, _ca_policy_use(policy_names))
        _keep_webhooks_in_use(webhook_plan, in_use)

    for plan in plans:
        counts = defaultdict(int)
        for entry in plan.entries:
            counts[entry.action] += 1
        log.debug(f"Import plan for type '{plan.typ}': {dict(counts)}")
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


def _quote_or_none(name: str | None) -> str:
    return f'"{name}"' if name else "none"


def _default_realm_change(plan: TypePlan) -> tuple | None:
    """The current and the planned default realm, if the plan changes the default realm, else None."""
    if plan.default_realm is NO_DEFAULT_REALM_PLAN:
        return None
    current = get_default_realm() or None
    return (current, plan.default_realm) if current != plan.default_realm else None


def plan_has_changes(plans: list) -> bool:
    """Tell whether the plan contains an entry that is not unchanged or a change of the default realm."""
    return (any(entry.action != UNCHANGED for plan in plans for entry in plan.entries)
            or any(_default_realm_change(plan) for plan in plans))


def format_import_plan(plans: list) -> list:
    """
    Return the plan as text lines, one per entry followed by the notes and
    warnings of each type. Only names of entries and fields are printed,
    never the value of a field.
    """
    lines = []
    for plan in plans:
        lines.extend(_format_entry(plan.typ, entry) for entry in plan.entries)
        change = _default_realm_change(plan)
        if change:
            lines.append(f"  default realm: {_quote_or_none(change[0])} -> {_quote_or_none(change[1])}")
        lines.extend(f"  {text}" for text in plan.notes + plan.warnings)
    return lines


def _surplus_event_deletes(plan: TypePlan) -> list:
    """
    The planned deletions of event handlers of a group that is also in the
    import: import_event deletes them in its own transaction, because it skips
    a group with more handlers on this system than in the import.
    """
    if plan.typ != "event":
        return []
    imported_keys = {entry.key for entry in plan.entries if entry.action != DELETE}
    return [entry for entry in plan.entries if entry.action == DELETE and entry.key in imported_keys]


def apply_import_plan(plans: list, name: str | None = None, skip_invalid: bool = False,
                      on_import: Callable[[str], None] | None = None,
                      on_error: Callable[[str, PlanEntry | None, Exception], None] | None = None) -> list:
    """
    Apply an import plan of :func:`build_import_plan` to this system.

    The importers of the types run in import order with the data of the
    create and update entries only, so unchanged entries are not written
    again. Afterwards the planned deletions run in ``DELETE_ORDER``. The
    surplus event handlers of a group that is also in the import are deleted
    in the same transaction as the import of the event handlers.

    A failing importer or deletion is rolled back, reported with ``on_error``
    and the type is marked as failed. The remaining types and deletions are
    still applied, but the planned deletions of a type whose importer failed
    are not. If the deletion of the default realm fails, the realm stays the
    default realm, also if the plan removes the default realm.

    :param plans: the list of ``TypePlan`` objects
    :param name: passed to the importers of types with plain names, the plan data is already filtered by it
        (folded types like realm get None, since their importers compare the raw name with the folded key)
    :param skip_invalid: passed to the importers that support it
    :param on_import: called with the type before its importer runs
    :param on_error: called with the type, the plan entry of a failed deletion
        (None for a failed importer) and the exception
    :return: the failed types in the order they failed, without duplicates
    """
    failed = []
    import_failed = set()
    failed_realm_deletes = set()

    def fail(typ: str, entry: PlanEntry | None, exx: Exception) -> None:
        db.session.rollback()
        log.warning(f"Import of configuration type '{typ}' failed: {exx!r}")
        log.debug(traceback.format_exc())
        if typ not in failed:
            failed.append(typ)
        if on_error:
            on_error(typ, entry, exx)

    def delete(typ: str, entry: PlanEntry) -> None:
        try:
            delete_plan_entry(typ, entry)
        except Exception as exx:  # Any error of a delete function is reported, the others go on
            if typ == "realm":
                failed_realm_deletes.add(entry.target_name or entry.key)
            fail(typ, entry, exx)

    for plan in plans:
        surplus = _surplus_event_deletes(plan)
        if not plan.data and not surplus:
            continue
        if on_import:
            on_import(plan.typ)
        func = IMPORT_FUNCTIONS[plan.typ]["func"]
        # the plan data is already filtered by name, the importers of folded types would compare the raw name
        kwargs = {"name": name if _ADAPTERS[plan.typ].fold_name is str else None}
        if "skip_invalid" in inspect.signature(func).parameters:
            kwargs["skip_invalid"] = skip_invalid
        if surplus:
            # If the import fails, the rollback also restores the surplus event handlers
            kwargs["delete_ids"] = [entry.target_id for entry in surplus]
        try:
            func(plan.data or [], **kwargs)
        except Exception as exx:  # Any error of an importer is reported, the other types go on
            import_failed.add(plan.typ)
            fail(plan.typ, None, exx)

    by_type = {plan.typ: plan for plan in plans}
    # delete_realm() makes the last realm that is left the default realm, so the default is read before the deletions
    default_before_deletes = get_default_realm() or None
    for typ in DELETE_ORDER:
        plan = by_type.get(typ)
        if not plan or typ in import_failed:
            # The entries of a type whose importer failed are kept, so that the type is not left half replaced.
            continue
        surplus = {id(entry) for entry in _surplus_event_deletes(plan)}
        for entry in plan.entries:
            if entry.action == DELETE and id(entry) not in surplus:
                delete(typ, entry)

    realm_plan = by_type.get("realm")
    if (realm_plan and realm_plan.default_realm is not NO_DEFAULT_REALM_PLAN
            and "realm" not in import_failed):
        # The import keeps a default realm whose deletion failed, and the realm stays as it was, also as the default
        keep_default = realm_plan.default_realm is None and default_before_deletes in failed_realm_deletes
        try:
            if not keep_default and (get_default_realm() or None) != realm_plan.default_realm:
                set_default_realm(realm_plan.default_realm)
        except Exception as exx:  # Any error is reported, the other steps are done
            fail("realm", None, exx)
    return failed
