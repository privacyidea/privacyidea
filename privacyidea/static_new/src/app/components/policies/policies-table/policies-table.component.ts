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

import { Component, input, inject, signal, linkedSignal } from "@angular/core";
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
import { CopyPolicyDialogComponent } from "../dialog/copy-policy-dialog/copy-policy-dialog.component";
import { EditPolicyDialogComponent } from "../dialog/edit-policy-dialog/edit-policy-dialog.component";
import { DialogService, DialogServiceInterface } from "../../../services/dialog/dialog.service";
import { MatInputModule } from "@angular/material/input";
import { MatPaginatorModule } from "@angular/material/paginator";
import { PoliciesTableActionsComponent } from "./policies-table-actions/policies-table-actions.component";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { trigger, state, style, transition, animate } from "@angular/animations";
import { PolicyPanelViewComponent } from "./policy-panels/policy-panel-edit-view/policy-panel-view/policy-panel-view.component";

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
    PolicyPanelViewComponent
  ],
  templateUrl: "./policies-table.component.html",
  styleUrl: "./policies-table.component.scss",
  animations: [
    trigger("detailExpand", [
      state("collapsed,void", style({ height: "0px", minHeight: "0" })),
      state("expanded", style({ height: "*" })),
      transition("expanded <=> collapsed", animate("225ms cubic-bezier(0.4, 0.0, 0.2, 1)"))
    ])
  ]
})
export class PoliciesTableComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly authService: AuthServiceInterface = inject(AuthService);

  readonly isFiltered = input.required<boolean>();
  readonly policiesListFiltered = input.required<PolicyDetail[]>();
  readonly selectedPolicies = signal<Set<string>>(new Set<string>());

  displayedColumns: string[] = ["select", "priority", "name", "scope", "description", "active", "actions"];
  expandedElements = linkedSignal<{ policiesListFiltered: PolicyDetail[]; isFiltered: boolean }, Set<PolicyDetail>>({
    source: () => ({ policiesListFiltered: this.policiesListFiltered(), isFiltered: this.isFiltered() }),
    computation: (source, previous) => {
      const { policiesListFiltered, isFiltered } = source;
      if (isFiltered) {
        return new Set<PolicyDetail>(policiesListFiltered);
      }
      return new Set<PolicyDetail>();
    }
  });

  isExpanded(policy: PolicyDetail): boolean {
    return this.expandedElements().has(policy);
  }

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
  toggleSelection(policyName: string) {
    const selected = this.selectedPolicies();
    if (selected.has(policyName)) {
      selected.delete(policyName);
    } else {
      selected.add(policyName);
    }
    this.selectedPolicies.set(selected);
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
  toggleExpansion(policy: PolicyDetail) {
    if (this.isFiltered()) {
      const expandedElements = this.expandedElements();
      if (expandedElements.has(policy)) {
        expandedElements.delete(policy);
      } else {
        expandedElements.add(policy);
      }
      this.expandedElements.set(expandedElements);
      return;
    }
    if (this.expandedElements().has(policy)) {
      this.expandedElements.set(new Set<PolicyDetail>());
    } else {
      this.expandedElements.set(new Set<PolicyDetail>([policy]));
    }
  }
}
