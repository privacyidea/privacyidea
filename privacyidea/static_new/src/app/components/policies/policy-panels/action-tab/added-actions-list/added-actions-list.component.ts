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

import { Component, computed, inject, input, output } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { PolicyActionDetail, PolicyService } from "../../../../../services/policies/policies.service";
import { parseBooleanValue } from "../../../../../utils/parse-boolean-value";
import { MatExpansionModule } from "@angular/material/expansion";
import { AddedActionEditComponent } from "./added-action-edit/added-action-edit.component";

@Component({
  selector: "app-added-actions-list",
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatSlideToggleModule,
    MatExpansionModule,
    AddedActionEditComponent
  ],
  templateUrl: "./added-actions-list.component.html",
  styleUrl: "./added-actions-list.component.scss"
})
export class AddedActionsListComponent {
  // Inputs
  actions = input.required<{ name: string; value: any }[]>();
  actionsFirstHalf = computed(() => this.actions().filter((_, index) => index % 2 === 0));
  actionsSecondHalf = computed(() => this.actions().filter((_, index) => index % 2 !== 0));
  actionsChange = output<{ name: string; value: any }[]>();
  actionRemove = output<string>();
  isEditMode = input.required<boolean>();
  selectedAction = input.required<{ name: string; value: any } | null>();
  selectedActionChange = output<{ name: string; value: any } | null>();

  // Services
  private policyService = inject(PolicyService);

  // Helper functions
  parseBooleanValue = parseBooleanValue;

  // Type Checking Methods
  isBooleanAction(actionName: string): boolean {
    return this.policyService.getDetailsOfAction(actionName)?.type === "bool";
  }

  // Event Handlers
  onActionClick(action: { name: string; value: any }) {
    if (this.selectedAction()?.name === action.name) {
      this.selectedActionChange.emit(null);
    } else {
      this.selectedActionChange.emit(action);
    }
  }

  onToggleChange(actionName: string, newValue: boolean): void {
    this.actionsChange.emit(
      this.actions().map((action) => (action.name === actionName ? { name: action.name, value: newValue } : action))
    );
  }

  removeActionFromSelectedPolicy(actionName: string) {
    const updatedActions = this.actions().filter((action) => action.name !== actionName);
    this.actionsChange.emit(updatedActions);
  }

  getDetailsOfAction(actionName: string): PolicyActionDetail | null {
    return this.policyService.getDetailsOfAction(actionName);
  }
  uodateActionInSelectedPolicy(actionName: string, newValue: string | number) {
    console.log("Updating action", actionName, "with value", newValue);
    const updatedActions = this.actions().map((action) =>
      action.name === actionName ? { name: action.name, value: newValue } : action
    );
    this.actionsChange.emit(updatedActions);
  }
}
