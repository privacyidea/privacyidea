import { Component, inject, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatExpansionModule } from "@angular/material/expansion";
import { PoliciesService, PolicyDetail } from "../../services/policies/policies.service";
import { MatIconModule } from "@angular/material/icon";

@Component({
  selector: "app-policies",
  standalone: true,
  imports: [CommonModule, MatExpansionModule, MatIconModule],
  templateUrl: "./policies.component.html",
  styleUrl: "./policies.component.scss"
})
export class PoliciesComponent {
  policiesService: PoliciesService = inject(PoliciesService);
  allPoliciesList = this.policiesService.allPolicies;
  activeEditPolicy: WritableSignal<string | null> = signal(null);

  getActionsOfPolicy(policy: PolicyDetail): [string, unknown][] {
    return Object.entries(policy.action);
  }

  toggleEditMode(policyName: string): void {
    if (this.activeEditPolicy() === policyName) {
      this.activeEditPolicy.set(null);
    } else {
      this.activeEditPolicy.set(policyName);
    }
  }

  isEditMode(policyName: string): boolean {
    return this.activeEditPolicy() === policyName;
  }

  isPanelExpanded(policyName: string): boolean {
    return this.activeEditPolicy() === policyName;
  }

  deletePolicy(policyName: string): void {
    // Implement delete logic here
    console.log(`Deleting policy: ${policyName}`);
  }
}
