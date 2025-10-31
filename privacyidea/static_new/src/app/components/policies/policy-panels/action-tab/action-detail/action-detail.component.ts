import { Component, computed, effect, inject, input, linkedSignal, signal, Signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { MatInputModule } from "@angular/material/input";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatSelectModule } from "@angular/material/select";
import { BoolSelectButtonsComponent } from "../selector-buttons/selector-buttons.component";
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
    BoolSelectButtonsComponent,
    MatIcon
  ],
  templateUrl: "./action-detail.component.html",
  styleUrls: ["./action-detail.component.scss"]
})
export class ActionDetailComponent {
  policyService = inject(PolicyService);
  documentationService = inject(DocumentationService);
  isEditMode = input.required<boolean>();
  inputIsValid: Signal<boolean> = computed(() => {
    const actionDetail = this.policyService.selectedActionDetail();
    const actionValue = this.policyService.selectedAction()?.value;
    if (actionDetail === null) return false;
    return this.policyService.actionValueIsValid(actionDetail, actionValue);
  });

  actionIsAlreadyAdded(): boolean {
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

  actionDocu = computed<string[] | null>(
    () => this.documentationService.policyActionDocumentation()?.actionDocu ?? null
  );
  actionNotes = computed<string[] | null>(
    () => this.documentationService.policyActionDocumentation()?.actionNotes ?? null
  );
  visibleContent = linkedSignal<any, "docu" | "notes" | "none">({
    source: () => ({
      docu: this.actionDocu(),
      notes: this.actionNotes()
    }),
    computation: (_) => "none"
  });

  toggleContent(contentType: "docu" | "notes") {
    if (this.visibleContent() === contentType) {
      this.visibleContent.set("none");
    } else {
      this.visibleContent.set(contentType);
    }
  }
}
