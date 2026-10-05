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
 * What the value of a boolean action means, like the backend decides it: true for no value, an empty value or one of
 * 1, "1", true, "True", "true" and "TRUE"; false for false, 0, "0" and "false" in any case; null for any other value,
 * like "hotp". The backend stores a boolean action saved with a false value as excluded action and rejects any other
 * value.
 */
export function boolActionValue(value: string | boolean | number | null | undefined): boolean | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (["false", "0"].includes(trimmed.toLowerCase())) return false;
    return trimmed === "" || ["1", "True", "true", "TRUE"].includes(trimmed) ? true : null;
  }
  if (value === undefined || value === null || value === true || value === 1) return true;
  return value === false || value === 0 ? false : null;
}

/**
 * Whether the stored value of an action does not fit its definition: a boolean action whose value does not enable
 * it, an integer action with a value that is no integer, or an action with a list of values and a value outside of it.
 * A list that is empty, like the realms of a fresh installation, is not checked.
 */
export function actionValueIsInvalid(detail: PolicyActionDetail, value: string | number | boolean): boolean {
  if (detail.type === "bool") return boolActionValue(value) !== true;
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
