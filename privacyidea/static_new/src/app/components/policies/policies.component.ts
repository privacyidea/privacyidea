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
import { Component, inject, linkedSignal, computed } from "@angular/core";
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
    PoliciesTableComponent,
    PolicyPanelNewComponent
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
  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly authService: AuthServiceInterface = inject(AuthService);

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
