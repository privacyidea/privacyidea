import { Component, inject, input } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatExpansionModule } from "@angular/material/expansion";
import { PolicyService } from "../../services/policies/policies.service";
import { MatIconModule } from "@angular/material/icon";
import { PolicyPanelComponent } from "./policy-panels/policy-panel/policy-panel.component";

@Component({
  selector: "app-policies",
  standalone: true,
  imports: [CommonModule, MatExpansionModule, MatIconModule, PolicyPanelComponent],
  templateUrl: "./policies.component.html",
  styleUrl: "./policies.component.scss"
})
export class PoliciesComponent {
  policyService: PolicyService = inject(PolicyService);
  allPoliciesList = this.policyService.allPolicies;
}
