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

import { Component, input, inject, signal, computed, linkedSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatTableModule } from "@angular/material/table";
import { MatSortModule } from "@angular/material/sort";
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
import { PoliciesViewActionColumnComponent } from "./policies-view-action-column/policies-view-action-column.component";
import { EditConditionsTabComponent } from "../dialogs/edit-policy-dialog/policy-panels/edit-conditions-tab/edit-conditions-tab.component";
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
  { key: "conditions", label: "Conditions" }
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
    PoliciesViewActionColumnComponent,
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

  readonly policiesListFiltered = linkedSignal<PolicyDetail[], PolicyDetail[]>({
    source: () => this.policyService.allPolicies(),
    computation: (allPolicies) => allPolicies
  });
  readonly isFiltered = input.required<boolean>();
  readonly selectedPolicies = signal<Set<string>>(new Set<string>());

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
  async copyPolicy(policy: PolicyDetail) {
    const newName = await lastValueFrom(
      this.dialogService
        .openDialog({
          component: CopyPolicyDialogComponent,
          data: policy.name
        })
        .afterClosed()
    );
    if (!newName) {
      return;
    }
    this.policyService.copyPolicy(policy, newName);
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
    console.log("Checkbox change event:", $event, "for policy:", policyName);
    const selected = this.selectedPolicies();
    if ($event.checked) {
      selected.add(policyName);
    } else {
      selected.delete(policyName);
    }
    this.selectedPolicies.set(new Set<string>(selected));
  }
  isAllSelected(): boolean {
    const selected = this.selectedPolicies();
    const filtered = this.policiesListFiltered();
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
  }

  toggleFilter(filterKeyword: string): void {
    const filterOption = policyFilterOptions.find((option) => option.key === filterKeyword);
    console.log("Toggling filter for keyword:", filterKeyword, "Found option:", filterOption);
    if (filterOption) {
      console.log("Option found, toggling filter.");
      const newFilter = this.filter().toggleFilterKeyword(filterOption);
      this.filter.set(newFilter);
    }
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
      if (value === "true") return "change_circle";
      if (value === "false") return "remove_circle";
      return "add_circle";
    },
    matches: (item: PolicyDetail, filter: FilterValueGeneric<PolicyDetail>) => {
      const value = filter.getValueOfKey("active")?.toLowerCase();
      if (value === "true") return item.active === true;
      if (value === "false") return item.active === false;
      return true;
    }
  }),
  new FilterOption({
    key: "policy_name",
    label: $localize`Policy Name`,
    hint: $localize`Filter by policy name.`,
    matches: (item: PolicyDetail, filter: FilterValueGeneric<PolicyDetail>) => {
      const value = filter.getValueOfKey("policy_name");
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
    key: "realm",
    label: $localize`Realm`,
    hint: $localize`Filter by realm.`,
    matches: (item: PolicyDetail, filter: FilterValueGeneric<PolicyDetail>) => {
      const value = filter.getValueOfKey("realm");
      if (!value) return true;
      return item.realm.includes(value);
    }
  })
];
