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

import { Component, computed, inject, input, linkedSignal, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { FormsModule } from "@angular/forms";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { PolicyDetail, PolicyService } from "../../../../services/policies/policies.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelectModule } from "@angular/material/select";
import { MatOptionModule } from "@angular/material/core";
import { PolicyPriorityComponent } from "../action-tab/policy-priority/policy-priority.component";
import { PolicyDescriptionComponent } from "../action-tab/policy-description/policy-description.component";
import { ActionTabComponent } from "../action-tab/action-tab.component";
import { ConditionsTabComponent } from "../conditions-tab/conditions-tab.component";

type PolicyTab = "actions" | "conditions";

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
    PolicyPriorityComponent,
    PolicyDescriptionComponent,
    ActionTabComponent,
    ConditionsTabComponent
  ],
  templateUrl: "./policy-panel-edit.component.html",
  styleUrl: "./policy-panel-edit.component.scss"
})
export class PolicyPanelEditComponent {
  // Angular Inputs and Services
  readonly isEditMode = signal<boolean>(false);
  readonly policyService: PolicyService = inject(PolicyService);
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
  currentPolicyHasConditions = computed(() => this.policyService.policyHasConditions(this.currentPolicy()));

  // Component State Signals
  readonly activeTab = linkedSignal<any, PolicyTab>({
    source: () => ({
      isEditMode: this.isEditMode(),
      currentPolicyHasConditions: this.currentPolicyHasConditions()
    }),
    computation: (source, previous) => {
      const { isEditMode, currentPolicyHasConditions } = source;
      if (isEditMode || currentPolicyHasConditions) {
        return previous?.value || "actions";
      }
      return "actions";
    }
  });

  handleCollapse(panel: MatExpansionPanel) {
    if (this.isPolicyEdited() && !this.confirmDiscardChanges()) {
      panel.open();
      return;
    }
    this.policyEdits.set({});
    this.isEditMode.set(false);
  }

  onNameChange(name: string): void {
    this.policyEdits.update((changes) => ({ ...changes, name }));
  }

  setActiveTab(tab: PolicyTab): void {
    this.activeTab.set(tab);
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

    this.isEditMode.set(false);
    this.policyEdits.set({});
  }

  deletePolicy(policyName: string): void {
    if (confirm(`Are you sure you want to delete the policy "${policyName}"? This action cannot be undone.`)) {
      this.policyService.deletePolicy(policyName).then((response) => {
        this.policyService.allPoliciesRecource.reload();
      });
    }
  }

  cancelEditMode() {
    if (!this.confirmDiscardChanges()) return;
    this.policyEdits.set({});
    this.isEditMode.set(false);
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

  confirmDiscardChanges(): boolean {
    if (this.isPolicyEdited() && !confirm("Are you sure you want to discard the changes? All changes will be lost.")) {
      return false;
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
    console.log("PolicyPanelEditComponent updating actions to:", actions);
    this.addPolicyEdit({ action: actions });
  }
  addPolicyEdit(edits: Partial<PolicyDetail>) {
    console.log("PolicyPanelEditComponent onPolicyEdit called with edits:", edits);
    this.policyEdits.update((currentChanges) => ({ ...currentChanges, ...edits }));
  }
}
