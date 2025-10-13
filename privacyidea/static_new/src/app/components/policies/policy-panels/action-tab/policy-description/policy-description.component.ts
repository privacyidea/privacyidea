import { Component, inject } from "@angular/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { FormsModule } from "@angular/forms";
import { TextFieldModule } from "@angular/cdk/text-field";
import { PolicyService } from "../../../../../services/policies/policies.service";

@Component({
  selector: "app-policy-description",
  templateUrl: "./policy-description.component.html",
  styleUrls: ["./policy-description.component.scss"],
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, FormsModule, TextFieldModule]
})
export class PolicyDescriptionComponent {
  policyService = inject(PolicyService);
  updatePolicyDescription($event: string) {
    this.policyService.updateSelectedPolicy({ description: $event });
  }
}
