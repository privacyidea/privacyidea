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
import { form, FormField } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { EventConditionListComponent } from "@components/event/event-edit-page/tabs/event-conditions-tab/event-condition-list/event-condition-list.component";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { ToggleGroupComponent } from "@components/shared/toggle-group/toggle-group.component";
import { EventService } from "@services/event/event.service";

@Component({
  selector: "app-event-conditions-tab",
  imports: [
    ClearableInputComponent,
    FormField,
    EventConditionListComponent,
    MatExpansionModule,
    MatButtonModule,
    ToggleGroupComponent
  ],
  templateUrl: "./event-conditions-tab.component.html",
  styleUrl: "./event-conditions-tab.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EventConditionsTabComponent {
  protected readonly eventService = inject(EventService);
  protected readonly Object = Object;
  conditions = input.required<Record<string, string>>();
  newConditions = output<Record<string, string>>();
  selectedConditions = linkedSignal(() => this.conditions());
  conditionsToBeAdded = signal<Record<string, string>>({});
  addToolTip = $localize`:@@common.addCondition:Add Condition`;
  removeToolTip = $localize`:@@event.removeCondition:Remove Condition`;

  addedCondition = signal("");
  searchModel = signal({ search: "" });
  searchForm = form(this.searchModel);
  searchTerm = computed(() => this.searchModel().search);

  availableGroups = computed(() => Object.keys(this.eventService.moduleConditionsByGroup()));
  remainingConditionsByGroup = linkedSignal({
    source: () => ({
      available: this.eventService.moduleConditionsByGroup(),
      selected: this.selectedConditions(),
      search: this.searchTerm(),
      toBeAdded: this.conditionsToBeAdded()
    }),
    computation: ({ available, selected, search, toBeAdded }) => {
      // TODO: Can we simplify this logic?
      // let remaining = deepCopy(available);
      const remaining: Record<string, Record<string, string>> = {};
      for (const [groupName, condition] of Object.entries(available)) {
        remaining[groupName] = {};
        for (const conditionName of Object.keys(condition)) {
          if (conditionName in selected || !conditionName.toLowerCase().includes(search.toLowerCase())) {
            // delete remaining[groupName][conditionName];
          } else {
            remaining[groupName][conditionName] = toBeAdded[conditionName] || "";
          }
        }
      }
      return remaining;
    }
  });
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

  onConditionValueToBeAddedChange(conditionName: string, value: string | string[]) {
    const normalizedValue = Array.isArray(value) ? value.join(",") : value;
    this.conditionsToBeAdded.update((current) => ({ ...current, [conditionName]: normalizedValue }));
  }

  onConditionValueChange(conditionName: string, value: string | string[]) {
    const normalizedValue = Array.isArray(value) ? value.join(",") : value;
    this.selectedConditions.set({
      ...this.selectedConditions(),
      [conditionName]: normalizedValue
    });
    this.newConditions.emit(this.selectedConditions());
    if (normalizedValue === "") {
      // notify selected condition list to focus the new empty input
      this.addedCondition.set(conditionName);
    }
  }

  removeCondition(conditionName: string) {
    this.selectedConditions.set(
      Object.fromEntries(Object.entries(this.selectedConditions()).filter(([name]) => name !== conditionName))
    );
    this.newConditions.emit(this.selectedConditions());
  }

  clearSearch(): void {
    this.searchModel.set({ search: "" });
  }
}
