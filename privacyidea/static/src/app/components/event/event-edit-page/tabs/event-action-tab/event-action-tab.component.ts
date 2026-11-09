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

import { NgClass } from "@angular/common";
import { Component, computed, effect, inject, input, output, signal, untracked } from "@angular/core";
import { applyEach, FieldTree, form, FormField, metadata, REQUIRED, required, validate } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { ActionOptionDetails, EventService } from "@services/event/event.service";
import { ERR } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";
import { valueDisplayLabel } from "@utils/value-label.utils";

/**
 * Value type for a single action option. The eventhandler backend supports
 * "str", "int", "bool", "text", "regexp" and "multi" option types. In the
 * action tab, "multi" renders as a single-select dropdown (the option's
 * `value` array defines the choices), so all variants map to primitive
 * form values here. Event *conditions* (different component) treat "multi"
 * as `string[]`.
 */
export type EventActionOptionValue = string | number | boolean | null;

/** Map of option name to its current user-entered value. */
export type EventActionOptionValues = Record<string, EventActionOptionValue>;

@Component({
  selector: "app-event-action-tab",
  standalone: true,
  imports: [MatFormField, MatHint, MatLabel, MatOption, MatSelect, MatInput, MatCheckbox, MatError, NgClass, FormField],
  templateUrl: "./event-action-tab.component.html",
  styleUrl: "./event-action-tab.component.scss"
})
export class EventActionTabComponent {
  protected readonly eventService = inject(EventService);
  protected readonly Object = Object;
  protected readonly hasError = hasError;
  protected readonly ERR = ERR;
  action = input.required<string>();
  options = input.required<EventActionOptionValues>();
  newAction = output<string>();
  newOptions = output<EventActionOptionValues>();
  optionsValid = output<boolean>();
  selectedAction = signal<string>("");
  selectedActionForm = form(this.selectedAction, (f) => {
    required(f);
  });

  selectedOptions = signal<EventActionOptionValues>({});
  optionsForm = form(this.selectedOptions, (f) => {
    applyEach(f, (option) => {
      metadata(option, REQUIRED, (ctx) => this.isOptionRequired(ctx.key()));
      validate(option, (ctx) =>
        this.isOptionRequired(ctx.key()) && this.isEmpty(ctx.value()) ? { kind: ERR.required } : undefined
      );
    });
  });

  actionOptions = computed(() => {
    const action = this.selectedAction();
    if (action) {
      return this.eventService.moduleActions()[action] || {};
    }
    if (this.action()) {
      return this.eventService.moduleActions()[this.action()] || {};
    }
    return {};
  });

  optionValueOptions = computed<Record<string, { value: string; label: string }[]>>(() => {
    const optionMap: Record<string, { value: string; label: string }[]> = {};
    for (const [name, definition] of Object.entries(this.actionOptions())) {
      const values = definition.value;
      if (!values) continue;
      optionMap[name] = values.map((value) => ({ value, label: valueDisplayLabel(value, values) }));
    }
    return optionMap;
  });

  optionNames = computed(() => Object.keys(this.selectedOptions()).filter((name) => name in this.actionOptions()));

  constructor() {
    // Sync the selectedAction signal with the input
    effect(() => {
      this.selectedAction.set(this.action());
    });

    // Rebuild option defaults when action or options input changes
    effect(() => {
      const optionDefinitions = this.actionOptions();
      const incoming = this.options();
      const rebuilt: EventActionOptionValues = {};
      for (const name of Object.keys(optionDefinitions)) {
        const definition = optionDefinitions[name] as ActionOptionDetails & {
          default?: EventActionOptionValue;
        };
        if (incoming[name] !== undefined) {
          rebuilt[name] = incoming[name];
        } else if (definition.default !== undefined) {
          rebuilt[name] = definition.default;
        } else {
          rebuilt[name] = "";
        }
      }
      this.selectedOptions.set(rebuilt);
      untracked(() => this.optionsForm().reset());
    });

    // Emit options + validity to the parent whenever they change
    effect(() => {
      const values = this.selectedOptions();
      this.optionsValid.emit(this.optionsForm().valid());
      this.newOptions.emit(this.optionsToDict(values));
    });
  }

  // The model holds text, numbers and booleans, so the native inputs take the field of an option as a typed view
  textField(name: string): FieldTree<string> {
    return this.optionsForm[name] as unknown as FieldTree<string>;
  }

  numberField(name: string): FieldTree<string | number | null> {
    return this.optionsForm[name] as unknown as FieldTree<string | number | null>;
  }

  showOptionError(name: string): boolean {
    const field = this.optionsForm[name];
    return !!field && field().touched() && field().invalid();
  }

  onActionSelectionChange(value: string): void {
    this.newAction.emit(value);
  }

  checkOptionVisibility(optionName: string): boolean {
    const optionDetails = this.actionOptions()[optionName];
    if (!optionDetails || !optionDetails.visibleIf) return true;
    if (optionDetails.visibleValue === undefined) return true;
    const dependent = this.selectedOptions()[optionDetails.visibleIf];
    return dependent === optionDetails.visibleValue;
  }

  private isOptionRequired(name: string): boolean {
    return !!this.actionOptions()[name]?.required && this.checkOptionVisibility(name);
  }

  private isEmpty(value: EventActionOptionValue | undefined): boolean {
    return value === null || value === undefined || value === "";
  }

  private optionsToDict(values: EventActionOptionValues): EventActionOptionValues {
    const result: EventActionOptionValues = {};
    for (const key of Object.keys(values)) {
      const value = values[key];
      if (value === null || value === undefined) continue;
      result[key] = value;
    }
    return result;
  }
}
