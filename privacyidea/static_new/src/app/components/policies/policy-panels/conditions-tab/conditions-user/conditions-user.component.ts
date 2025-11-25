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

import { Component, computed, inject, input, ViewChild } from "@angular/core";
import { CommonModule } from "@angular/common";
import {
  AbstractControl,
  FormControl,
  FormsModule,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn
} from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { RealmService, RealmServiceInterface } from "../../../../../services/realm/realm.service";
import { ResolverService } from "../../../../../services/resolver/resolver.service";
import { MatInputModule } from "@angular/material/input";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { PolicyService } from "../../../../../services/policies/policies.service";

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
    ReactiveFormsModule
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
  isEditMode = this.policyService.isEditMode;

  // Form Controls
  userFormControl = new FormControl<string>("", this.userValidator.bind(this));

  // Computed Properties
  selectedRealms = computed(() => this.policyService.selectedPolicy()?.realm || []);
  selectedResolvers = computed(() => this.policyService.selectedPolicy()?.resolver || []);
  selectedUsers = computed(() => this.policyService.selectedPolicy()?.user || []);
  userCaseInsensitive = computed(() => this.policyService.selectedPolicy()?.user_case_insensitive || false);
  isAllRealmsSelected = computed(() => this.selectedRealms().length === this.realmService.realmOptions().length);
  isAllResolversSelected = computed(
    () => this.selectedResolvers().length === this.resolverService.resolverOptions().length
  );

  // Realm Management
  selectRealm(realmNames: string[]): void {
    this.policyService.updateSelectedPolicy({ realm: realmNames });
  }

  toggleAllRealms() {
    if (this.isAllRealmsSelected()) {
      this.policyService.updateSelectedPolicy({ realm: [] });
    } else {
      const allRealms = this.realmService.realmOptions();
      this.policyService.updateSelectedPolicy({ realm: allRealms });
    }
    setTimeout(() => {
      this.realmSelect.close();
    });
  }

  // Resolver Management
  selectResolver(resolverNames: string[]): void {
    this.policyService.updateSelectedPolicy({ resolver: resolverNames });
  }

  toggleAllResolvers() {
    if (this.isAllResolversSelected()) {
      this.policyService.updateSelectedPolicy({ resolver: [] });
    } else {
      const allResolvers = this.resolverService.resolverOptions();
      this.policyService.updateSelectedPolicy({ resolver: allResolvers });
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
      this.policyService.updateSelectedPolicy({ user: [...this.selectedUsers(), user] });
    }
  }

  removeUser(user: string) {
    this.policyService.updateSelectedPolicy({ user: this.selectedUsers().filter((u) => u !== user) });
  }

  clearUsers() {
    this.policyService.updateSelectedPolicy({ user: [] });
  }

  toggleUserCaseInsensitive() {
    this.policyService.updateSelectedPolicy({ user_case_insensitive: !this.userCaseInsensitive() });
  }

  // Validators
  userValidator(control: AbstractControl): ValidationErrors | null {
    return /[,]/.test(control.value) ? { includesComma: { value: control.value } } : null;
  }
}
