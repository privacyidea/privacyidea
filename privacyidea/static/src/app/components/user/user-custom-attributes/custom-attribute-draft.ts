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
import { computed, effect, inject, signal } from "@angular/core";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { firstValueFrom } from "rxjs";

/**
 * The state of the custom attribute card: the key and value being entered and the helpers derived from the
 * attribute policy of the server. The admin user details page and the self-service page each own one.
 * Must be created in an injection context.
 */
export class CustomAttributeDraft {
  private readonly userService: UserServiceInterface = inject(UserService);

  readonly attributeSetMap = this.userService.attributeSetMap;
  readonly deletableAttributes = this.userService.deletableAttributes;
  readonly keyOptions = this.userService.keyOptions;
  readonly hasWildcardKey = this.userService.hasWildcardKey;
  readonly attributesList = this.userService.userAttributesList;
  readonly canSetCustomAttribute = computed(() => this.keyOptions().length > 0 || this.hasWildcardKey());

  readonly addKeyInput = signal<string>("");
  readonly addValueInput = signal<string>("");
  readonly selectedKey = signal<string | null>(null);
  readonly selectedValue = signal<string | null>(null);
  readonly keyMode = signal<"select" | "input">("select");
  // The empty row for a new attribute is shown only after the add button was clicked.
  readonly isAdding = signal(false);

  readonly valueOptions = computed<string[]>(() => {
    const map = this.attributeSetMap();
    const key = this.keyMode() === "input" ? this.addKeyInput().trim() : (this.selectedKey() ?? "");
    if (key && map[key]) return map[key];
    if (map["*"]) return map["*"];
    return [];
  });
  readonly isValueInput = computed<boolean>(() => {
    const opts = this.valueOptions();
    if (opts.includes("*")) return true;
    return opts.length === 0;
  });
  readonly key = computed(() =>
    this.keyMode() === "input" ? this.addKeyInput().trim() : (this.selectedKey() ?? "").trim()
  );
  readonly value = computed(() =>
    this.isValueInput() ? this.addValueInput().trim() : (this.selectedValue() ?? "").trim()
  );
  readonly canAddAttribute = computed<boolean>(() => this.key().length > 0 && this.value().length > 0);
  readonly hasInput = computed(
    () => !!this.addKeyInput() || !!this.addValueInput() || !!this.selectedKey() || !!this.selectedValue()
  );

  // The stored attribute whose value is edited in its own row, and the value entered there.
  readonly editingKey = signal<string | null>(null);
  readonly editValue = signal<string>("");
  readonly editValueOptions = computed<string[]>(() => {
    const map = this.attributeSetMap();
    const key = this.editingKey();
    if (key && map[key]) return map[key];
    return map["*"] ?? [];
  });
  readonly isEditValueInput = computed<boolean>(() => {
    const opts = this.editValueOptions();
    return opts.includes("*") || opts.length === 0;
  });
  readonly canSaveEdit = computed<boolean>(() => this.editingKey() !== null && this.editValue().trim().length > 0);
  readonly hasChanges = computed(() => this.hasInput() || this.editingKey() !== null);

  constructor() {
    effect(() => {
      const hasWildcard = this.hasWildcardKey();
      const hasFixedKeys = this.keyOptions().length > 0;
      if (hasWildcard && !hasFixedKeys) {
        this.keyMode.set("input");
      } else {
        this.keyMode.set("select");
      }
    });
  }

  canEdit(key: string): boolean {
    return this.hasWildcardKey() || Object.prototype.hasOwnProperty.call(this.attributeSetMap(), key);
  }

  startEdit(key: string, value: string) {
    this.editingKey.set(key);
    this.editValue.set(value);
  }

  cancelEdit() {
    this.editingKey.set(null);
    this.editValue.set("");
  }

  async saveEdit(): Promise<boolean> {
    const key = this.editingKey();
    const value = this.editValue().trim();
    if (!key || !value) return false;

    try {
      await firstValueFrom(this.userService.setUserAttribute(key, value));
      this.userService.userAttributesResource.reload();
      this.userService.userResource.reload();
      this.cancelEdit();
      return true;
    } catch {
      return false;
    }
  }

  startAdd() {
    this.isAdding.set(true);
  }

  clearInput() {
    this.isAdding.set(false);
    this.addKeyInput.set("");
    this.addValueInput.set("");
    this.selectedKey.set(null);
    this.selectedValue.set(null);
  }

  switchToCustomKey() {
    this.keyMode.set("input");
    this.selectedKey.set(null);
  }

  switchToSelectKey() {
    this.keyMode.set("select");
    this.addKeyInput.set("");
  }

  async add(): Promise<boolean> {
    const key = this.key();
    const value = this.value();

    if (!key || !value) return false;

    try {
      await firstValueFrom(this.userService.setUserAttribute(key, value));
      this.userService.userAttributesResource.reload();
      this.userService.userResource.reload();
      this.clearInput();
      return true;
    } catch {
      return false;
    }
  }

  delete(key: string) {
    this.userService.deleteUserAttribute(key).subscribe({
      next: () => {
        this.userService.userAttributesResource.reload();
        this.userService.userResource.reload();
      }
    });
  }
}
