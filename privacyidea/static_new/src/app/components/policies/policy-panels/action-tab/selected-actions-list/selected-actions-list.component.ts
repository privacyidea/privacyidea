/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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

import { Component, computed, inject, input, Signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { parseBooleanValue } from "../../../../../utils/parse-boolean-value";

@Component({
  selector: "app-selected-actions-list",
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatSlideToggleModule],
  templateUrl: "./selected-actions-list.component.html",
  styleUrl: "./selected-actions-list.component.scss"
})
export class SelectedActionsListComponent {
  // Inputs
  actions = input.required<{ name: string; value: string }[]>();

  // Services
  policyService = inject(PolicyService);

  // Component State
  isEditMode = this.policyService.isEditMode;

  // Helper functions
  parseBooleanValue = parseBooleanValue;

  // Type Checking Methods
  isBooleanAction(actionName: string): boolean {
    return this.policyService.getDetailsOfAction(actionName)?.type === "bool";
  }

  // Event Handlers
  onActionClick(action: { name: string; value: string }) {
    this.policyService.selectedAction.set(action);
  }

  onToggleChange(actionName: string, newValue: boolean): void {
    this.policyService.updateActionValue(actionName, newValue);
  }
}
