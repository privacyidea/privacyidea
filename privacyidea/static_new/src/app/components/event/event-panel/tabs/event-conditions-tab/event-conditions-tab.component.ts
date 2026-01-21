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
  inject,
  input,
  linkedSignal,
  output,
  signal
} from "@angular/core";
import { EventService } from "../../../../../services/event/event.service";
import { ClearableInputComponent } from "../../../../shared/clearable-input/clearable-input.component";
import { MatInput, MatLabel } from "@angular/material/input";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatFormField } from "@angular/material/form-field";
import { TitleCasePipe } from "@angular/common";
import { MatTab, MatTabGroup, MatTabLabel } from "@angular/material/tabs";
import { EventConditionListComponent } from "./event-condition-list/event-condition-list.component";
import { MatCardModule } from "@angular/material/card";
import { MatIcon } from "@angular/material/icon";

@Component({
  selector: "app-event-conditions-tab",
  imports: [
    ClearableInputComponent,
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    TitleCasePipe,
    MatTabGroup,
    MatTab,
    MatTabLabel,
    EventConditionListComponent,
    MatCardModule,
    MatIcon
  ],
  templateUrl: "./event-conditions-tab.component.html",
  styleUrl: "./event-conditions-tab.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EventConditionsTabComponent {
  protected readonly eventService = inject(EventService);
  conditions = input.required<Record<string, any>>();
  isEditMode = input.required<boolean>();
  newConditions = output<Record<string, any>>();

  selectedConditions = linkedSignal(() => this.conditions());
  conditionsToBeAdded: Record<string, any> = {};
  selectedGroupIndex = 0;
  protected readonly Object = Object;

  addToolTip = $localize`Add Condition`;
  removeToolTip = $localize`Remove Condition`;

  addedCondition = signal("");
  searchTerm = signal("");

  availableGroups = computed(() => Object.keys(this.eventService.moduleConditionsByGroup()));

  remainingConditionsByGroup = linkedSignal({
    source: () => ({
      available: this.eventService.moduleConditionsByGroup(),
      selected: this.selectedConditions(),
      search: this.searchTerm()
    }),
    computation: ({ available, selected, search }) => {
      // TODO: Can we simplify this logic?
      // let remaining = deepCopy(available);
      let remaining: Record<string, any> = {};
      for (const [groupName, condition] of Object.entries(available)) {
        remaining[groupName] = {};
        for (const conditionName of Object.keys(condition)) {
          if (conditionName in selected || !conditionName.toLowerCase().includes(search.toLowerCase())) {
            // delete remaining[groupName][conditionName];
          } else {
            remaining[groupName][conditionName] = this.conditionsToBeAdded[conditionName] || "";
          }
        }
      }
      return remaining;
    }
  });

  onConditionValueToBeAddedChange(conditionName: string, value: any) {
    this.conditionsToBeAdded[conditionName] = value;
  }

  onConditionValueChange(conditionName: string, value: any) {
    this.selectedConditions.set({
      ...this.selectedConditions(),
      [conditionName]: value
    });
    this.newConditions.emit(this.selectedConditions());
    if (value === "") {
      // notify selected condition list to focus the new empty input
      this.addedCondition.set(conditionName);
    }
  }

  removeCondition(conditionName: string) {
    delete this.selectedConditions()[conditionName];
    this.selectedConditions.set({ ...this.selectedConditions() }); // Trigger change detection
    this.newConditions.emit(this.selectedConditions());
  }
}
