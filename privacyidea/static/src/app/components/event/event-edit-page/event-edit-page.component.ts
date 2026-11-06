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

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  OnDestroy,
  signal,
  untracked
} from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { disabled, form, FormField, pattern, required, validate } from "@angular/forms/signals";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButton } from "@angular/material/button";
import { MatChipsModule } from "@angular/material/chips";
import { MatFormField, MatFormFieldModule, MatHint } from "@angular/material/form-field";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { MatInput, MatLabel } from "@angular/material/input";
import { MatOption, MatSelect, MatSelectModule } from "@angular/material/select";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatTab, MatTabGroup } from "@angular/material/tabs";
import { MatTooltip } from "@angular/material/tooltip";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { AuthService } from "@services/auth/auth.service";
import {
  EMPTY_EVENT,
  EventHandlerSaveParams,
  EventHandler,
  EventService,
  isValidOrdering,
  MAX_ORDERING,
  toEventHandlerSaveParams
} from "@services/event/event.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { deepCopy } from "@utils/deep-copy.utils";
import { ERR, EVENT_NAME_PATTERN, requiredNonEmptyArray } from "@utils/form-rules.utils";
import { clearField, hasError, touchAll } from "@utils/form-state.utils";
import { EventSelectionComponent } from "./event-selection/event-selection.component";
import { EventActionOptionValues, EventActionTabComponent } from "./tabs/event-action-tab/event-action-tab.component";
import { EventConditionsTabComponent } from "./tabs/event-conditions-tab/event-conditions-tab.component";

export type eventTab = "events" | "action" | "conditions";

const ORDERING_RANGE = "orderingRange";
const CONDITION_VALUE = "conditionValue";

/**
 * A comparable form of a handler. The order of options and conditions does not matter, and an option without a
 * value equals an option that is not set, because the action tab fills every option of its action with an empty value.
 */
function comparableHandler(handler: EventHandler): string {
  const sortedEntries = (record: Record<string, unknown> | null | undefined, keep: (value: unknown) => boolean) =>
    Object.fromEntries(
      Object.entries(record ?? {})
        .filter(([, value]) => keep(value))
        .sort(([a], [b]) => a.localeCompare(b))
    );
  return JSON.stringify({
    ...handler,
    options: sortedEntries(handler.options, (value) => value !== "" && value !== null && value !== undefined),
    conditions: sortedEntries(handler.conditions, () => true)
  });
}

