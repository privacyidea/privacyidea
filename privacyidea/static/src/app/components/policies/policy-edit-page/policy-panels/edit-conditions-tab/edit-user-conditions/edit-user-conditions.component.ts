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

import { Component, computed, effect, inject, input, linkedSignal, output, untracked, ViewChild } from "@angular/core";

import { form, FormField } from "@angular/forms/signals";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { ChipListInputComponent } from "@components/shared/chip-list-input/chip-list-input.component";
import { MultiSelectOnlyComponent } from "@components/shared/multi-select-only/multi-select-only.component";
import { PolicyDetail, PolicyService } from "@services/policies/policies.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { ResolverService, ResolverServiceInterface } from "@services/resolver/resolver.service";

@Component({
  selector: "app-edit-user-conditions",
  standalone: true,
  imports: [
    FormField,
    MatIconModule,
    MatAutocompleteModule,
    MatSelectModule,
    MatButtonModule,
    MatExpansionModule,
    MultiSelectOnlyComponent,
    MatCheckboxModule,
    ChipListInputComponent
  ],
  templateUrl: "./edit-user-conditions.component.html",
  styleUrl: "./edit-user-conditions.component.scss"
})
export class EditUserConditionsComponent {
  @ViewChild("resolverSelect") resolverSelect!: MatSelect;
  @ViewChild("realmSelect") realmSelect!: MatSelect;

  readonly realmService: RealmServiceInterface = inject(RealmService);
  readonly resolverService: ResolverServiceInterface = inject(ResolverService);
  readonly policyService = inject(PolicyService);

  readonly policy = input.required<PolicyDetail>();
  readonly policyEdit = output<Partial<PolicyDetail>>();

  readonly selectedRealms = computed(() => this.policy().realm || []);
  readonly selectedResolvers = computed(() => this.policy().resolver || []);
  readonly selectedUsers = computed(() => this.policy().user || []);
  readonly userCaseInsensitive = computed(() => this.policy().user_case_insensitive || false);
  /** The state of the checkbox. It follows the policy and hands its own changes to the policy as edits. */
  readonly caseInsensitive = linkedSignal(() => this.userCaseInsensitive());
  readonly caseInsensitiveField = form(this.caseInsensitive);

  readonly isAllRealmsSelected = computed(
    () => this.selectedRealms().length === this.realmService.realmOptions().length
  );
  readonly isAllResolversSelected = computed(
    () => this.selectedResolvers().length === this.resolverService.resolverOptions().length
  );

  readonly availableRealms = computed(() => {
    const selectedResolvers = this.selectedResolvers();
    if (selectedResolvers.length === 0) {
      return this.realmService.realmOptions();
    }
    const realms = this.realmService.realms();
    return Object.entries(realms)
      .filter(([, realm]) => realm.resolver.some((r) => selectedResolvers.includes(r.name)))
      .map(([name]) => name);
  });

  readonly availableResolvers = computed(() => {
    const selectedRealms = this.selectedRealms();
    if (selectedRealms.length === 0) {
      return this.resolverService.resolverOptions();
    }
    const realms = this.realmService.realms();
    const resolversSet = new Set<string>();
    selectedRealms.forEach((realmName) => {
      realms[realmName]?.resolver.forEach((r) => resolversSet.add(r.name));
    });
    return Array.from(resolversSet);
  });

  readonly selectResolverTooltip = computed(() =>
    this.availableResolvers().length === 0
      ? $localize`:@@policy.noResolversAvailable:No resolvers available for the selected realms.`
      : ""
  );

  readonly selectRealmTooltip = computed(() =>
    this.availableRealms().length === 0
      ? $localize`:@@policy.noRealmsAvailable:No realms available for the selected resolvers.`
      : ""
  );

  constructor() {
    effect(() => {
      const caseInsensitive = this.caseInsensitive();
      if (caseInsensitive !== untracked(this.userCaseInsensitive)) {
        this.emitEdits({ user_case_insensitive: caseInsensitive });
      }
    });
  }

  emitEdits(edits: Partial<PolicyDetail>) {
    this.policyEdit.emit(edits);
  }

  selectRealm(realmNames: string[]): void {
    this.emitEdits({ realm: realmNames });
  }

  toggleAllRealms() {
    this.emitEdits({ realm: this.isAllRealmsSelected() ? [] : this.realmService.realmOptions() });
    setTimeout(() => this.realmSelect?.close());
  }

  selectResolver(resolverNames: string[]): void {
    this.emitEdits({ resolver: resolverNames });
  }

  toggleAllResolvers() {
    this.emitEdits({ resolver: this.isAllResolversSelected() ? [] : this.resolverService.resolverOptions() });
    setTimeout(() => this.resolverSelect?.close());
  }

  clearUsers() {
    this.emitEdits({ user: [] });
  }
}
