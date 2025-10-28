import { Component, inject, Input, input, linkedSignal, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { FormsModule } from "@angular/forms";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { PolicyDetail, PolicyService } from "../../../../services/policies/policies.service";
import { HorizontalWheelComponent } from "../../../shared/horizontal-wheel/horizontal-wheel.component";
import { ActionTabComponent } from "../action-tab/action-tab.component";
import { ConditionsTabComponent } from "../conditions-tab/conditions-tab.component";
import { PolicyDescriptionComponent } from "../action-tab/policy-description/policy-description.component";
import { PolicyPriorityComponent } from "../action-tab/policy-priority/policy-priority.component";

type PolicyTab = "actions" | "conditions";

@Component({
  selector: "app-policy-panel",
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatButtonToggleModule,
    FormsModule,
    MatExpansionModule,
    HorizontalWheelComponent,
    MatSlideToggleModule,
    ActionTabComponent,
    ConditionsTabComponent,
    PolicyDescriptionComponent,
    PolicyPriorityComponent
  ],
  templateUrl: "./policy-panel.component.html",
  styleUrl: "./policy-panel.component.scss"
})
export class PolicyPanelComponent {
  togglePolicyActive(policy: PolicyDetail, activate: boolean) {
    if (activate) {
      this.policyService.enablePolicy(policy.name);
    } else {
      this.policyService.disablePolicy(policy.name);
    }
  }

  canSavePolicy(): boolean {
    const policy = this.policyService.selectedPolicy();
    if (!policy) return false;
    if (!policy.name || policy.name.trim() === "") return false;
    if (!this.policyService.isPolicyEdited()) return false;
    const allPolicies = this.policyService.allPolicies();
    const originalName = this.policyService.selectedPolicyOriginal()?.name;
    if (allPolicies.some((p) => p.name === policy.name && (originalName === undefined || p.name !== originalName))) {
      return false;
    }
    return true;
  }
  isEditMode = input.required<boolean>();
  policy = input.required<PolicyDetail>();

  activeTab: WritableSignal<PolicyTab> = linkedSignal<
    {
      selectedPolicyHasConditions: boolean;
      isEditMode: boolean;
    },
    PolicyTab
  >({
    source: () => ({
      selectedPolicyHasConditions: this.policyService.selectedPolicyHasConditions(),
      isEditMode: this.isEditMode()
    }),
    computation: (source, previous) => {
      const { selectedPolicyHasConditions, isEditMode } = source;
      if (isEditMode) return previous?.value || "actions";
      if (selectedPolicyHasConditions === true) return previous?.value || "actions";
      return "actions";
    }
  });

  policyService: PolicyService = inject(PolicyService);

  confirmDiscardChanges(): boolean {
    if (
      this.policyService.isPolicyEdited() &&
      this.policyService.viewMode() !== "view" &&
      !confirm("Are you sure you want to discard the changes? All changes will be lost.")
    ) {
      return false;
    }
    return true;
  }

  cancelEditMode() {
    if (!this.confirmDiscardChanges()) return;
    this.policyService.cancelEditMode();
  }

  deletePolicy(policyName: string): void {
    if (confirm(`Are you sure you want to delete the policy "${policyName}"? This action cannot be undone.`)) {
      this.policyService.deletePolicy(policyName).then((response) => {
        this.policyService.allPoliciesRecource.reload();
      });
    }
  }

  deselectPolicy(name: string): void {
    if (!this.confirmDiscardChanges()) return;
    this.policyService.deselectPolicy(name);
  }

  enableEditMode(editMode: "edit" | "new"): void {
    this.policyService.viewMode.set(editMode);
  }

  isEditingPolicy(name: string): boolean {
    return this.isEditMode() && this.policyService.selectedPolicyOriginal()?.name === name;
  }

  savePolicy() {
    this.policyService.savePolicyEdits();
  }

  selectPolicy(policyName: string): void {
    if (!this.confirmDiscardChanges()) return;
    this.policyService.selectPolicyByName(policyName);
  }

  selectPolicyScope(scope: string) {
    this.policyService.updateSelectedPolicy({ scope: scope });
  }

  setActiveTab(tab: PolicyTab): void {
    this.activeTab.set(tab);
  }

  onNameChange(name: string): void {
    this.policyService.updateSelectedPolicy({ name: name });
  }
}
