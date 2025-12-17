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

import { Component, computed, inject, input, output, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import {
  PolicyServiceInterface as PolicyServiceInterface,
  PolicyService as PolicyService,
  PolicyActionDetail,
  PolicyDetail
} from "../../../../../services/policies/policies.service";
import { SelectorButtons } from "../selector-buttons/selector-buttons.component";

import { MatTooltipModule } from "@angular/material/tooltip";

@Component({
  selector: "app-action-selector",
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, SelectorButtons, MatTooltipModule],
  templateUrl: "./action-selector.component.html",
  styleUrls: ["./action-selector.component.scss"]
})
export class ActionSelectorComponent {
  actionFilter = signal<string>("");

  policy = input.required<PolicyDetail>();
  policyChange = output<PolicyDetail>();

  policyScope = computed(() => {
    const policy = this.policy();
    if (!policy) return "";
    return policy.scope;
  });
  // selectedPolicyAction = input.required<{ name: string; value: any } | null>();
  selectedPolicyAction = input.required<{ name: string; value: any } | null>();
  selectedPolicyActionChange = output<{ name: string; value: any }>();
  onSelectedActionChange(policyAction: { name: string; value: any }) {
    this.selectedPolicyActionChange.emit(policyAction);
  }
  // selectedPolicyActionChange = output<{ name: string; value: any }>();
  // selectedActionDetail = input.required<PolicyActionDetail | null>();
  // selectedActionDetailChange = output<PolicyActionDetail>();

  selectedActionGroup = signal<string>("");

  addedActionNames = computed(() => {
    const policy = this.policy();
    if (!policy || !policy.action) return [];
    return Object.keys(policy.action);
  });
  // Services
  policyService: PolicyServiceInterface = inject(PolicyService);

  actionGroupsFiltered = computed(() => {
    return this.policyService.filterPolicyActionGroups(this.addedActionNames(), this.actionFilter().toLowerCase());
  });

  actionGroupNamesFiltered = computed(() => {
    const actionGroups = this.actionGroupsFiltered()[this.policyScope()];
    if (!actionGroups) return [];
    return Object.keys(actionGroups);
  });

  actionNamesFiltered = computed(() => {
    const group = this.selectedActionGroup();
    if (!group) return [];
    let actionNames = this.policyService.actionNamesOfGroup(group);
    const filter = this.actionFilter().toLowerCase();
    return actionNames.filter((actionName) => actionName.toLowerCase().includes(filter));
  });

  selectActionByName(actionName: string) {
    const actionNames = this.policyService.actionNamesOfGroup(this.selectedActionGroup());
    console.log("Selecting action by name:", actionName);
    if (actionNames.includes(actionName)) {
      console.log("Action found, emitting selection: ", actionName);
      this.onSelectedActionChange({ name: actionName, value: "" });
    }
  }

  addPolicyAction({ name, value }: { name: string; value: any }) {
    const editedPolicy = { ...this.policy() };
    if (!editedPolicy.action) {
      editedPolicy.action = {};
    }
    editedPolicy.action[name] = value;
    this.policyChange.emit(editedPolicy);
  }

  _getActionDetail = (actionName: string): PolicyActionDetail | null => {
    const actions = this.policyService.policyActions();
    const scope = this.policyScope();
    if (!scope) return null;
    if (actionName && actions && actions[scope]) {
      return actions[scope][actionName] ?? null;
    }
    return null;
  };
}
