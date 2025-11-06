import { Component, computed, inject, Input, input, linkedSignal, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { FormsModule } from "@angular/forms";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
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
  // Angular Inputs and Services
  policyService: PolicyService = inject(PolicyService);
  isNew = input<boolean>(false);
  policy = input<PolicyDetail | undefined>(undefined);

  // Component State Signals
  isEditMode = this.policyService.isEditMode;
  selectedPolicy = computed<PolicyDetail | null>(() => this.policyService.selectedPolicy());
  activeTab = linkedSignal<any, PolicyTab>({
    source: () => ({
      isEditMode: this.isEditMode(),
      selectedPolicyHasConditions: this.policyService.selectedPolicyHasConditions()
    }),
    computation: (source, previous) => {
      const { isEditMode, selectedPolicyHasConditions } = source;
      if (isEditMode || selectedPolicyHasConditions) {
        return previous?.value || "actions";
      }
      return "actions";
    }
  });

  // Computed properties for new policies
  newPolicyName = computed(() => {
    if (!this.isNew()) return "";
    if (this.policyService.selectedPolicyOriginal()?.name) return "";
    return this.policyService.selectedPolicyOriginal()?.name || "";
  });

  newPolicyScope = computed(() => {
    if (!this.isNew()) return "";
    if (this.policyService.selectedPolicyOriginal()?.name) return "";
    return this.policyService.selectedPolicy()?.scope || "";
  });

  // Event Handlers
  handleExpansion(panel: MatExpansionPanel, policyName: string | undefined) {
    console.log("handleExpansion called");
    if (this.policyIsSelected(policyName)) {
      console.log("Policy (" + policyName + ") is already selected, cancelling handleExpansion.");
      return;
    }
    if (this.isNew()) {
      console.log("Initializing new policy");
      this.policyService.initializeNewPolicy();
      this.isEditMode.set(true);
    } else if (policyName) {
      this.policyService.selectPolicyByName(policyName);
      this.isEditMode.set(false);
    }
    console.log("handleExpansion completed");
  }

  handleCollapse(panel: MatExpansionPanel, policyName: string | undefined) {
    console.log("handleCollapse called");
    if (!this.policyIsSelected(policyName)) {
      return;
    }
    if (this.isNew()) {
      if (this.policyService.isPolicyEdited()) {
        if (confirm("Are you sure you want to discard the new policy? All changes will be lost.")) {
          this.policyService.deselectNewPolicy();
          this.isEditMode.set(false);
        } else {
          panel.open(); // Re-open if user cancels
        }
      } else {
        this.policyService.deselectNewPolicy();
        this.isEditMode.set(false);
      }
    } else if (policyName) {
      if (!this.confirmDiscardChanges()) {
        panel.open();
        return;
      }
      this.policyService.deselectPolicy(policyName);
      this.isEditMode.set(false);
    }
    console.log("handleCollapse completed");
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
    if (this.isNew()) {
      this.policyService.savePolicyEdits({ asNew: true });
      this.policyService.deselectPolicy(this.newPolicyName());
      this.isEditMode.set(false);
    } else {
      this.policyService.savePolicyEdits();
    }
    this.isEditMode.set(false);
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
    this.isEditMode.set(false);
  }

  resetPolicy(panel: MatExpansionPanel) {
    if (this.policyService.isPolicyEdited()) {
      if (confirm("Are you sure you want to discard the new policy? All changes will be lost.")) {
        this.policyService.deselectPolicy(this.newPolicyName());
        this.isEditMode.set(false);
        panel.close();
      }
    } else {
      this.policyService.deselectPolicy(this.newPolicyName());
      this.isEditMode.set(false);
      panel.close();
    }
  }

  // State-checking Methods
  canSavePolicy(): boolean {
    if (this.isNew()) {
      return this.policyService.canSaveSelectedPolicy();
    }
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
    return this.isEditMode() && this.policyService.selectedPolicyOriginal()?.name === name;
  }

  // Policy Manipulation Methods
  selectPolicyScope(scope: string) {
    this.policyService.updateSelectedPolicy({ scope: scope });
  }
}
