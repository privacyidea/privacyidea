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

import { Component, computed, inject, input, linkedSignal, output } from "@angular/core";
import { EventService } from "../../../../../../services/event/event.service";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatButton } from "@angular/material/button";
import { MatFormField } from "@angular/material/form-field";
import { MatOption, MatSelect } from "@angular/material/select";

@Component({
  selector: "app-event-condition-details",
  imports: [
    MatButton,
    MatFormField,
    MatOption,
    MatSelect,
    ReactiveFormsModule,
    FormsModule
  ],
  templateUrl: "./event-condition-details.component.html",
  styleUrl: "./event-condition-details.component.scss"
})
export class EventConditionDetailsComponent {
  protected readonly eventService = inject(EventService);
  conditionName = input.required<string>();
  originalConditionValue = input<any>(null);
  isEditMode = input<boolean>(false);
  isNewCondition = input<boolean>(false);
  conditionSubmitted = output<any>();

  conditionValue = linkedSignal(() => {
    if (this.originalConditionValue()) {
      if (this.conditionDetails()?.type === "multi") {
        return (this.originalConditionValue() as string).split(",");
      }
      return this.originalConditionValue();
    }
    const details = this.conditionDetails();
    if (details && Array.isArray(details.value) && details.value.length > 0
    ) {
      return details.value[0];
    }
    return null;
  });
  conditionDetails = computed(() => this.eventService.moduleConditions()[this.conditionName()] || {});

  availableConditionValues = computed(() => {
    const values = this.conditionDetails().value || [];
    if (this.conditionDetails().type === "multi") {
      return values.map((valueMap) => valueMap.name);
    }
    return values;
  });

  submitCondition() {
    let valueToEmit = this.conditionValue();
    if (Array.isArray(valueToEmit)) {
      valueToEmit = valueToEmit.join(",");
    }
    this.conditionSubmitted.emit(valueToEmit);
  }

  inputIsValid(): boolean {
    if (this.conditionDetails().type === "bool") {
      return true;
    }
    return this.conditionValue() !== null && this.conditionValue() !== undefined && this.conditionValue() !== "";
  }
}
