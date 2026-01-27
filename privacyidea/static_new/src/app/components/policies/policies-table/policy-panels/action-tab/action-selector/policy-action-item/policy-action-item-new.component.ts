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
import { MatSelect } from "@angular/material/select";
import { MatTooltipModule } from "@angular/material/tooltip";
import {
  PolicyServiceInterface,
  PolicyService,
  PolicyActionDetail
} from "../../../../../../../services/policies/policies.service";
import { SelectorButtonsComponent } from "../../selector-buttons/selector-buttons.component";

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
    MatSelect,
    MatAutocompleteModule
  ],
  templateUrl: "./policy-action-item-new.component.html",
  styleUrls: ["./policy-action-item-new.component.scss"]
})
export class PolicyActionItemComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);

  readonly actionName = input.required<string>();
  readonly actionValue = input.required<any>();
  readonly actionDetail = input.required<PolicyActionDetail | null>();
  readonly isSelected = input.required<boolean>();
  readonly isBooleanAction = computed(() => this.actionDetail()?.type === "bool");
  readonly inputIsValid = computed<boolean>(() => {
    const actionDetail = this.actionDetail();
    const actionValue = this.currentAction()?.value;
    if (actionDetail === null || actionValue === undefined) return false;
    return this.policyService.actionValueIsValid(actionDetail, actionValue);
  });
  readonly selectActionByName = output<string>();
  readonly actionAdd = output<{ name: string; value: any }>();

  currentAction = linkedSignal({
    source: () => this.actionDetail(),
    computation: (actionDetail) => {
      const actionName = this.actionName();
      if (!actionDetail) return { name: actionName, value: undefined };
      const defaultValue = actionDetail.type === "bool" ? "true" : (actionDetail?.value?.[0] ?? "");
      return { name: actionName, value: defaultValue };
    }
  });

  addAction(value?: any) {
    let currentAction = this.currentAction();
    if (value !== undefined) {
      currentAction.value = value;
    }
    this.actionAdd.emit(currentAction);
  }

  updateSelectedActionValue(value: any) {
    const actionName = this.actionName();
    this.currentAction.set({ name: actionName, value: value });
  }

  onEnter(): void {
    if (!this.inputIsValid()) {
      return;
    }
    this.addAction();
  }

  inputEl = viewChild<ElementRef>("inputElement");
  selectEl = viewChild<MatSelect>("selectElement");
  buttonEl = viewChild<ElementRef>("buttonElement");
  selectorComponent = viewChild<SelectorButtonsComponent<any>>("selectorComponent");

  focusFirstInput() {
    setTimeout(() => {
      const input = this.inputEl()?.nativeElement;
      const select = this.selectEl();
      const button = this.buttonEl()?.nativeElement;
      const selector = this.selectorComponent();
      console.log("Focusing first input among:", { input, select, selector, button });
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
