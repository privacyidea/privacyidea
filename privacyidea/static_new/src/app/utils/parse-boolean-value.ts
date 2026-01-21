/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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

import { assert } from "./assert";

export function parseBooleanValue(initialValue: string | number | boolean): boolean {
  const typeofInitialValue = typeof initialValue;
  if (typeofInitialValue === "boolean") {
    return !!initialValue;
  }
  if (typeofInitialValue === "number") {
    if (initialValue === 1) return true;
    if (initialValue === 0) return false;
    assert(false, `Initial value for parseBooleanValue must be 0 or 1 if number, but was ${initialValue}`);
  }
  if (typeofInitialValue === "string") {
    const lower = String(initialValue).toLowerCase();
    if (lower === "true" || lower === "1") return true;
    if (lower === "false" || lower === "0") return false;
    assert(
      false,
      `Initial value for parseBooleanValue must be "true", "false", "1" or "0" if string, but was ${initialValue}`
    );
  }
  assert(
    false,
    `Initial value for parseBooleanValue must be boolean, 0, 1, "true", "false", "1" or "0", but was ${initialValue}`
  );
  return false;
}
