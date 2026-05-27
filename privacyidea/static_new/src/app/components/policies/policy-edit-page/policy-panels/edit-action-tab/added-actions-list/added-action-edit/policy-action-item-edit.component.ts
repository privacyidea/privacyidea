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
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { SelectorButtonsComponent } from "@components/policies/policy-edit-page/policy-panels/edit-action-tab/selector-buttons/selector-buttons.component";
import { MultiSelectOnlyComponent } from "@components/shared/multi-select-only/multi-select-only.component";
import { PolicyActionDetail, PolicyService, PolicyServiceInterface } from "@services/policies/policies.service";

@Component({
  selector: "app-policy-action-item-edit",
  standalone: true,
  imports: [
    MatIconModule,
    MatButtonModule,
    MatSlideToggleModule,
    MatExpansionModule,
    SelectorButtonsComponent,
    MatInputModule,
    MatSelectModule,
    MatFormFieldModule,
    MatAutocompleteModule,
    MultiSelectOnlyComponent
  ],
  templateUrl: "./policy-action-item-edit.component.html",
  styleUrl: "./policy-action-item-edit.component.scss"
})
export class PolicyActionItemEditComponent<T extends string | number = string | number> {
  readonly action = input.required<{ name: string; value: T }>();
  readonly actionDetail = input.required<PolicyActionDetail<T> | null>();
  readonly onRemoveAction = output<void>();
  readonly onUpdateAction = output<T | undefined>();

  readonly policyService: PolicyServiceInterface = inject(PolicyService);

  readonly inputIsValid = computed<boolean>(() => {
    const actionDetail = this.actionDetail();
    const actionValue = this.action()?.value;
    if (actionDetail === null || actionValue === undefined) return false;
    return this.policyService.actionValueIsValid(actionDetail, actionValue);
  });

  selectedItems = computed<T[]>(() => {
    const value = this.action()?.value;
    const valueList = typeof value === "string" ? value.split(" ") : [value];
    return valueList as T[];
  });

  isBooleanAction(_actionName: string): boolean {
    return this.actionDetail()?.type === "bool";
  }

  removeAction() {
    this.onRemoveAction.emit();
  }

  updateAction(value?: T | T[]): void {
    if (Array.isArray(value)) {
      const stringValue = value.map((v) => v.toString()).join(" ");
      this.onUpdateAction.emit(stringValue as T);
    } else {
      this.onUpdateAction.emit(value as T);
    }
  }
  isNumber(value: T): boolean {
    return value !== null && value !== "" && !isNaN(Number(value));
  }
}
