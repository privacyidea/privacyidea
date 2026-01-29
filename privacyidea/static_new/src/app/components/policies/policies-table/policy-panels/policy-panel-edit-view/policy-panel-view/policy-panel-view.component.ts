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

import { CommonModule } from "@angular/common";
import { Component, inject, output, input } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { MatCardModule } from "@angular/material/card";
import { MatOptionModule } from "@angular/material/core";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatSelectModule } from "@angular/material/select";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { lastValueFrom } from "rxjs";
import { DialogServiceInterface, DialogService } from "../../../../../../services/dialog/dialog.service";
import {
  PolicyServiceInterface,
  PolicyService,
  PolicyDetail
} from "../../../../../../services/policies/policies.service";
import {
  SimpleConfirmationDialogData,
  SimpleConfirmationDialogComponent
} from "../../../../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ActionTabComponent } from "../../action-tab/action-tab.component";
import { ConditionsTabComponent } from "../../conditions-tab/conditions-tab.component";

@Component({
  selector: "app-policy-panel-view",
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    FormsModule,
    MatIconModule,
    MatButtonModule,
    MatButtonToggleModule,
    FormsModule,
    MatExpansionModule,
    MatSlideToggleModule,
    MatFormFieldModule,
    MatSelectModule,
    MatOptionModule,
    ActionTabComponent,
    ConditionsTabComponent
  ],
  templateUrl: "./policy-panel-view.component.html",
  styleUrl: "./policy-panel-view.component.scss"
})
export class PolicyPanelViewComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);

  // readonly isEditMode = signal<boolean>(false);
  onEditModeChange = output<boolean>();
  readonly policy = input.required<PolicyDetail>();

  // currentPolicyHasConditions = computed(() => this.policyService.policyHasConditions(this.currentPolicy()));

  // Component State Signals

  togglePolicyActive(policy: PolicyDetail, activate: boolean) {
    if (activate) {
      this.policyService.enablePolicy(policy.name);
    } else {
      this.policyService.disablePolicy(policy.name);
    }
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
}
