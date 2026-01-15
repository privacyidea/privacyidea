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

import { Component, computed, inject, input, output, ViewChild } from "@angular/core";
import { CommonModule } from "@angular/common";
import { AbstractControl, FormControl, FormsModule, ReactiveFormsModule, ValidationErrors } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { RealmService, RealmServiceInterface } from "../../../../../services/realm/realm.service";
import { ResolverService } from "../../../../../services/resolver/resolver.service";
import { MatInputModule } from "@angular/material/input";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { PolicyDetail, PolicyService } from "../../../../../services/policies/policies.service";
import { MatTooltip } from "@angular/material/tooltip";
import { MultiSelectOnlyComponent } from "../../../../shared/multi-select-only/multi-select-only.component";

@Component({
  selector: "app-conditions-user",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatInputModule,
    MatAutocompleteModule,
    MatSelectModule,
    MatButtonModule,
    MatExpansionModule,
    ReactiveFormsModule,
    MultiSelectOnlyComponent
  ],
  templateUrl: "./conditions-user.component.html",
  styleUrl: "./conditions-user.component.scss"
})
export class ConditionsUserComponent {
  // ViewChild
  @ViewChild("resolverSelect") resolverSelect!: MatSelect;
  @ViewChild("realmSelect") realmSelect!: MatSelect;
  // Services
  realmService: RealmServiceInterface = inject(RealmService);
  resolverService: ResolverService = inject(ResolverService);
  policyService = inject(PolicyService);
  // Component State
  isEditMode = input.required<boolean>();
  policy = input.required<PolicyDetail>();
  policyEdit = output<Partial<PolicyDetail>>();
  emitEdits(edits: Partial<PolicyDetail>) {
    this.policyEdit.emit(edits);
  }

  // Form Controls
  userFormControl = new FormControl<string>("", this.userValidator.bind(this));
  // Computed Properties
  selectedRealms = computed(() => this.policy().realm || []);
  selectedResolvers = computed(() => this.policy().resolver || []);
  selectedUsers = computed(() => this.policy().user || []);
  userCaseInsensitive = computed(() => this.policy().user_case_insensitive || false);
  isAllRealmsSelected = computed(() => this.selectedRealms().length === this.realmService.realmOptions().length);
  isAllResolversSelected = computed(
    () => this.selectedResolvers().length === this.resolverService.resolverOptions().length
  );
  availableRealms = computed(() => {
    const selectedResolvers = this.selectedResolvers();
    if (selectedResolvers.length === 0) {
      // No resolvers selected, return all realms
      return this.realmService.realmOptions();
    }
    const realms = this.realmService.realms();
    let availableRealms: string[] = [];
    for (const [realmName, realm] of Object.entries(realms)) {
      const realmResolvers = realm.resolver.map((r) => r.name);
      if (selectedResolvers.some((sr) => realmResolvers.includes(sr))) {
        availableRealms.push(realmName);
      }
    }
    return availableRealms;
  });
  availableResolvers = computed(() => {
    const selectedRealms = this.selectedRealms();
    if (selectedRealms.length === 0) {
      // No realms selected, return all resolvers
      return this.resolverService.resolverOptions();
    }
    const realms = this.realmService.realms();
    let availableResolversSet: Set<string> = new Set();
    for (const realmName of selectedRealms) {
      const realm = realms[realmName];
      if (realm) {
        realm.resolver.forEach((r) => {
          return availableResolversSet.add(r.name);
        });
      }
    }
    return Array.from(availableResolversSet);
  });
  selectResolverTooltip = computed(() => {
    if (this.availableResolvers().length === 0) {
      return $localize`No resolvers available for the selected realms.`;
    }
    return "";
  });
  selectRealmTooltip = computed(() => {
    if (this.availableRealms().length === 0) {
      return $localize`No realms available for the selected resolvers.`;
    }
    return "";
  });
  // Realm Management
  selectRealm(realmNames: string[]): void {
    this.emitEdits({ realm: realmNames });
  }
  toggleAllRealms() {
    if (this.isAllRealmsSelected()) {
      this.emitEdits({ realm: [] });
    } else {
      const allRealms = this.realmService.realmOptions();
      this.emitEdits({ realm: allRealms });
    }
    setTimeout(() => {
      this.realmSelect.close();
    });
  }
  // Resolver Management
  selectResolver(resolverNames: string[]): void {
    this.emitEdits({ resolver: resolverNames });
  }
  toggleAllResolvers() {
    if (this.isAllResolversSelected()) {
      this.emitEdits({ resolver: [] });
    } else {
      const allResolvers = this.resolverService.resolverOptions();
      this.emitEdits({ resolver: allResolvers });
    }
    setTimeout(() => {
      this.resolverSelect.close();
    });
  }
  // User Management
  addUser(user: string) {
    if (this.userFormControl.invalid) {
      return;
    }
    if (user && !this.selectedUsers().includes(user)) {
      this.emitEdits({ user: [...this.selectedUsers(), user] });
    }
  }
  removeUser(user: string) {
    this.emitEdits({ user: this.selectedUsers().filter((u) => u !== user) });
  }
  clearUsers() {
    this.emitEdits({ user: [] });
  }
  toggleUserCaseInsensitive() {
    this.emitEdits({ user_case_insensitive: !this.userCaseInsensitive() });
  }
  // Validators
  userValidator(control: AbstractControl): ValidationErrors | null {
    return /[,]/.test(control.value) ? { includesComma: { value: control.value } } : null;
  }
}
