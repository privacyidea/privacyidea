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
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from "@angular/material/dialog";
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
import { CommonModule } from "@angular/common";
import { EventSelectionComponent } from "./event-selection/event-selection.component";
import { MatTab, MatTabGroup } from "@angular/material/tabs";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { PendingChangesService } from "../../../services/pending-changes/pending-changes.service";
import { ConfirmationDialogComponent } from "../../shared/confirmation-dialog/confirmation-dialog.component";
import { ROUTE_PATHS } from "../../../route_paths";
import { ContentService } from "../../../services/content/content.service";
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
    CommonModule,
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
  private readonly dialog: MatDialog = inject(MatDialog);
  public readonly data = inject(MAT_DIALOG_DATA, { optional: false });
  protected readonly renderer: Renderer2 = inject(Renderer2);
  private readonly contentService = inject(ContentService);
  public readonly dialogRef = inject(MatDialogRef<EventPanelComponent>, { optional: true });

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

  selectedEvents = linkedSignal(() => this.event().event);

  constructor() {
    this.event.set(deepCopy(this.data.eventHandler ?? EMPTY_EVENT));
    this.editEvent.set(deepCopy(this.data.eventHandler ?? EMPTY_EVENT));
    this.isNewEvent.set(this.data.isNewEvent ?? false);

    // Avoid closing the dialog with pending changes (when clicking next to the dialog or pressing ESC)
    if (this.dialogRef) {
      this.dialogRef.disableClose = true;
      this.dialogRef.backdropClick().subscribe(() => {
        this.cancelEdit();
      });
      this.dialogRef.keydownEvents().subscribe(event => {
        if (event.key === "Escape") {
          this.cancelEdit();
        }
      });
    }

    this.pendingChangesService.registerHasChanges(() => this.hasChanges());

    // Close the dialog when navigating away from the events route
    // However, changing the route is disabled via the pendingChangesGuard when there are unsaved changes. This effect
    // will only be triggered when there are no unsaved changes or when the user confirmed discarding them.
    effect(() => {
      if (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.EVENTS)) {
        this.dialogRef?.close(true);
      }
    });
  }

  ngAfterViewInit(): void {
    // Setup for sticky header
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) {
      return;
    }

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
    this.pendingChangesService.unregisterHasChanges();
    if (this.observer) {
      this.observer.disconnect();
    }
  }

  // effect to notify the event service to reload handler module related data
  protected readonly setHandlerModuleEffect = effect(() => {
    if (this.event().handlermodule) {
      this.eventService.selectedHandlerModule.set(this.event().handlermodule);
    } else if (this.isNewEvent()) {
      const modules = this.eventService.eventHandlerModules();
      if (modules.length > 0 && !this.eventService.selectedHandlerModule()) {
        this.eventService.selectedHandlerModule.set(modules[0]);
      }
    }
  });

  cancelEdit(): void {
    if (this.hasChanges()) {
      this.dialog.open(ConfirmationDialogComponent, {
        data: {
          title: $localize`Discard changes`,
          action: "discard",
          type: "resolver"
        }
      }).afterClosed().subscribe(result => {
        if (result?.confirmed) {
          this.closeActual();
        } else if (result?.furtherAction === 'saveAndExit') {
          this.saveEvent();
        }
      });
    } else {
      this.closeActual();
    }
  }

  private closeActual(): void {
    this.editEvent.set(this.event());
    this.eventService.selectedHandlerModule.set(this.eventService.eventHandlerModules()[0] || "");
    if (this.dialogRef) {
      this.dialogRef.close();
    }
  }

  validConditionsDefinition = computed(() => {
    if (!this.editEvent().conditions) {
      return true;
    }
    for (const conditionValue of Object.values(this.editEvent().conditions)) {
      if (conditionValue === null || conditionValue === undefined || conditionValue === "") {
        return false;
      }
    }
    return true;
  });

  validOptions = signal(false);

  sectionValidity = computed(() => {
    const validity: Record<string, any> = {};
    validity["events"] = this.editEvent().event.length > 0;
    validity["action"] = !!this.editEvent().action && this.validOptions();
    validity["name"] = this.editEvent().name !== "";
    validity["handlerModule"] = this.eventService.selectedHandlerModule() !== null && this.eventService.selectedHandlerModule() !== "";
    validity["position"] = this.editEvent().position !== null && this.editEvent().position !== "";
    validity["conditions"] = this.validConditionsDefinition();
    return validity;
  });
  canSave = computed(() => Object.values(this.sectionValidity()).every((value: boolean) => value));

  setNewAction(action: string): void {
    this.editEvent.set({ ...this.editEvent(), action: action });
    this.hasChanges.set(true);
  }

  setNewOptions(options: any): void {
    this.editEvent.set({ ...this.editEvent(), options: options });
    this.hasChanges.set(true);
  }

  setNewConditions(conditions: any): void {
    this.editEvent.set({ ...this.editEvent(), conditions: conditions });
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
    // Update function to trigger change detection
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

  saveEvent(): void {
    let eventParams = this.getSaveParameters();
    if (this.isNewEvent()) {
      // new event handler do not yet have an ID
      delete eventParams["id"];
    }
    this.eventService.saveEventHandler(eventParams).subscribe({
      next: (response) => {
        if (response?.result?.value !== undefined) {
          this.eventService.allEventsResource.reload();
          this.dialogRef?.close();
          if (this.isNewEvent()) {
            this.notificationService.openSnackBar("Event handler created successfully.");
          } else {
            this.notificationService.openSnackBar("Event handler updated successfully.");
          }
        }
      }
    });
  }

  deleteEvent(): void {
    this.eventService.deleteWithConfirmDialog(this.event(), this.dialog, () => this.eventService.allEventsResource.reload());
  }

  toggleActive(activate: boolean): void {
    if (!this.editEvent()) {
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
