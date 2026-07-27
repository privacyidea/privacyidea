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

import { CommonModule, KeyValuePipe } from "@angular/common";
import { Component, computed, inject, linkedSignal, signal, viewChild } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxChange, MatCheckboxModule } from "@angular/material/checkbox";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { MatSortModule, Sort } from "@angular/material/sort";
import { MatTableModule } from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";

import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { HighlightPipe } from "@components/shared/pipes/highlight.pipe";
import { FilterOption } from "@core/models/filter_value_generic/filter-option";
import { FilterValueGeneric } from "@core/models/filter_value_generic/filter-value-generic";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PolicyDetail, PolicyService, PolicyServiceInterface } from "@services/policies/policies.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { PoliciesTableActionsComponent } from "./policies-table-actions/policies-table-actions.component";
import { PolicyFilterComponent } from "./policy-filter/policy-filter.component";
import { ViewActionColumnComponent } from "./view-action-column/view-action-column.component";
import { ViewConditionsColumnComponent } from "./view-conditions-column/view-conditions-column.component";

@Component({
  selector: "app-policies-table",
  standalone: true,
  imports: [
    CommonModule,
    KeyValuePipe,
    MatTableModule,
    MatSortModule,
    MatIconModule,
    MatButtonModule,
    MatSlideToggleModule,
    MatInputModule,
    PoliciesTableActionsComponent,
    MatCheckboxModule,
    ViewActionColumnComponent,
    MatTooltipModule,
    PolicyFilterComponent,
    ViewConditionsColumnComponent,
    CopyButtonComponent,
    HighlightPipe
  ],
  templateUrl: "./policies-table.component.html",
  styleUrl: "./policies-table.component.scss"
})
export class PoliciesTableComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  private readonly router = inject(Router);

  readonly filterComponent = viewChild<PolicyFilterComponent>("filterComponent");

  readonly columns = {
    priority: { label: $localize`Priority`, filterable: true, sortable: true },
    name: { label: $localize`Name`, filterable: true, sortable: true },
    scope: { label: $localize`Scope`, filterable: true, sortable: true },
    description: { label: $localize`Description`, filterable: true, sortable: true },
    actions: { label: $localize`Actions`, filterable: true, sortable: false },
    conditions: { label: $localize`Conditions`, filterable: true, sortable: false },
    active: { label: $localize`Active`, filterable: true, sortable: true }
  } as const;

  readonly columnKeys = computed(() => ["select", ...Object.keys(this.columns)]);

  readonly skeletonRowCount = 10;

  readonly sort = signal<Sort>({ active: "priority", direction: "asc" });
  readonly filter = signal<FilterValueGeneric<PolicyDetail>>(
    new FilterValueGeneric({ availableFilters: policyFilterOptions })
  );

  // Terms to visually highlight per dense column: the keyword-less search terms plus that column's
  // own keyword value. Short columns (name/scope/priority/active) are not highlighted on purpose.
  readonly highlightTerms = computed(() => {
    const filter = this.filter();
    const freeText = filter.freeTextTerms;
    const withKeyword = (key: string): string[] => {
      const value = filter.getFilterOfKey(key);
      return value ? [...freeText, value] : freeText;
    };
    return {
      description: withKeyword("description"),
      actions: withKeyword("actions"),
      conditions: withKeyword("conditions")
    };
  });

  readonly emptyResource = linkedSignal({
    source: () => this.policyService.allPolicies(),
    computation: () => Array.from({ length: this.skeletonRowCount }, () => ({ name: "" }) as PolicyDetail)
  });

  readonly policiesListFiltered = computed(() => {
    const all = this.policyService.allPolicies();
    if (all.length === 0) return this.emptyResource();
    return this.filter().filterItems(all);
  });

  readonly sortedFilteredPolicies = computed(() => {
    const policies = this.policiesListFiltered();
    const sort = this.sort();
    if (!sort.active || sort.direction === "" || this.policyService.allPolicies().length === 0) return policies;

    return [...policies].sort((a, b) => {
      const isAsc = sort.direction === "asc";
      const valA = a[sort.active as keyof PolicyDetail] ?? "";
      const valB = b[sort.active as keyof PolicyDetail] ?? "";
      if (valA === valB) return 0;
      return (valA < valB ? -1 : 1) * (isAsc ? 1 : -1);
    });
  });

  readonly selectedPolicies = linkedSignal<PolicyDetail[], Set<string>>({
    source: () => this.policiesListFiltered(),
    computation: (source, previous) => {
      const selected = new Set(previous?.value ?? []);
      if (this.policyService.allPolicies().length === 0) return new Set();
      const currentNames = new Set(source.map((p) => p.name));
      for (const name of selected) {
        if (!currentNames.has(name)) selected.delete(name);
      }
      return selected;
    }
  });

  readonly keepOrder = () => 0;

  onSortChange(sort: Sort): void {
    this.sort.set(sort);
  }

  onFilterUpdate(newFilter: FilterValueGeneric<PolicyDetail>): void {
    this.filter.set(newFilter);
  }

  onFilterClick(columnKey: string): void {
    const option = policyFilterOptions.find((o) => o.key === columnKey);
    if (!option) return;
    const nextFilter = option.toggle ? option.toggle(this.filter()) : this.filter().toggleKey(option.key);
    this.onFilterUpdate(nextFilter);
    this.filterComponent()?.updateFilterManually(nextFilter);
  }

  updateSelection($event: MatCheckboxChange, policyName: string): void {
    if (!policyName) return;
    const selected = new Set(this.selectedPolicies());
    if ($event.checked) {
      selected.add(policyName);
    } else {
      selected.delete(policyName);
    }
    this.selectedPolicies.set(selected);
  }

  isAllSelected(): boolean {
    const displayed = this.sortedFilteredPolicies().filter((p) => !!p.name);
    if (displayed.length === 0) return false;
    return displayed.every((p) => this.selectedPolicies().has(p.name));
  }

  masterToggle(): void {
    const selected = new Set(this.selectedPolicies());
    const displayed = this.sortedFilteredPolicies().filter((p) => !!p.name);
    if (this.isAllSelected()) {
      displayed.forEach((p) => selected.delete(p.name));
    } else {
      displayed.forEach((p) => selected.add(p.name));
    }
    this.selectedPolicies.set(selected);
  }

  getFilterIconName(columnKey: string): string {
    const actionType = policyFilterOptions.find((o) => o.key === columnKey)?.getActionType?.(this.filter()) ?? "add";
    switch (actionType) {
      case "add":
        return "filter_alt";
      case "remove":
        return "filter_alt_off";
      case "change":
        return "screen_rotation_alt";
      default:
        return "filter_alt";
    }
  }

  getFilterTooltipText(columnKey: string): string {
    return policyFilterOptions.find((o) => o.key === columnKey)?.hint ?? "";
  }

  isFilterable(columnKey: string): boolean {
    return policyFilterOptions.some((o) => o.key === columnKey);
  }

  togglePolicyActive(policy: PolicyDetail): void {
    if (!policy.name) return;
    this.policyService.togglePolicyActive(policy);
  }

  async editPolicy(policy: PolicyDetail): Promise<void> {
    if (!policy.name) return;
    this.router.navigateByUrl(ROUTE_PATHS.POLICIES_DETAILS + policy.name);
  }
}

