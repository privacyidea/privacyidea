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

import { Component, computed, inject, input, linkedSignal, output, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { FormsModule } from "@angular/forms";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { PolicyDetail, PolicyService, PolicyServiceInterface } from "../../../../../services/policies/policies.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelectModule } from "@angular/material/select";
import { MatOptionModule } from "@angular/material/core";
import { ActionTabComponent } from "../../action-tab/action-tab.component";
import { ConditionsTabComponent } from "../../conditions-tab/conditions-tab.component";
import { DialogService, DialogServiceInterface } from "../../../../../services/dialog/dialog.service";
import {
  SimpleConfirmationDialogComponent,
  SimpleConfirmationDialogData
} from "../../../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { lastValueFrom } from "rxjs";
import { PolicyDescriptionComponent } from "../../action-tab/policy-description/policy-description.component";
import { PolicyTab } from "../../../policies.component";

@Component({
  selector: "app-policy-panel-edit",
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
    ActionTabComponent,
    ConditionsTabComponent,
    PolicyDescriptionComponent
  ],
  templateUrl: "./policy-panel-edit.component.html",
  styleUrl: "./policy-panel-edit.component.scss"
})
export class PolicyPanelEditComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);

  onEditModeChange = output<boolean>();
  readonly isEditMode = input.required<boolean>();
  readonly policy = input.required<PolicyDetail>();
  readonly policyEdits = input.required<Partial<PolicyDetail>>();
  readonly policyEditsChange = output<Partial<PolicyDetail>>();
  readonly currentPolicy = computed<PolicyDetail>(() => {
    // if (this.isEditMode()) {
    return { ...this.policy(), ...this.policyEdits() };
    // }
    // return this.policy();
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
  // currentPolicyHasConditions = computed(() => this.policyService.policyHasConditions(this.currentPolicy()));

  // Component State Signals
  readonly activeTab = signal<PolicyTab>("actions");
  // readonly activeTab = linkedSignal<any, PolicyTab>({
  //   source: () => ({
  //     // isEditMode: this.isEditMode(),
  //     currentPolicyHasConditions: this.currentPolicyHasConditions()
  //   }),
  //   computation: (source, previous) => {
  //     const { currentPolicyHasConditions } = source;
  //     if (currentPolicyHasConditions) {
  //       return previous?.value || "actions";
  //     }
  //     return "actions";
  //   }
  // });

  // async handleCollapse(panel: MatExpansionPanel) {
  //   if (this.isPolicyEdited() && !(await this.confirmDiscardChanges())) {
  //     panel.open();
  //     return;
  //   }
  //   // this.policyEdits.set({});
  //   this.policyEditsChange.emit({});
  //   // this.isEditMode.set(false);
  //   this.onEditModeChange.emit(false);
  // }

  onNameChange(name: string): void {
    // this.policyEdits.update((changes) => ({ ...changes, name }));
    this.policyEditsChange.emit({ ...this.policyEdits(), name });
  }

  setActiveTab(tab: PolicyTab): void {
    this.activeTab.set(tab);
    // this.onEditModeChange.emit(true);
  }

  togglePolicyActive(policy: PolicyDetail, activate: boolean) {
    if (activate) {
      this.policyService.enablePolicy(policy.name);
    } else {
      this.policyService.disablePolicy(policy.name);
    }
  }

  // Action Methods
  savePolicy(panel?: MatExpansionPanel) {
    if (!this.canSavePolicy()) return;

    this.policyService.savePolicyEdits(this.policy().name, this.policyEdits());

    // this.isEditMode.set(false);
    this.onEditModeChange.emit(false);
    // this.policyEdits.set({});
    this.policyEditsChange.emit({});
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

  async cancelEditMode() {
    if (!(await this.confirmDiscardChanges())) return;
    // this.policyEdits.set({});
    this.policyEditsChange.emit({});
    // this.isEditMode.set(false);
    this.onEditModeChange.emit(false);
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

  selectPolicyScope(scope: string) {
    this.addPolicyEdit({ scope });
  }

  updatePolicyPriority(priority: number) {
    this.addPolicyEdit({ priority });
  }
  updateActions(actions: { [actionName: string]: string }) {
    this.addPolicyEdit({ action: actions });
  }
  addPolicyEdit(edits: Partial<PolicyDetail>) {
    // this.policyEdits.update((currentChanges) => ({ ...currentChanges, ...edits }));
    this.policyEditsChange.emit({ ...this.policyEdits(), ...edits });
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
