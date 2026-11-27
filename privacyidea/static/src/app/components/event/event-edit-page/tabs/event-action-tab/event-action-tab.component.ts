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
import { HttpErrorResponse } from "@angular/common/http";
import {
  afterNextRender,
  Component,
  computed,
  effect,
  inject,
  Injector,
  input,
  output,
  signal,
  untracked,
  viewChild
} from "@angular/core";
import {
  applyEach,
  disabled,
  FieldTree,
  form,
  FormField,
  metadata,
  REQUIRED,
  required,
  validate
} from "@angular/forms/signals";
import { MatButton } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { ActionOptionDetails, CONFIG_ADMIN_ERROR_CODE, EventService } from "@services/event/event.service";
import { WebhookService, WebhookServiceInterface } from "@services/webhook/webhook.service";
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
  imports: [
    MatButton,
    MatFormField,
    MatHint,
    MatIcon,
    MatLabel,
    MatOption,
    MatSelect,
    MatInput,
    MatCheckbox,
    MatError,
    NgClass,
    FormField
  ],
  templateUrl: "./event-action-tab.component.html",
  styleUrl: "./event-action-tab.component.scss"
})
export class EventActionTabComponent {
  protected readonly eventService = inject(EventService);
  private readonly injector = inject(Injector);
  protected readonly Object = Object;
  protected readonly hasError = hasError;
  protected readonly ERR = ERR;
  action = input.required<string>();
  options = input.required<EventActionOptionValues>();
  newAction = output<string>();
  newOptions = output<EventActionOptionValues>();
  optionsValid = output<boolean>();
  selectedAction = signal<string>("");
  private readonly actionSelect = viewChild(MatSelect);
  private readonly awaitingReload = signal(false);
  selectedActionForm = form(this.selectedAction, (f) => {
    required(f);
  });

  selectedOptions = signal<EventActionOptionValues>({});
  optionsForm = form(this.selectedOptions, (f) => {
    applyEach(f, (option) => {
      // A read-only option shows a value that belongs elsewhere, e.g. the URL of the webhook a WebHook handler names
      disabled(option, (ctx) => !!this.actionOptions()[ctx.key()]?.readonly);
      metadata(option, REQUIRED, (ctx) => this.isOptionRequired(ctx.key()));
      validate(option, (ctx) =>
        this.isOptionRequired(ctx.key()) && this.isEmpty(ctx.value()) ? { kind: ERR.required } : undefined
      );
    });
  });

  /**
   * The Script handler offers each file in its script directory as an action. If the directory is empty, or if the
   * server answers that it cannot open the directory, the tab explains where the scripts go instead of showing an
   * empty dropdown. The server reads the directory on each request, so new scripts show up after a reload of the
   * actions. A reload keeps the hint visible. During the first load, after any other failed request and if the
   * request does not run (for example without eventhandling_read), the tab shows the dropdown.
   */
  noScriptsFound = computed(() => {
    if (this.eventService.selectedHandlerModule() !== "Script") {
      return false;
    }
    const resource = this.eventService.moduleActionsResource;
    const status = resource.status();
    if (status === "error") {
      const error = resource.error() as HttpErrorResponse | undefined;
      return error?.error?.result?.error?.code === CONFIG_ADMIN_ERROR_CODE;
    }
    return (
      (status === "resolved" || status === "reloading") && Object.keys(this.eventService.moduleActions()).length === 0
    );
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

  optionNames = computed(() => Object.keys(this.selectedOptions()).filter((name) => name in this.actionOptions()));

  /**
   * The option names in the order they are shown. A handler module states it per option (`order`);
   * the ones that do not come after, in the order the response carries them. `sort` is stable, so
   * that order is preserved rather than reshuffled.
   */
  orderedOptionNames = computed<string[]>(() => {
    const definitions = this.actionOptions();
    return [...this.optionNames()].sort((left, right) => {
      const leftOrder = definitions[left]?.order;
      const rightOrder = definitions[right]?.order;
      if (leftOrder != null && rightOrder != null) return leftOrder - rightOrder;
      if (leftOrder != null) return -1;
      if (rightOrder != null) return 1;
      return 0;
    });
  });

  constructor() {
    effect(() => {
      const status = this.eventService.moduleActionsResource.status();
      if (!this.awaitingReload() || status === "loading" || status === "reloading") {
        return;
      }
      untracked(() => this.finishReload());
    });

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

  reloadScripts(): void {
    if (this.eventService.moduleActionsResource.isLoading()) {
      return;
    }
    this.awaitingReload.set(this.eventService.moduleActionsResource.reload());
  }

  /**
   * The reload button leaves the page together with the hint, so focus moves to the action dropdown. If the hint
   * stays, the button keeps focus.
   */
  private finishReload(): void {
    this.awaitingReload.set(false);
    if (!this.noScriptsFound()) {
      afterNextRender({ read: () => this.actionSelect()?.focus() }, { injector: this.injector });
    }
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
    const definitions = this.actionOptions();
    const result: EventActionOptionValues = {};
    for (const key of Object.keys(values)) {
      const value = values[key];
      if (value === null || value === undefined) continue;
      // An *empty* read-only option is dropped: nobody can set it here, so a blank row carries no
      // intent. One that holds a value is passed through, because the save replaces the whole
      // option set and that value is the inline endpoint of a handler the 3.15 upgrade converted.
      // The migration promises not to delete it, and that promise is what keeps
      // `pi-manage db downgrade` safe: the downgrade strips the `webhook` option from every
      // handler, so one that lost its URL here would come back with no endpoint at all.
      if (definitions[key]?.readonly && value === "") continue;
      result[key] = value;
    }
    return result;
  }
}
