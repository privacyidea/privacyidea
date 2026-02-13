/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import { CommonModule } from "@angular/common";
import { Component, inject, viewChild, signal, linkedSignal, computed, input } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule, MatCheckboxChange } from "@angular/material/checkbox";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatPaginatorModule } from "@angular/material/paginator";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { MatSortModule, Sort } from "@angular/material/sort";
import { MatTableModule } from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";
import { lastValueFrom } from "rxjs";

import {
  SimpleConfirmationDialogData,
  SimpleConfirmationDialogComponent
} from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { FilterValueGeneric } from "src/app/core/models/filter_value_generic/filter-value-generic";
import { FilterOption } from "src/app/core/models/filter_value_generic/filter-option";
import { AuthServiceInterface, AuthService } from "src/app/services/auth/auth.service";
import { DialogServiceInterface, DialogService } from "src/app/services/dialog/dialog.service";
import { PolicyServiceInterface, PolicyService, PolicyDetail } from "src/app/services/policies/policies.service";
import { TableUtilsServiceInterface, TableUtilsService } from "src/app/services/table-utils/table-utils.service";
import { EditPolicyDialogComponent } from "../dialogs/edit-policy-dialog/edit-policy-dialog.component";
import { PoliciesTableActionsComponent } from "./policies-table-actions/policies-table-actions.component";
import { PolicyFilterComponent } from "./policy-filter/policy-filter.component";
import { ConditionsTabComponent } from "./view-conditions-column/view-conditions-column.component";
import { ViewActionColumnComponent } from "./view-action-column/view-action-column.component";

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
  readonly sort = signal<Sort>({ active: "", direction: "" });

  readonly isFiltered = input.required<boolean>();
  readonly filter = signal<FilterValueGeneric<PolicyDetail>>(
    new FilterValueGeneric({ availableFilters: policyFilterOptions })
  );

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
    if (!sort.active || sort.direction === "") return policies;

    return [...policies].sort((a, b) => {
      const isAsc = sort.direction === "asc";
      switch (sort.active) {
        case "priority":
          return this.compare(a.priority, b.priority, isAsc);
        case "name":
          return this.compare(a.name, b.name, isAsc);
        case "scope":
          return this.compare(a.scope, b.scope, isAsc);
        case "description":
          return this.compare(a.description ?? "", b.description ?? "", isAsc);
        case "active":
          return this.compare(a.active, b.active, isAsc);
        default:
          return 0;
      }
    });
  });

  readonly selectedPolicies = linkedSignal<PolicyDetail[], Set<string>>({
    source: () => this.policiesListFiltered(),
    computation: (source, previous) => {
      const selected = previous?.value ?? new Set<string>();
      for (const name of selected) {
        if (!source.some((p) => p.name === name)) selected.delete(name);
      }
      return selected;
    }
  });

  public onSortChange(sort: Sort): void {
    this.sort.set(sort);
  }

  private compare(a: number | string | boolean, b: number | string | boolean, isAsc: boolean): number {
    return (a < b ? -1 : 1) * (isAsc ? 1 : -1);
  }

  public onFilterUpdate(newFilter: FilterValueGeneric<PolicyDetail>): void {
    this.filter.set(newFilter);
  }

  public onFilterClick(columnKey: string): void {
    this.toggleFilter(columnKey);
    this.filterComponent()?.focusInput();
  }

  public toggleFilter(columnKey: string): void {
    const option = policyFilterOptions.find((o) => o.key === columnKey);
    if (!option) return;

    const nextFilter = option.toggle ? option.toggle(this.filter()) : this.filter().toggleKey(option.key);

    this.filter.set(nextFilter);
    this.filterComponent()?.updateFilterManually(nextFilter);
  }

  public getFilterIconName(columnKey: string): string {
    const option = policyFilterOptions.find((o) => o.key === columnKey);
    if (!option) return "filter_alt";
    // Hier rufen wir die Property des Klassen-Instanz auf (getIconName)
    return option.getIconName ? option.getIconName(this.filter()) : this.filter().getFilterIconNameOf(option);
  }

  public getFilterTooltipText(columnKey: string): string {
    return policyFilterOptions.find((o) => o.key === columnKey)?.hint ?? "";
  }

  public isFilterable(columnKey: string): boolean {
    return policyFilterOptions.some((o) => o.key === columnKey);
  }

  public isSelected(policyName: string): boolean {
    return this.selectedPolicies().has(policyName);
  }

  public updateSelection($event: MatCheckboxChange, policyName: string): void {
    const selected = new Set(this.selectedPolicies());
    $event.checked ? selected.add(policyName) : selected.delete(policyName);
    this.selectedPolicies.set(selected);
  }

  public isAllSelected(): boolean {
    const filtered = this.policiesListFiltered();
    if (filtered.length === 0) return false;
    const selected = this.selectedPolicies();
    return selected.size === filtered.length && filtered.every((p) => selected.has(p.name));
  }

  public masterToggle(): void {
    if (this.isAllSelected()) {
      this.selectedPolicies.set(new Set<string>());
    } else {
      this.selectedPolicies.set(new Set(this.policiesListFiltered().map((p) => p.name)));
    }
  }

  async deletePolicy(policyName: string): Promise<void> {
    const confirmed = await this._confirm({
      title: "Confirm Deletion",
      confirmAction: { type: "destruct", label: "Delete", value: true },
      cancelAction: { type: "cancel", label: "Cancel", value: false },
      items: [policyName],
      itemType: "policy"
    });
    if (confirmed) this.policyService.deletePolicy(policyName);
  }

  async editPolicy(policy: PolicyDetail): Promise<void> {
    const result = await lastValueFrom(
      this.dialogService
        .openDialog({
          component: EditPolicyDialogComponent,
          data: { mode: "edit", policyDetail: policy }
        })
        .afterClosed()
    );
    if (result) this.policyService.updatePolicyOptimistic(result);
  }

  private async _confirm(data: SimpleConfirmationDialogData): Promise<boolean> {
    const res = await lastValueFrom(
      this.dialogService.openDialog({ component: SimpleConfirmationDialogComponent, data }).afterClosed()
    );
    return res === true;
  }
}

