import { Component, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { FormsModule } from "@angular/forms";
import { AdditionalCondition } from "../../../../../services/policies/policies.service";

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
  additionalConditions = signal<AdditionalCondition[]>([]);

  updateCondition(index: number, updated: AdditionalCondition) {
    const conditions = this.additionalConditions();
    conditions[index] = updated;
    this.additionalConditions.set([...conditions]);
  }

  addCondition(condition: AdditionalCondition) {
    this.additionalConditions.set([...this.additionalConditions(), condition]);
  }

  removeCondition(condition: AdditionalCondition) {
    this.additionalConditions.set(this.additionalConditions().filter((cond) => cond !== condition));
  }
}
