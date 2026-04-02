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

import { Component, computed, effect, inject, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { ReactiveFormsModule } from "@angular/forms";
import { DialogWrapperComponent } from "../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { PolicyDetail, PolicyService, PolicyServiceInterface } from "../../../../services/policies/policies.service";
import { DialogAction } from "../../../../models/dialog";
import { PolicyPanelEditComponent } from "./policy-panels/policy-panel-edit/policy-panel-edit.component";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { ROUTE_PATHS } from "../../../../route_paths";
import { NAVIGATION_ACCESSIBLE_DIALOG_CLASS } from "../../../../constants/global.constants";
import { PendingChangesDialogComponent } from "@components/shared/dialog/abstract-dialog/pending-changes-dialog.component";

@Component({
  selector: "app-edit-policy-dialog",
  standalone: true,
  host: {
    class: NAVIGATION_ACCESSIBLE_DIALOG_CLASS
  },
  imports: [DialogWrapperComponent, CommonModule, ReactiveFormsModule, PolicyPanelEditComponent],
  templateUrl: "./edit-policy-dialog.component.html",
  styleUrl: "./edit-policy-dialog.component.scss"
})
export class EditPolicyDialogComponent extends PendingChangesDialogComponent<
  { policyDetail: PolicyDetail; mode: "edit" | "create" },
  Partial<PolicyDetail> | null
> {
  private readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly contentService: ContentServiceInterface = inject(ContentService);

  readonly policy = signal<PolicyDetail>(this.data.policyDetail);
  readonly policyEdits = signal<Partial<PolicyDetail>>({});
  readonly editedPolicy = computed(() => ({ ...this.policy(), ...this.policyEdits() }));
  readonly isPolicyEdited = computed(() => Object.keys(this.policyEdits()).length > 0);
  readonly isDirty = this.isPolicyEdited;
  readonly mode = this.data.mode;

  readonly actions = computed<DialogAction<"submit" | null>[]>(() => [
    {
      label: this.mode === "create" ? $localize`Create Policy` : $localize`Save`,
      value: "submit",
      type: "confirm",
      primary: true,
      disabled: !this.canSave(),
      className: "button-width-s",
    }
  ]);

  constructor() {
    super();

    // Close the dialog when navigating away from the events route
    // However, changing the route is disabled via the pendingChangesGuard when there are unsaved changes. This effect
    // will only be triggered when there are no unsaved changes or when the user confirmed discarding them.
    effect(() => {
      if (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.POLICIES)) {
        this.dialogRef.close();
      }
    });
  }

  addPolicyEdit(edits: Partial<PolicyDetail>): void {
    this.policyEdits.set({ ...this.policyEdits(), ...edits });
  }

  canSave = computed(() => this.isPolicyEdited() && !!this.editedPolicy().name?.trim());

  onAction(value: "submit" | null): void {
    if (value !== "submit") return;
    this.onSave();
  }

  async onSave() {
    let success = false;
    if (this.mode === "create") {
      success = await this.policyService.saveNewPolicy({ ...this.policy(), ...this.policyEdits() });
    } else {
      success = await this.policyService.savePolicyEdits(this.policy().name, { ...this.policy(), ...this.policyEdits() });
    }
    if (success) {
      this.dialogRef.close();
    }
    return success;
  }
}
