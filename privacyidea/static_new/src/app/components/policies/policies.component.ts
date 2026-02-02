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

import { trigger, state, style, transition, animate } from "@angular/animations";
import { CommonModule } from "@angular/common";
import { Component, inject, linkedSignal, computed, signal, effect } from "@angular/core";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { MatSortModule } from "@angular/material/sort";
import { MatTableModule } from "@angular/material/table";
import { AuthServiceInterface, AuthService } from "../../services/auth/auth.service";
import { DialogServiceInterface, DialogService } from "../../services/dialog/dialog.service";
import { PolicyServiceInterface, PolicyService, PolicyDetail } from "../../services/policies/policies.service";
import { PoliciesTableComponent } from "./policies-table/policies-table.component";
import { PolicyFilterComponent } from "./policy-filter/policy-filter.component";
import { PolicyPanelNewComponent } from "./policy-panel-new/policy-panel-new.component";
import { FilterValueGeneric } from "../../core/models/filter_value_generic/filter_value_generic";
import { FilterOption } from "../shared/keyword-filter-generic/keyword-filter-generic.component";

export type PolicyTab = "actions" | "conditions";

@Component({
  selector: "app-policies",
  standalone: true,
  imports: [
    CommonModule,
    MatExpansionModule,
    MatIconModule,
    PolicyFilterComponent,
    MatTableModule,
    MatSortModule,
    MatSlideToggleModule,
    PoliciesTableComponent
  ],
  templateUrl: "./policies.component.html",
  styleUrl: "./policies.component.scss",
  animations: [
    trigger("detailExpand", [
      state("collapsed,void", style({ height: "0px", minHeight: "0" })),
      state("expanded", style({ height: "*" })),
      transition("expanded <=> collapsed", animate("225ms cubic-bezier(0.4, 0.0, 0.2, 1)"))
    ])
  ]
})
export class PoliciesComponent {
  readonly policyFilterOptions = policyFilterOptions;
  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly authService: AuthServiceInterface = inject(AuthService);

  constructor() {
    effect(() => {
      console.log("New Filter Value:", this.filter());
    });
  }

  readonly filter = signal<FilterValueGeneric<PolicyDetail>>(
    new FilterValueGeneric({ availableFilters: policyFilterOptions })
  );
  readonly policiesListFiltered = linkedSignal<PolicyDetail[], PolicyDetail[]>({
    source: () => this.policyService.allPolicies(),
    computation: (allPolicies) => allPolicies
  });

  displayedColumns: string[] = ["priority", "name", "scope", "description", "active", "actions"];
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
