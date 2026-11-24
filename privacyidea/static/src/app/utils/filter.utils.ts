/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { MultiSelectFilterOption } from "@components/shared/multi-select-filter/multi-select-filter-option";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { parseBooleanValue } from "@utils/parse-boolean-value";
import { StringUtils } from "@utils/string.utils";

/**
 * Value equality for the query parameter records the list resources are built from.
 * Without it every keystroke produces a new object literal, which the default
 * `Object.is` equality reports as a change and the resource answers with a request,
 * even when the parameters themselves did not change.
 */
export function filterParamsEqual(a: Record<string, string>, b: Record<string, string>): boolean {
  const keys = Object.keys(a);
  if (keys.length !== Object.keys(b).length) {
    return false;
  }
  return keys.every((key) => a[key] === b[key]);
}

// Written before a filter value, asks for that value in full instead of anywhere in the field, e.g.
// `serial: =OATH0001`. The inline "filter by this value" buttons write their values this way.
const EXACT_MATCH_PREFIX = "=";

// Realm presence values of the tokenrealm and container_realm filters, written as `tokenrealm: *`
// and `tokenrealm: ""`. The backend reads the same values: any realm and no realm.
export const REALM_FILTER_WITH_REALM = "*";
export const REALM_FILTER_WITHOUT_REALM = "";
export const REALM_FILTER_WITH_REALM_LABEL = $localize`:@@common.filterWithRealm:With realm`;
export const REALM_FILTER_WITHOUT_REALM_LABEL = $localize`:@@common.filterWithoutRealm:Without realm`;

/** The options of a realm presence filter: with realm, without realm, then each realm. */
export function realmPresenceFilterOptions(realms: string[]): MultiSelectFilterOption[] {
  return [
    { label: REALM_FILTER_WITH_REALM_LABEL, value: REALM_FILTER_WITH_REALM },
    { label: REALM_FILTER_WITHOUT_REALM_LABEL, value: REALM_FILTER_WITHOUT_REALM },
    ...realms.map((realm) => ({ label: realm, value: realm }))
  ];
}

/**
 * The entries of a realm presence filter value: a quoted empty value is "without realm", an
 * asterisk-only entry is "with realm", the rest are realm names. Reads a value of `rawFilterMap`.
 */
export function splitRealmFilterList(value: string | null | undefined): string[] {
  if (value == null) {
    return [];
  }
  if (value.trim() === "") {
    return [REALM_FILTER_WITHOUT_REALM];
  }
  const entries = value
    .split(",")
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0)
    .map((entry) => (isWildcardOnly(entry) ? REALM_FILTER_WITH_REALM : entry));
  return Array.from(new Set(entries));
}

function isWildcardOnly(value: string): boolean {
  return /^\*+$/.test(value.trim());
}

/** The keyword sets of a table service that give an empty or a wildcard-only value a meaning of its own. */
export interface FilterKeyRules {
  /** See `FilterableTableService.keepEmptyKeys`. */
  keepEmptyKeys?: ReadonlySet<string>;
  /** See `FilterableTableService.presenceKeys`. */
  presenceKeys?: ReadonlySet<string>;
}

/**
 * The entries of a filter as they were typed, for `keyRuleParam`: a lone `*` and a quoted empty value
 * stay, and a key without a value yet comes with null. The hidden entries follow the visible ones, so
 * that a hidden entry wins over a visible one of the same key.
 */
export function typedFilterEntries(
  filter: FilterValue,
  { withHidden = false }: { withHidden?: boolean } = {}
): [string, string | null][] {
  const typed = (raw: Map<string, string>, parsed: Map<string, string>): [string, string | null][] => [
    ...raw.entries(),
    // A key that only the parsed map knows has no value yet: the raw map leaves out nothing else.
    ...[...parsed.keys()].filter((key) => !raw.has(key)).map((key): [string, null] => [key, null])
  ];
  const visible = typed(filter.rawFilterMap, filter.filterMap);
  return withHidden ? [...visible, ...typed(filter.rawHiddenFilterMap, filter.hiddenFilterMap)] : visible;
}

/**
 * The query parameter the key rules give a value, with null for a key without a value yet. Undefined
 * when no rule decides, so the value is mapped as usual, and an empty record when the rules send nothing.
 *
 * - `keepEmptyKeys`: an empty value, bare or quoted, is sent as `key=`.
 * - `presenceKeys`: a wildcard-only value, or a list with a wildcard-only entry, is sent as `key=*`, a
 *   quoted empty value as `key=`, and a bare key or a list without entries not at all.
 */
