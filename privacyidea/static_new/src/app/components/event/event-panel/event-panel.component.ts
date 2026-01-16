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

import { Component, computed, effect, inject, input, linkedSignal, signal, WritableSignal } from "@angular/core";
import {
  MatExpansionPanel,
  MatExpansionPanelDescription,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatTooltip } from "@angular/material/tooltip";
import { AuthService } from "../../../services/auth/auth.service";
import { MatDialog } from "@angular/material/dialog";
import { EventHandler, EventService } from "../../../services/event/event.service";
import { EventActionTabComponent } from "./tabs/event-action-tab/event-action-tab.component";
import { EventConditionsTabComponent } from "./tabs/event-conditions-tab/event-conditions-tab.component";
import { MatInput, MatLabel } from "@angular/material/input";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatFormField, MatFormFieldModule, MatHint } from "@angular/material/form-field";
import { MatOption, MatSelect, MatSelectModule } from "@angular/material/select";
import { deepCopy } from "../../../utils/deep-copy.utils";
import { EventActionTabReadComponent } from "./tabs/event-action-tab-read/event-action-tab-read.component";
import { NotificationService } from "../../../services/notification/notification.service";
import { MatChipsModule } from "@angular/material/chips";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { CommonModule } from "@angular/common";
import { EventSelectionComponent } from "./event-selection/event-selection.component";

export type eventTab = "events" | "action" | "conditions";

@Component({
  selector: "app-event-panel",
  imports: [
    MatExpansionPanel,
    MatExpansionPanelDescription,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatIcon,
    MatIconButton,
    MatSlideToggle,
    MatTooltip,
    MatButton,
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
    EventActionTabReadComponent,
    MatAutocompleteModule,
    CommonModule,
    MatFormFieldModule,
    MatChipsModule,
    MatSelectModule,
    MatIconModule,
    FormsModule,
    ReactiveFormsModule,
    EventSelectionComponent
  ],
  standalone: true,
  templateUrl: "./event-panel.component.html",
  styleUrl: "./event-panel.component.scss"
})
export class EventPanelComponent {
  eventService = inject(EventService);
  authService = inject(AuthService);
  notificiationService = inject(NotificationService);
  private readonly dialog: MatDialog = inject(MatDialog);
  event = input.required<EventHandler>();
  isNewEvent = input<boolean>(false);
  isEditMode = signal(false);
  activeTab: WritableSignal<eventTab> = signal("events");
  isExpanded = signal(false);

  selectedEvents = linkedSignal(() => this.event().event);

  onPanelOpened() {
    this.isExpanded.set(true);
  }

  onPanelClosed() {
    this.isExpanded.set(false);
  }

  // effect to notify the event service to reload handler module related data
  protected readonly setHandlerModuleEffect = effect(() => {
    if (this.isExpanded() && this.event().handlermodule) {
      this.eventService.selectedHandlerModule.set(this.event().handlermodule);
    }
  });

  editEvent = linkedSignal(() => this.event());

  cancelEdit(): void {
    this.isEditMode.set(false);
    this.editEvent.set(this.event());
  }

  validActionDefinition = computed(() => {
    if (!this.editEvent().action) {
      return false;
    }
    const options = this.eventService.moduleActions()[this.editEvent().action] || {};
    for (const [optionName, optionDetails] of Object.entries(options)) {
      if (optionDetails.required) {
        // Required options must be included and contain a valid value
        const optionValue = this.editEvent().options?.[optionName];
        if (optionValue === undefined || optionValue === null) {
          return false;
        }
        if (typeof optionValue === "string" && optionValue === "") {
          return false;
        }
      }
    }
    return true;
  });

  sectionValidity = computed(() => {
    const validity: Record<string, any> = {};
    validity["events"] = this.editEvent().event.length > 0;
    validity["action"] = this.validActionDefinition();
    validity["name"] = this.editEvent().name !== "";
    validity["handlerModule"] = this.eventService.selectedHandlerModule() !== null && this.eventService.selectedHandlerModule() !== "";
    validity["position"] = this.editEvent().position !== null && this.editEvent().position !== "";
    return validity;
  });
  canSave = computed(() => Object.values(this.sectionValidity()).every((value: boolean) => value));

  setNewAction(action: string): void {
    this.editEvent.set({ ...this.editEvent(), action: action });
  }

  setNewOptions(options: any): void {
    this.editEvent.set({ ...this.editEvent(), options: options });
  }

  setNewConditions(conditions: any): void {
    this.editEvent.set({ ...this.editEvent(), conditions: conditions });
  }

  setNewEvents(events: string[]): void {
    this.editEvent.set({ ...this.editEvent(), event: events });
  }


  updateEventHandler(key: string, value: any): void {
    // Update function to trigger change detection
    this.editEvent.set({ ...this.editEvent(), [key]: value });
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
    this.eventService.saveEventHandler(eventParams).subscribe({
      next: (response) => {
        if (response?.result?.value !== undefined) {
          this.eventService.allEventsResource.reload();
          this.isEditMode.set(false);
          this.notificiationService.openSnackBar("Event handler updated successfully.");
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
    if (!this.isEditMode()) {
      if (activate) {
        this.eventService.enableEvent(this.event()!.id);
      } else {
        this.eventService.disableEvent(this.event()!.id);
      }
    }
  }
}
