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

import { CommonModule } from "@angular/common";
import { Component, inject, input, output, computed, Signal, signal, linkedSignal, effect } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import {
  DocumentationServiceInterface,
  DocumentationService,
  ActionDocumentation
} from "../../../../../../services/documentation/documentation.service";
import {
  PolicyServiceInterface,
  PolicyService,
  PolicyActionDetail,
  PolicyDetail
} from "../../../../../../services/policies/policies.service";
import { SelectorButtonsComponent } from "../selector-buttons/selector-buttons.component";

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
    SelectorButtonsComponent,
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
  readonly actionDocu = signal<ActionDocumentation | null>(null);

  readonly actionDocuInfo = computed<string | undefined>(() => {
    const docuList = this.actionDocu()?.info ?? null;
    return docuList?.join("\n");
  });
  readonly actionDocuNotes = computed<string | undefined>(() => {
    const notesList = this.actionDocu()?.notes ?? null;
    return notesList?.join("\n");
  });
  readonly visibleContent = linkedSignal<any, "info" | "notes" | "none">({
    source: () => ({
      docu: this.actionDocuInfo(),
      notes: this.actionDocuNotes()
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

  constructor() {
    effect(() => {
      const selectedAction = this.selectedAction();
      if (!selectedAction) {
        this.actionDocu.set(null);
        return;
      }
      this.documentationService.getPolicyActionDocumentation(this.policy().scope, selectedAction.name).then((docu) => {
        this.actionDocu.set(docu);
      });
    });
  }

  // Public Methods
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

  toggleContent(contentType: "info" | "notes") {
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