// Split a priority filter into its comparison operator and numeric operand.
// The operand is parsed strictly: anything that is not a whole number (e.g.
// ">10x") yields NaN, so a partially-numeric value does not silently match.
const PRIORITY_OPERATORS: readonly [string, (a: number, b: number) => boolean][] = [
  [">=", (a, b) => a >= b],
  ["<=", (a, b) => a <= b],
  ["!=", (a, b) => a !== b],
  [">", (a, b) => a > b],
  ["<", (a, b) => a < b],
  ["=", (a, b) => a === b]
];

function matchesPriority(priority: number, val: string): boolean {
  const [prefix, compare] = PRIORITY_OPERATORS.find(([p]) => val.startsWith(p)) ?? ["", (a: number, b: number) => a === b];
  const rest = val.substring(prefix.length).trim();
  if (!/^-?\d+$/.test(rest)) return false;
  return compare(priority, Number(rest));
}

function matchesActions(item: PolicyDetail, term: string): boolean {
  if (!item.action) return false;
  return Object.entries(item.action).some(
    ([name, value]) => name.toLowerCase().includes(term) || String(value).toLowerCase().includes(term)
  );
}

function matchesConditions(item: PolicyDetail, term: string): boolean {
  const listFields = [
    item.adminrealm,
    item.adminuser,
    item.realm,
    item.user,
    item.pinode,
    item.client,
    item.user_agents
  ];
  if (listFields.some((list) => list?.some((entry) => entry.toLowerCase().includes(term)))) return true;
  return Boolean(
    item.time?.toLowerCase().includes(term) ||
      item.conditions?.some((cond) => cond.some((c) => String(c).toLowerCase().includes(term)))
  );
}

