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

import { Component, input, inject, signal, computed, linkedSignal, viewChild } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatTableModule } from "@angular/material/table";
import { MatSortModule, Sort } from "@angular/material/sort";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { AuthServiceInterface, AuthService } from "../../../services/auth/auth.service";
import { PolicyServiceInterface, PolicyService, PolicyDetail } from "../../../services/policies/policies.service";
import { lastValueFrom } from "rxjs";
import {
  SimpleConfirmationDialogData,
  SimpleConfirmationDialogComponent
} from "../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { CopyPolicyDialogComponent } from "../dialogs/copy-policy-dialog/copy-policy-dialog.component";
import { EditPolicyDialogComponent } from "../dialogs/edit-policy-dialog/edit-policy-dialog.component";
import { DialogService, DialogServiceInterface } from "../../../services/dialog/dialog.service";
import { MatInputModule } from "@angular/material/input";
import { MatPaginatorModule } from "@angular/material/paginator";
import { PoliciesTableActionsComponent } from "./policies-table-actions/policies-table-actions.component";
import { MatCheckboxChange, MatCheckboxModule } from "@angular/material/checkbox";
import { PoliciesViewActionColumnComponent as ViewActionColumnComponent } from "./view-action-column/view-action-column.component";
import { MatTooltipModule } from "@angular/material/tooltip";
import { FilterValueGeneric } from "../../../core/models/filter_value_generic/filter_value_generic";
import { FilterOption } from "../../shared/keyword-filter-generic/keyword-filter-generic.component";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { PolicyFilterComponent } from "../policy-filter/policy-filter.component";
import { ConditionsTabComponent } from "./view-conditions-column/view-conditions-column.component";

const columnKeysMap = [
  { key: "select", label: "" },
  { key: "priority", label: "Priority" },
  { key: "name", label: "Name" },
  { key: "scope", label: "Scope" },
  { key: "description", label: "Description" },
  { key: "actions", label: "Actions" },
  { key: "conditions", label: "Conditions" },
  { key: "active", label: "" }
];

