import { TextFieldModule } from "@angular/cdk/text-field";
import { Component, input, output } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";

@Component({
  selector: "app-policy-name-edit",
  templateUrl: "./policy-name-edit.component.html",
  styleUrls: ["./policy-name-edit.component.scss"],
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, FormsModule, TextFieldModule]
})
export class PolicyNameEditComponent {
  policyName = input.required<string>();
  policyNameChange = output<string>();

  updatePolicyName($event: string) {
    this.policyNameChange.emit($event);
  }
}
