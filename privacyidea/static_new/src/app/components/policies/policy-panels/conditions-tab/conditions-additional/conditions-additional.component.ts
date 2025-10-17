import { Component, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { FormsModule } from "@angular/forms";

type SectionOptions =
  | "HTTP Environment"
  | "HTTP Request Header"
  | "Requst Data"
  | "container"
  | "container_info"
  | "token"
  | "tokeninfo"
  | "userinfo";

type ComporatorOptions =
  | "!contains"
  | "!date_within_last"
  | "!equals"
  | "!in"
  | "!matches"
  | "!string_contains"
  | "<"
  | ">"
  | "contains"
  | "date_after"
  | "date_before"
  | "date_within_last"
  | "equals"
  | "in"
  | "matches"
  | "string_contains";

type HandleMissigDataOptions = "raise_error" | "condition_is_false" | "condition_is_true";

// Mock data for policy condition definitions
const mockPolicyConditionDefs = [
  { name: "condition1", type: "string", desc: "A simple string condition" },
  { name: "condition2", type: "number", desc: "A number condition" },
  { name: "condition3", type: "boolean", desc: "A boolean condition" },
  { name: "condition4", type: "select", options: ["option1", "option2", "option3"], desc: "A select condition" }
];

@Component({
  selector: "app-conditions-additional",
  standalone: true,
  imports: [
    CommonModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    FormsModule
  ],
  templateUrl: "./conditions-additional.component.html",
  styleUrls: ["./conditions-additional.component.scss"]
})
export class ConditionsAdditionalComponent {
  policyConditionDefs = signal<any[]>([]);
  conditions = signal<{ [key: string]: any }>({});

  constructor() {
    // In a real implementation, this would be fetched from a service
    this.policyConditionDefs.set(mockPolicyConditionDefs);
  }

  updateCondition(name: string, value: any) {
    this.conditions.update((c) => ({ ...c, [name]: value }));
  }
}