/**
 * Filter-Optionen mit korrektem Key 'iconName' für den Konstruktor.
 */
const policyFilterOptions = [
  new FilterOption<PolicyDetail>({
    key: "priority",
    label: $localize`Priority`,
    matches: (item, filter) => {
      const val = filter.getValueOfKey("priority");
      if (!val) return true;
      const priority = item.priority;
      try {
        if (val.startsWith(">=")) return priority >= parseInt(val.substring(2), 10);
        if (val.startsWith("<=")) return priority <= parseInt(val.substring(2), 10);
        if (val.startsWith(">")) return priority > parseInt(val.substring(1), 10);
        if (val.startsWith("<")) return priority < parseInt(val.substring(1), 10);
        if (val.startsWith("!=")) return priority !== parseInt(val.substring(2), 10);
        if (val.startsWith("=")) return priority === parseInt(val.substring(1), 10);
        if (val.includes("-")) {
          const [min, max] = val.split("-").map((v) => parseInt(v, 10));
          return priority >= min && priority <= max;
        }
        return priority === parseInt(val, 10);
      } catch {
        return false;
      }
    }
  }),
  new FilterOption<PolicyDetail>({
    key: "active",
    label: $localize`Active`,
    toggle: (filter) => {
      const v = filter.getValueOfKey("active")?.toLowerCase();
      if (v === "true") return filter.setValueOfKey("active", "false");
      if (v === "false") return filter.removeKey("active");
      return filter.setValueOfKey("active", "true");
    },
    // Korrigiert: iconName statt getIconName
    iconName: (filter) => {
      const v = filter.getValueOfKey("active")?.toLowerCase();
      return v === "true" ? "screen_rotation_alt" : v === "false" ? "filter_alt_off" : "filter_alt";
    },
    matches: (item, filter) => {
      const v = filter.getValueOfKey("active")?.toLowerCase();
      return v === "true" ? item.active === true : v === "false" ? item.active === false : true;
    }
  }),
  new FilterOption<PolicyDetail>({
    key: "name",
    label: $localize`Policy Name`,
    matches: (item, filter) => {
      const val = filter.getValueOfKey("name");
      return !val || item.name.toLowerCase().includes(val.toLowerCase());
    }
  }),
  new FilterOption<PolicyDetail>({
    key: "scope",
    label: $localize`Scope`,
    matches: (item, filter) => {
      const val = filter.getValueOfKey("scope");
      return !val || item.scope.toLowerCase().includes(val.toLowerCase());
    }
  }),
  new FilterOption<PolicyDetail>({
    key: "actions",
    label: $localize`Actions`,
    matches: (item, filter) => {
      const val = filter.getValueOfKey("actions")?.toLowerCase();
      if (!val || !item.action) return true;
      return Object.entries(item.action).some(
        ([n, v]) => n.toLowerCase().includes(val) || String(v).toLowerCase().includes(val)
      );
    }
  }),
  new FilterOption<PolicyDetail>({
    key: "conditions",
    label: $localize`Conditions`,
    matches: (item, filter) => {
      const val = filter.getValueOfKey("conditions")?.toLowerCase();
      if (!val) return true;
      const fields = [
        item.adminrealm,
        item.adminuser,
        item.realm,
        item.user,
        item.pinode,
        item.client,
        item.user_agents
      ];
      if (fields.some((l) => l.some((e) => e.toLowerCase().includes(val)))) return true;
      return (
        item.time.toLowerCase().includes(val) ||
        item.conditions.some((cond) => cond.some((c) => String(c).toLowerCase().includes(val)))
      );
    }
  })
];
