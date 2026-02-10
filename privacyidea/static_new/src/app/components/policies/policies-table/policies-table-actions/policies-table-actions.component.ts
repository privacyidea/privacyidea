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

import { Component, inject, input } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { lastValueFrom } from "rxjs";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { PolicyService } from "../../../../services/policies/policies.service";
import { EditPolicyDialogComponent } from "../../dialogs/edit-policy-dialog/edit-policy-dialog.component";
import { SimpleConfirmationDialogComponent } from "../../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { CopyPolicyDialogComponent } from "@components/policies/dialogs/copy-policy-dialog/copy-policy-dialog.component";

@Component({
  selector: "app-policies-table-actions",
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: "./policies-table-actions.component.html",
  styleUrl: "./policies-table-actions.component.scss"
})
export class PoliciesTableActionsComponent {
  readonly policySelection = input.required<Set<string>>();

  readonly dialogService = inject(DialogService);
  readonly authService = inject(AuthService);
  readonly policyService = inject(PolicyService);

  createNewPolicy(): void {
    this.dialogService.openDialog({
      component: EditPolicyDialogComponent,
      data: { mode: "create", policyDetail: this.policyService.getEmptyPolicy() }
    });
  }

  async deleteSelectedPolicies(): Promise<void> {
    const selection = Array.from(this.policySelection());
    const confirmed = await lastValueFrom(
      this.dialogService
        .openDialog({
          component: SimpleConfirmationDialogComponent,
          data: {
            title: $localize`Delete Policies`,
            items: selection,
            itemType: $localize`Policies`,
            confirmAction: { label: $localize`Delete`, value: true, type: "destruct" },
            cancelAction: { label: $localize`Cancel`, value: false, type: "cancel" }
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
    for (const name of this.policySelection()) {
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
