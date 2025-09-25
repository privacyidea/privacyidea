import { Component, inject, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatExpansionModule } from "@angular/material/expansion";
import { PoliciesService, PolicyDetail } from "../../services/policies/policies.service";
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
  policiesService: PoliciesService = inject(PoliciesService);
  allPoliciesList = this.policiesService.allPolicies;
  editPolicyName: WritableSignal<string | null> = signal(null);

  isEditMode(policyName: string): boolean {
    return this.editPolicyName() === policyName;
  }

  getActionsOfPolicy(policy: PolicyDetail): [string, unknown][] {
    return Object.entries(policy.action);
  }

  activateEditMode(policyName: string): void {
    this.editPolicyName.set(policyName);
  }

  savePolicy(arg0: string) {
    console.log(`Saving policy: ${arg0}`);
    this.editPolicyName.set(null);
  }

  deletePolicy(policyName: string): void {
    // Implement delete logic here
    console.log(`Deleting policy: ${policyName}`);
  }
  onSelect(policy: PolicyDetail, scope: string) {
    console.log(`Selected policy: ${policy.name} with scope: ${scope}`);
    // Implement selection logic here
  }
}
