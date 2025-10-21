import { Component, computed, inject, signal } from "@angular/core";
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
  policyService = inject(PolicyService);

  allSectionOptions = allSectionOptions;
  allComporatorOptions = allComporatorOptions;
  allHandleMissingDataOptions = allHandleMissingDataOptions;
  additionalConditions = computed<AdditionalCondition[]>(() => {
    return this.policyService.selectedPolicy()?.conditions || [];
  });
  editIndex = signal<number | null>(null);
  isCreatingNewCondition = computed(
    () => this.editIndex() !== null && this.editIndex() === this.additionalConditions().length
  );
  conditionSection = signal<SectionOption | "">("");
  conditionKey = signal<string>("");
  conditionComparator = signal<ComporatorOption | "">("");
  conditionValue = signal<string>("");
  conditionActive = signal<boolean>(false);
  conditionHandleMissingData = signal<HandleMissigDataOption | "">("");

  initNewCondition() {
    const newIndex = -1;
    this.editIndex.set(newIndex);
    this.conditionSection.set("");
    this.conditionKey.set("");
    this.conditionComparator.set("");
    this.conditionValue.set("");
    this.conditionActive.set(false);
    this.conditionHandleMissingData.set("");
  }

  startEditCondition(condition: AdditionalCondition, index: number) {
    this.editIndex.set(index);
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
    const conditionFirstValue = this.conditionKey();
    const conditionComparator = this.conditionComparator();
    const conditionSecondValue = this.conditionValue();
    const conditionHandleMissingData = this.conditionHandleMissingData();

    if (
      conditionSection === "" ||
      conditionFirstValue === "" ||
      conditionComparator === "" ||
      conditionSecondValue === "" ||
      conditionHandleMissingData === ""
    ) {
      // Incomplete data; do not save
      return;
    }

    const updatedCondition: AdditionalCondition = [
      conditionSection,
      conditionFirstValue,
      conditionComparator,
      conditionSecondValue,
      this.conditionActive(),
      conditionHandleMissingData
    ];

    if (this.isCreatingNewCondition()) {
      this.addCondition(updatedCondition);
    } else {
      this.updateCondition(index, updatedCondition);
    }
    this.editIndex.set(null);
  }
  cancelEdit() {
    this.editIndex.set(null);
  }

  updateCondition(index: number, updated: AdditionalCondition) {
    const conditions = this.additionalConditions();
    conditions[index] = updated;
    this.policyService.updateSelectedPolicy({ conditions });
  }

  addCondition(condition: AdditionalCondition) {
    this.policyService.updateSelectedPolicy({ conditions: [...this.additionalConditions(), condition] });
  }

  removeCondition(condition: AdditionalCondition) {
    this.policyService.updateSelectedPolicy({ conditions: this.additionalConditions().filter((c) => c !== condition) });
  }

  updateAdditionalCondition(index: number, field: number, value: any) {
    const conditions = this.additionalConditions();
    const conditionToUpdate = conditions[index];
    conditionToUpdate[field] = value;
    conditions[index] = conditionToUpdate;
    this.policyService.updateSelectedPolicy({ conditions });
  }
}
