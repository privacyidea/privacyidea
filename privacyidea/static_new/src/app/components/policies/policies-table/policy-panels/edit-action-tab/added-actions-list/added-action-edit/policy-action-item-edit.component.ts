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

import { CommonModule } from "@angular/common";
import { Component, input, output, computed, inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import {
  PolicyActionDetail,
  PolicyServiceInterface,
  PolicyService
} from "../../../../../../../services/policies/policies.service";
import { SelectorButtonsComponent } from "../../selector-buttons/selector-buttons.component";

@Component({
  selector: "app-policy-action-item-edit",
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatSlideToggleModule,
    MatExpansionModule,
    SelectorButtonsComponent,
    MatInputModule,
    MatSelect,
    MatAutocompleteModule,
    FormsModule
  ],
  templateUrl: "./policy-action-item-edit.component.html",
  styleUrl: "./policy-action-item-edit.component.scss"
})
export class PolicyActionItemEditComponent {
  readonly action = input.required<{ name: string; value: any }>();
  readonly actionDetail = input.required<PolicyActionDetail | null>();
  readonly onRemoveAction = output<void>();
  readonly onUpdateAction = output<string | number>();
  readonly inputIsValid = computed<boolean>(() => {
    const actionDetail = this.actionDetail();
    const actionValue = this.action()?.value;
    if (actionDetail === null || actionValue === undefined) return false;
    return this.policyService.actionValueIsValid(actionDetail, actionValue);
  });
  readonly policyService: PolicyServiceInterface = inject(PolicyService);

  // Type Checking Methods
  isBooleanAction(actionName: string): boolean {
    return this.policyService.getDetailsOfAction(actionName)?.type === "bool";
  }
  removeAction() {
    this.onRemoveAction.emit();
  }
  updateAction(newValue: string | number): void {
    this.onUpdateAction.emit(newValue);
  }

  isNumber(value: any): boolean {
    return value !== null && value !== "" && !isNaN(Number(value));
  }
}
