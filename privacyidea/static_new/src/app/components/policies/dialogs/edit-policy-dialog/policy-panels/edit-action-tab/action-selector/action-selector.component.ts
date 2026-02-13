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
import {
  Component,
  inject,
  input,
  output,
  WritableSignal,
  linkedSignal,
  signal,
  computed,
  viewChildren,
  model
} from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { MatTooltipModule } from "@angular/material/tooltip";
import {
  PolicyServiceInterface,
  PolicyService,
  PolicyDetail,
  PolicyActionDetail
} from "../../../../../../../services/policies/policies.service";
import { SelectorButtonsComponent } from "../selector-buttons/selector-buttons.component";
import { PolicyActionItemComponent } from "./policy-action-item/policy-action-item-new.component";
import { ClearableInputComponent } from "../../../../../../shared/clearable-input/clearable-input.component";

@Component({
  selector: "app-action-selector",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    SelectorButtonsComponent,
    MatTooltipModule,
    PolicyActionItemComponent,
    ClearableInputComponent
  ],
  templateUrl: "./action-selector.component.html",
  styleUrls: ["./action-selector.component.scss"]
})
export class ActionSelectorComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);

  readonly policy = input.required<PolicyDetail>();
  readonly actionAdd = output<{ action: { name: string; value: any }; newScope?: string | null }>();
  readonly scopeChange = output<string | null>();

  readonly allPolicyScopes = this.policyService.allPolicyScopes();

  readonly selectedActionGroup: WritableSignal<string> = linkedSignal({
    source: () => this.actionGroupNamesFiltered(),
    computation: (groupNames, previous) => {
      const previousGroup = previous?.value;
      if (previousGroup && groupNames.includes(previousGroup)) return previousGroup;
      return groupNames.length > 0 ? groupNames[0] : "";
    }
  });

  readonly actionFilter = signal<string>("");

  readonly policyHasNoActions = computed(() => {
    const policy = this.policy();
    return !policy?.action || Object.keys(policy.action).length === 0;
  });

  readonly addedActionNames = computed(() => {
    const policy = this.policy();
    if (!policy || !policy.action) return [];
    return Object.keys(policy.action);
  });

  readonly policyScope = computed(() => this.policy()?.scope || "");

  readonly actionGroupsFiltered = computed(() => {
    return this.policyService.filteredPolicyActionGroups(this.addedActionNames(), this.actionFilter().toLowerCase());
  });

  readonly actionGroupNamesFiltered = computed(() => {
    const actionGroups = this.actionGroupsFiltered()[this.policyScope()];
    if (!actionGroups) return [];
    return Object.keys(actionGroups);
  });

  readonly actionsFiltered = computed<Record<string, PolicyActionDetail>>(() => {
    const group = this.selectedActionGroup();
    const scope = this.policyScope();
    const actions = this.policyService.getActionsOf(scope, group);
    const filterText = this.actionFilter().toLowerCase().trim();
    const filteredActions: Record<string, PolicyActionDetail> = {};

    for (const actionName in actions) {
      if (!this.addedActionNames().includes(actionName) && actionName.toLowerCase().includes(filterText)) {
        filteredActions[actionName] = actions[actionName];
      }
    }
    return filteredActions;
  });

  actionItems = viewChildren(PolicyActionItemComponent);

  selectActionGroup(group: string | null): void {
    this.selectedActionGroup.set(group ?? "");
  }

  addPolicyAction(action: { name: string; value: any }) {
    if (this.policy().scope) {
      this.actionAdd.emit({ action });
    } else {
      const scope = this.policy().scope || this.policyService.getScopeOfAction(action.name);
      this.actionAdd.emit({ action, newScope: scope });
    }
    this.focusNextActionItem(action.name);
  }

  focusNextActionItem(currentActionName: string) {
    const currentIndex = Object.keys(this.actionsFiltered()).indexOf(currentActionName);
    setTimeout(() => {
      const items = this.actionItems();
      const nextItem = items[currentIndex] || items[currentIndex - 1];
      if (nextItem) {
        nextItem.focusFirstInput();
      }
    });
  }

  selectActionScope(scope: string | null) {
    this.scopeChange.emit(scope);
  }
}
