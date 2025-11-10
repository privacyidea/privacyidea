import { Component, computed, effect, inject, input, linkedSignal, signal, Signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { PolicyService } from "../../../../../services/policies/policies.service";
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
  policyService = inject(PolicyService);
  documentationService = inject(DocumentationService);

  // Component State
  isEditMode = this.policyService.isEditMode;

  // Computed Properties
  inputIsValid: Signal<boolean> = computed(() => {
    const actionDetail = this.policyService.selectedActionDetail();
    const actionValue = this.policyService.selectedAction()?.value;
    if (actionDetail === null) return false;
    return this.policyService.actionValueIsValid(actionDetail, actionValue);
  });

  actionDocuString = computed<string | undefined>(() => {
    const docuList = this.documentationService.policyActionDocumentation()?.actionDocu ?? null;
    return docuList?.join("\n");
  });

  actionNotesString = computed<string | undefined>(() => {
    const notesList = this.documentationService.policyActionDocumentation()?.actionNotes ?? null;
    return notesList?.join("\n");
  });

  visibleContent = linkedSignal<any, "docu" | "notes" | "none">({
    source: () => ({
      docu: this.actionDocuString(),
      notes: this.actionNotesString()
    }),
    computation: (_) => "none"
  });

  // Public Methods
  selectedActionIsAlreadyAdded(): boolean {
    const selectedAction = this.policyService.selectedAction();
    if (!selectedAction) return false;
    const policy = this.policyService.selectedPolicy();
    if (!policy || !policy.action) return false;
    return Object.prototype.hasOwnProperty.call(policy.action, selectedAction.name);
  }

  applyChanges() {
    if (!this.inputIsValid()) return;
    this.policyService.updateActionInSelectedPolicy();
    this.policyService.selectedAction.set(null);
  }

  toggleContent(contentType: "docu" | "notes") {
    if (this.visibleContent() === contentType) {
      this.visibleContent.set("none");
    } else {
      this.visibleContent.set(contentType);
    }
  }
}
