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
import { computed, Injectable, Signal, signal } from "@angular/core";

/**
 * A self-contained detail field that manages its own edit state and persistence.
 * Field components register a handle so the host (token/container details) can
 * aggregate "is anything editing?" and "save all" without iterating a data list
 * or querying the view tree.
 */
export interface DetailFieldHandle {
  readonly isEditing: Signal<boolean>;
  save(): void | Promise<void>;
  cancel(): void;
}

@Injectable()
export class DetailsEditRegistry {
  private readonly fields = signal<readonly DetailFieldHandle[]>([]);

  readonly anyEditing = computed(() => this.fields().some((field) => field.isEditing()));

  register(field: DetailFieldHandle): void {
    this.fields.update((list) => (list.includes(field) ? list : [...list, field]));
  }

  unregister(field: DetailFieldHandle): void {
    this.fields.update((list) => list.filter((entry) => entry !== field));
  }

  async saveAll(): Promise<void> {
    for (const field of this.fields()) {
      if (field.isEditing()) {
        await field.save();
      }
    }
  }

  cancelAll(): void {
    for (const field of this.fields()) {
      if (field.isEditing()) {
        field.cancel();
      }
    }
  }
}
