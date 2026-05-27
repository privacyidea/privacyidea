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
  signal,
  WritableSignal
} from "@angular/core";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { EventConditionListComponent } from "@components/event/event-edit-page/tabs/event-conditions-tab/event-condition-list/event-condition-list.component";
import { SelectorButtonsComponent } from "@components/policies/policy-edit-page/policy-panels/edit-action-tab/selector-buttons/selector-buttons.component";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { EventService } from "@services/event/event.service";

@Component({
  selector: "app-event-conditions-tab",
  imports: [
    ClearableInputComponent,
    ReactiveFormsModule,
    FormsModule,
    EventConditionListComponent,
    MatExpansionModule,
    MatButtonModule,
    SelectorButtonsComponent
  ],
  templateUrl: "./event-conditions-tab.component.html",
  styleUrl: "./event-conditions-tab.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EventConditionsTabComponent {
  protected readonly eventService = inject(EventService);
  conditions = input.required<Record<string, any>>();
  newConditions = output<Record<string, any>>();

  selectedConditions = linkedSignal(() => this.conditions());
  conditionsToBeAdded: Record<string, any> = {};
  protected readonly Object = Object;

  addToolTip = $localize`Add Condition`;
  removeToolTip = $localize`Remove Condition`;

  addedCondition = signal("");
  searchTerm = signal("");

  availableGroups = computed(() => Object.keys(this.eventService.moduleConditionsByGroup()));

  availableNonEmptyGroups = computed(() =>
    this.availableGroups().filter((g) => Object.keys(this.remainingConditionsByGroup()[g] || {}).length > 0)
  );

  selectedGroup: WritableSignal<string> = linkedSignal({
    source: () => this.availableNonEmptyGroups(),
    computation: (groups, previous) => {
      const prev = previous?.value;
      if (prev && groups.includes(prev)) return prev;
      return groups[0] ?? "";
    }
  });

  remainingConditionsInSelectedGroup = computed(() => this.remainingConditionsByGroup()[this.selectedGroup()] ?? {});

  remainingConditionsByGroup = linkedSignal({
    source: () => ({
      available: this.eventService.moduleConditionsByGroup(),
      selected: this.selectedConditions(),
      search: this.searchTerm()
    }),
    computation: ({ available, selected, search }) => {
      // TODO: Can we simplify this logic?
      // let remaining = deepCopy(available);
      const remaining: Record<string, any> = {};
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
