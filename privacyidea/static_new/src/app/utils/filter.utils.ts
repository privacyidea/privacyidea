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

/**
 * A single query parameter, wrapped in wildcards unless the backend matches the key
 * exactly. An empty value yields no parameter at all, because it would filter for
 * everything the key can hold.
 */
export function toWildcardParam(
  key: string,
  value: string | null | undefined,
  plainKeys: ReadonlySet<string>
): Record<string, string> {
  const trimmed = (value ?? "").trim();
  if (!StringUtils.validFilterValue(trimmed)) return {};
  return { [key]: plainKeys.has(key) ? trimmed : `*${trimmed}*` };
}

/**
 * The query parameters for the entries a backend accepts, skipping the keys it does not
 * know and the values it cannot use.
 */
export function buildFilterParams(
  entries: Iterable<readonly [string, string | null | undefined]>,
  allowed: string[],
  plainKeys: ReadonlySet<string> = new Set()
): Record<string, string> {
  return Object.fromEntries(
    Array.from(entries)
      .filter(([key]) => allowed.includes(key))
      .flatMap(([key, value]) => Object.entries(toWildcardParam(key, value, plainKeys)))
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
