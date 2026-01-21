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

import { Component, inject, input, linkedSignal, model, output, ViewChild } from "@angular/core";
import { EventService } from "../../../../services/event/event.service";
import { deepCopy } from "../../../../utils/deep-copy.utils";
import { ENTER } from "@angular/cdk/keycodes";
import {
  MatAutocomplete,
  MatAutocompleteSelectedEvent,
  MatAutocompleteTrigger,
  MatOption
} from "@angular/material/autocomplete";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatChipsModule } from "@angular/material/chips";
import { MatFormFieldModule, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";

@Component({
  selector: "app-event-selection",
  imports: [
    FormsModule,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatChipsModule,
    MatFormFieldModule,
    MatHint,
    MatIcon,
    MatLabel,
    MatOption,
    ReactiveFormsModule,
    MatInput
  ],
  templateUrl: "./event-selection.component.html",
  styleUrl: "./event-selection.component.scss"
})
export class EventSelectionComponent {
  protected readonly eventService = inject(EventService);
  events = input.required<string[]>();
  newEvents = output<string[]>();

  selectedEvents = linkedSignal(() => deepCopy(this.events()));

  searchTerm = model("");
  lastSearchTerm = "";
  readonly separatorKeysCodes: number[] = [ENTER];

  removeEvent(event: string): void {
    const index = this.selectedEvents().indexOf(event);
    if (index > -1) {
      this.selectedEvents().splice(index, 1);
      this.newEvents.emit(this.selectedEvents());
    }
  }

  addEvent(event: string): void {
    if (event && this.selectedEvents().indexOf(event) === -1) {
      this.selectedEvents().push(event);
      this.newEvents.emit(this.selectedEvents());
    }
  }

  @ViewChild("autocompleteTrigger") autocompleteTrigger!: MatAutocompleteTrigger;

  selected(event: MatAutocompleteSelectedEvent): void {
    this.addEvent(event.option.viewValue);
    this.searchTerm.set(this.lastSearchTerm);
    setTimeout(() => {
      this.autocompleteTrigger.openPanel();
    });
  }

  onSearchInputChanges(event: any): void {
    this.lastSearchTerm = event.target.value;
  }

  remainingEvents = linkedSignal({
    source: () => ({
      available: this.eventService.availableEvents(),
      selected: this.selectedEvents(),
      search: this.searchTerm()
    }),
    computation: ({ available, selected, search }) =>
      available.filter(event =>
        !selected.includes(event) &&
        (!search || event.toLowerCase().includes(search.toLowerCase()))
      )
  });
}
