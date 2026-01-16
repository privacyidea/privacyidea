/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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

import { Component, computed, effect, inject, input, model, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { FormsModule } from "@angular/forms";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelectModule } from "@angular/material/select";
import { MatOptionModule } from "@angular/material/core";
import { PolicyPanelViewComponent } from "./policy-panel-view/policy-panel-view.component";
import { PolicyDetail, PolicyService, PolicyServiceInterface } from "../../../../services/policies/policies.service";
import { PolicyPanelEditComponent } from "./policy-panel-edit/policy-panel-edit.component";
import { lastValueFrom } from "rxjs";
import { DialogServiceInterface, DialogService } from "../../../../services/dialog/dialog.service";
import {
  SimpleConfirmationDialogData,
  SimpleConfirmationDialogComponent
} from "../../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { PolicyPanelEditHeaderComponent } from "./policy-panel-edit-header/policy-panel-edit-header.component";
import { PolicyPanelViewHeaderComponent } from "./policy-panel-view-header/policy-panel-view-header.component";

export type PolicyTab = "actions" | "conditions";

@Component({
  selector: "app-policy-panel-edit-view",
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatButtonToggleModule,
    FormsModule,
    MatExpansionModule,
    MatSlideToggleModule,
    MatFormFieldModule,
    MatSelectModule,
    MatOptionModule,
    PolicyPanelViewComponent,
    PolicyPanelEditComponent,
    PolicyPanelEditHeaderComponent,
    PolicyPanelViewHeaderComponent
  ],
  templateUrl: "./policy-panel-edit-view.component.html",
  styleUrl: "./policy-panel-edit-view.component.scss"
})
export class PolicyPanelEditViewComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);

  readonly isEditMode = signal<boolean>(false);
  readonly policy = input.required<PolicyDetail>();
  readonly policyEdits = signal<Partial<PolicyDetail>>({});
  readonly currentPolicy = computed<PolicyDetail>(() => {
    if (this.isEditMode()) {
      return { ...this.policy(), ...this.policyEdits() };
    }
    return this.policy();
  });
  readonly isPolicyEdited = computed(() => {
    const currentPolicy = this.policy;
    const editedPolicyFields = this.policyEdits();
    return (
      Object.keys(editedPolicyFields).length > 0 &&
      Object.keys(editedPolicyFields).some((key) => {
        return (currentPolicy as any)[key] !== (editedPolicyFields as any)[key];
      })
    );
  });

  async handleCollapse(panel: MatExpansionPanel) {
    if (this.isPolicyEdited() && !(await this.confirmDiscardChanges())) {
      panel.open();
      return;
    }
    this.policyEdits.set({});
    this.isEditMode.set(false);
  }

  savePolicy() {
    if (!this.canSavePolicy()) return;

    this.policyService.savePolicyEdits(this.policy().name, this.policyEdits());

    this.isEditMode.set(false);
    this.policyEdits.set({});
  }

  // State-checking Methods
  canSavePolicy(): boolean {
    if (!this.isPolicyEdited()) return false;
    const edits = this.policyEdits();
    if (edits.name !== undefined && edits.name?.trim() === "") {
      return false;
    }
    return true;
  }

  async confirmDiscardChanges(): Promise<boolean> {
    if (this.isPolicyEdited()) {
      return this._confirm({
        title: "Discard Changes",
        confirmAction: {
          type: "destruct",
          label: "Discard",
          value: true
        },
        cancelAction: {
          type: "cancel",
          label: "Keep Editing",
          value: false
        },
        items: [],
        itemType: ""
      });
    }
    return true;
  }

  updatePolicyPriority(priority: number) {
    this.addPolicyEdit({ priority });
  }
  addPolicyEdit(edits: Partial<PolicyDetail>) {
    this.policyEdits.update((currentChanges) => ({ ...currentChanges, ...edits }));
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
