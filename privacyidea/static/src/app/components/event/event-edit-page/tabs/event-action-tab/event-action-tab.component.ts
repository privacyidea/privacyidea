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
import { ActionOptionDetails, EventService } from "@services/event/event.service";
import { WebhookService, WebhookServiceInterface } from "@services/webhook/webhook.service";
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
  /**
   * The option names in the order they are shown. A handler module states it per option (`order`);
   * the ones that do not come after, in the order the response carries them. `sort` is stable, so
   * that order is preserved rather than reshuffled.
   */
  orderedOptionNames = computed<string[]>(() => {
    const definitions = this.actionOptions();
    return Object.keys(definitions).sort((left, right) => {
      const leftOrder = definitions[left]?.order;
      const rightOrder = definitions[right]?.order;
      if (leftOrder != null && rightOrder != null) return leftOrder - rightOrder;
      if (leftOrder != null) return -1;
      if (rightOrder != null) return 1;
      return 0;
    });
  });
  protected readonly Object = Object;
  action = input.required<string>();
  options = input.required<EventActionOptionValues>();
  newAction = output<string>();
  newOptions = output<EventActionOptionValues>();
  optionsValid = output<boolean>();
  selectedAction = signal<string>("");
  selectedActionForm = form(this.selectedAction, (f) => {
    required(f);
  });

  showActionError = computed(() => {
    const actionForm = this.selectedActionForm();
    return actionForm.errors().some((error) => error.kind === "required") && actionForm.touched();
  });

  selectedOptions = signal<EventActionOptionValues>({});
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
  private readonly webhookService: WebhookServiceInterface = inject(WebhookService);

  optionValueOptions = computed<Record<string, { value: string; label: string }[]>>(() => {
    const optionMap: Record<string, { value: string; label: string }[]> = {};
    for (const [name, definition] of Object.entries(this.actionOptions())) {
      const values = definition.value;
      if (!values) continue;
      optionMap[name] = values.map((value) => ({ value, label: valueDisplayLabel(value, values) }));
    }
    return optionMap;
  });

  optionsAreValid = computed(() => {
    const optionDefinitions = this.actionOptions();
    const values = this.selectedOptions();
    for (const name of Object.keys(optionDefinitions)) {
      if (optionDefinitions[name].required && this.checkOptionVisibility(name) && this.isEmpty(values[name])) {
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
      this.touchedOptions.set({});
    });

    // Emit options + validity to the parent whenever they change
    effect(() => {
      const values = this.selectedOptions();
      this.optionsValid.emit(this.optionsAreValid());
      this.newOptions.emit(this.optionsToDict(values));
    });
  }

  setOption(name: string, value: EventActionOptionValue): void {
    this.selectedOptions.update((current) => ({ ...current, [name]: value }));
  }

  markOptionTouched(name: string): void {
    this.touchedOptions.update((current) => ({ ...current, [name]: true }));
  }

  isOptionInvalid(name: string): boolean {
    const definition = this.actionOptions()[name];
    if (!definition || !definition.required) return false;
    if (!this.checkOptionVisibility(name)) return false;
    return this.isEmpty(this.selectedOptions()[name]);
  }

  showOptionError(name: string): boolean {
    return !!this.touchedOptions()[name] && this.isOptionInvalid(name);
  }

  onActionSelectionChange(value: string): void {
    this.selectedAction.set(value);
    this.newAction.emit(value);
  }

  /**
   * What a read-only option displays.
   *
   * An option carrying `fromWebhook` mirrors a field of the webhook the `webhook` option names,
   * so the field shows where the handler actually posts rather than a value it no longer uses:
   * selecting a webhook replaces the stored inline URL and content type, and both have to follow
   * the selection as it changes. Without a selection the stored value is shown, which is what a
   * handler still on the inline shape has.
   *
   * Empty when a webhook is selected but cannot be resolved - /webhook/ needs webhook_read, and
   * an identifier may name a webhook that has since been deleted. Showing the stored inline value
   * there would name an endpoint this handler does not post to.
   */
  readonlyDisplayValue(optionName: string): string {
    const stored = this.selectedOptions()[optionName];
    const field = this.actionOptions()[optionName]?.fromWebhook;
    const identifier = field ? this.selectedOptions()["webhook"] : null;
    if (field && identifier) {
      const selected = this.webhookService.webhooks().find((webhook) => webhook.identifier === identifier);
      const value = selected ? (selected as unknown as Record<string, unknown>)[field] : null;
      return value == null ? "" : String(value);
    }
    return stored == null ? "" : String(stored);
  }

  checkOptionVisibility(optionName: string): boolean {
    const optionDetails = this.actionOptions()[optionName];
    if (!optionDetails || !optionDetails.visibleIf) return true;
    if (optionDetails.visibleValue === undefined) return true;
    const dependent = this.selectedOptions()[optionDetails.visibleIf];
    return dependent === optionDetails.visibleValue;
  }

  private isEmpty(value: EventActionOptionValue | undefined): boolean {
    return value === null || value === undefined || value === "";
  }

  private optionsToDict(values: EventActionOptionValues): EventActionOptionValues {
    const definitions = this.actionOptions();
    const result: EventActionOptionValues = {};
    for (const key of Object.keys(values)) {
      const value = values[key];
      if (value === null || value === undefined) continue;
      // A read-only option is never written back. Nobody can set it here, so storing one only
      // adds a row to the handler definition that nothing put there on purpose.
      if (definitions[key]?.readonly) continue;
      result[key] = value;
    }
    return result;
  }
}
