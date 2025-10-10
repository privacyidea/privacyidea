import { Component, computed, inject, Input, input, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { PolicyDetail, PolicyService } from "../../../services/policies/policies.service";
import { FormsModule } from "@angular/forms";
import { ActionSelectorComponent } from "../new-policy-panel/action-selector/action-selector.component";
import { ActionDetailComponent } from "../new-policy-panel/action-detail/action-detail.component";
import { PolicyDescriptionComponent } from "../new-policy-panel/policy-description/policy-description.component";
import { SelectedActionsListComponent } from "../new-policy-panel/selected-actions-list/selected-actions-list.component";
import { MatExpansionModule } from "@angular/material/expansion";
import { HorizontalWheelComponent } from "../../shared/horizontal-wheel/horizontal-wheel.component";

type Tab = "actions" | "conditions";

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
    ActionSelectorComponent,
    ActionDetailComponent,
    PolicyDescriptionComponent,
    SelectedActionsListComponent,
    MatExpansionModule,
    HorizontalWheelComponent
  ],
  templateUrl: "./policy-panel.component.html",
  styleUrl: "./policy-panel.component.scss"
})
export class PolicyPanelComponent {
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
  @Input({ required: true }) isEditMode!: boolean;
  policy = input.required<PolicyDetail>();

  activeTab: WritableSignal<Tab> = signal("actions");
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
    return this.isEditMode && this.policyService.selectedPolicyOriginal()?.name === name;
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

  setActiveTab(tab: Tab): void {
    this.activeTab.set(tab);
  }

  onNameChange(name: string): void {
    this.policyService.updateSelectedPolicy({ name: name });
  }
}
