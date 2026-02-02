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
  viewChildren
} from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { MatTooltipModule } from "@angular/material/tooltip";
import {
  PolicyServiceInterface,
  PolicyService,
  PolicyDetail,
  PolicyActionDetail
} from "../../../../../../services/policies/policies.service";
import { SelectorButtonsComponent } from "../selector-buttons/selector-buttons.component";
import { PolicyActionItemComponent } from "./policy-action-item/policy-action-item-new.component";
import { ClearableInputComponent } from "../../../../../shared/clearable-input/clearable-input.component";

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
  // Services
  readonly policyService: PolicyServiceInterface = inject(PolicyService);

  // Bindings Inputs/Outputs
  readonly policy = input.required<PolicyDetail>();
  readonly policyScopeChange = output<string>();
  readonly selectedPolicyAction = input.required<{ name: string; value: any } | null>();
  readonly selectedPolicyActionChange = output<{ name: string; value: any }>();
  readonly actionAdd = output<{ name: string; value: any }>();

  readonly allPolicyScopes = this.policyService.allPolicyScopes();
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

  readonly policyHasNoActions = computed(() => {
    let numOfActions = 0;
    const policy = this.policy();
    if (policy && policy.action) {
      console.log("policy.action", policy.action);
      numOfActions = Object.keys(policy.action).length;
    }
    console.log("numOfActions", numOfActions);
    return numOfActions === 0;
  });

  // Computed Signals
  readonly addedActionNames = computed(() => {
    const policy = this.policy();
    if (!policy || !policy.action) return [];
    return Object.keys(policy.action);
  });
  readonly policyScope = computed(() => {
    const policy = this.policy();
    if (!policy) return "";
    return policy.scope;
  });

  readonly actionGroupsFiltered = computed(() => {
    return this.policyService.filteredPolicyActionGroups(this.addedActionNames(), this.actionFilter().toLowerCase());
  });

  readonly actionGroupNamesFiltered = computed(() => {
    const actionGroups = this.actionGroupsFiltered()[this.policyScope()];
    if (!actionGroups) return [];
    return Object.keys(actionGroups);
  });

  // { key(policyName): PolicyActionDetail }
  readonly actionsFiltered = computed<Record<string, PolicyActionDetail>>(() => {
    console.log("Computing actionsFiltered");

    const group = this.selectedActionGroup();
    console.log("Selected action group:", group);
    const scope = this.policyScope();
    console.log("Selected scope:", scope);
    const actions = this.policyService.getActionsOf(scope, group);
    console.log("Actions of selected scope and group:", actions);
    const filterText = this.actionFilter().toLowerCase().trim();
    console.log("Filter text:", filterText);
    const filteredActions: Record<string, PolicyActionDetail> = {};
    for (const actionName in actions) {
      if (!this.addedActionNames().includes(actionName) && actionName.toLowerCase().includes(filterText)) {
        filteredActions[actionName] = actions[actionName];
      }
    }
    return filteredActions;
  });

  readonly selectedScope = computed(() => {
    const policy = this.policy();
    if (!policy) return "";
    return policy.scope;
  });

  readonly everySingleAction = computed<{ name: string; value: PolicyActionDetail }[]>(() => {
    const policyActions = this.policyService.policyActions();
    const allActionsList: { name: string; value: PolicyActionDetail }[] = [];
    for (const scope in policyActions) {
      for (const actionName in policyActions[scope]) {
        const action = policyActions[scope][actionName];
        allActionsList.push({ name: actionName, value: action });
      }
    }
    return allActionsList;
  });

  // actionDescription(actionName: string): string {
  //   return this.getActionDetail(actionName)?.desc ?? "";
  // }

  // selectActionByName(actionName: string) {
  //   const group = this.selectedActionGroup();
  //   const scope = this.policyScope();
  //   if (!group || !scope) return;
  //   const actionNames = this.policyService.getActionNamesOf(scope, group);
  //   if (actionNames.includes(actionName)) {
  //     const actionDetail = this.getActionDetail(actionName);
  //     const defaultValue =
  //       this.getActionDetail(actionName)?.type === "bool" ? "true" : (actionDetail?.value?.[0] ?? "");
  //     this.selectedPolicyActionChange.emit({ name: actionName, value: defaultValue });
  //   }
  // }

  actionItems = viewChildren(PolicyActionItemComponent);

  addPolicyAction(event: { name: string; value: any }) {
    if (!this.policy().scope) {
      const scope = this.policyService.getScopeOfAction(event.name);
      if (scope) {
        this.policyScopeChange.emit(scope);
      }
    }
    this.actionAdd.emit(event);
    this.focusNextActionItem(event.name);
  }

  focusNextActionItem(currentActionName: string) {
    const currentIndex = this.actionsFiltered() ? Object.keys(this.actionsFiltered()).indexOf(currentActionName) : -1;
    setTimeout(() => {
      const items = this.actionItems();
      const nextItem = items[currentIndex] || items[currentIndex - 1];
      if (nextItem) {
        nextItem.focusFirstInput();
      }
    });
  }

  selectActionScope($event: string) {
    this.selectedActionGroup.set("");
    this.policyScopeChange.emit($event);
  }
  // getActionDetail(actionName: string): PolicyActionDetail | null {
  //   const actions = this.policyService.policyActions();
  //   const scope = this.policyScope();
  //   if (!scope) return null;
  //   if (actionName && actions && actions[scope]) {
  //     return actions[scope][actionName] ?? null;
  //   }
  //   return null;
  // }
}
