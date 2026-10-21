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

import { Component, computed, effect, inject, input, linkedSignal, output, untracked } from "@angular/core";
import { FieldTree, FormField, form } from "@angular/forms/signals";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
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

@Component({
  selector: "app-policy-action-item-edit",
  standalone: true,
  imports: [
    FormField,
    MatIconModule,
    MatButtonModule,
    MatSlideToggleModule,
    MatExpansionModule,
    ToggleGroupComponent,
    MatInputModule,
    MatSelectModule,
    MatFormFieldModule,
    MatAutocompleteModule,
    MultiSelectOnlyComponent,
    HighlightPipe
  ],
  templateUrl: "./policy-action-item-edit.component.html",
  styleUrl: "./policy-action-item-edit.component.scss"
})
export class PolicyActionItemEditComponent<T extends string | number | boolean = string | number | boolean> {
  readonly action = input.required<{ name: string; value: T }>();
  readonly actionDetail = input.required<PolicyActionDetail<T> | null>();
  readonly highlight = input<string>("");
  readonly removeAction = output<void>();
  readonly updateAction = output<T | undefined>();

  readonly policyService: PolicyServiceInterface = inject(PolicyService);

  /** Names the value controls after the action they belong to. */
  readonly valueLabel = computed(() => this.action().name);

  // The value being edited, seeded from the action and re-seeded when the action's value changes. A number without
  // options is seeded as text, so the model of the native inputs stays a string.
  readonly valueModel = linkedSignal<string | number | boolean>(() => {
    const value = this.action().value;
    return typeof value === "number" && !this.actionDetail()?.value ? String(value) : value;
  });

  // Holds the one rule every kind of control shares: the value must suit the action's type.
  readonly valueForm = form(this.valueModel, (path) =>
    actionValueRule(path, this.policyService, () => this.actionDetail())
  );

  // The native inputs write text, so they bind the value form as a text field.
  readonly textField = this.valueForm as unknown as FieldTree<string>;

  /**
   * False while the value being edited does not suit the action's type, an emptied field and text the number input
   * cannot parse included. A row without an action detail has no control to correct, so it does not count.
   */
  readonly valid = computed(() => !this.actionDetail() || this.valueForm().valid());

  /** Id of the hint, which the invalid control points to. */
  readonly errorId = computed(() => `${this.action().name}-error`);

  /** The hint shown under an invalid row; null while the value is valid. */
  readonly errorHint = computed<string | null>(() => {
    if (this.valid()) return null;
    return this.actionDetail()?.type === "int"
      ? $localize`:@@policy.actionValueNotInteger:Enter a whole number.`
      : $localize`:@@policy.actionValueRequired:Enter a value.`;
  });

  private readonly labelOptions = computed<ValueLabelOptions>(() => ({
    vocabulary: POLICY_VOCABULARY_ACTIONS.has(this.action().name)
  }));

  readonly valueLabels = computed<string[] | undefined>(() =>
    valueDisplayLabels(this.actionDetail()?.value, this.labelOptions())
  );

  /** Label of a single value, for the multi select which sorts its items itself. */
  readonly valueLabelOf = (value: T): string =>
    valueDisplayLabel(value, this.actionDetail()?.value, this.labelOptions());

  readonly valueOptions = computed(() => labeledOptions(this.actionDetail()?.value, this.labelOptions()));

  constructor() {
    // Emits what the user changed. A value that equals the action's own value is the seed or the parent's echo of an
    // earlier emit, so it is not emitted again. An invalid value is never emitted: the policy keeps the last valid one.
    effect(() => {
      const value = this.valueModel();
      if (!this.valid()) return;
      untracked(() => {
        if (String(value) !== String(this.action().value)) {
          this.updateAction.emit(value as T);
        }
      });
    });
  }

  // The option equal to the current value when both are compared as text, so a stored "6" selects the option 6.
  readonly selectedValue = computed<T>(() => {
    const value = this.valueModel() as T;
    return this.actionDetail()?.value?.find((option) => String(option) === String(value)) ?? value;
  });

  selectedItems = computed<T[]>(() => {
    const value = this.valueModel();
    const valueList = typeof value === "string" ? value.split(" ") : [value];
    return valueList as T[];
  });

  isBooleanAction(): boolean {
    return this.actionDetail()?.type === "bool";
  }

  handleRemoveAction() {
    this.removeAction.emit();
  }

  /** The select, the multi select and the toggle group write their choice to the value model. */
  updateValue(value: T | T[] | undefined): void {
    this.valueModel.set(Array.isArray(value) ? value.map((v) => v.toString()).join(" ") : (value ?? ""));
  }
}
