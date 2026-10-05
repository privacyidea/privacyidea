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
import type { PolicyActionDetail } from "@services/policies/policies.service";

/**
 * An action with a leading "-" or "!" is excluded from the policy, also from a "*" in it.
 */
export function isExcludedActionName(name: string): boolean {
  return name.startsWith("-") || name.startsWith("!");
}

export function actionNameWithoutExclusion(name: string): string {
  return isExcludedActionName(name) ? name.slice(1) : name;
}

/**
 * Whether the value of a boolean action enables it, like the backend decides it: no value, an empty value or one of
 * 1, "1", true, "True", "true" and "TRUE". The backend stores a boolean action saved with any other value as excluded
 * action, the WebUI leaves it out when saving a policy.
 */
export function boolActionValueEnablesAction(value: string | boolean | number | null | undefined): boolean {
  if (value === undefined || value === null || value === true || value === 1) return true;
  if (typeof value !== "string") return false;
  const trimmed = value.trim();
  return trimmed === "" || ["1", "True", "true", "TRUE"].includes(trimmed);
}

/**
 * The actions without the boolean actions whose value does not enable them. Saving a policy in the WebUI sends these
 * actions, so such an action is removed from the policy instead of being stored as excluded action.
 */
export function withoutDisablingBoolActions(
  actions: Record<string, string | boolean>,
  detailOf: (name: string) => PolicyActionDetail | null
): Record<string, string | boolean> {
  return Object.fromEntries(
    Object.entries(actions).filter(
      ([name, value]) =>
        isExcludedActionName(name) || detailOf(name)?.type !== "bool" || boolActionValueEnablesAction(value)
    )
  );
}

/**
 * Whether the stored value of an action does not fit its definition: a boolean action whose value does not enable
 * it, an integer action with a value that is no integer, or an action with a list of values and a value outside of it.
 * A list that is empty, like the realms of a fresh installation, is not checked.
 */
export function actionValueIsInvalid(detail: PolicyActionDetail, value: string | number | boolean): boolean {
  if (detail.type === "bool") return !boolActionValueEnablesAction(value);
  const values =
    detail.multiple && typeof value === "string" ? value.split(" ").filter((part) => part !== "") : [value];
  if (detail.type === "int" && values.some((part) => String(part).trim() === "" || !Number.isInteger(Number(part)))) {
    return true;
  }
  if (detail.value?.length) {
    const allowedValues = detail.value.map(String);
    return values.some((part) => !allowedValues.includes(String(part)));
  }
  return false;
}