@Component({
  selector: "app-policies-table",
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatSortModule,
    MatIconModule,
    MatButtonModule,
    MatSlideToggleModule,
    MatInputModule,
    MatPaginatorModule,
    PoliciesTableActionsComponent,
    MatCheckboxModule,
    ViewActionColumnComponent,
    MatTooltipModule,
    PolicyFilterComponent,
    ConditionsTabComponent
  ],
  templateUrl: "./policies-table.component.html",
  styleUrl: "./policies-table.component.scss"
})
export class PoliciesTableComponent {
  readonly displayedColumns: string[] = columnKeysMap.map((c) => c.key);
  readonly columnKeysMap = columnKeysMap;

  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);

  readonly filterComponent = viewChild.required<PolicyFilterComponent>("filterComponent");

  readonly sort = signal<Sort>({ active: "priority", direction: "asc" });

  readonly policiesListFiltered = linkedSignal<
    { filter: FilterValueGeneric<PolicyDetail>; allPolicies: PolicyDetail[] },
    PolicyDetail[]
  >({
    source: () => ({ filter: this.filter(), allPolicies: this.policyService.allPolicies() }),
    computation: (source) => source.filter.filterItems(source.allPolicies)
  });

  readonly sortedFilteredPolicies = computed(() => {
    const policies = this.policiesListFiltered();
    const sort = this.sort();
    console.log("Sorting policies by", sort);
    if (!sort.active || sort.direction === "") {
      return policies;
    }

    const sortedPolicies = [...policies].sort((a, b) => {
      const isAsc = sort.direction === "asc";
      switch (sort.active) {
        case "priority":
          return this.compare(a.priority, b.priority, isAsc);
        case "name":
          return this.compare(a.name, b.name, isAsc);
        case "scope":
          return this.compare(a.scope, b.scope, isAsc);
        case "description":
          console.log("Comparing descriptions", a.description, b.description);
          console.log("Result:", this.compare(a.description ?? "", b.description ?? "", isAsc));
          return this.compare(a.description ?? "", b.description ?? "", isAsc);
        case "active":
          return this.compare(a.active, b.active, isAsc);
        default:
          return 0;
      }
    });

    console.log("Unsorted policies:", policies);
    console.log("Sorted policies:", sortedPolicies);
    return sortedPolicies;
  });

  onSortChange(sort: Sort) {
    this.sort.set(sort);
  }

  private compare(a: number | string | boolean, b: number | string | boolean, isAsc: boolean) {
    return (a < b ? -1 : 1) * (isAsc ? 1 : -1);
  }

  readonly isFiltered = input.required<boolean>();
  readonly selectedPolicies = linkedSignal<PolicyDetail[], Set<string>>({
    source: () => this.policiesListFiltered(),

    computation: (source, previous) => {
      const selectedPolicies = previous?.value;
      if (!selectedPolicies) return new Set<string>();
      for (const selectedPolicy of selectedPolicies) {
        if (!source.some((policy) => policy.name === selectedPolicy)) {
          selectedPolicies.delete(selectedPolicy);
        }
      }
      return selectedPolicies;
    }
  });

  readonly filter = signal<FilterValueGeneric<PolicyDetail>>(
    new FilterValueGeneric({ availableFilters: policyFilterOptions })
  );

  async deletePolicy(policyName: string): Promise<void> {
    if (
      await this._confirm({
        title: "Confirm Deletion",
        confirmAction: {
          type: "destruct",
          label: "Delete",
          value: true
        },
        cancelAction: {
          type: "cancel",
          label: "Cancel",
          value: false
        },
        items: [policyName],
        itemType: "policy"
      })
    ) {
      this.policyService.deletePolicy(policyName);
    }
  }
  async editPolicy(policy: PolicyDetail) {
    const result = await lastValueFrom(
      this.dialogService
        .openDialog({
          component: EditPolicyDialogComponent,
          data: { mode: "edit", policyDetail: policy }
        })
        .afterClosed()
    );
    if (result) {
      this.policyService.updatePolicyOptimistic(result);
    }
  }

  async _confirm(data: SimpleConfirmationDialogData): Promise<boolean> {
    return (
      (await lastValueFrom(
        this.dialogService
          .openDialog({
            component: SimpleConfirmationDialogComponent,
            data: data
          })
          .afterClosed()
      )) === true
    );
  }
  isSelected(policyName: string): boolean {
    return this.selectedPolicies().has(policyName);
  }
  updateSelection($event: MatCheckboxChange, policyName: string) {
    const selected = this.selectedPolicies();
    if ($event.checked) {
      selected.add(policyName);
    } else {
      selected.delete(policyName);
    }
    this.selectedPolicies.set(new Set<string>(selected));
  }
  isAllSelected(): boolean {
    const filtered = this.policiesListFiltered();
    if (filtered.length === 0) return false;
    const selected = this.selectedPolicies();
    return selected.size === filtered.length && filtered.every((policy) => selected.has(policy.name));
  }
  masterToggle() {
    if (this.isAllSelected()) {
      this.selectedPolicies.set(new Set<string>());
    } else {
      const newSelected = new Set<string>();
      for (const policy of this.policiesListFiltered()) {
        newSelected.add(policy.name);
      }
      this.selectedPolicies.set(newSelected);
    }
  }

  onFilterClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    const filterComponent = this.filterComponent();
    if (filterComponent) {
      filterComponent.focusInput();
    }
  }

  toggleFilter(filterKeyword: string): void {
    const filterOption = policyFilterOptions.find((option) => option.key === filterKeyword);
    if (filterOption) {
      const newFilter = this.filter().toggleFilterKeyword(filterOption);
      this.filter.set(newFilter);
    }
  }

  getFilterTooltipText(filterKeyword: string): string {
    const filterOption = policyFilterOptions.find((option) => option.key === filterKeyword);
    if (filterOption) {
      return filterOption.hint ?? "";
    }
    return "";
  }

  getFilterIconName(keyword: string): string {
    const filterOption = policyFilterOptions.find((option) => option.key === keyword);
    if (filterOption && filterOption.getIconName) {
      return filterOption.getIconName(this.filter());
    }
    return "filter_alt";
  }

  isFilterable(columnKey: string): boolean {
    return !!policyFilterOptions.find((option) => option.key === columnKey);
  }

  expandedElement: PolicyDetail | null = null;
  policiesIsFiltered = computed(() => this.policiesListFiltered().length < this.policyService.allPolicies().length);

  onPolicyListFilteredChange(filteredPolicies: PolicyDetail[]): void {
    this.policiesListFiltered.set(filteredPolicies);
  }
}

