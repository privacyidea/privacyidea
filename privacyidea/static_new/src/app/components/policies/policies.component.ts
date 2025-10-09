import { Component, computed, inject, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatExpansionModule } from "@angular/material/expansion";
import { PolicyService, PolicyDetail } from "../../services/policies/policies.service";
import { MatIconModule } from "@angular/material/icon";
import { PolicyPanelComponent } from "./policy-panel/policy-panel.component";
import { HorizontalWheelComponent } from "../shared/horizontal-wheel/horizontal-wheel.component";
import { NewPolicyPanelComponent } from "./new-policy-panel/new-policy-panel.component";

@Component({
  selector: "app-policies",
  standalone: true,
  imports: [
    CommonModule,
    MatExpansionModule,
    MatIconModule,
    PolicyPanelComponent,
    HorizontalWheelComponent,
    NewPolicyPanelComponent
  ],
  templateUrl: "./policies.component.html",
  styleUrl: "./policies.component.scss"
})
export class PoliciesComponent {
  policiesService: PolicyService = inject(PolicyService);
  allPoliciesList = this.policiesService.allPolicies;
  editPolicyName = computed(() => {
    if (!this.policiesService.editModeEnabled()) return null;
    return this.policiesService.getSelectedPolicy()?.name || null;
  });

  isEditMode(policyName: string): boolean {
    return this.editPolicyName() === policyName;
  }

  getActionsOfPolicy(policy: PolicyDetail): [string, unknown][] {
    if (!policy.action) return [];
    return Object.entries(policy.action);
  }

  selectPolicy(policyName: string): void {
    if (
      this.policiesService.isPolicyEdited() &&
      !confirm("Are you sure you want to discard the changes? All changes will be lost.")
    ) {
      return;
    }
    this.policiesService.selectPolicyByName(policyName);
  }

  deselectPolicy() {
    if (
      this.policiesService.isPolicyEdited() &&
      !confirm("Are you sure you want to discard the changes? All changes will be lost.")
    ) {
      return;
    }
    this.policiesService.deselectPolicy();
  }

  enableEditMode(): void {
    this.policiesService.editModeEnabled.set(true);
  }

  savePolicy(arg0: string) {
    this.policiesService.saveSelectedPolicy();
  }

  deletePolicy(policyName: string): void {
    if (confirm(`Are you sure you want to delete the policy "${policyName}"? This action cannot be undone.`)) {
      this.policiesService.deletePolicy(policyName).then((response) => {
        console.log("Policy deleted successfully: ", response);
        this.policiesService.allPoliciesRecource.reload();
      });
    }
  }

  selectPolicyScope(scope: string) {
    this.policiesService.updateSelectedPolicy({ scope: scope });
  }

  cancelEditMode() {
    if (
      this.policiesService.isPolicyEdited() &&
      !confirm("Are you sure you want to discard the changes? All changes will be lost.")
    ) {
      return;
    }
    this.policiesService.cancelEditMode();
  }
}
