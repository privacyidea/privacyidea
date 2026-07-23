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
  linkedSignal,
  OnDestroy,
  signal
} from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
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
import { ErrorStateDirective } from "@components/shared/directives/error-state.directive";
import { AuthService } from "@services/auth/auth.service";
import { EMPTY_EVENT, EventHandlerSaveParams, EventService } from "@services/event/event.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { deepCopy } from "@utils/deep-copy.utils";
import { EventSelectionComponent } from "./event-selection/event-selection.component";
import { EventActionOptionValues, EventActionTabComponent } from "./tabs/event-action-tab/event-action-tab.component";
import { EventConditionsTabComponent } from "./tabs/event-conditions-tab/event-conditions-tab.component";

export type eventTab = "events" | "action" | "conditions";

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
    ErrorStateDirective,
    ClearableInputComponent
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
    this.isNewEvent() ? $localize`Create New Event Handler` : $localize`Edit Event Handler`
  );
  hasChanges = signal(false);
  selectedEvents = linkedSignal(() => this.event().event);
  validConditionsDefinition = computed(() => {
    if (!this.editEvent().conditions) return true;
    for (const conditionValue of Object.values(this.editEvent().conditions)) {
      if (conditionValue === null || conditionValue === undefined || conditionValue === "") return false;
    }
    return true;
  });
  validOptions = signal(false);
  sectionValidity = computed(() => {
    const validity: Record<string, boolean> = {};
    validity["events"] = this.editEvent().event.length > 0;
    validity["action"] = !!this.editEvent().action && this.validOptions();
    validity["name"] = this.editEvent().name !== "" && /^[a-zA-Z0-9._-]*$/.test(this.editEvent().name);
    validity["handlerModule"] =
      this.eventService.selectedHandlerModule() !== null && this.eventService.selectedHandlerModule() !== "";
    validity["position"] = this.editEvent().position !== null && this.editEvent().position !== "";
    validity["conditions"] = this.validConditionsDefinition();
    return validity;
  });
  canSave = computed(() => Object.values(this.sectionValidity()).every((value: boolean) => value));
  nameTouched = signal(false);
  showNameError = computed(() => this.nameTouched() && !this.sectionValidity()["name"]);
  showHandlerModuleError = computed(() => !this.sectionValidity()["handlerModule"]);
  showPositionError = computed(() => !this.sectionValidity()["position"]);
  showOrderingError = computed(
    () => this.editEvent().ordering === null || (this.editEvent().ordering as unknown) === ""
  );

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
          this.eventService.selectedHandlerModule.set(handler.handlermodule);
        }
      } else {
        this.isNewEvent.set(true);
        this.editEventId = null;
        this.event.set(deepCopy(EMPTY_EVENT));
        this.editEvent.set(deepCopy(EMPTY_EVENT));
        const modules = this.eventService.eventHandlerModules();
        if (modules.length > 0) {
          this.eventService.selectedHandlerModule.set(modules[0]);
        }
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
          this.eventService.selectedHandlerModule.set(found.handlermodule);
        }
      }
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

  setNewAction(action: string): void {
    this.editEvent.set({ ...this.editEvent(), action });
    this.hasChanges.set(true);
  }

  setNewOptions(options: EventActionOptionValues): void {
    const current = this.editEvent().options || {};
    if (JSON.stringify(options) === JSON.stringify(current)) return;
    this.editEvent.set({ ...this.editEvent(), options: options as unknown as Record<string, string> | null });
    this.hasChanges.set(true);
  }

  setNewConditions(conditions: Record<string, string>): void {
    this.editEvent.set({ ...this.editEvent(), conditions });
    this.hasChanges.set(true);
  }

  setNewEvents(events: string[]): void {
    this.editEvent.set({ ...this.editEvent(), event: events });
    this.hasChanges.set(true);
  }

  setNewHandlerModule(module: string): void {
    this.eventService.selectedHandlerModule.set(module);
    this.hasChanges.set(true);
  }

  updateEventHandler(key: string, value: string | number | boolean): void {
    this.editEvent.set({ ...this.editEvent(), [key]: value });
    this.hasChanges.set(true);
  }

  getSaveParameters(): EventHandlerSaveParams {
    type EventHandlerParams = EventHandlerSaveParams & { options?: Record<string, unknown> };
    const eventParams = deepCopy(this.editEvent()) as unknown as EventHandlerParams;
    const options = eventParams.options ?? {};
    for (const [optionKey, optionValue] of Object.entries(options)) {
      eventParams["option." + optionKey] = optionValue;
    }
    if (eventParams.id != null) {
      eventParams.id = String(eventParams.id);
    }
    eventParams.handlermodule = this.eventService.selectedHandlerModule();
    delete eventParams.options;
    return eventParams;
  }

  saveEvent(): Promise<boolean> {
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
              ? $localize`Event handler created successfully.`
              : $localize`Event handler updated successfully.`;
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
    await this.eventService.deleteWithConfirmDialog(this.event());
    this.eventService.allEventsResource.reload();
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
