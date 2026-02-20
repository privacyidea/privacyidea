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

import { Component, computed, inject, output, ViewChild, input } from "@angular/core";
import { CommonModule } from "@angular/common";
import { AbstractControl, FormControl, FormsModule, ReactiveFormsModule, ValidationErrors } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { PolicyService, PolicyDetail } from "../../../../../../../services/policies/policies.service";
import { RealmServiceInterface, RealmService } from "../../../../../../../services/realm/realm.service";
import { ResolverService, ResolverServiceInterface } from "../../../../../../../services/resolver/resolver.service";
import { MultiSelectOnlyComponent } from "../../../../../../shared/multi-select-only/multi-select-only.component";

@Component({
  selector: "app-edit-admin-conditions",
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
  templateUrl: "./edit-admin-conditions.component.html",
  styleUrl: "./edit-admin-conditions.component.scss"
})
export class EditAdminConditionsComponent {
  @ViewChild("resolverSelect") resolverSelect!: MatSelect;
  @ViewChild("realmSelect") realmSelect!: MatSelect;

  readonly realmService: RealmServiceInterface = inject(RealmService);
  readonly resolverService: ResolverServiceInterface = inject(ResolverService);
  readonly policyService = inject(PolicyService);

  readonly policy = input.required<PolicyDetail>();
  readonly policyEdit = output<PolicyDetail>();

  adminFormControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [this.adminValidator.bind(this)]
  });

  readonly selectedRealms = computed(() => this.policy().realm || []);
  readonly selectedResolvers = computed(() => this.policy().resolver || []);
  readonly selectedAdmins = computed(() => this.policy().adminuser || []);
  readonly selectedAdminrealm = computed(() => this.policy().adminrealm || []);

  readonly isAllRealmsSelected = computed(
    () => this.selectedRealms().length === this.realmService.realmOptions().length
  );
  readonly isAllResolversSelected = computed(
    () => this.selectedResolvers().length === this.resolverService.resolverOptions().length
  );

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
      if (this.realmSelect) {
        this.realmSelect.close();
      }
    });
  }

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
      if (this.resolverSelect) {
        this.resolverSelect.close();
      }
    });
  }

  selectAdminRealm($event: string[]) {
    this.updatePolicy({ adminrealm: $event });
  }

  addAdmin(adminuser: string) {
    const trimmed = adminuser?.trim();
    if (this.adminFormControl.invalid || !trimmed) {
      return;
    }
    if (!this.selectedAdmins().includes(trimmed)) {
      this.updatePolicy({ adminuser: [...this.selectedAdmins(), trimmed] });
      this.adminFormControl.setValue("");
    }
  }

  removeAdmin(adminuser: string) {
    this.updatePolicy({ adminuser: this.selectedAdmins().filter((u) => u !== adminuser) });
  }

  clearAdmins() {
    this.updatePolicy({ adminuser: [] });
  }

  adminValidator(control: AbstractControl): ValidationErrors | null {
    return /[,]/.test(control.value) ? { includesComma: { value: control.value } } : null;
  }

  updatePolicy(patch: Partial<PolicyDetail>) {
    this.policyEdit.emit({ ...this.policy(), ...patch });
  }
}
