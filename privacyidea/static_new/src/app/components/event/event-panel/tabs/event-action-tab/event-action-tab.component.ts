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

import { Component, computed, inject, input, linkedSignal, output, signal, WritableSignal } from "@angular/core";
import { ActionOptions, EventService } from "../../../../../services/event/event.service";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatOption, MatSelect } from "@angular/material/select";
import { FormsModule } from "@angular/forms";
import { MatInput } from "@angular/material/input";
import { MatCheckbox } from "@angular/material/checkbox";

@Component({
  selector: "app-event-action-tab",
  standalone: true,
  imports: [
    MatFormField,
    MatHint,
    MatLabel,
    MatOption,
    MatSelect,
    FormsModule,
    MatInput,
    MatCheckbox
  ],
  templateUrl: "./event-action-tab.component.html",
  styleUrl: "./event-action-tab.component.scss"
})
export class EventActionTabComponent {
  protected readonly eventService = inject(EventService);
  action = input.required<string>();
  options = input.required<Record<string, any>>();
  isEditMode = input.required<boolean>();
  newAction = output<string>();
  newOptions = output<ActionOptions>();
  protected readonly Object = Object;

  selectedAction: WritableSignal<string> = signal("");
  selectedOptions: WritableSignal<Record<string, any>> = linkedSignal(() => this.options());

  ngOnInit() {
    if (!this.selectedAction()) {
      this.selectedAction.set(this.action());
    }
  }

  onActionSelectionChange() {
    this.newAction.emit(this.selectedAction());
    this.selectedOptions.set({});
    this.newOptions.emit(this.selectedOptions());
  }

  onOptionChange(optionName: string, value: any) {
    this.selectedOptions.set({
      ...this.selectedOptions(),
      [optionName]: value
    });
    this.newOptions.emit(this.selectedOptions());
  }

  actionOptions = computed(() => {
    if (!this.selectedAction()) {
      return {};
    }
    return this.eventService.moduleActions()[this.selectedAction()] || {};
  });

  checkOptionVisibility(optionName: string): boolean {
    // checks if the visible conditions of an option are met
    const optionDetails = this.actionOptions()[optionName];
    if (!optionDetails || !optionDetails.visibleIf) {
      // no visible condition set
      return true;
    }
    if (optionDetails.visibleValue === undefined) {
      // related option is set, but no specific value is required
      return true;
    }
    // check if the related option matches the required value
    const dependentOptionValue = this.selectedOptions()[optionDetails.visibleIf];
    return dependentOptionValue === optionDetails.visibleValue;
  }
}
