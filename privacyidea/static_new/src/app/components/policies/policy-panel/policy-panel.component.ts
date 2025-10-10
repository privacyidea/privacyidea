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
  policyService: PolicyService = inject(PolicyService);
  policy = input.required<PolicyDetail>();
  @Input({ required: true }) isEditMode!: boolean;
  activeTab: WritableSignal<Tab> = signal("actions");

  setActiveTab(tab: Tab): void {
    this.activeTab.set(tab);
  }

  isEditingPolicy(name: string): boolean {
    return this.isEditMode && this.policyService.selectedPolicy()?.name === name;
  }

  selectPolicy(policyName: string): void {
    if (
      this.policyService.isPolicyEdited() &&
      !confirm("Are you sure you want to discard the changes? All changes will be lost.")
    ) {
      return;
    }
    this.policyService.selectPolicyByName(policyName);
  }

  deselectPolicy(name: string): void {
    if (
      this.policyService.isPolicyEdited() &&
      !confirm("Are you sure you want to discard the changes? All changes will be lost.")
    ) {
      return;
    }
    this.policyService.deselectPolicy(name);
  }

  enableEditMode(editMode: "edit" | "new"): void {
    this.policyService.viewMode.set(editMode);
  }

  savePolicy(arg0: string) {
    this.policyService.saveSelectedPolicy();
  }

  deletePolicy(policyName: string): void {
    if (confirm(`Are you sure you want to delete the policy "${policyName}"? This action cannot be undone.`)) {
      this.policyService.deletePolicy(policyName).then((response) => {
        console.log("Policy deleted successfully: ", response);
        this.policyService.allPoliciesRecource.reload();
      });
    }
  }

  selectPolicyScope(scope: string) {
    this.policyService.updateSelectedPolicy({ scope: scope });
  }

  cancelEditMode() {
    if (
      this.policyService.isPolicyEdited() &&
      !confirm("Are you sure you want to discard the changes? All changes will be lost.")
    ) {
      return;
    }
    this.policyService.cancelEditMode();
  }
}
