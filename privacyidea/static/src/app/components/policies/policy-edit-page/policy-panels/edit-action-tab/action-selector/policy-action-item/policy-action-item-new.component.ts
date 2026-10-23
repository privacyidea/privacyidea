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
import { FieldTree, FormField, form } from "@angular/forms/signals";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MultiSelectOnlyComponent } from "@components/shared/multi-select-only/multi-select-only.component";
import { HighlightPipe } from "@components/shared/pipes/highlight.pipe";
import { ToggleGroupComponent } from "@components/shared/toggle-group/toggle-group.component";
import { PolicyActionDetail, PolicyService, PolicyServiceInterface } from "@services/policies/policies.service";
import {
  labeledOptions,
  POLICY_VOCABULARY_ACTIONS,
  valueDisplayLabel,
  valueDisplayLabels,
  ValueLabelOptions
} from "@utils/value-label.utils";
import { actionValueRule } from "../../action-value.rule";

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
    FormField,
    MatButtonModule,
    MatIconModule,
    ToggleGroupComponent,
    MatInputModule,
    MatSelectModule,
    MatAutocompleteModule,
    MultiSelectOnlyComponent,
    HighlightPipe
  ],
  templateUrl: "./policy-action-item-new.component.html",
  styleUrls: ["./policy-action-item-new.component.scss"]
})
export class PolicyActionItemComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);

  readonly selectableAction = input.required<SelectableAction>();
  readonly highlight = input<string>("");
  readonly actionValue = input<string | number>();

  // Names the value controls and the add button after the action they belong to.
  readonly valueLabel = computed(() => this.selectableAction().label);
  readonly addLabel = computed(() => {
    const action = this.selectableAction().label;
    return $localize`:@@policy.addAction:Add ${action}:ACTION:`;
  });
  readonly isBooleanAction = computed(() => this.selectableAction().detail?.type === "bool");
  readonly actionAdd = output<{ name: string; value: string | number | boolean | undefined }>();

  // The value being edited. The select, the multi select and the toggle group write it through
  // `updateSelectedActionValue`; the native inputs are bound to it by `valueForm`.
  readonly valueModel = linkedSignal<SelectableAction, string | number>({
    source: () => this.selectableAction(),
    computation: ({ detail }) => (detail?.type === "bool" ? "true" : (this.actionValue() ?? ""))
  });

  // Holds the one rule every kind of control shares: the value must suit the action's type.
  readonly valueForm = form(this.valueModel, (path) =>
    actionValueRule(path, this.policyService, () => this.selectableAction().detail)
  );

  // The text and the textarea write strings, so they bind the value form as a text field.
  readonly textField = this.valueForm as unknown as FieldTree<string>;

  readonly currentAction = computed(() => ({ name: this.selectableAction().actionName, value: this.valueModel() }));

  private readonly labelOptions = computed<ValueLabelOptions>(() => ({
    vocabulary: POLICY_VOCABULARY_ACTIONS.has(this.selectableAction().actionName)
  }));

  readonly valueLabels = computed<string[] | undefined>(() =>
    valueDisplayLabels(this.selectableAction().detail?.value, this.labelOptions())
  );

  /** Label of a single value, for the multi select which sorts its items itself. */
  readonly valueLabelOf = (value: string | number | boolean): string =>
    valueDisplayLabel(value, this.selectableAction().detail?.value, this.labelOptions());

  readonly valueOptions = computed(() => labeledOptions(this.selectableAction().detail?.value, this.labelOptions()));

  // The option equal to the current value when both are compared as text, so a stored "6" selects the option 6.
  readonly selectedValue = computed<string | number>(() => {
    const value = this.currentAction().value;
    const options = this.selectableAction().detail?.value;
    return (options?.find((option) => String(option) === String(value)) ?? value) as string | number;
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
    if (Array.isArray(value)) {
      this.valueModel.set(value.map((v) => v.toString()).join(" "));
    } else {
      this.valueModel.set(typeof value === "boolean" ? String(value) : value);
    }
  }

  onEnter(): void {
    if (!this.valueForm().valid()) {
      return;
    }
    this.addAction();
  }

  inputElementRef = viewChild<ElementRef>("inputElement");
  selectElementRef = viewChild<MatSelect>("selectElement");
  buttonElementRef = viewChild<ElementRef>("buttonElement");
  selectorComponent = viewChild<ToggleGroupComponent<string | number>>("selectorComponent");

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
        selector.focus();
        return;
      }
      if (button) {
        button.focus();
        return;
      }
    }, 0);
  }
}
