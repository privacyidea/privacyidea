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

@Component({
  selector: "app-action-selector",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    SelectorButtonsComponent,
    MatTooltipModule,
    PolicyActionItemComponent
  ],
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

  readonly actionsNamesFiltered = computed(() => {
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

  actionDescription(actionName: string): string {
    return this.getActionDetail(actionName)?.desc ?? "";
  }

  selectActionByName(actionName: string) {
    const group = this.selectedActionGroup();
    const scope = this.policyScope();
    if (!group || !scope) return;
    const actionNames = this.policyService.actionNamesOfGroup(scope, group);
    if (actionNames.includes(actionName)) {
      const actionDetail = this.getActionDetail(actionName);
      const defaultValue =
        this.getActionDetail(actionName)?.type === "bool" ? "true" : (actionDetail?.value?.[0] ?? "");
      this.selectedPolicyActionChange.emit({ name: actionName, value: defaultValue });
    }
  }

  actionItems = viewChildren(PolicyActionItemComponent);

  addPolicyAction(event: any) {
    const currentIndex = this.actionsNamesFiltered().indexOf(event.name);

    this.actionAdd.emit(event);

    setTimeout(() => {
      const items = this.actionItems();
      const nextItem = items[currentIndex] || items[currentIndex - 1];
      if (nextItem) {
        nextItem.focusFirstInput();
      }
    });
  }
  getActionDetail(actionName: string): PolicyActionDetail | null {
    const actions = this.policyService.policyActions();
    const scope = this.policyScope();
    if (!scope) return null;
    if (actionName && actions && actions[scope]) {
      return actions[scope][actionName] ?? null;
    }
    return null;
  }
}
