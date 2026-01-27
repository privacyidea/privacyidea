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

import { Component, computed, effect, inject, input, output } from "@angular/core";
import { ActionOptions, EventService } from "../../../../../services/event/event.service";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatOption, MatSelect } from "@angular/material/select";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatInput } from "@angular/material/input";
import { MatCheckbox } from "@angular/material/checkbox";
import { toSignal } from "@angular/core/rxjs-interop";

@Component({
  selector: "app-event-action-tab",
  standalone: true,
  imports: [
    MatFormField,
    MatHint,
    MatLabel,
    MatOption,
    MatSelect,
    FormsModule,
    MatInput,
    MatCheckbox,
    ReactiveFormsModule,
    MatError
  ],
  templateUrl: "./event-action-tab.component.html",
  styleUrl: "./event-action-tab.component.scss"
})
export class EventActionTabComponent {
  protected readonly eventService = inject(EventService);
  action = input.required<string>();
  options = input.required<Record<string, any>>();
  newAction = output<string>();
  newOptions = output<ActionOptions>();
  optionsValid = output<boolean>();
  protected readonly Object = Object;

  selectedAction = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  selectedActionSignal = toSignal(this.selectedAction.valueChanges, { initialValue: this.selectedAction.value });
  selectedOptions = new FormGroup<any>({});

  constructor() {
    // Set initial values
    effect(() => {
      this.selectedAction.setValue(this.action(), { emitEvent: false });
      this.rebuildOptionsForm(this.options());
    });

    // Subscribe to value changes in selectedOptions and emit to parent
    this.selectedOptions.valueChanges.subscribe(() => {
      this.emitOptionsToParent();
    });

    // Rebuild options form when selectedAction changes
    this.selectedAction.valueChanges.subscribe(actionValue => {
      const options = this.eventService.moduleActions()[actionValue] || {};
      this.rebuildOptionsForm(options);
      // Emit after rebuilding, as structure/values may have changed
      this.emitOptionsToParent();
    });
  }

  rebuildOptionsForm(options: Record<string, any>) {
    // Remove controls that are not in the new options
    Object.keys(this.selectedOptions.controls).forEach(key => {
      if (!(key in options)) {
        this.selectedOptions.removeControl(key);
      }
    });
    // Add or update controls for each option
    for (const optionName of Object.keys(options)) {
      const option = options[optionName];
      const validators = option.required ? [Validators.required] : [];
      if (this.selectedOptions.contains(optionName)) {
        this.selectedOptions.get(optionName)?.setValidators(validators);
        this.selectedOptions.get(optionName)?.setValue(this.options()[optionName] ?? option.default ?? "");
        this.selectedOptions.get(optionName)?.updateValueAndValidity({ emitEvent: false });
      } else {
        this.selectedOptions.addControl(
          optionName,
          new FormControl(this.options()[optionName] ?? option.default ?? "", validators)
        );
      }
    }
    // Emit after rebuilding
    this.emitOptionsToParent();
  }

  emitOptionsToParent() {
    this.newOptions.emit(this.optionsToDict());
    this.optionsValid.emit(this.selectedOptions.valid);
  }

  onActionSelectionChange() {
    this.newAction.emit(this.selectedAction.value);
  }

  optionsToDict() {
    let newOptions: Record<string, any> = {};
    for (const key of Object.keys(this.selectedOptions.controls)) {
      const value = this.selectedOptions.get(key)?.value;
      if (value === null || value === undefined) {
        continue; // skip undefined or empty values
      }
      newOptions[key] = this.selectedOptions.get(key)?.value;
    }
    return newOptions;
  }

  actionOptions = computed(() => {
    if (!this.selectedActionSignal()) {
      return {};
    }
    return this.eventService.moduleActions()[this.selectedActionSignal()] || {};
  });

  checkOptionVisibility(optionName: string): boolean {
    // checks if the visible conditions of an option are met
    const optionDetails = this.actionOptions()[optionName];
    if (!optionDetails || !optionDetails.visibleIf) {
      // no visible condition set
      return true;
    }
    if (optionDetails.visibleValue === undefined) {
      // related option is set, but no specific value is required
      return true;
    }
    // check if the related option matches the required value
    const dependentOptionValue = (this.selectedOptions.value as Record<string, any>)[optionDetails.visibleIf];
    return dependentOptionValue === optionDetails.visibleValue;
  }
}
