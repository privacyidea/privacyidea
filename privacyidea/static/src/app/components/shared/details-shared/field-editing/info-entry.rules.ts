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
import { SchemaPathTree, validate } from "@angular/forms/signals";
import { ERR } from "@utils/form-rules.utils";

/** The "add key and value" row of an information card. */
export interface InfoEntry {
  key: string;
  value: string;
}

/** Error kind of a key that is already present in the information. */
export const INFO_KEY_EXISTS = "keyExists";

/**
 * Rules of the "add key and value" row. The row may stay empty, but once one of its inputs is filled in the other
 * one is required too. The key must not be one that `existingKeys` already holds, because adding it would
 * silently replace the value of that entry. Both inputs are compared trimmed, like the save does.
 */
export function infoEntryRules(path: SchemaPathTree<InfoEntry>, existingKeys: () => readonly string[]): void {
  validate(path.key, (ctx) => {
    const key = ctx.value().trim();
    if (key === "") {
      return ctx.valueOf(path.value).trim() === "" ? [] : [{ kind: ERR.required }];
    }
    return existingKeys().includes(key) ? [{ kind: INFO_KEY_EXISTS }] : [];
  });
  validate(path.value, (ctx) =>
    ctx.value().trim() === "" && ctx.valueOf(path.key).trim() !== "" ? [{ kind: ERR.required }] : []
  );
}
