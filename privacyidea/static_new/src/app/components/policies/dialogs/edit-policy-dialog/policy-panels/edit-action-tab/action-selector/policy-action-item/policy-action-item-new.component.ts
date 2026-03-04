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
import { Component, inject, input, computed, output, linkedSignal, viewChild, ElementRef } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MatTooltipModule } from "@angular/material/tooltip";
import {
  PolicyServiceInterface,
  PolicyService,
  PolicyActionDetail
} from "../../../../../../../../services/policies/policies.service";
import { SelectorButtonsComponent } from "../../selector-buttons/selector-buttons.component";
import { MultiSelectOnlyComponent } from "@components/shared/multi-select-only/multi-select-only.component";

@Component({
  selector: "app-policy-action-item-new",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatTooltipModule,
    SelectorButtonsComponent,
    MatInputModule,
    MatSelectModule,
    MatAutocompleteModule,
    MultiSelectOnlyComponent
  ],
  templateUrl: "./policy-action-item-new.component.html",
  styleUrls: ["./policy-action-item-new.component.scss"]
})
export class PolicyActionItemComponent<T extends string | number = string | number> {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);

  readonly actionName = input.required<string>();
  readonly actionValue = input<T>();
  readonly actionDetail = input.required<PolicyActionDetail<T> | null>();
  readonly isBooleanAction = computed(() => this.actionDetail()?.type === "bool");
  readonly inputIsValid = computed<boolean>(() => {
    const actionDetail = this.actionDetail();
    const actionValue = this.currentAction()?.value;
    if (actionDetail === null || actionValue === undefined) return false;
    return this.policyService.actionValueIsValid(actionDetail, actionValue);
  });
  readonly selectActionByName = output<string>();
  readonly actionAdd = output<{ name: string; value: T | undefined }>();

  currentAction = linkedSignal({
    source: () => this.actionDetail(),
    computation: (actionDetail) => {
      const actionName = this.actionName();
      if (!actionDetail) return { name: actionName, value: undefined };
      const defaultValue = actionDetail.type === "bool" ? ("true" as T) : this.actionValue();
      return { name: actionName, value: defaultValue };
    }
  });

  selectedItems = computed<T[]>(() => {
    const value = this.currentAction()?.value;
    const valueList = typeof value === "string" ? value.split(" ") : [value];
    return valueList as T[];
  });

  addAction(value?: T) {
    const name = this.actionName();
    const finalValue = value !== undefined ? value : this.currentAction().value;
    this.actionAdd.emit({ name, value: finalValue });
  }

  updateSelectedActionValue(value: T | T[]) {
    const actionName = this.actionName();
    if (Array.isArray(value)) {
      const stringValue = value.map((v) => v.toString()).join(" ");
      this.currentAction.set({ name: actionName, value: stringValue as T });
    } else {
      this.currentAction.set({ name: actionName, value: value });
    }
  }

  onEnter(): void {
    if (!this.inputIsValid()) {
      return;
    }
    this.addAction();
  }

  inputElementRef = viewChild<ElementRef>("inputElement");
  selectElementRef = viewChild<MatSelect>("selectElement");
  buttonElementRef = viewChild<ElementRef>("buttonElement");
  selectorComponent = viewChild<SelectorButtonsComponent<any>>("selectorComponent");

  focusFirstInput() {
    setTimeout(() => {
      const input = this.inputElementRef()?.nativeElement;
      const select = this.selectElementRef();
      const button = this.buttonElementRef()?.nativeElement;
      const selector = this.selectorComponent();
      if (input) {
        input.focus();
        return;
      }
      if (select) {
        select.focus();
        return;
      }
      if (selector) {
        selector.focusFirst();
        return;
      }
      if (button) {
        button.focus();
        return;
      }
    }, 0);
  }
}
