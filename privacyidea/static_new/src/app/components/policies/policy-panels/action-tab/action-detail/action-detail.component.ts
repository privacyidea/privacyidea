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

import { Component, computed, effect, inject, input, linkedSignal, output, signal, Signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import {
  PolicyActionDetail,
  PolicyDetail,
  PolicyService,
  PolicyServiceInterface
} from "../../../../../services/policies/policies.service";
import { MatInputModule } from "@angular/material/input";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatSelectModule } from "@angular/material/select";
import { SelectorButtons } from "../selector-buttons/selector-buttons.component";
import {
  DocumentationService,
  DocumentationServiceInterface
} from "../../../../../services/documentation/documentation.service";
import { MatIcon } from "@angular/material/icon";

@Component({
  selector: "app-action-detail",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatInputModule,
    MatAutocompleteModule,
    MatSelectModule,
    SelectorButtons,
    MatIcon
  ],
  templateUrl: "./action-detail.component.html",
  styleUrls: ["./action-detail.component.scss"]
})
export class ActionDetailComponent {
  // Services

  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly documentationService: DocumentationServiceInterface = inject(DocumentationService);

  // Component State

  readonly isEditMode = input.required<boolean>();
  readonly selectedAction = input.required<{ name: string; value: any } | null>();
  readonly selectedActionChange = output<{ name: string; value: any }>();
  readonly actionAdd = output<{ name: string; value: any }>();
  readonly actionsUpdate = output<{ name: string; value: any }>();

  //  PolicyActionDetail

  readonly selectedActionDetail = computed<PolicyActionDetail | null>(() => {
    const action = this.selectedAction();
    if (!action) return null;
    const details = this.policyService.getActionDetail(action.name, this.policy().scope);
    return details;
  });
  readonly policy = input.required<PolicyDetail>();

  // Computed Properties

  readonly inputIsValid: Signal<boolean> = computed(() => {
    const actionDetail = this.selectedActionDetail();
    const actionValue = this.selectedAction()?.value;
    if (actionDetail === null) return false;
    return this.policyService.actionValueIsValid(actionDetail, actionValue);
  });
  readonly actionDocuString = computed<string | undefined>(() => {
    const docuList = this.documentationService.policyActionDocumentation()?.actionDocu ?? null;
    return docuList?.join("\n");
  });
  readonly actionNotesString = computed<string | undefined>(() => {
    const notesList = this.documentationService.policyActionDocumentation()?.actionNotes ?? null;
    return notesList?.join("\n");
  });
  readonly visibleContent = linkedSignal<any, "docu" | "notes" | "none">({
    source: () => ({
      docu: this.actionDocuString(),
      notes: this.actionNotesString()
    }),
    computation: (_) => "none"
  });
  readonly selectedActionIsAlreadyAdded = computed((): boolean => {
    const selectedAction = this.selectedAction();
    if (!selectedAction) return false;
    const policy = this.policy();
    if (!policy || !policy.action) return false;
    return Object.prototype.hasOwnProperty.call(policy.action, selectedAction.name);
  });
  readonly alreadyAddedActionNames = computed(() => {
    const currentActions = this.policy()?.action;
    if (!currentActions) return [];
    return Object.keys(currentActions);
  });

  // Public Methods-
  updateSelectedActionValue(newValue: any) {
    const selectedAction = this.selectedAction();
    if (!selectedAction) return;
    this.selectedActionChange.emit({ name: selectedAction.name, value: newValue });
  }

  applyChanges() {
    if (!this.inputIsValid()) return;
    const selectedAction = this.selectedAction();
    if (!selectedAction) return;
    this.actionsUpdate.emit(selectedAction);
  }

  toggleContent(contentType: "docu" | "notes") {
    if (this.visibleContent() === contentType) {
      this.visibleContent.set("none");
    } else {
      this.visibleContent.set(contentType);
    }
  }

  addAction() {
    const selectedAction = this.selectedAction();
    if (!selectedAction) return;
    this.actionAdd.emit(selectedAction);
  }
}
