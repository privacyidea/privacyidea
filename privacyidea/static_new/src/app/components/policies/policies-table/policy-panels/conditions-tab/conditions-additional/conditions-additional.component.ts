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
import { Component, computed, inject, input, output, signal, linkedSignal } from "@angular/core";
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
} from "../../../../../../services/policies/policies.service";
import { MatAutocompleteModule } from "@angular/material/autocomplete";

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
    MatDividerModule,
    MatAutocompleteModule
  ],
  templateUrl: "./conditions-additional.component.html",
  styleUrls: ["./conditions-additional.component.scss"]
})
export class ConditionsAdditionalComponent {
  readonly tokenKeys = [
    "id",
    "description",
    "serial",
    "tokentype",
    "info",
    "resolver",
    "user_id",
    "otplen",
    "maxfail",
    "active",
    "revoked",
    "locked",
    "failcount",
    "count",
    "count_window",
    "sync_window",
    "rollout_state"
  ];
  readonly tokenKeysFiltered = computed(() => {
    const filterString = this.conditionKey();
    return this.tokenKeys.filter((key) => key.includes(filterString));
  });

  readonly containerKeys = [
    "type",
    "serial",
    "description",
    "last_authentication",
    "last_synchronized",
    "states",
    "info",
    "internal_info_keys",
    "realms",
    "users",
    "tokens",
    "templates"
  ];
  readonly containerKeysFiltered = computed(() => {
    const filterString = this.conditionKey();
    return this.containerKeys.filter((key) => key.includes(filterString));
  });

  // Services
  policyService: PolicyService = inject(PolicyService);

  // Component State
  isEditMode = input.required<boolean>();
  policy = input.required<PolicyDetail>();
  policyEdit = output<Partial<PolicyDetail>>();

  showAddConditionForm = signal(false);
  editIndex = signal<number | null>(null);

  // Constants for Template
  SECTION_OPTIONS = SECTION_OPTIONS;
  COMPARATOR_OPTIONS = COMPARATOR_OPTIONS;
  HANDLE_MISSING_DATA_OPTIONS = HANDLE_MISSING_DATA_OPTIONS;

  // Form Signals - Now using Key types instead of Option objects
  conditionSection = linkedSignal<boolean, SectionOptionKey | "">({
    source: () => this.isEditMode(),
    computation: () => ""
  });
  conditionKey = linkedSignal<boolean, string>({ source: () => this.isEditMode(), computation: () => "" });
  conditionComparator = linkedSignal<boolean, ComparatorOptionKey | "">({
    source: () => this.isEditMode(),
    computation: () => ""
  });
  conditionValue = linkedSignal<boolean, string>({ source: () => this.isEditMode(), computation: () => "" });
  conditionActive = linkedSignal<boolean, boolean>({ source: () => this.isEditMode(), computation: () => false });
  conditionHandleMissingData = linkedSignal<boolean, HandleMissingDataOptionKey | "">({
    source: () => this.isEditMode(),
    computation: () => ""
  });
  isSelected(index: number): boolean {
    return this.editIndex() === index;
  }

  // Computed Properties
  additionalConditions = computed<AdditionalCondition[]>(() => {
    return this.policy().conditions || [];
  });

  emitEdits(edits: Partial<PolicyDetail>) {
    this.policyEdit.emit({ ...edits });
  }

  // Condition Form Management
  startEditCondition(condition: AdditionalCondition, index: number) {
    if (!this.isEditMode()) return;
    this.editIndex.set(index);
    this.showAddConditionForm.set(true);

    this.conditionSection.set(condition[0]);
    this.conditionKey.set(condition[1]);
    this.conditionComparator.set(condition[2]);
    this.conditionValue.set(condition[3]);
    this.conditionActive.set(!condition[4]); // UI expects "active", storage is "disabled"
    this.conditionHandleMissingData.set(condition[5]);
  }

  saveCondition() {
    const section = this.conditionSection();
    const comparator = this.conditionComparator();
    const missingData = this.conditionHandleMissingData();

    if (section === "" || comparator === "" || missingData === "" || this.conditionKey() === "") {
      return;
    }

    const condition: AdditionalCondition = [
      section,
      this.conditionKey(),
      comparator,
      this.conditionValue(),
      !this.conditionActive(), // Store as negated boolean (disabled)
      missingData
    ];

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
    updatedCondition[4] = !active; // Store as negated (disabled)

    this.updateCondition(index, updatedCondition);

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
    if (this.editIndex() === index) {
      this.editIndex.set(null);
    }
  }

  updateSelectedPolicy(patch: Partial<PolicyDetail>) {
    this.emitEdits({ ...patch });
  }

  // Label Helpers
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
