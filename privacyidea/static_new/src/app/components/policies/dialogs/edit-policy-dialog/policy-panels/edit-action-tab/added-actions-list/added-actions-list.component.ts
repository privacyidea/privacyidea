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

import { CommonModule } from "@angular/common";
import { Component, input, output, inject } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { PolicyService, PolicyActionDetail } from "../../../../../../../services/policies/policies.service";
import { parseBooleanValue } from "../../../../../../../utils/parse-boolean-value";
import { PolicyActionItemEditComponent } from "./added-action-edit/policy-action-item-edit.component";

@Component({
  selector: "app-added-actions-list",
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatSlideToggleModule,
    MatExpansionModule,
    PolicyActionItemEditComponent
  ],
  templateUrl: "./added-actions-list.component.html",
  styleUrl: "./added-actions-list.component.scss"
})
export class AddedActionsListComponent {
  readonly actions = input.required<{ name: string; value: any }[]>();
  readonly actionsChange = output<{ name: string; value: any }[]>();
  readonly actionRemove = output<string>();
  readonly isEditMode = input.required<boolean>();

  private policyService = inject(PolicyService);

  parseBooleanValue = parseBooleanValue;

  isBooleanAction(actionName: string): boolean {
    return this.policyService.getDetailsOfAction(actionName)?.type === "bool";
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

  updateActionInSelectedPolicy(actionName: string, newValue: string | number) {
    const updatedActions = this.actions().map((action) =>
      action.name === actionName ? { name: action.name, value: newValue } : action
    );
    this.actionsChange.emit(updatedActions);
  }
}
