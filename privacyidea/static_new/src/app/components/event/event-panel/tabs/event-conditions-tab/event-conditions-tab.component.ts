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

import { Component, computed, inject, input, linkedSignal, output, signal } from "@angular/core";
import { EventCondition, EventService } from "../../../../../services/event/event.service";
import { deepCopy } from "../../../../../utils/deep-copy.utils";
import { MatIcon } from "@angular/material/icon";
import { MatIconButton } from "@angular/material/button";
import { ClearableInputComponent } from "../../../../shared/clearable-input/clearable-input.component";
import { MatDivider } from "@angular/material/divider";
import { MatInput, MatLabel } from "@angular/material/input";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatFormField } from "@angular/material/form-field";
import { TitleCasePipe } from "@angular/common";
import { MatTab, MatTabGroup, MatTabLabel } from "@angular/material/tabs";
import { EventConditionDetailsComponent } from "./event-condition-details/event-condition-details.component";

@Component({
  selector: "app-event-conditions-tab",
  imports: [
    MatIcon,
    MatIconButton,
    ClearableInputComponent,
    MatDivider,
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    TitleCasePipe,
    MatTabGroup,
    MatTab,
    MatTabLabel,
    EventConditionDetailsComponent
  ],
  templateUrl: "./event-conditions-tab.component.html",
  styleUrl: "./event-conditions-tab.component.scss"
})
export class EventConditionsTabComponent {
  protected readonly eventService = inject(EventService);
  conditions = input.required<Record<string, any>>();
  isEditMode = input.required<boolean>();
  newConditions = output<Record<string, any>>();

  selectedConditions = linkedSignal(() => deepCopy(this.conditions()));
  clickedCondition = linkedSignal(() => Object.keys(this.selectedConditions())[0] || "");
  searchTerm = signal("");

  isBooleanCondition(conditionName: string) {
    const conditionDefinition = this.eventService.moduleConditions()[conditionName];
    return conditionDefinition?.type === "bool";
  }

  removeCondition(conditionName: string) {
    delete this.selectedConditions()[conditionName];
    this.selectedConditions.set({ ...this.selectedConditions() }); // Trigger change detection
    this.newConditions.emit(this.selectedConditions());
  }

  availableGroups = computed(() => Object.keys(this.eventService.moduleConditionsByGroup()));

  remainingConditionsByGroup = linkedSignal({
    source: () => ({
      available: this.eventService.moduleConditionsByGroup(),
      selected: this.selectedConditions(),
      search: this.searchTerm()
    }),
    computation: ({ available, selected, search }) => {
      if (search === "" && Object.keys(selected).length === 0) {
        return available;
      }
      let remaining = deepCopy(available);
      for (const [groupName, condition] of Object.entries(remaining)) {
        for (const conditionName of Object.keys(condition)) {
          if (conditionName in selected || !conditionName.toLowerCase().includes(search.toLowerCase())) {
            delete remaining[groupName][conditionName];
          }
        }
      }
      return remaining;
    }
  });

  onConditionSubmitted(value: any) {
    const name = this.clickedCondition();
    if (name) {
      // Add or update the selected condition
      this.selectedConditions.update((dict) => ({
        ...dict,
        [name]: value
      }));
      this.newConditions.emit(this.selectedConditions());
    }
  }

  protected readonly Object = Object;
}
