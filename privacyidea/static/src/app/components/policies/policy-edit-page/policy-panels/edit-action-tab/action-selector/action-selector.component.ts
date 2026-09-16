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
import { Component, computed, inject, input, linkedSignal, model, output, viewChildren } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import {
  policyActionMatchesFilter,
  PolicyDetail,
  PolicyService,
  PolicyServiceInterface
} from "@services/policies/policies.service";
import { PolicyActionItemComponent, SelectableAction } from "./policy-action-item/policy-action-item-new.component";

@Component({
  selector: "app-action-selector",
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatExpansionModule, PolicyActionItemComponent],
  templateUrl: "./action-selector.component.html",
  styleUrls: ["./action-selector.component.scss"]
})
export class ActionSelectorComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);

  readonly policy = input.required<PolicyDetail>();
  readonly actionAdd = output<{ action: { name: string; value: string | boolean }; newScope?: string | null }>();

  readonly actionFilter = model<string>("");

  /**
   * Which group panels are open. A search opens every group that still has a match, so the hits are
   * visible without hunting; clearing the search collapses them again. In between the user is free
   * to open and close whichever they like.
   */
  readonly openGroups = linkedSignal<string, Set<string>>({
    source: () => this.actionFilter().trim(),
    computation: (filter) => (filter ? new Set(this.actionGroups().map((group) => group.name)) : new Set<string>())
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

  /**
   * The groups of the selected scope, each with the actions that are still addable. Groups that the
   * search leaves empty are dropped by the service, so the list is only ever the groups worth opening.
   */
  readonly actionGroups = computed<{ name: string; actions: SelectableAction[] }[]>(() => {
    const scope = this.policyScope();
    if (!scope) return [];
    const groups = this.actionGroupsFiltered()[scope] ?? {};
    return Object.keys(groups).map((name) => ({
      name,
      actions: Object.keys(groups[name]).map((actionName) => ({
        label: actionName,
        actionName,
        scope,
        detail: groups[name][actionName]
      }))
    }));
  });

  /** Without a scope there are no groups to speak of, so every scope's actions are listed flat. */
  readonly allScopeActions = computed<SelectableAction[]>(() => {
    if (this.policyScope()) return [];
    const filterText = this.actionFilter().toLowerCase().trim();
    const result: SelectableAction[] = [];
    const policyActions = this.policyService.policyActions();
    for (const scopeName in policyActions) {
      const actions = policyActions[scopeName];
      for (const actionName in actions) {
        if (
          !this.addedActionNames().includes(actionName) &&
          policyActionMatchesFilter(actionName, actions[actionName], filterText)
        ) {
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

  readonly hasActionsToAdd = computed(() =>
    this.policyScope() ? this.actionGroups().length > 0 : this.allScopeActions().length > 0
  );

  /**
   * The actions that are on screen, in the order they are rendered: a collapsed group renders none.
   * Keeping this in step with the rendered items is what lets focus move to the next one.
   */
  readonly renderedActions = computed<SelectableAction[]>(() => {
    if (!this.policyScope()) return this.allScopeActions();
    const open = this.openGroups();
    return this.actionGroups()
      .filter((group) => open.has(group.name))
      .flatMap((group) => group.actions);
  });

  actionItems = viewChildren(PolicyActionItemComponent);

  setGroupOpen(group: string, open: boolean): void {
    const next = new Set(this.openGroups());
    if (open) next.add(group);
    else next.delete(group);
    this.openGroups.set(next);
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
    const currentIndex = this.renderedActions().findIndex(
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
}
