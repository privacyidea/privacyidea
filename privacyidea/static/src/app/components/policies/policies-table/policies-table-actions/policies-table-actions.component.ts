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

import { Component, computed, inject, input } from "@angular/core";

import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { CopyPolicyDialogComponent } from "@components/policies/dialogs/copy-policy-dialog/copy-policy-dialog.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { PolicyDetail, PolicyService } from "@services/policies/policies.service";
import { lastValueFrom } from "rxjs";
import { TableAction, TableActionsComponent } from "../../../shared/table-actions/table-actions.component";
import { TableActionsHost } from "../../../shared/table-actions/table-actions-host";

@Component({
  selector: "app-policies-table-actions",
  standalone: true,
  imports: [TableActionsComponent],
  templateUrl: "./policies-table-actions.component.html"
})
export class PoliciesTableActionsComponent extends TableActionsHost {
  readonly policySelection = input.required<PolicyDetail[]>();
  readonly selectedPolicyNames = computed(() => this.policySelection().map((policy) => policy.name));

  readonly dialogService = inject(DialogService);
  readonly authService = inject(AuthService);
  readonly policyService = inject(PolicyService);
  private readonly router = inject(Router);

  protected readonly actions = computed<TableAction[]>(() => {
    const noSelection = this.policySelection().length < 1;
    return [
      {
        id: "create",
        label: $localize`:@@policy.createPolicy:Create Policy`,
        tone: "primary",
        width: "l",
        icon: "gavel",
        iconClass: "padding-right-4",
        badge: true,
        spacedBadge: true,
        visible: this.authService.actionAllowed("policywrite"),
        run: () => this.createNewPolicy()
      },
      {
        id: "delete",
        label: $localize`:@@common.delete:Delete`,
        tone: "delete-secondary",
        width: "m",
        icon: "delete_sweep",
        visible: this.authService.actionAllowed("policydelete"),
        disabled: noSelection,
        run: () => this.deleteSelectedPolicies()
      },
      {
        id: "copy",
        label: $localize`:@@common.copy:Copy`,
        tone: "secondary",
        width: "m",
        icon: "content_copy",
        visible: this.authService.actionAllowed("policywrite"),
        disabled: noSelection,
        run: () => this.copySelectedPolicies()
      }
    ];
  });

  createNewPolicy(): void {
    this.router.navigateByUrl(ROUTE_PATHS.POLICIES_NEW);
  }

  async deleteSelectedPolicies(): Promise<void> {
    const selection = this.selectedPolicyNames();
    const confirmed = await lastValueFrom(
      this.dialogService
        .openDialog({
          component: SimpleConfirmationDialogComponent,
          data: {
            title: $localize`:@@policy.deletePolicies:Delete Policies`,
            items: selection,
            itemType: $localize`:@@common.policies:Policies`,
            confirmAction: { label: $localize`:@@common.delete:Delete`, value: true, type: "destruct" }
          }
        })
        .afterClosed()
    );

    if (confirmed) {
      for (const name of selection) {
        await this.policyService.deletePolicy(name);
      }
    }
  }

  async copySelectedPolicies(): Promise<void> {
    for (const name of this.selectedPolicyNames()) {
      const newName = await lastValueFrom(
        this.dialogService
          .openDialog({
            component: CopyPolicyDialogComponent,
            data: name
          })
          .afterClosed()
      );

      if (newName) {
        this.policyService.copyPolicy(name, newName);
      }
    }
  }
}