const policyFilterOptions: FilterOption<PolicyDetail>[] = [
  new FilterOption<PolicyDetail>({
    key: "priority",
    label: $localize`Priority`,
    matches: (item, filter) => {
      const val = filter.getFilterOfKey("priority");
      return !val || matchesPriority(item.priority, val);
    },
    globalMatches: (item, term) => String(item.priority).includes(term)
  }),
  new FilterOption<PolicyDetail>({
    key: "active",
    label: $localize`Active`,
    toggle: (filter) => {
      const v = filter.getFilterOfKey("active")?.toLowerCase();
      if (v === "true") return filter.setValueOfKey("active", "false");
      if (v === "false") return filter.removeKey("active");
      return filter.setValueOfKey("active", "true");
    },
    getActionType: (filter) => {
      const v = filter.getFilterOfKey("active")?.toLowerCase();
      return v === "true" ? "change" : v === "false" ? "remove" : "add";
    },
    matches: (item, filter) => {
      const v = filter.getFilterOfKey("active")?.toLowerCase();
      return v === "true" ? item.active === true : v === "false" ? item.active === false : true;
    },
    globalMatches: (item, term) => String(item.active).includes(term)
  }),
  new FilterOption<PolicyDetail>({
    key: "name",
    label: $localize`Policy Name`,
    matches: (item, filter) => {
      const val = filter.getFilterOfKey("name");
      return !val || item.name.toLowerCase().includes(val.toLowerCase());
    },
    globalMatches: (item, term) => item.name.toLowerCase().includes(term)
  }),
  new FilterOption<PolicyDetail>({
    key: "scope",
    label: $localize`Scope`,
    matches: (item, filter) => {
      const val = filter.getFilterOfKey("scope");
      return !val || item.scope.toLowerCase().includes(val.toLowerCase());
    },
    globalMatches: (item, term) => item.scope.toLowerCase().includes(term)
  }),
  new FilterOption<PolicyDetail>({
    key: "description",
    label: $localize`Description`,
    matches: (item, filter) => {
      const val = filter.getFilterOfKey("description");
      return !val || (item.description?.toLowerCase().includes(val.toLowerCase()) ?? false);
    },
    globalMatches: (item, term) => item.description?.toLowerCase().includes(term) ?? false
  }),
  new FilterOption<PolicyDetail>({
    key: "actions",
    label: $localize`Actions`,
    matches: (item, filter) => {
      const val = filter.getFilterOfKey("actions")?.toLowerCase();
      return !val || matchesActions(item, val);
    },
    globalMatches: (item, term) => matchesActions(item, term)
  }),
  new FilterOption<PolicyDetail>({
    key: "conditions",
    label: $localize`Conditions`,
    matches: (item, filter) => {
      const val = filter.getFilterOfKey("conditions")?.toLowerCase();
      return !val || matchesConditions(item, val);
    },
    globalMatches: (item, term) => matchesConditions(item, term)
  })
];
