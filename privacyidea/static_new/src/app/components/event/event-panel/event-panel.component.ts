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
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  linkedSignal,
  OnDestroy,
  Renderer2,
  signal,
  ViewChild
} from "@angular/core";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { MatButton } from "@angular/material/button";
import { AuthService } from "../../../services/auth/auth.service";
import { ActivatedRoute, Router } from "@angular/router";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { EMPTY_EVENT, EventService } from "../../../services/event/event.service";
import { EventActionTabComponent } from "./tabs/event-action-tab/event-action-tab.component";
import { EventConditionsTabComponent } from "./tabs/event-conditions-tab/event-conditions-tab.component";
import { MatInput, MatLabel } from "@angular/material/input";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatFormField, MatFormFieldModule, MatHint } from "@angular/material/form-field";
import { MatOption, MatSelect, MatSelectModule } from "@angular/material/select";
import { deepCopy } from "../../../utils/deep-copy.utils";
import { NotificationService } from "../../../services/notification/notification.service";
import { MatChipsModule } from "@angular/material/chips";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { EventSelectionComponent } from "./event-selection/event-selection.component";
import { MatTab, MatTabGroup } from "@angular/material/tabs";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { PendingChangesService } from "../../../services/pending-changes/pending-changes.service";
import { ROUTE_PATHS } from "../../../route_paths";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatTooltip } from "@angular/material/tooltip";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";

export type eventTab = "events" | "action" | "conditions";

@Component({
  selector: "app-event-panel",
  imports: [
    MatIcon,
    EventActionTabComponent,
    EventConditionsTabComponent,
    MatFormField,
    MatHint,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatSelect,
    MatOption,
    MatAutocompleteModule,
    MatFormFieldModule,
    MatChipsModule,
    MatSelectModule,
    MatIconModule,
    FormsModule,
    ReactiveFormsModule,
    EventSelectionComponent,
    MatTabGroup,
    MatTab,
    ScrollToTopDirective,
    MatButton,
    MatSlideToggle,
    MatTooltip,
    CopyButtonComponent
  ],
  standalone: true,
  templateUrl: "./event-panel.component.html",
  styleUrl: "./event-panel.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EventPanelComponent implements AfterViewInit, OnDestroy {
  protected readonly eventService = inject(EventService);
  protected readonly authService = inject(AuthService);
  protected readonly notificationService = inject(NotificationService);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  protected readonly renderer: Renderer2 = inject(Renderer2);

  private observer!: IntersectionObserver;

  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;
  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;

  availableTabs: eventTab[] = ["action", "conditions"];

  // original event handler serves as input for child components to avoid a loop of change detection
  event = signal(EMPTY_EVENT);
  // edited event handler
  editEvent = signal(EMPTY_EVENT);
  isNewEvent = signal(false);
  hasChanges = signal(false);
  private editEventId: string | null = null;

  selectedEvents = linkedSignal(() => this.event().event);

  readonly title = computed(() =>
    this.isNewEvent() ? $localize`Create New Event Handler` : $localize`Edit Event Handler`
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

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) return;

    const options: IntersectionObserverInit = {
      root: this.scrollContainer.nativeElement,
      threshold: [0, 1]
    };

    this.observer = new IntersectionObserver(([entry]) => {
      if (!entry.rootBounds) return;

      const shouldFloat = entry.boundingClientRect.top < entry.rootBounds.top;

      if (shouldFloat) {
        this.renderer.addClass(this.stickyHeader.nativeElement, "is-sticky");
      } else {
        this.renderer.removeClass(this.stickyHeader.nativeElement, "is-sticky");
      }
    }, options);

    this.observer.observe(this.stickySentinel.nativeElement);
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
    this.observer?.disconnect();
  }


  cancelEdit(): void {
    this.router.navigateByUrl(ROUTE_PATHS.EVENTS);
  }

  validConditionsDefinition = computed(() => {
    if (!this.editEvent().conditions) return true;
    for (const conditionValue of Object.values(this.editEvent().conditions)) {
      if (conditionValue === null || conditionValue === undefined || conditionValue === "") return false;
    }
    return true;
  });

  validOptions = signal(false);

  sectionValidity = computed(() => {
    const validity: Record<string, any> = {};
    validity["events"] = this.editEvent().event.length > 0;
    validity["action"] = !!this.editEvent().action && this.validOptions();
    validity["name"] = this.editEvent().name !== "";
    validity["handlerModule"] =
      this.eventService.selectedHandlerModule() !== null && this.eventService.selectedHandlerModule() !== "";
    validity["position"] = this.editEvent().position !== null && this.editEvent().position !== "";
    validity["conditions"] = this.validConditionsDefinition();
    return validity;
  });
  canSave = computed(() => Object.values(this.sectionValidity()).every((value: boolean) => value));

  setNewAction(action: string): void {
    this.editEvent.set({ ...this.editEvent(), action });
    this.hasChanges.set(true);
  }

  setNewOptions(options: any): void {
    this.editEvent.set({ ...this.editEvent(), options });
    this.hasChanges.set(true);
  }

  setNewConditions(conditions: any): void {
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

  updateEventHandler(key: string, value: any): void {
    this.editEvent.set({ ...this.editEvent(), [key]: value });
    this.hasChanges.set(true);
  }

  getSaveParameters(): Record<string, any> {
    let eventParams = deepCopy(this.editEvent()) as Record<string, any>;
    for (const [optionKey, optionValue] of Object.entries(eventParams["options"] || {})) {
      eventParams["option." + optionKey] = optionValue;
    }
    eventParams["id"] = eventParams["id"].toString();
    eventParams["handlermodule"] = this.eventService.selectedHandlerModule();
    delete eventParams["options"];
    return eventParams;
  }

  saveEvent(): Promise<boolean> {
    return new Promise((resolve) => {
      let eventParams = this.getSaveParameters();
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
            this.notificationService.openSnackBar(message);
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
    if (!this.editEvent()) return;
    this.editEvent()!.active = activate;
    if (activate) {
      this.eventService.enableEvent(this.event()!.id);
    } else {
      this.eventService.disableEvent(this.event()!.id);
    }
  }
}
