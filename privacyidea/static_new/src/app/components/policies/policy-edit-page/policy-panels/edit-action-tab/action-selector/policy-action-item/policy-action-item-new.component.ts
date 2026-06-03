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

import { Component, computed, ElementRef, inject, input, linkedSignal, output, viewChild } from "@angular/core";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MatTooltipModule } from "@angular/material/tooltip";
import { SelectorButtonsComponent } from "@components/policies/policy-edit-page/policy-panels/edit-action-tab/selector-buttons/selector-buttons.component";
import { MultiSelectOnlyComponent } from "@components/shared/multi-select-only/multi-select-only.component";
import { PolicyActionDetail, PolicyService, PolicyServiceInterface } from "@services/policies/policies.service";

export interface SelectableAction {
  label: string;
  actionName: string;
  scope: string;
  detail: PolicyActionDetail;
}

@Component({
  selector: "app-policy-action-item-new",
  standalone: true,
  imports: [
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
export class PolicyActionItemComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);

  readonly selectableAction = input.required<SelectableAction>();
  readonly actionValue = input<string | number>();

  readonly isBooleanAction = computed(() => this.selectableAction().detail?.type === "bool");
  readonly inputIsValid = computed<boolean>(() => {
    const detail = this.selectableAction().detail;
    const actionValue = this.currentAction()?.value;
    if (!detail || actionValue === undefined) return false;
    return this.policyService.actionValueIsValid(detail, actionValue);
  });
  readonly selectActionByName = output<string>();
  readonly actionAdd = output<{ name: string; value: string | number | boolean | undefined }>();

  currentAction = linkedSignal({
    source: () => this.selectableAction(),
    computation: (selectableAction) => {
      const { actionName, detail } = selectableAction;
      const defaultValue = detail?.type === "bool" ? "true" : this.actionValue();
      return { name: actionName, value: defaultValue };
    }
  });

  selectedItems = computed<(string | number)[]>(() => {
    const value = this.currentAction()?.value;
    const valueList = typeof value === "string" ? value.split(" ") : [value];
    return valueList as (string | number)[];
  });

  addAction(value?: string | number | boolean) {
    const name = this.selectableAction().actionName;
    const finalValue = value !== undefined ? value : this.currentAction().value;
    this.actionAdd.emit({ name, value: finalValue });
  }

  updateSelectedActionValue(value: string | number | boolean | (string | number | boolean)[]) {
    const actionName = this.selectableAction().actionName;
    if (Array.isArray(value)) {
      const stringValue = value.map((v) => v.toString()).join(" ");
      this.currentAction.set({ name: actionName, value: stringValue });
    } else {
      this.currentAction.set({ name: actionName, value: typeof value === "boolean" ? String(value) : value });
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
  selectorComponent = viewChild<SelectorButtonsComponent<string | number>>("selectorComponent");

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
