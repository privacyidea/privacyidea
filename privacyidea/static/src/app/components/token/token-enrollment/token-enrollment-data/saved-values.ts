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

import { signal } from "@angular/core";

/**
 * Remembers once-only enrollment data by value. A component that pages between tokens keeps what was saved for each
 * of them, and a regenerated value counts as unsaved again.
 */
export class SavedValues {
  private readonly values = signal<ReadonlySet<string>>(new Set());

  has(value: string): boolean {
    return this.values().has(value);
  }

  add(value: string): void {
    this.values.update((values) => new Set(values).add(value));
  }
}
