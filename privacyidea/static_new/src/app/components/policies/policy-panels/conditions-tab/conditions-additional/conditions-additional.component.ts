/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import { Component, computed, inject, input, Input, linkedSignal, output, signal, WritableSignal } from "@angular/core";
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
  HandleMissingDataOption,
  PolicyDetail,
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
  // Services
  policyService: PolicyService = inject(PolicyService);

  // Component State
  isEditMode = input.required<boolean>();
  policy = input.required<PolicyDetail>();
  policyEdit = output<Partial<PolicyDetail>>();
  emitEdits(edits: Partial<PolicyDetail>) {
    this.policyEdit.emit({ ...edits });
  }

  showAddConditionForm = signal(false);
  editIndex = signal<number | null>(null);

  // Form Signals
  conditionSection = linkedSignal<boolean, SectionOption | "">({
    source: () => this.isEditMode(),
    computation: () => ""
  });
  conditionKey = linkedSignal<boolean, string>({ source: () => this.isEditMode(), computation: () => "" });
  conditionComparator = linkedSignal<boolean, ComporatorOption | "">({
    source: () => this.isEditMode(),
    computation: () => ""
  });
  conditionValue = linkedSignal<boolean, string>({ source: () => this.isEditMode(), computation: () => "" });
  conditionActive = linkedSignal<boolean, boolean>({ source: () => this.isEditMode(), computation: () => false });
  conditionHandleMissingData = linkedSignal<boolean, HandleMissingDataOption | "">({
    source: () => this.isEditMode(),
    computation: () => ""
  });

  // Computed Properties
  additionalConditions = computed<AdditionalCondition[]>(() => {
    return this.policy().conditions || [];
  });

  // Constants
  allSectionOptions = allSectionOptions;
  allComporatorOptions = allComporatorOptions;
  allHandleMissingDataOptions = allHandleMissingDataOptions;

  // Condition Form Management
  startEditCondition(condition: AdditionalCondition, index: number) {
    if (!this.isEditMode) return;
    this.editIndex.set(index);
    this.showAddConditionForm.set(true);

    // When starting to edit, copy the values to the editing signals
    this.conditionSection.set(condition[0]);
    this.conditionKey.set(condition[1]);
    this.conditionComparator.set(condition[2]);
    this.conditionValue.set(condition[3]);
    this.conditionActive.set(condition[4]);
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

  // Condition State Management
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
    this.updateSelectedPolicy({ conditions });
  }

  addCondition(condition: AdditionalCondition) {
    this.updateSelectedPolicy({ conditions: [...this.additionalConditions(), condition] });
  }

  removeCondition(index: number) {
    this.updateSelectedPolicy({
      conditions: this.additionalConditions().filter((_, i) => i !== index)
    });
    // If we remove the row we are editing, we should cancel the edit mode
    if (this.editIndex() === index) {
      this.editIndex.set(null);
    }
  }

  updateSelectedPolicy(patch: Partial<PolicyDetail>) {
    this.emitEdits({ ...patch });
  }
}
