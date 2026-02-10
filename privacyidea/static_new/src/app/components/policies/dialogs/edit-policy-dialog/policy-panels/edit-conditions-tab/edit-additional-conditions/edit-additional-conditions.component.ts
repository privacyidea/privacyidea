/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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

import { Component, computed, inject, output, signal, linkedSignal, input } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { FormsModule } from "@angular/forms";
import { MatButtonModule, MatIconButton } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { MatDividerModule } from "@angular/material/divider";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import {
  PolicyService,
  PolicyDetail,
  SECTION_OPTIONS,
  COMPARATOR_OPTIONS,
  HANDLE_MISSING_DATA_OPTIONS,
  SectionOptionKey,
  ComparatorOptionKey,
  HandleMissingDataOptionKey,
  AdditionalCondition
} from "../../../../../../../services/policies/policies.service";

@Component({
  selector: "app-edit-additional-conditions",
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
    MatDividerModule,
    MatAutocompleteModule
  ],
  templateUrl: "./edit-additional-conditions.component.html",
  styleUrls: ["./edit-additional-conditions.component.scss"]
})
export class EditAdditionalConditionsComponent {
  readonly policyService: PolicyService = inject(PolicyService);

  // Inputs/Outputs
  readonly policy = input.required<PolicyDetail>();
  readonly policyEdit = output<Partial<PolicyDetail>>();

  // UI State
  readonly showAddConditionForm = signal(false);
  readonly editIndex = signal<number | null>(null);

  // Constants
  readonly SECTION_OPTIONS = SECTION_OPTIONS;
  readonly COMPARATOR_OPTIONS = COMPARATOR_OPTIONS;
  readonly HANDLE_MISSING_DATA_OPTIONS = HANDLE_MISSING_DATA_OPTIONS;

  // Form Signals - Typed using the provided keys
  readonly conditionSection = linkedSignal<boolean, SectionOptionKey | "">({
    source: () => true,
    computation: () => ""
  });
  readonly conditionKey = linkedSignal<boolean, string>({ source: () => true, computation: () => "" });
  readonly conditionComparator = linkedSignal<boolean, ComparatorOptionKey | "">({
    source: () => true,
    computation: () => ""
  });
  readonly conditionValue = linkedSignal<boolean, string>({ source: () => true, computation: () => "" });
  readonly conditionActive = linkedSignal<boolean, boolean>({ source: () => true, computation: () => true });
  readonly conditionHandleMissingData = linkedSignal<boolean, HandleMissingDataOptionKey | "">({
    source: () => true,
    computation: () => "condition_is_false"
  });

  readonly additionalConditions = computed<AdditionalCondition[]>(() => this.policy().conditions || []);

  startEditCondition(condition: AdditionalCondition, index: number) {
    this.editIndex.set(index);
    this.showAddConditionForm.set(true);

    this.conditionSection.set(condition[0]);
    this.conditionKey.set(condition[1]);
    this.conditionComparator.set(condition[2]);
    this.conditionValue.set(condition[3]);
    this.conditionActive.set(!condition[4]);
    this.conditionHandleMissingData.set(condition[5]);
  }

  saveCondition() {
    const section = this.conditionSection();
    const comparator = this.conditionComparator();
    const missingData = this.conditionHandleMissingData();
    const key = this.conditionKey().trim();

    if (!section || !comparator || !missingData || !key) return;

    const condition: AdditionalCondition = [
      section,
      key,
      comparator,
      this.conditionValue(),
      !this.conditionActive(),
      missingData
    ];

    const currentConditions = [...this.additionalConditions()];
    const index = this.editIndex();

    if (index !== null) {
      currentConditions[index] = condition;
    } else {
      currentConditions.push(condition);
    }

    this.policyEdit.emit({ conditions: currentConditions });
    this.cancelEdit();
  }

  cancelEdit() {
    this.editIndex.set(null);
    this.showAddConditionForm.set(false);
    this.conditionSection.set("");
    this.conditionKey.set("");
    this.conditionComparator.set("");
    this.conditionValue.set("");
    this.conditionActive.set(true);
    this.conditionHandleMissingData.set("condition_is_false");
  }

  updateActiveState(index: number, active: boolean) {
    const conditions = [...this.additionalConditions()];
    if (!conditions[index]) return;

    conditions[index] = [...conditions[index]];
    conditions[index][4] = !active;

    this.policyEdit.emit({ conditions });

    if (this.editIndex() === index) {
      this.conditionActive.set(active);
    }
  }

  removeCondition(index: number) {
    const conditions = this.additionalConditions().filter((_, i) => i !== index);
    this.policyEdit.emit({ conditions });
    if (this.editIndex() === index) this.cancelEdit();
  }

  getSectionLabel(key: SectionOptionKey): string {
    return SECTION_OPTIONS.find((o) => o.key === key)?.label ?? key;
  }

  getComparatorLabel(key: ComparatorOptionKey): string {
    return COMPARATOR_OPTIONS.find((o) => o.key === key)?.label ?? key;
  }

  getMissingDataLabel(key: HandleMissingDataOptionKey): string {
    return HANDLE_MISSING_DATA_OPTIONS.find((o) => o.key === key)?.label ?? key;
  }
}
