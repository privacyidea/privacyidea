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

@Component({
  selector: "app-conditions-admin",
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
  templateUrl: "./conditions-admin.component.html",
  styleUrl: "./conditions-admin.component.scss"
})
export class ConditionsAdminComponent {
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
  policyEdit = output<PolicyDetail>();

  // Form Controls
  adminFormControl = new FormControl<string>("", this.adminValidator.bind(this));

  // Computed Properties
  selectedRealms = computed(() => this.policy().realm || []);
  selectedResolvers = computed(() => this.policy().resolver || []);
  selectedAdmins = computed(() => this.policy().adminuser || []);
  selectedAdminrealm = computed(() => this.policy().adminrealm || []);

  isAllRealmsSelected = computed(() => this.selectedRealms().length === this.realmService.realmOptions().length);
  isAllResolversSelected = computed(
    () => this.selectedResolvers().length === this.resolverService.resolverOptions().length
  );

  // Realm Management
  selectRealm(realmNames: string[]): void {
    this.updatePolicy({ realm: realmNames });
  }

  toggleAllRealms() {
    if (this.isAllRealmsSelected()) {
      this.updatePolicy({ realm: [] });
    } else {
      const allRealms = this.realmService.realmOptions();
      this.updatePolicy({ realm: allRealms });
    }
    setTimeout(() => {
      this.realmSelect.close();
    });
  }

  // Resolver Management
  selectResolver(resolverNames: string[]): void {
    this.updatePolicy({ resolver: resolverNames });
  }

  toggleAllResolvers() {
    if (this.isAllResolversSelected()) {
      this.updatePolicy({ resolver: [] });
    } else {
      const allResolvers = this.resolverService.resolverOptions();
      this.updatePolicy({ resolver: allResolvers });
    }
    setTimeout(() => {
      this.resolverSelect.close();
    });
  }

  // Admin Management
  addAdmin(adminuser: string) {
    if (this.adminFormControl.invalid) {
      return;
    }
    if (adminuser && !this.selectedAdmins().includes(adminuser)) {
      this.updatePolicy({ adminuser: [...this.selectedAdmins(), adminuser] });
    }
  }

  removeAdmin(adminuser: string) {
    this.updatePolicy({ adminuser: this.selectedAdmins().filter((u) => u !== adminuser) });
  }

  clearAdmins() {
    this.updatePolicy({ adminuser: [] });
  }

  // Validators
  adminValidator(control: AbstractControl): ValidationErrors | null {
    return /[,]/.test(control.value) ? { includesComma: { value: control.value } } : null;
  }

  updatePolicy(patch: Partial<PolicyDetail>) {
    this.policyEdit.emit({ ...this.policy(), ...patch });
  }
}
