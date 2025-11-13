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
import { ActionDetailComponent } from "../action-tab/action-detail/action-detail.component";
import { SelectedActionsListComponent } from "../action-tab/selected-actions-list/selected-actions-list.component";
import { ActionSelectorComponent } from "../action-tab/action-selector/action-selector.component";
import { PolicyService } from "../../../../services/policies/policies.service";

@Component({
  selector: "app-action-tab",
  standalone: true,
  imports: [SelectedActionsListComponent, ActionSelectorComponent, ActionDetailComponent],
  templateUrl: "./action-tab.component.html",
  styleUrl: "./action-tab.component.scss"
})
export class ActionTabComponent {
  policyService = inject(PolicyService);

  isEditMode = this.policyService.isEditMode;

  actions: Signal<{ name: string; value: string }[]> = computed(() => {
    const policy = this.policyService.selectedPolicy();
    if (!policy || !policy.action) return [];
    return Object.entries(policy.action).map(([name, value]) => ({ name: name, value }));
  });
}
