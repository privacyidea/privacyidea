import { Component, computed, effect, inject, linkedSignal, signal, Signal } from "@angular/core";
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
  inputIsValid: Signal<boolean> = computed(() => {
    const actionDetail = this.policyService.selectedActionDetail();
    const actionValue = this.policyService.selectedAction()?.value;
    if (actionDetail === null) return false;
    return this.policyService.actionValueIsValid(actionDetail, actionValue);
  });
  policyService = inject(PolicyService);

  documentationService: DocumentationServiceInterface = inject(DocumentationService);

  constructor() {
    effect(async () => {
      const action = this.policyService.selectedAction();
      if (!action) return [];
      const scope = this.policyService.selectedPolicyScope();
      console.log("Fetching documentation for action:", action.name, "in action:", action);
      const sectionId = action ? action.name : "";
      if (!scope || !sectionId) {
        console.warn("Cannot fetch action documentation: Missing scope or sectionId");
        this.actionDocu.set(null);
        this.actionNotes.set(null);
        return;
      }

      const result = await this.documentationService.getPolicyActionDocumentation(scope, sectionId);

      console.log("result:", result);
      if (result) {
        console.log("Found action documentation:", result);
        this.actionDocu.set(result.actionDocu);
        this.actionNotes.set(result.actionNotes);
      } else {
        console.warn("No documentation found for action:", action.name);
        this.actionDocu.set(null);
        this.actionNotes.set(null);
      }
      return;
    });
  }

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

  actionDocu = signal<string[] | null>(null);
  actionNotes = signal<string[] | null>(null);
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
