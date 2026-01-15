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

import { Component, inject, input, linkedSignal, output, signal } from "@angular/core";
import { MatDivider } from "@angular/material/divider";
import { MatTooltip } from "@angular/material/tooltip";
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { EventService } from "../../../../../services/event/event.service";
import { deepCopy } from "../../../../../utils/deep-copy.utils";
import { FormsModule } from "@angular/forms";
import { ClearableInputComponent } from "../../../../shared/clearable-input/clearable-input.component";
import { MatInput } from "@angular/material/input";
import { MatFormField, MatLabel } from "@angular/material/form-field";

@Component({
  selector: "app-events-tab",
  imports: [
    MatDivider,
    MatIcon,
    MatIconButton,
    MatTooltip,
    FormsModule,
    MatFormField,
    MatLabel,
    ClearableInputComponent,
    MatInput
  ],
  templateUrl: "./events-tab.component.html",
  styleUrl: "./events-tab.component.scss"
})
export class EventsTabComponent {
  protected readonly eventService = inject(EventService);
  events = input.required<string[]>();
  isEditMode = input.required<boolean>();
  newEvents = output<string[]>();

  editEvents = linkedSignal(() => deepCopy(this.events()));
  searchTerm = signal("");

  addEvent(eventName: string): void {
    this.editEvents.set([...this.editEvents(), eventName]);
    this.newEvents.emit(this.editEvents());
  }

  removeEvent(event: string): void {
    const index = this.editEvents().indexOf(event);
    if (index > -1) {
      this.editEvents().splice(index, 1);
      this.editEvents.set([...this.editEvents()]); // Trigger change detection
      this.newEvents.emit(this.editEvents());
    }
  }

  remainingEvents = linkedSignal({
    source: () => ({
      available: this.eventService.availableEvents(),
      selected: this.editEvents(),
      search: this.searchTerm()
    }),
    computation: ({ available, selected, search }) =>
      available.filter(event =>
        !selected.includes(event) &&
        (!search || event.toLowerCase().includes(search.toLowerCase()))
      )
  });
}
