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
import { Component, computed, effect, inject, input, output, signal } from "@angular/core";
import { form, required } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { ErrorStateDirective } from "@components/shared/directives/error-state.directive";
import { ActionOptions, EventService } from "@services/event/event.service";

@Component({
  selector: "app-event-action-tab",
  standalone: true,
  imports: [
    MatFormField,
    MatHint,
    MatLabel,
    MatOption,
    MatSelect,
    MatInput,
    MatCheckbox,
    MatError,
    NgClass,
    ErrorStateDirective
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

  selectedAction = signal<string>("");
  selectedActionForm = form(this.selectedAction, (f) => {
    required(f);
  });

  showActionError = computed(() => {
    const f = this.selectedActionForm();
    return f.errors().some((e) => e.kind === "required") && f.touched();
  });

  selectedOptions = signal<Record<string, any>>({});
  touchedOptions = signal<Record<string, boolean>>({});

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

  optionsAreValid = computed(() => {
    const opts = this.actionOptions();
    const values = this.selectedOptions();
    for (const name of Object.keys(opts)) {
      if (opts[name].required && this.isEmpty(values[name])) {
        return false;
      }
    }
    return true;
  });

  constructor() {
    // Sync the selectedAction signal with the input
    effect(() => {
      this.selectedAction.set(this.action());
    });

    // Rebuild option defaults when action or options input changes
    effect(() => {
      const opts = this.actionOptions();
      const incoming = this.options();
      const rebuilt: Record<string, any> = {};
      for (const name of Object.keys(opts)) {
        const optAny = opts[name] as Record<string, any>;
        if (incoming[name] !== undefined) {
          rebuilt[name] = incoming[name];
        } else if (optAny["default"] !== undefined) {
          rebuilt[name] = optAny["default"];
        } else {
          rebuilt[name] = "";
        }
      }
      this.selectedOptions.set(rebuilt);
      this.touchedOptions.set({});
    });

    // Emit options + validity to the parent whenever they change
    effect(() => {
      const values = this.selectedOptions();
      this.optionsValid.emit(this.optionsAreValid());
      this.newOptions.emit(this.optionsToDict(values));
    });
  }

  private isEmpty(value: any): boolean {
    return value === null || value === undefined || value === "";
  }

  private optionsToDict(values: Record<string, any>): Record<string, any> {
    const out: Record<string, any> = {};
    for (const key of Object.keys(values)) {
      const v = values[key];
      if (v === null || v === undefined) continue;
      out[key] = v;
    }
    return out;
  }

  setOption(name: string, value: any): void {
    this.selectedOptions.update((m) => ({ ...m, [name]: value }));
  }

  markOptionTouched(name: string): void {
    this.touchedOptions.update((m) => ({ ...m, [name]: true }));
  }

  isOptionInvalid(name: string): boolean {
    const opt = this.actionOptions()[name];
    if (!opt || !opt.required) return false;
    return this.isEmpty(this.selectedOptions()[name]);
  }

  showOptionError(name: string): boolean {
    return !!this.touchedOptions()[name] && this.isOptionInvalid(name);
  }

  onActionSelectionChange(value: string): void {
    this.selectedAction.set(value);
    this.newAction.emit(value);
  }

  checkOptionVisibility(optionName: string): boolean {
    const optionDetails = this.actionOptions()[optionName];
    if (!optionDetails || !optionDetails.visibleIf) return true;
    if (optionDetails.visibleValue === undefined) return true;
    const dependent = this.selectedOptions()[optionDetails.visibleIf];
    return dependent === optionDetails.visibleValue;
  }
}
