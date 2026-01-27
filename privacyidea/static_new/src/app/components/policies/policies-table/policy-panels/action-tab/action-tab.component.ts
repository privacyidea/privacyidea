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

import { Component, input, output, WritableSignal, linkedSignal, signal, computed, Signal } from "@angular/core";
import { PolicyDetail, PolicyActionDetail } from "../../../../../services/policies/policies.service";
import { ActionDetailComponent } from "./action-detail/action-detail.component";
import { ActionSelectorComponent } from "./action-selector/action-selector.component";
import { AddedActionsListComponent } from "./added-actions-list/added-actions-list.component";

@Component({
  selector: "app-action-tab",
  standalone: true,
  imports: [AddedActionsListComponent, ActionSelectorComponent, ActionDetailComponent],
  templateUrl: "./action-tab.component.html",
  styleUrl: "./action-tab.component.scss"
})
export class ActionTabComponent {
  isEditMode = input.required<boolean>();

  policy = input.required<PolicyDetail>();
  actionsUpdate = output<{
    [actionName: string]: string;
  }>();

  selectedAction: WritableSignal<{ name: string; value: any } | null> = linkedSignal({
    source: () => ({
      scope: this.policy().scope
    }),
    computation: () => null
  });
  selectedActionDetail = signal<PolicyActionDetail | null>(null);

  actionsFirstHalf = computed(() => this.actions().filter((_, index) => index % 2 === 0));
  actionsSecondHalf = computed(() => this.actions().filter((_, index) => index % 2 !== 0));

  onSelectedActionChange(action: { name: string; value: any }) {
    this.selectedAction.set(action);
  }

  actions: Signal<{ name: string; value: any }[]> = computed(() => {
    const policy = this.policy();
    if (!policy || !policy.action) return [];
    return Object.entries(policy.action).map(([name, value]) => ({ name: name, value }));
  });

  onActionsChange(updatedActions: { name: string; value: any }[]) {
    const newActions: { [key: string]: any } = {};
    updatedActions.forEach((action) => {
      newActions[action.name] = action.value;
    });
    this.actionsUpdate.emit(newActions);
  }
  onActionAdd(action: { name: string; value: any }) {
    const newActions = [...this.actions(), action];
    this.onActionsChange(newActions);
    if (this.selectedAction()?.name === action.name) {
      this.selectedAction.set(null);
    }
  }
  onActionUpdate(action: { name: string; value: any }) {
    const newActions = this.actions().map((a) => (a.name === action.name ? action : a));
    this.onActionsChange(newActions);
    if (this.selectedAction()?.name === action.name) {
      this.selectedAction.set(null);
    }
  }

  onActionRemove(actionName: string) {
    const newActions = this.actions().filter((action) => action.name !== actionName);
    this.onActionsChange(newActions);
    if (this.selectedAction()?.name === actionName) {
      this.selectedAction.set(null);
    }
  }
}
