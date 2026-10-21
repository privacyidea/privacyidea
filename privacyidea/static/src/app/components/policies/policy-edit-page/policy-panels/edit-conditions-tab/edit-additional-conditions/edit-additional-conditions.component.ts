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

import { Component, computed, inject, input, output, signal } from "@angular/core";

import { form, FormField, required } from "@angular/forms/signals";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButtonModule, MatIconButton } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatDividerModule } from "@angular/material/divider";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import {
  AdditionalCondition,
  COMPARATOR_OPTIONS,
  ComparatorOptionKey,
  HANDLE_MISSING_DATA_OPTIONS,
  HandleMissingDataOptionKey,
  PolicyDetail,
  PolicyService,
  SECTION_OPTIONS,
  SectionOptionKey
} from "@services/policies/policies.service";
import { ERR, requiredNonBlank } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";

/** The fields of the condition form. `""` stands for an option that is not chosen yet. */
interface ConditionModel {
  section: SectionOptionKey | "";
  key: string;
  comparator: ComparatorOptionKey | "";
  value: string;
  active: boolean;
  handleMissingData: HandleMissingDataOptionKey | "";
}

const emptyCondition = (): ConditionModel => ({
  section: "",
  key: "",
  comparator: "",
  value: "",
  active: true,
  handleMissingData: "condition_is_false"
});

@Component({
  selector: "app-edit-additional-conditions",
  standalone: true,
  imports: [
    FormField,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
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
  readonly TOKEN_KEYS = [
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

  readonly CONTAINER_KEYS = [
    "type",
    "serial",
    "description",
    "last_authentication",
    "last_synchronization",
    "states",
    "info",
    "realms",
    "users",
    "tokens",
    "templates"
  ];

  readonly policyService = inject(PolicyService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);

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

  protected readonly ERR = ERR;
  protected readonly hasError = hasError;

  readonly condition = signal<ConditionModel>(emptyCondition());
  readonly conditionForm = form(this.condition, (f) => {
    required(f.section);
    required(f.comparator);
    required(f.handleMissingData);
    requiredNonBlank(f.key);
  });

  readonly availableKeys = computed<string[]>(() => {
    const { section, key: currentKey } = this.condition();
    if (section === "token") {
      return this.TOKEN_KEYS.filter((key) => key.includes(currentKey));
    } else if (section === "container") {
      return this.CONTAINER_KEYS.filter((key) => key.includes(currentKey));
    }
    return [];
  });

  readonly additionalConditions = computed<AdditionalCondition[]>(() => this.policy().conditions || []);

  readonly canSaveCondition = computed(() => this.conditionForm().valid());

  /** The open form holds input that was typed or chosen since it was opened or loaded. */
  readonly isFormDirty = computed(() => this.showAddConditionForm() && this.conditionForm().dirty());

  startEditCondition(condition: AdditionalCondition, index: number) {
    this.editIndex.set(index);
    this.showAddConditionForm.set(true);
    this._loadForm({
      section: condition[0],
      key: condition[1],
      comparator: condition[2],
      value: condition[3],
      active: condition[4],
      handleMissingData: condition[5]
    });
  }

  saveCondition() {
    if (!this.canSaveCondition()) return;

    const { section, key, comparator, value, active, handleMissingData } = this.condition();
    const condition: AdditionalCondition = [
      section as SectionOptionKey,
      key.trim(),
      comparator as ComparatorOptionKey,
      value,
      active,
      handleMissingData as HandleMissingDataOptionKey
    ];

    const currentConditions = [...this.additionalConditions()];
    const index = this.editIndex();

    if (index !== null) {
      currentConditions[index] = condition;
    } else {
      currentConditions.push(condition);
    }

    this.policyEdit.emit({ conditions: currentConditions });
    this._resetForm();
  }

  cancelEdit() {
    if (!this.isFormDirty()) {
      this._resetForm();
      return;
    }
    this.dialogService
      .openDialog({
        component: SaveAndExitDialogComponent,
        data: {
          title: $localize`:@@common.discardChanges:Discard changes`,
          allowSaveExit: this.canSaveCondition(),
          saveExitDisabled: !this.canSaveCondition()
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result === "save-exit") {
            if (!this.canSaveCondition()) return;
            this.saveCondition();
          } else if (result === "discard") {
            this._resetForm();
          }
        }
      });
  }

  private _resetForm() {
    this.editIndex.set(null);
    this.showAddConditionForm.set(false);
    this._loadForm(emptyCondition());
  }

  /** Fills the form with `values` and leaves it untouched and unmodified. */
  private _loadForm(values: ConditionModel) {
    this.condition.set(values);
    this.conditionForm().reset();
  }

  updateActiveState(index: number, active: boolean) {
    const conditions = [...this.additionalConditions()];
    if (!conditions[index]) return;

    conditions[index] = [...conditions[index]];
    conditions[index][4] = active;

    this.policyEdit.emit({ conditions });

    if (this.editIndex() === index) {
      this.condition.update((condition) => ({ ...condition, active }));
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
