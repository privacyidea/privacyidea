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

import { Component, computed, effect, inject, input, linkedSignal, output, signal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatIconButton } from "@angular/material/button";
import { MatChipsModule } from "@angular/material/chips";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIcon } from "@angular/material/icon";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { EventService } from "@services/event/event.service";

@Component({
  selector: "app-event-selection",
  imports: [FormsModule, MatIconButton, MatChipsModule, MatExpansionModule, MatIcon, ClearableInputComponent],
  templateUrl: "./event-selection.component.html",
  styleUrl: "./event-selection.component.scss"
})
export class EventSelectionComponent {
  protected readonly eventService = inject(EventService);
  events = input.required<string[]>();
  newEvents = output<string[]>();

  selectedEvents = signal<string[]>([]);
  touched = signal(false);
  invalid = computed(() => this.selectedEvents().length === 0);
  showError = computed(() => this.touched() && this.invalid());
  searchTerm = signal("");
  remainingEvents = linkedSignal({
    source: () => ({
      available: this.eventService.availableEvents(),
      selected: this.selectedEvents(),
      search: this.searchTerm()
    }),
    computation: ({ available, selected, search }) =>
      available.filter(
        (event) => !selected.includes(event) && (!search || event.toLowerCase().includes(search.toLowerCase()))
      )
  });

  constructor() {
    effect(() => {
      this.selectedEvents.set(this.events());
    });
  }

  markTouched(): void {
    this.touched.set(true);
  }

  removeEvent(event: string): void {
    const current = this.selectedEvents();
    const index = current.indexOf(event);
    if (index > -1) {
      const updated = [...current.slice(0, index), ...current.slice(index + 1)];
      this.selectedEvents.set(updated);
      this.newEvents.emit(updated);
      this.markTouched();
    }
  }

  addEvent(event: string): void {
    const current = this.selectedEvents();
    if (event && current.indexOf(event) === -1) {
      const updated = [...current, event];
      this.selectedEvents.set(updated);
      this.newEvents.emit(updated);
    }
  }
}