const policyFilterOptions = [
  new FilterOption<PolicyDetail>({
    key: "priority",
    label: $localize`Priority`,
    hint: $localize`Filter by priority. Use operators like >, <, =, !=, >=, <= or range (e.g., 3-5). When no operator is specified, exact match is used.`,
    matches: (item: PolicyDetail, filter: FilterValueGeneric<PolicyDetail>) => {
      const value = filter.getValueOfKey("priority");
      if (!value) return true;
      const priority = item.priority;
      try {
        if (value.startsWith(">=")) {
          const num = parseInt(value.substring(2), 10);
          return priority >= num;
        } else if (value.startsWith("<=")) {
          const num = parseInt(value.substring(2), 10);
          return priority <= num;
        } else if (value.startsWith(">")) {
          const num = parseInt(value.substring(1), 10);
          return priority > num;
        } else if (value.startsWith("<")) {
          const num = parseInt(value.substring(1), 10);
          return priority < num;
        } else if (value.startsWith("!=")) {
          const num = parseInt(value.substring(2), 10);
          return priority !== num;
        } else if (value.startsWith("=")) {
          const num = parseInt(value.substring(1), 10);
          return priority === num;
        } else if (value.includes("-")) {
          const [minStr, maxStr] = value.split("-");
          const min = parseInt(minStr, 10);
          const max = parseInt(maxStr, 10);
          return priority >= min && priority <= max;
        } else {
          const num = parseInt(value, 10);
          return priority === num;
        }
      } catch {
        return false;
      }
    }
  }),
  new FilterOption({
    key: "active",
    label: $localize`Active`,
    hint: $localize`Filter by active status.`,
    toggle: (filter: FilterValueGeneric<PolicyDetail>) => {
      const value = filter.getValueOfKey("active")?.toLowerCase();
      if (value === "true") return filter.setValueOfKey("active", "false");
      if (value === "false") return filter.removeKey("active");
      return filter.setValueOfKey("active", "true");
    },
    iconName: (filter: FilterValueGeneric<PolicyDetail>) => {
      const value = filter.getValueOfKey("active")?.toLowerCase();
      if (value === "true") return "screen_rotation_alt ";
      if (value === "false") return "filter_alt_off";
      return "filter_alt";
    },
    matches: (item: PolicyDetail, filter: FilterValueGeneric<PolicyDetail>) => {
      const value = filter.getValueOfKey("active")?.toLowerCase();
      console.log("Filtering active with value:", value, "on item:", item.active);
      if (value === "true") return item.active === true;
      if (value === "false") return item.active === false;
      return true;
    }
  }),
  new FilterOption({
    key: "name",
    label: $localize`Policy Name`,
    hint: $localize`Filter by policy name.`,
    matches: (item: PolicyDetail, filter: FilterValueGeneric<PolicyDetail>) => {
      const value = filter.getValueOfKey("name");
      if (!value) return true;
      return item.name.includes(value);
    }
  }),
  new FilterOption({
    key: "scope",
    label: $localize`Scope`,
    hint: $localize`Filter by scope.`,
    matches: (item: PolicyDetail, filter: FilterValueGeneric<PolicyDetail>) => {
      const value = filter.getValueOfKey("scope");
      if (!value) return true;
      return item.scope.includes(value);
    }
  }),
  new FilterOption({
    key: "actions",
    label: $localize`Actions`,
    hint: $localize`Filter by action names.`,
    matches: (item: PolicyDetail, filter: FilterValueGeneric<PolicyDetail>) => {
      const value = filter.getValueOfKey("actions");
      if (!value) return true;
      return Object.keys(item.action || {}).some((actionName) => actionName.includes(value));
    }
  }),
  new FilterOption({
    key: "conditions",
    label: $localize`Conditions`,
    hint: $localize`Filter policies by conditions. Matches policies that have at least one condition containing the filter value in its name or value.`,
    matches: (item: PolicyDetail, filter: FilterValueGeneric<PolicyDetail>) => {
      const substring = filter.getValueOfKey("conditions")?.toLocaleLowerCase();
      if (!substring) return true;
      function _isSubstringInList(substring: string, list: string[]): boolean {
        return list.some((item) => item.includes(substring));
      }

      // Admin conditions
      if (
        ("admin realms".includes(substring) && item.adminrealm.length > 0) ||
        _isSubstringInList(substring, item.adminrealm)
      ) {
        return true;
      }
      if (
        ("admin users".includes(substring) && item.adminuser.length > 0) ||
        _isSubstringInList(substring, item.adminuser)
      ) {
        return true;
      }
      // User conditions
      if (("user realms".includes(substring) && item.realm.length > 0) || _isSubstringInList(substring, item.realm)) {
        return true;
      }
      if (("user users".includes(substring) && item.user.length > 0) || _isSubstringInList(substring, item.user)) {
        return true;
      }
      // Environment conditions
      if (
        ("privacyidea nodes".includes(substring) && item.pinode.length > 0) ||
        _isSubstringInList(substring, item.pinode)
      ) {
        return true;
      }
      if (("valid time".includes(substring) && item.time.length > 0) || item.time.includes(substring)) {
        return true;
      }
      if (("clients".includes(substring) && item.client.length > 0) || _isSubstringInList(substring, item.client)) {
        return true;
      }
      if (
        ("user agents".includes(substring) && item.user_agents.length > 0) ||
        _isSubstringInList(substring, item.user_agents)
      ) {
        return true;
      }
      // Additional conditions
      if ("additional conditions".includes(substring) && item.conditions.length > 0) {
        return true;
      }
      for (const condition of item.conditions) {
        for (const conditionItem of condition) {
          if (conditionItem.toString().toLowerCase().includes(substring)) {
            return true;
          }
        }
      }

      return false;
    }
  })
];
