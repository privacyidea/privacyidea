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

import { Component, computed, inject, linkedSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatExpansionModule } from "@angular/material/expansion";
import { PolicyDetail, PolicyService, PolicyServiceInterface } from "../../services/policies/policies.service";
import { MatIconModule } from "@angular/material/icon";
import { AuthService, AuthServiceInterface } from "../../services/auth/auth.service";
import { PolicyFilterComponent } from "./policy-panels/policy-filter/policy-filter.component";
import { PolicyPanelNewComponent } from "./policy-panels/policy-panel-new/policy-panel-new.component";
import { MatTableModule } from "@angular/material/table";
import { MatSortModule } from "@angular/material/sort";
import { PolicyTableRowDetailsComponent } from "./policy-table-row-details/policy-table-row-details.component";
import { animate, state, style, transition, trigger } from "@angular/animations";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { lastValueFrom } from "rxjs";
import { CopyPolicyDialogComponent } from "./dialog/copy-policy-dialog/copy-policy-dialog.component";
import { EditPolicyDialogComponent } from "./dialog/edit-policy-dialog/edit-policy-dialog.component";
import { DialogService, DialogServiceInterface } from "../../services/dialog/dialog.service";
import {
  SimpleConfirmationDialogData,
  SimpleConfirmationDialogComponent
} from "../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { PoliciesTableComponent } from "./policies-table/policies-table.component";

export type PolicyTab = "actions" | "conditions";

@Component({
  selector: "app-policies",
  standalone: true,
  imports: [
    CommonModule,
    MatExpansionModule,
    MatIconModule,
    PolicyFilterComponent,
    PolicyPanelNewComponent,
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
  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly authService: AuthServiceInterface = inject(AuthService);

  readonly policiesListFiltered = linkedSignal<PolicyDetail[], PolicyDetail[]>({
    source: () => this.policyService.allPolicies(),
    computation: (allPolicies) => allPolicies
  });

  displayedColumns: string[] = ["priority", "name", "scope", "description", "active", "actions"];
  expandedElement: PolicyDetail | null = null;
  policiesIsFiltered = computed(() => {
    console.log(
      "Comparing lengths:",
      this.policiesListFiltered().length,
      "vs",
      this.policyService.allPolicies().length
    );
    console.log("policiesIsFiltered is:", this.policiesListFiltered().length < this.policyService.allPolicies().length);
    return this.policiesListFiltered().length < this.policyService.allPolicies().length;
  });

  onPolicyListFilteredChange(filteredPolicies: PolicyDetail[]): void {
    this.policiesListFiltered.set(filteredPolicies);
  }
}
