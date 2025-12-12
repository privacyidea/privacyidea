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
import { ActionTabComponent } from "../action-tab/action-tab.component";
import { ConditionsTabComponent } from "../conditions-tab/conditions-tab.component";
import { PolicyDescriptionComponent } from "../action-tab/policy-description/policy-description.component";
import { PolicyPriorityComponent } from "../action-tab/policy-priority/policy-priority.component";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelectModule } from "@angular/material/select";
import { MatOptionModule } from "@angular/material/core";
import { FilterValueGeneric } from "../../../../core/models/filter_value_generic/filter_value_generic";

type PolicyTab = "actions" | "conditions";

@Component({
  selector: "app-policy-panel-new",
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
    ActionTabComponent,
    ConditionsTabComponent,
    PolicyDescriptionComponent,
    PolicyPriorityComponent,
    MatFormFieldModule,
    MatSelectModule,
    MatOptionModule
  ],
  templateUrl: "./policy-panel-new.component.html",
  styleUrl: "./policy-panel-new.component.scss"
})
export class PolicyPanelNewComponent {
  // Angular Inputs and Services
  // readonly policyService: PolicyService = inject(PolicyService);

  // Component State Signals

  readonly newPolicy = signal<PolicyDetail>(inject(PolicyService).getEmptyPolicy());
  readonly activeTab = linkedSignal<any, PolicyTab>({
    source: () => ({
      selectedPolicyHasConditions: inject(PolicyService).policyHasConditions(this.newPolicy())
    }),
    computation: (source, previous) => {
      const { isEditMode, selectedPolicyHasConditions } = source;
      if (isEditMode || selectedPolicyHasConditions) {
        return previous?.value || "actions";
      }
      return "actions";
    }
  });

  // Event Handlers
  handleExpansion() {
    this.newPolicy.set(inject(PolicyService).getEmptyPolicy());
  }

  handleCollapse(panel: MatExpansionPanel) {
    if (this.policyService.isPolicyEdited()) {
      if (confirm("Are you sure you want to discard the new policy? All changes will be lost.")) {
        this.policyService.deselectNewPolicy();
      } else {
        panel.open(); // Re-open if user cancels
      }
    } else {
      this.policyService.deselectNewPolicy();
    }
  }

  onNameChange(name: string): void {
    this.policyService.updateSelectedPolicy({ name: name });
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

    this.policyService.savePolicyEditsAsNew();
    this.policyService.deselectPolicy(this.newPolicyName());

    if (panel) panel.close();
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
    this.policyService.cancelEditMode();
  }

  resetPolicy(panel: MatExpansionPanel) {
    if (this.policyService.isPolicyEdited()) {
      if (confirm("Are you sure you want to discard the new policy? All changes will be lost.")) {
        this.policyService.deselectPolicy(this.newPolicyName());

        panel.close();
      }
    } else {
      this.policyService.deselectPolicy(this.newPolicyName());

      panel.close();
    }
  }

  // State-checking Methods
  canSavePolicy(): boolean {
    return this.policyService.canSaveSelectedPolicy();
  }

  confirmDiscardChanges(): boolean {
    if (
      this.policyService.isPolicyEdited() &&
      !confirm("Are you sure you want to discard the changes? All changes will be lost.")
    ) {
      return false;
    }
    return true;
  }

  policyIsSelected(policyName: string = ""): boolean {
    const selectedPolicy = this.policyService.selectedPolicyOriginal();
    return selectedPolicy !== null && selectedPolicy.name === policyName;
  }

  isEditingPolicy(name: string): boolean {
    return this.policyService.selectedPolicyOriginal()?.name === name;
  }

  // Policy Manipulation Methods
  selectPolicyScope(scope: string) {
    this.policyService.updateSelectedPolicy({ scope: scope });
  }

  policyHas;
}
