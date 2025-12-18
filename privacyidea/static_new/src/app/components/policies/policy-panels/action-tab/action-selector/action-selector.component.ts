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

import { Component, computed, inject, input, linkedSignal, output, signal, WritableSignal } from "@angular/core";
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
  // Services
  policyService: PolicyServiceInterface = inject(PolicyService);

  // Bindings Inputs/Outputs
  readonly policy = input.required<PolicyDetail>();
  readonly selectedPolicyAction = input.required<{ name: string; value: any } | null>();
  readonly selectedPolicyActionChange = output<{ name: string; value: any }>();
  readonly actionAdd = output<{ name: string; value: any }>();

  // Local State
  readonly selectedActionGroup: WritableSignal<string> = linkedSignal({
    source: () => ({
      action: this.selectedPolicyAction(),
      scope: this.policy().scope,
      policyService: this.policyService,
      groupNames: this.actionGroupNamesFiltered()
    }),
    computation: (source, previous) => {
      const { action, scope, policyService, groupNames } = source;
      if (action) {
        const group = policyService.getGroupOfAction(action.name, scope);
        if (group) return group;
      }
      const previousGroup = previous?.value;
      if (previousGroup && groupNames.includes(previousGroup)) return previousGroup;
      return groupNames.length > 0 ? groupNames[0] : "";
    }
  });
  readonly actionFilter = signal<string>("");

  // Computed Signals
  readonly addedActionNames = computed(() => {
    const policy = this.policy();
    console.log("Computing addedActionNames for policy:", policy);
    if (!policy || !policy.action) return [];
    return Object.keys(policy.action);
  });
  readonly policyScope = computed(() => {
    const policy = this.policy();
    if (!policy) return "";
    return policy.scope;
  });

  readonly actionGroupsFiltered = computed(() => {
    console.log("Computing actionGroupsFiltered for policy:", this.policy());
    return this.policyService.filteredPolicyActionGroups(this.addedActionNames(), this.actionFilter().toLowerCase());
  });

  readonly actionGroupNamesFiltered = computed(() => {
    const actionGroups = this.actionGroupsFiltered()[this.policyScope()];
    if (!actionGroups) return [];
    return Object.keys(actionGroups);
  });

  readonly actionNamesFiltered = computed(() => {
    const group = this.selectedActionGroup();
    const scope = this.policyScope();
    if (!group && !scope) return [];
    let actionNames = this.policyService.actionNamesOfGroup(scope, group);
    const filter = this.actionFilter().toLowerCase();
    const addedActionNames = this.addedActionNames();
    return actionNames
      .filter((actionName) => !addedActionNames.includes(actionName))
      .filter((actionName) => actionName.toLowerCase().includes(filter));
  });

  selectActionByName(actionName: string) {
    const group = this.selectedActionGroup();
    const scope = this.policyScope();
    if (!group || !scope) return;
    const actionNames = this.policyService.actionNamesOfGroup(scope, group);
    if (actionNames.includes(actionName)) {
      const actionDetail = this._getActionDetail(actionName);
      const defaultValue =
        this._getActionDetail(actionName)?.type === "bool" ? "true" : (actionDetail?.value?.[0] ?? "");
      this.selectedPolicyActionChange.emit({ name: actionName, value: defaultValue });
    }
  }

  addPolicyAction(name: string, value: any) {
    this.actionAdd.emit({ name, value });
  }

  private _getActionDetail(actionName: string): PolicyActionDetail | null {
    const actions = this.policyService.policyActions();
    const scope = this.policyScope();
    if (!scope) return null;
    if (actionName && actions && actions[scope]) {
      return actions[scope][actionName] ?? null;
    }
    return null;
  }
}
