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

import { Component, computed, inject, input, linkedSignal, output, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatButtonModule } from "@angular/material/button";
import { FormsModule } from "@angular/forms";
import { PolicyDetail } from "../../../../../../services/policies/policies.service";
import { EditActionTabComponent } from "../edit-action-tab/edit-action-tab.component";
import { EditConditionsTabComponent } from "../edit-conditions-tab/edit-conditions-tab.component";
import { DialogService, DialogServiceInterface } from "../../../../../../services/dialog/dialog.service";
import { PolicyDescriptionEditComponent } from "./policy-description/policy-description-edit.component";
import { PolicyPriorityEditComponent } from "./policy-priority-edit/policy-priority-edit.component";
import { PolicyNameEditComponent } from "./policy-name-edit/policy-name-edit.component";

export type PolicyTab = "actions" | "conditions";

@Component({
  selector: "app-policy-panel-edit",
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    FormsModule,
    EditActionTabComponent,
    EditConditionsTabComponent,
    PolicyDescriptionEditComponent,
    PolicyPriorityEditComponent,
    PolicyNameEditComponent
  ],
  templateUrl: "./policy-panel-edit.component.html",
  styleUrl: "./policy-panel-edit.component.scss"
})
export class PolicyPanelEditComponent {
  private readonly dialogService: DialogServiceInterface = inject(DialogService);

  /**
   * Initial policy data from parent.
   */
  readonly policy = input.required<PolicyDetail>();

  /**
   * Notifies the parent about any attribute changes.
   */
  readonly onPolicyEdit = output<Partial<PolicyDetail>>();

  readonly activeTab = signal<PolicyTab>("actions");

  /**
   * Puffer for local changes.
   * It resets to an empty object whenever the source 'policy' input changes.
   */
  readonly policyEdits = linkedSignal<PolicyDetail, Partial<PolicyDetail>>({
    source: () => this.policy(),
    computation: () => ({}) // Reset local edits if a new policy is loaded
  });

  /**
   * Merged view of the original policy and local edits.
   */
  readonly editedPolicy = computed<PolicyDetail>(() => ({
    ...this.policy(),
    ...this.policyEdits()
  }));

  /**
   * Helper to check if the current draft has unsaved changes.
   */
  readonly isPolicyEdited = computed(() => Object.keys(this.policyEdits()).length > 0);

  public setActiveTab(tab: PolicyTab): void {
    this.activeTab.set(tab);
  }

  /**
   * Stores a local edit and propagates it to the parent.
   */
  public addPolicyEdit(edits: Partial<PolicyDetail>): void {
    this.policyEdits.set({ ...this.policyEdits(), ...edits });
    this.onPolicyEdit.emit(edits);
  }

  public updateActions(actions: { [actionName: string]: any }): void {
    this.addPolicyEdit({ action: actions });
  }

  /**
   * Handles scope changes with a safety confirmation if actions are present.
   */
  public async onPolicyScopeChange(newScope: string): Promise<void> {
    const currentActions = this.editedPolicy().action;

    if (currentActions && Object.keys(currentActions).length > 0) {
      const confirm = await this.dialogService.confirm({
        title: $localize`Change Policy Scope`,
        message: $localize`Changing the policy scope will remove all currently added actions. Do you want to proceed?`,
        confirmButtonText: $localize`Yes, change scope`
      });

      if (!confirm) return;

      // Clear actions on scope change
      this.addPolicyEdit({ scope: newScope, action: {} });
    } else {
      this.addPolicyEdit({ scope: newScope });
    }
  }
}
