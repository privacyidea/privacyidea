import { Component, computed, inject, input, Input, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { FormsModule } from "@angular/forms";
import {
  AdditionalCondition,
  allComporatorOptions,
  allHandleMissingDataOptions,
  allSectionOptions,
  ComporatorOption,
  HandleMissigDataOption,
  PolicyService,
  SectionOption
} from "../../../../../services/policies/policies.service";
import { MatButtonModule, MatIconButton } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";

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
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatIconButton
  ],
  templateUrl: "./conditions-additional.component.html",
  styleUrls: ["./conditions-additional.component.scss"]
})
export class ConditionsAdditionalComponent {
  isEditMode = input.required<boolean>();
  showAddConditionForm = signal(false);
  policyService = inject(PolicyService);

  allSectionOptions = allSectionOptions;
  allComporatorOptions = allComporatorOptions;
  allHandleMissingDataOptions = allHandleMissingDataOptions;
  additionalConditions = computed<AdditionalCondition[]>(() => {
    return this.policyService.selectedPolicy()?.conditions || [];
  });
  editIndex = signal<number | null>(null);

  // For editing existing condition
  conditionSection = signal<SectionOption | "">("");
  conditionKey = signal<string>("");
  conditionComparator = signal<ComporatorOption | "">("");
  conditionValue = signal<string>("");
  conditionActive = signal<boolean>(false);
  conditionHandleMissingData = signal<HandleMissigDataOption | "">("");

  // For adding new condition
  newConditionSection = signal<SectionOption | "">("");
  newConditionKey = signal<string>("");
  newConditionComparator = signal<ComporatorOption | "">("");
  newConditionValue = signal<string>("");
  newConditionActive = signal<boolean>(false);
  newConditionHandleMissingData = signal<HandleMissigDataOption | "">("");

  startEditCondition(condition: AdditionalCondition, index: number) {
    if (!this.isEditMode) return;
    this.editIndex.set(index);
    // When starting to edit, copy the values to the editing signals
    this.conditionSection.set(condition[0]);
    this.conditionKey.set(condition[1]);
    this.conditionComparator.set(condition[2]);
    this.conditionValue.set(condition[3]);
    this.conditionActive.set(condition[4]);
    this.conditionHandleMissingData.set(condition[5]);
  }

  saveEditedCondition() {
    const index = this.editIndex();
    if (index === null) return;

    const conditionSection = this.conditionSection();
    if (conditionSection === "") return;
    const conditionComparator = this.conditionComparator();
    if (conditionComparator === "") return;
    const conditionHandleMissingData = this.conditionHandleMissingData();
    if (conditionHandleMissingData === "") return;

    const updatedCondition: AdditionalCondition = [
      conditionSection,
      this.conditionKey(),
      conditionComparator,
      this.conditionValue(),
      this.conditionActive(),
      conditionHandleMissingData
    ];

    // Basic validation
    if (updatedCondition.some((v) => v === "")) {
      return;
    }

    this.updateCondition(index, updatedCondition);
    this.editIndex.set(null);
  }

  saveNewCondition() {
    const newConditionSection = this.newConditionSection();
    if (newConditionSection === "") return;
    const newConditionComparator = this.newConditionComparator();
    if (newConditionComparator === "") return;
    const newConditionHandleMissingData = this.newConditionHandleMissingData();
    if (newConditionHandleMissingData === "") return;

    const newCondition: AdditionalCondition = [
      newConditionSection,
      this.newConditionKey(),
      newConditionComparator,
      this.newConditionValue(),
      this.newConditionActive(),
      newConditionHandleMissingData
    ];

    if (newCondition.some((v) => v === "")) {
      return; // Or show some error
    }

    this.addCondition(newCondition);

    this.showAddConditionForm.set(false);

    // Reset form
    this.newConditionSection.set("");
    this.newConditionKey.set("");
    this.newConditionComparator.set("");
    this.newConditionValue.set("");
    this.newConditionActive.set(false);
    this.newConditionHandleMissingData.set("");
  }

  cancelEdit() {
    this.editIndex.set(null);
  }

  updateCondition(index: number, updated: AdditionalCondition) {
    const conditions = [...this.additionalConditions()];
    conditions[index] = updated;
    this.policyService.updateSelectedPolicy({ conditions });
  }

  addCondition(condition: AdditionalCondition) {
    this.policyService.updateSelectedPolicy({ conditions: [...this.additionalConditions(), condition] });
  }

  removeCondition(index: number) {
    this.policyService.updateSelectedPolicy({
      conditions: this.additionalConditions().filter((_, i) => i !== index)
    });
    // If we remove the row we are editing, we should cancel the edit mode
    if (this.editIndex() === index) {
      this.editIndex.set(null);
    }
  }
}
