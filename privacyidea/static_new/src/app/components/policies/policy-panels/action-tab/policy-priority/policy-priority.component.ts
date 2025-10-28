import { Component, inject } from "@angular/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { FormsModule } from "@angular/forms";
import { TextFieldModule } from "@angular/cdk/text-field";
import { PolicyService } from "../../../../../services/policies/policies.service";

@Component({
  selector: "app-policy-priority",
  templateUrl: "./policy-priority.component.html",
  styleUrls: ["./policy-priority.component.scss"],
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, FormsModule, TextFieldModule]
})
export class PolicyPriorityComponent {
  policyService = inject(PolicyService);
  updatePolicyPriority($event: any) {
    this.policyService.updateSelectedPolicy({ priority: $event });
  }
}
