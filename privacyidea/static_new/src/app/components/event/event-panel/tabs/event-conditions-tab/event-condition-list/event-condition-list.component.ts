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
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  input,
  linkedSignal,
  NgZone,
  output,
  QueryList,
  signal,
  ViewChildren
} from "@angular/core";
import { EventService } from "../../../../../../services/event/event.service";
import { MatInput } from "@angular/material/input";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatError, MatFormField } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatIconButton } from "@angular/material/button";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatTooltip } from "@angular/material/tooltip";

@Component({
  selector: "app-event-condition-list",
  imports: [
    MatFormField,
    MatIcon,
    MatIconButton,
    MatInput,
    MatOption,
    MatSelect,
    ReactiveFormsModule,
    MatIconButton,
    MatIcon,
    FormsModule,
    MatTooltip,
    MatError
  ],
  templateUrl: "./event-condition-list.component.html",
  styleUrl: "./event-condition-list.component.scss"
})
export class EventConditionListComponent {
  protected readonly eventService = inject(EventService);
  conditions = input.required<Record<string, any>>();
  action = input<string>();
  emitOnConditionValueChange = input<boolean>(false);
  inputRequired = input<boolean>(false);
  actionOnEnter = input<boolean>(false);
  inputName = input<string>("");
  focusConditionName = input<string | null>(null);
  toolTipText = input<string>("");
  newConditionValue = output<{ conditionName: string, conditionValue: any }>();
  actionButtonClicked = output<{ conditionName: string, conditionValue: any }>();

  selectedCondition = signal("");
  editConditions = linkedSignal(() => {
    return this.conditions();
  });
  showDescription: Record<string, boolean> = {};
  protected readonly Object = Object;

  @ViewChildren("selectedConditionInput") selectedConditionInput!: QueryList<ElementRef | MatSelect>;

  constructor(private ngZone: NgZone) {}

  protected focusEffect = effect(() => {
    const conditionName = this.focusConditionName();
    if (conditionName) {
      this.focusInputByConditionName(conditionName);
    }
  });

  private focusInputByConditionName(conditionName: string) {
    this.ngZone.runOutsideAngular(() => {
      setTimeout(() => {
        const inputs = this.selectedConditionInput.toArray();
        // Try to find the input by name attribute or index
        for (const input of inputs) {
          if (input instanceof ElementRef) {
            if (input.nativeElement && input.nativeElement.name === `conditionInput_${conditionName}`) {
              input.nativeElement.focus();
              break;
            }
          } else if (input instanceof MatSelect) {
            // For MatSelect, try to match by a custom property if needed
            // (Assume order matches for now)
            // Optionally, add logic to match by conditionName if possible
          }
        }
      });
    });
  }

  availableConditionValues = computed(() => {
    let valueMap: Record<string, any> = {};
    for (const [name, details] of Object.entries(this.eventService.moduleConditions())) {
      if (details.type == "multi") {
        valueMap[name] = details.value?.map((valueMap) => valueMap.name) || [];
      } else if (details.value) {
        valueMap[name] = details.value;
      }
    }
    return valueMap;
  });

  getMultiValues(value: string | string[]): string[] {
    if (typeof value === "string") {
      return value.split(",").map(value => value.trim()).filter(value => value.length > 0);
    } else if (Array.isArray(value)) {
      return value;
    }
    return [];
  }

  onConditionValueChange(conditionName: string, value: any) {
    this.editConditions()[conditionName] = value;
    if (this.emitOnConditionValueChange()) {
      this.newConditionValue.emit({ conditionName, conditionValue: value });
    }
  }

  onActionButtonClicked(conditionName: string) {
    const conditionValue = this.editConditions()[conditionName];
    this.actionButtonClicked.emit({ conditionName, conditionValue });
  }

  disableShowDescription(conditionName: string) {
    this.showDescription[conditionName] = false;
  }

  enableShowDescription(conditionName: string) {
    this.showDescription[conditionName] = true;
  }
}
