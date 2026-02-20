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

import { Component, computed, inject, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { ReactiveFormsModule } from "@angular/forms";
import { DialogWrapperComponent } from "../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { AbstractDialogComponent } from "../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import { PolicyService, PolicyDetail, PolicyServiceInterface } from "../../../../services/policies/policies.service";
import { DialogAction } from "../../../../models/dialog";
import { PolicyPanelEditComponent } from "./policy-panels/policy-panel-edit/policy-panel-edit.component";
import { DialogServiceInterface, DialogService } from "src/app/services/dialog/dialog.service";

@Component({
  selector: "app-edit-policy-dialog",
  standalone: true,
  imports: [DialogWrapperComponent, CommonModule, ReactiveFormsModule, PolicyPanelEditComponent],
  templateUrl: "./edit-policy-dialog.component.html",
  styleUrl: "./edit-policy-dialog.component.scss"
})
export class EditPolicyDialogComponent extends AbstractDialogComponent<
  { policyDetail: PolicyDetail; mode: "edit" | "create" },
  Partial<PolicyDetail> | null
> {
  private readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);

  readonly policy = signal<PolicyDetail>(this.data.policyDetail);
  readonly policyEdits = signal<Partial<PolicyDetail>>({});
  readonly editedPolicy = computed(() => ({ ...this.policy(), ...this.policyEdits() }));
  readonly isPolicyEdited = computed(() => Object.keys(this.policyEdits()).length > 0);

  readonly actions = computed<DialogAction<"submit" | null>[]>(() => [
    {
      label: this.data.mode === "create" ? $localize`Create Policy` : $localize`Save Changes`,
      value: "submit",
      type: "confirm",
      disabled: !this.canSave()
    }
  ]);

  addPolicyEdit(edits: Partial<PolicyDetail>): void {
    this.policyEdits.set({ ...this.policyEdits(), ...edits });
  }

  canSave(): boolean {
    return this.isPolicyEdited() && !!this.editedPolicy().name?.trim();
  }

  onAction(value: "submit" | null): void {
    if (value !== "submit") return;

    const finalPolicy = this.editedPolicy();
    if (this.data.mode === "create") {
      this.policyService.saveNewPolicy(finalPolicy);
    } else {
      this.policyService.savePolicyEdits(this.policy().name, this.policyEdits());
    }
    this.dialogRef.close(this.policyEdits());
  }

  protected override close(dialogResult?: Partial<PolicyDetail> | null): void {
    if (!this.isPolicyEdited()) {
      super.close(dialogResult);
      return;
    }

    this.dialogService
      .confirm({
        title: $localize`Discard Changes?`,
        message: $localize`You have unsaved changes. Are you sure you want to discard them?`,
        confirmButtonText: $localize`Discard Changes`
      })
      .then((confirmed) => {
        if (confirmed) {
          super.close(dialogResult);
        }
      });
  }
}
