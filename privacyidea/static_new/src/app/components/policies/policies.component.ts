import { Component, inject } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatExpansionModule } from "@angular/material/expansion";
import { PolicyService } from "../../services/policies/policies.service";
import { MatIconModule } from "@angular/material/icon";
import { PolicyPanelComponent } from "./policy-panel/policy-panel.component";
import { NewPolicyPanelComponent } from "./new-policy-panel/new-policy-panel.component";

@Component({
  selector: "app-policies",
  standalone: true,
  imports: [CommonModule, MatExpansionModule, MatIconModule, PolicyPanelComponent, NewPolicyPanelComponent],
  templateUrl: "./policies.component.html",
  styleUrl: "./policies.component.scss"
})
export class PoliciesComponent {
  policyService: PolicyService = inject(PolicyService);
  allPoliciesList = this.policyService.allPolicies;

  isEditMode(): boolean {
    if (this.policyService.viewMode() === "new" && this.policyService.isPolicyEdited()) {
      return true;
    }
    return this.policyService.viewMode() === "edit";
  }

  isEditingPolicy(name: string): boolean {
    return this.isEditMode() && this.policyService.selectedPolicyOriginal()?.name === name;
  }
}
