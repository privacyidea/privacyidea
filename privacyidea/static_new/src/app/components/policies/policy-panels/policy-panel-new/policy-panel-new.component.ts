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

import { Component, computed, inject, input, linkedSignal, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { FormsModule } from "@angular/forms";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { PolicyDetail, PolicyService, PolicyServiceInterface } from "../../../../services/policies/policies.service";
import { ActionTabComponent } from "../action-tab/action-tab.component";
import { ConditionsTabComponent } from "../conditions-tab/conditions-tab.component";
import { PolicyDescriptionComponent } from "../action-tab/policy-description/policy-description.component";
import { PolicyPriorityComponent } from "../action-tab/policy-priority/policy-priority.component";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelectModule } from "@angular/material/select";
import { MatOptionModule } from "@angular/material/core";
import { FilterValueGeneric } from "../../../../core/models/filter_value_generic/filter_value_generic";
import { empty } from "rxjs";

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
  readonly policyService: PolicyService = inject(PolicyService);

  // Component State Signals
  readonly newPolicy: WritableSignal<PolicyDetail> = linkedSignal({
    source: () => ({
      emptyPolicy: this.policyService.getEmptyPolicy(),
      availableScopes: this.policyService.allPolicyScopes()
    }),
    computation: (source, previous) => {
      const { emptyPolicy, availableScopes } = source;
      if (previous?.value && previous.value !== emptyPolicy) {
        return previous.value;
      }
      if (availableScopes.length > 0) {
        return { ...emptyPolicy, scope: availableScopes[0] };
      }
      return emptyPolicy;
    }
  });

  readonly activeTab = linkedSignal<any, PolicyTab>({
    source: () => ({
      selectedPolicyHasConditions: this.policyService.policyHasConditions(this.newPolicy())
    }),
    computation: (source, previous) => {
      const { isEditMode, selectedPolicyHasConditions } = source;
      if (isEditMode || selectedPolicyHasConditions) {
        return previous?.value || "actions";
      }
      return "actions";
    }
  });

  isPolicyEdited = computed(() => {
    return this.policyService.isPolicyEdited(this.newPolicy(), this.policyService.getEmptyPolicy());
  });

  private _resetNewPolicy(): void {
    const emptyPolicy = this.policyService.getEmptyPolicy();
    const availableScopes = this.policyService.allPolicyScopes();
    if (availableScopes.length > 0) {
      this.newPolicy.set({ ...emptyPolicy, scope: availableScopes[0] });
    } else {
      this.newPolicy.set(emptyPolicy);
    }
  }

  // Event Handlers
  handleExpansion() {
    this._resetNewPolicy();
  }

  handleCollapse(panel: MatExpansionPanel) {
    if (this.resetPolicy()) {
      panel.close();
    } else {
      panel.open();
    }
  }

  onPriorityChange(priority: number): void {
    this.newPolicy.set({ ...this.newPolicy(), priority: priority });
  }

  onNameChange(name: string): void {
    this.newPolicy.set({ ...this.newPolicy(), name: name });
  }

  setActiveTab(tab: PolicyTab): void {
    this.activeTab.set(tab);
  }

  // Action Methods
  async savePolicy(panel?: MatExpansionPanel) {
    if (!this.canSavePolicy()) return;
    try {
      await this.policyService.saveNewPolicy(this.newPolicy());
    } catch (error) {
      return;
    }
    this._resetNewPolicy();
    if (panel) panel.close();
  }

  cancelEditMode() {
    if (!this.confirmDiscardChanges()) return;
    this._resetNewPolicy();
  }

  resetPolicy(): boolean {
    if (this.isPolicyEdited()) {
      if (confirm("Are you sure you want to discard the new policy? All changes will be lost.")) {
        this._resetNewPolicy();
        return true;
      }
    } else {
      this._resetNewPolicy();
      return true;
    }
    return false;
  }

  // State-checking Methods
  canSavePolicy(): boolean {
    return this.policyService.canSavePolicy(this.newPolicy());
  }

  confirmDiscardChanges(): boolean {
    if (this.isPolicyEdited() && !confirm("Are you sure you want to discard the changes? All changes will be lost.")) {
      return false;
    }
    return true;
  }

  // Policy Manipulation Methods
  selectPolicyScope(scope: string) {
    this.newPolicy.set({ ...this.newPolicy(), scope: scope });
    // this.policyService.selectedPolicyScope.set(scope);
  }

  policyHasActions(): boolean {
    return this.policyService.policyHasActions(this.newPolicy());
  }

  policyHasConditions(): boolean {
    return this.policyService.policyHasConditions(this.newPolicy());
  }

  onPolicyChange(policy: PolicyDetail) {
    this.newPolicy.set(policy);
  }
}
