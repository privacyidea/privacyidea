import { Component, inject, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatExpansionModule } from "@angular/material/expansion";
import { PoliciesService, PolicyDetail } from "../../services/policies/policies.service";
import { MatIconModule } from "@angular/material/icon";
import { PolicyPanelComponent } from "./policy-panel/policy-panel.component";
import { HorizontalWheelComponent } from "../shared/horizontal-wheel/horizontal-wheel.component";
import { c } from "../../../../node_modules/@angular/cdk/a11y-module.d-9287508d";

@Component({
  selector: "app-policies",
  standalone: true,
  imports: [CommonModule, MatExpansionModule, MatIconModule, PolicyPanelComponent, HorizontalWheelComponent, c],
  templateUrl: "./policies.component.html",
  styleUrl: "./policies.component.scss"
})
export class PoliciesComponent {
  policiesService: PoliciesService = inject(PoliciesService);
  allPoliciesList = this.policiesService.allPolicies;
  isEditMode = signal(false);

  getActionsOfPolicy(policy: PolicyDetail): [string, unknown][] {
    return Object.entries(policy.action);
  }

  activateEditMode(): void {
    this.isEditMode.set(true);
  }

  savePolicy(arg0: string) {
    console.log(`Saving policy: ${arg0}`);
    this.isEditMode.set(false);
  }

  deletePolicy(policyName: string): void {
    // Implement delete logic here
    console.log(`Deleting policy: ${policyName}`);
  }
  onSelect(policy: PolicyDetail, scope: string) {
    throw new Error("Method not implemented.");
  }
}