export function keyRuleParam(
  key: string,
  value: string | null | undefined,
  rules: FilterKeyRules
): Record<string, string> | undefined {
  const keepEmpty = rules.keepEmptyKeys?.has(key) ?? false;
  const presence = rules.presenceKeys?.has(key) ?? false;
  if (!keepEmpty && !presence) {
    return undefined;
  }
  if (value == null) {
    return keepEmpty ? { [key]: "" } : {};
  }
  if (value.trim() === "") {
    return { [key]: "" };
  }
  if (presence) {
    const entries = value
      .split(",")
      .map((entry) => entry.trim())
      .filter((entry) => entry.length > 0);
    if (entries.some(isWildcardOnly)) {
      return { [key]: "*" };
    }
    if (entries.length === 0) {
      return {};
    }
  }
  return undefined;
}

/** A filter value that matches the given text in full. */
export function exactMatch(value: string): string {
  return `${EXACT_MATCH_PREFIX}${value}`;
}

/** Whether a filter value asks for an exact match, and the text it matches. */
export function splitExactMatch(value: string): { exact: boolean; text: string } {
  return value.startsWith(EXACT_MATCH_PREFIX)
    ? { exact: true, text: value.slice(EXACT_MATCH_PREFIX.length).trim() }
    : { exact: false, text: value };
}

/**
 * Whether a text matches a filter term, ignoring case: in full for a term that asks for an exact match,
 * anywhere in it otherwise. For the tables that filter in the browser.
 */
export function matchesFilterTerm(text: string, term: string): boolean {
  const { exact, text: wanted } = splitExactMatch(term.trim());
  const haystack = text.toLowerCase();
  const needle = wanted.toLowerCase();
  return exact ? haystack === needle : haystack.includes(needle);
}

/**
 * A single query parameter, wrapped in wildcards unless the backend matches the key
 * exactly or the value asks for an exact match. An empty value yields no parameter at
 * all, because it would filter for everything the key can hold.
 */
export function toWildcardParam(
  key: string,
  value: string | null | undefined,
  plainKeys: ReadonlySet<string>
): Record<string, string> {
  const { exact, text } = splitExactMatch((value ?? "").trim());
  if (!StringUtils.validFilterValue(text)) return {};
  return { [key]: exact || plainKeys.has(key) ? text : `*${text}*` };
}

/**
 * The query parameters for the entries a backend accepts, skipping the keys it does not
 * know and the values it cannot use. The key rules decide first, so pass entries that keep
 * what was typed (`typedFilterEntries`) when a rule set is not empty.
 */
export function buildFilterParams(
  entries: Iterable<readonly [string, string | null | undefined]>,
  allowed: string[],
  plainKeys: ReadonlySet<string> = new Set(),
  rules: FilterKeyRules = {}
): Record<string, string> {
  return Object.fromEntries(
    Array.from(entries)
      .filter(([key]) => allowed.includes(key))
      .flatMap(([key, value]) =>
        Object.entries(keyRuleParam(key, value, rules) ?? toWildcardParam(key, value, plainKeys))
      )
  );
}

/**
 * The spelling the backend expects for a boolean, and undefined for a value that does
 * not read as one.
 */
export function toBooleanParam(value: string): string | undefined {
  const lower = value.toLowerCase();
  if (lower !== "true" && lower !== "1" && lower !== "false" && lower !== "0") {
    return undefined;
  }
  return parseBooleanValue(value) ? "True" : "False";
}

/**
 * Scopes a filter to a realm, because a username is only unique within one. A filter
 * that already names a realm, and one without a user, keep the realm they have.
 */
export function withDefaultRealm(filter: FilterValue, defaultRealm: string): FilterValue {
  if (!defaultRealm || !filter.hasKey("user") || filter.hasKey("realm")) {
    return filter;
  }
  return filter.addEntry("realm", defaultRealm);
}

/**
 * Filters by one user. The backend resolves a user only within a realm, so the user's realm goes
 * along with the name, and a realm the filter held for an earlier user is dropped when this one has none.
 */
export function withUser(filter: FilterValue, username: string, realm: string | undefined): FilterValue {
  const withName = filter.addEntry("user", username);
  return realm ? withName.addEntry("realm", realm) : withName.removeKey("realm");
}