@Component({
  selector: "app-event-edit-page",
  imports: [
    MatIcon,
    EventActionTabComponent,
    EventConditionsTabComponent,
    MatFormField,
    MatHint,
    MatInput,
    MatLabel,
    MatSelect,
    MatOption,
    MatAutocompleteModule,
    MatFormFieldModule,
    MatChipsModule,
    MatSelectModule,
    MatIconModule,
    EventSelectionComponent,
    MatTabGroup,
    MatTab,
    ScrollToTopDirective,
    StickyHeaderDirective,
    MatButton,
    MatSlideToggle,
    MatTooltip,
    ClearableInputComponent,
    FormField
  ],
  standalone: true,
  templateUrl: "./event-edit-page.component.html",
  styleUrl: "./event-edit-page.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EventEditPageComponent implements OnDestroy {
  protected readonly eventService = inject(EventService);
  protected readonly authService = inject(AuthService);
  protected readonly notificationService = inject(NotificationService);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private editEventId: string | null = null;
  availableTabs: eventTab[] = ["action", "conditions"];
  // original event handler serves as input for child components to avoid a loop of change detection
  event = signal(EMPTY_EVENT);
  // edited event handler
  editEvent = signal(EMPTY_EVENT);
  isNewEvent = signal(false);
  readonly title = computed(() =>
    this.isNewEvent()
      ? $localize`:@@event.createNewEvent:Create New Event Handler`
      : $localize`:@@event.editEventHandler:Edit Event Handler`
  );
  eventLoaded = computed(() => this.isNewEvent() || this.editEvent() !== EMPTY_EVENT);
  editForm = form(this.editEvent, (f) => {
    disabled(f.name, () => !this.eventLoaded());
    required(f.name);
    pattern(f.name, EVENT_NAME_PATTERN);
    required(f.handlermodule);
    disabled(f.handlermodule, () => !this.isNewEvent());
    required(f.position);
    required(f.ordering);
    validate(f.ordering, (ctx) => {
      const ordering = ctx.value();
      return ordering === null || isValidOrdering(ordering) ? undefined : { kind: ORDERING_RANGE };
    });
    required(f.action);
    requiredNonEmptyArray(f.event);
    validate(f.conditions, (ctx) =>
      Object.values(ctx.value() ?? {}).some((value) => value === null || value === undefined || value === "")
        ? { kind: CONDITION_VALUE }
        : undefined
    );
    disabled(f.active, () => !this.authService.actionAllowed("eventhandling_write"));
  });
  hasChanges = computed(() => comparableHandler(this.editEvent()) !== comparableHandler(this.event()));
  // Validity of the options of the action, reported by the action tab
  validOptions = signal(false);
  canSave = computed(() => this.editForm().valid() && this.validOptions());
  protected readonly hasError = hasError;
  protected readonly ERR = ERR;
  protected readonly ORDERING_RANGE = ORDERING_RANGE;
  protected readonly MAX_ORDERING = MAX_ORDERING;

  constructor() {
    // Determine new vs edit mode from route
    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const id = params.get("id");
      if (id) {
        this.isNewEvent.set(false);
        this.editEventId = id;
        const handler = (this.eventService.eventHandlers() ?? []).find((h) => String(h.id) === id);
        if (handler) {
          this.event.set(deepCopy(handler));
          this.editEvent.set(deepCopy(handler));
        }
      } else {
        this.isNewEvent.set(true);
        this.editEventId = null;
        const emptyEvent = deepCopy(EMPTY_EVENT);
        const modules = this.eventService.eventHandlerModules();
        if (modules.length > 0) {
          emptyEvent.handlermodule = modules[0];
        }
        this.event.set(deepCopy(emptyEvent));
        this.editEvent.set(emptyEvent);
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const handlers = this.eventService.eventHandlers() ?? [];
      if (!this.isNewEvent() && this.editEventId && !this.hasChanges()) {
        const found = handlers.find((h) => String(h.id) === this.editEventId);
        if (found) {
          this.event.set(deepCopy(found));
          this.editEvent.set(deepCopy(found));
        }
      }
    });

    // The positions, actions and conditions of the service follow the handler module of the edited event handler
    effect(() => {
      this.eventService.selectedHandlerModule.set(this.editEvent().handlermodule || null);
    });

    // A handler whose result the request consumes is created with "abort on error" enabled, see
    // GET /event/defaults/<handlermodule>. The default only fills in for a new binding that the user has not
    // decided on yet: an existing binding keeps its stored value, and so does an explicit choice of the user.
    effect(() => {
      const defaults = this.eventService.moduleDefaults();
      if (!defaults || !this.isNewEvent() || this.editForm.abort_on_error().dirty()) {
        return;
      }
      untracked(() => {
        this.event.update((current) => ({ ...current, abort_on_error: defaults.abort_on_error }));
        this.editEvent.update((current) => ({ ...current, abort_on_error: defaults.abort_on_error }));
      });
    });

    this.pendingChangesService.registerHasChanges(() => this.hasChanges());
    this.pendingChangesService.registerSave(this.saveEvent.bind(this));
    this.pendingChangesService.registerValidChanges(() => this.canSave());
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  cancelEdit(): void {
    this.router.navigateByUrl(ROUTE_PATHS.EVENTS);
  }

  clearName(): void {
    clearField(this.editForm.name, "");
  }

  setNewAction(action: string): void {
    this.editEvent.update((current) => ({ ...current, action }));
  }

  setNewOptions(options: EventActionOptionValues): void {
    const current = this.editEvent().options || {};
    if (JSON.stringify(options) === JSON.stringify(current)) return;
    this.editEvent.update((handler) => ({ ...handler, options: options as unknown as Record<string, string> | null }));
  }

  setNewConditions(conditions: Record<string, string>): void {
    this.editEvent.update((current) => ({ ...current, conditions }));
  }

  setNewEvents(events: string[]): void {
    this.editEvent.update((current) => ({ ...current, event: events }));
  }

  getSaveParameters(): EventHandlerSaveParams {
    const eventParams = toEventHandlerSaveParams(deepCopy(this.editEvent()));
    // The edit form always carries the complete option set of the selected action, so the stored
    // options have to be replaced even when the action has none. Without this flag, a request
    // without any "option.*" parameter leaves the stored options untouched.
    eventParams.clear_options = true;
    return eventParams;
  }

  async saveEvent(): Promise<boolean> {
    if (!this.canSave()) {
      await touchAll(this.editForm);
      return false;
    }
    return new Promise((resolve) => {
      const eventParams = this.getSaveParameters();
      if (this.isNewEvent()) {
        delete eventParams["id"];
      }
      this.eventService.saveEventHandler(eventParams).subscribe({
        next: (response) => {
          if (response?.result?.value !== undefined) {
            this.eventService.allEventsResource.reload();
            this.pendingChangesService.clearAllRegistrations();
            this.router.navigateByUrl(ROUTE_PATHS.EVENTS);
            const message = this.isNewEvent()
              ? $localize`:@@event.eventHandlerCreated:Event handler created successfully.`
              : $localize`:@@event.eventHandlerUpdated:Event handler updated successfully.`;
            this.notificationService.success(message);
            resolve(true);
          } else {
            resolve(false);
          }
        },
        error: () => resolve(false)
      });
    });
  }

  async deleteEvent(): Promise<void> {
    const result = await this.eventService.deleteWithConfirmDialog(this.event());
    if (!result) {
      return;
    }
    this.eventService.allEventsResource.reload();
    this.pendingChangesService.clearAllRegistrations();
    await this.router.navigateByUrl(ROUTE_PATHS.EVENTS);
  }

  toggleActive(activate: boolean): void {
    if (!this.editEvent() || this.event()!.id == null) {
      return;
    }
    this.editEvent()!.active = activate;
    if (activate) {
      this.eventService.enableEvent(this.event()!.id);
    } else {
      this.eventService.disableEvent(this.event()!.id);
    }
  }
}
