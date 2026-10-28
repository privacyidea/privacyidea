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

import { computed, Injectable, signal } from "@angular/core";

export type PolicyActionDraftValue = string | number | boolean;

/**
 * The action values being edited that do not suit their action, by action name. An invalid value never reaches the
 * policy, so it is kept here: a row that is destroyed (closed tab, action filter) shows it again when it is created
 * anew, and the panel blocks the save while one is left. Provided by the policy panel, so it lives as long as the edit.
 */
@Injectable()
export class PolicyActionDrafts {
  private readonly drafts = signal<Record<string, PolicyActionDraftValue>>({});

  /** Names of the actions that hold an invalid value. */
  readonly names = computed(() => Object.keys(this.drafts()));

  get(name: string): PolicyActionDraftValue | undefined {
    return this.drafts()[name];
  }

  has(name: string): boolean {
    return name in this.drafts();
  }

  set(name: string, value: PolicyActionDraftValue): void {
    this.drafts.update((drafts) => (name in drafts && drafts[name] === value ? drafts : { ...drafts, [name]: value }));
  }

  clear(name: string): void {
    this.drafts.update((drafts) => {
      if (!(name in drafts)) return drafts;
      const rest = { ...drafts };
      delete rest[name];
      return rest;
    });
  }
}
