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

import { Component, computed, inject, input, output } from "@angular/core";

import { ChipListInputComponent } from "@components/shared/chip-list-input/chip-list-input.component";
import { MultiSelectOnlyComponent } from "@components/shared/multi-select-only/multi-select-only.component";
import { PolicyDetail } from "@services/policies/policies.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";

@Component({
  selector: "app-edit-admin-conditions",
  standalone: true,
  imports: [MultiSelectOnlyComponent, ChipListInputComponent],
  templateUrl: "./edit-admin-conditions.component.html",
  styleUrl: "./edit-admin-conditions.component.scss"
})
export class EditAdminConditionsComponent {
  readonly realmService: RealmServiceInterface = inject(RealmService);

  readonly policy = input.required<PolicyDetail>();
  readonly policyEdit = output<Partial<PolicyDetail>>();

  readonly selectedAdmins = computed(() => this.policy().adminuser || []);
  readonly selectedAdminrealm = computed(() => this.policy().adminrealm || []);

  selectAdminRealm($event: string[]) {
    this.updatePolicy({ adminrealm: $event });
  }

  updatePolicy(patch: Partial<PolicyDetail>) {
    this.policyEdit.emit(patch);
  }
}
