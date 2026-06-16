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
  computed,
  inject,
  input,
  linkedSignal,
  output,
  signal,
  viewChildren,
  WritableSignal
} from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { MatTooltipModule } from "@angular/material/tooltip";
import { SelectorButtonsComponent } from "@components/policies/policy-edit-page/policy-panels/edit-action-tab/selector-buttons/selector-buttons.component";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { PolicyDetail, PolicyService, PolicyServiceInterface } from "@services/policies/policies.service";
import { PolicyActionItemComponent, SelectableAction } from "./policy-action-item/policy-action-item-new.component";

@Component({
  selector: "app-action-selector",
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatExpansionModule,
    SelectorButtonsComponent,
    MatTooltipModule,
    PolicyActionItemComponent,
    ClearableInputComponent,
    MatButtonToggleModule
  ],
  templateUrl: "./action-selector.component.html",
  styleUrls: ["./action-selector.component.scss"]
})
export class ActionSelectorComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);

  readonly policy = input.required<PolicyDetail>();
  readonly actionAdd = output<{ action: { name: string; value: string | boolean }; newScope?: string | null }>();
  readonly scopeChange = output<string | undefined>();

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

  readonly actionsFiltered = computed<SelectableAction[]>(() => {
    const group = this.selectedActionGroup();
    const scope = this.policyScope();
    const filterText = this.actionFilter().toLowerCase().trim();
    const result: SelectableAction[] = [];

    if (scope) {
      const actions = this.policyService.getActionsOf(scope, group);
      for (const actionName in actions) {
        if (!this.addedActionNames().includes(actionName) && actionName.toLowerCase().includes(filterText)) {
          result.push({ label: actionName, actionName, scope: scope, detail: actions[actionName] });
        }
      }
      return result;
    }
    const policyActions = this.policyService.policyActions();
    for (const scopeName in policyActions) {
      const actions = policyActions[scopeName];
      for (const actionName in actions) {
        if (!this.addedActionNames().includes(actionName) && actionName.toLowerCase().includes(filterText)) {
          result.push({
            label: `[${scopeName}] ${actionName}`,
            actionName,
            scope: scopeName,
            detail: actions[actionName]
          });
        }
      }
    }
    return result;
  });

  actionItems = viewChildren(PolicyActionItemComponent);

  selectActionGroup(group?: string): void {
    this.selectedActionGroup.set(group ?? "");
  }

  addPolicyAction(action: { name: string; value: string | number | boolean | undefined }, itemScope?: string | null) {
    const normalizedAction: { name: string; value: string | boolean } = {
      name: action.name,
      value: typeof action.value === "number" ? String(action.value) : (action.value ?? "")
    };
    if (this.policy().scope) {
      this.actionAdd.emit({ action: normalizedAction });
    } else {
      const scope = itemScope || this.policyService.getScopeOfAction(action.name);
      this.actionAdd.emit({ action: normalizedAction, newScope: scope });
    }
    this.focusNextActionItem(action.name, itemScope);
  }

  focusNextActionItem(currentActionName: string, itemScope?: string | null) {
    const currentIndex = this.actionsFiltered().findIndex(
      (item) => item.actionName === currentActionName && item.scope === itemScope
    );
    setTimeout(() => {
      const items = this.actionItems();
      const nextItem = items[currentIndex] || items[currentIndex - 1];
      if (nextItem) {
        nextItem.focusFirstInput();
      }
    });
  }

  selectActionScope(scope?: string) {
    this.scopeChange.emit(scope);
  }
}
