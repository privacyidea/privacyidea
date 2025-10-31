import { Component, computed, inject, input, Input, linkedSignal, signal, WritableSignal } from "@angular/core";
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
import { MatSlideToggleModule } from "@angular/material/slide-toggle";

import { MatDividerModule } from "@angular/material/divider";

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
    MatIconButton,
    MatSlideToggleModule,
    MatDividerModule
  ],
  templateUrl: "./conditions-additional.component.html",
  styleUrls: ["./conditions-additional.component.scss"]
})
export class ConditionsAdditionalComponent {
  showAddConditionForm = signal(false);
  policyService = inject(PolicyService);
  isEditMode = this.policyService.isEditMode;

  allSectionOptions = allSectionOptions;
  allComporatorOptions = allComporatorOptions;
  allHandleMissingDataOptions = allHandleMissingDataOptions;
  additionalConditions = computed<AdditionalCondition[]>(() => {
    return this.policyService.selectedPolicy()?.conditions || [];
  });
  editIndex = signal<number | null>(null);

  conditionSection = linkedSignal<boolean, SectionOption | "">({
    source: () => this.isEditMode(),
    computation: () => ""
  });
  conditionKey = linkedSignal<boolean, string>({
    source: () => this.isEditMode(),
    computation: () => ""
  });
  conditionComparator = linkedSignal<boolean, ComporatorOption | "">({
    source: () => this.isEditMode(),
    computation: () => ""
  });
  conditionValue = linkedSignal<boolean, string>({
    source: () => this.isEditMode(),
    computation: () => ""
  });
  conditionActive = linkedSignal<boolean, boolean>({
    source: () => this.isEditMode(),
    computation: () => false
  });
  conditionHandleMissingData = linkedSignal<boolean, HandleMissigDataOption | "">({
    source: () => this.isEditMode(),
    computation: () => ""
  });

  startEditCondition(condition: AdditionalCondition, index: number) {
    if (!this.isEditMode) return;
    this.editIndex.set(index);
    this.showAddConditionForm.set(true);

    // When starting to edit, copy the values to the editing signals
    this.conditionSection.set(condition[0]);
    this.conditionKey.set(condition[1]);
    this.conditionComparator.set(condition[2]);
    this.conditionValue.set(condition[3]);
    this.conditionActive.set(!condition[4]); // Inverted
    this.conditionHandleMissingData.set(condition[5]);
  }

  saveCondition() {
    const conditionSection = this.conditionSection();
    if (conditionSection === "") return;
    const conditionComparator = this.conditionComparator();
    if (conditionComparator === "") return;
    const conditionHandleMissingData = this.conditionHandleMissingData();
    if (conditionHandleMissingData === "") return;

    const condition: AdditionalCondition = [
      conditionSection,
      this.conditionKey(),
      conditionComparator,
      this.conditionValue(),
      this.conditionActive(),
      conditionHandleMissingData
    ];

    if (condition.some((v) => v === "")) {
      return;
    }

    const index = this.editIndex();
    if (index !== null) {
      this.updateCondition(index, condition);
    } else {
      this.addCondition(condition);
    }

    this.cancelEdit();
  }

  cancelEdit() {
    this.editIndex.set(null);
    this.showAddConditionForm.set(false);
    // Reset form
    this.conditionSection.set("");
    this.conditionKey.set("");
    this.conditionComparator.set("");
    this.conditionValue.set("");
    this.conditionActive.set(false);
    this.conditionHandleMissingData.set("");
  }

  updateActiveState(index: number, active: boolean) {
    const condition = this.additionalConditions()[index];
    if (!condition) return;

    const updatedCondition: AdditionalCondition = [...condition];
    updatedCondition[4] = !active; // Store as negate

    this.updateCondition(index, updatedCondition);

    // if we are currently editing this condition, update the signal for the form
    if (this.editIndex() === index) {
      this.conditionActive.set(active);
    }
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
