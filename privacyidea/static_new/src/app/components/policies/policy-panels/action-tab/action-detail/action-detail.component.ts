import { Component, computed, inject, Signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { MatInputModule } from "@angular/material/input";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatSelectModule } from "@angular/material/select";
import { BoolSelectButtonsComponent } from "../selector-buttons/selector-buttons.component";

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
    BoolSelectButtonsComponent
  ],
  templateUrl: "./action-detail.component.html",
  styleUrls: ["./action-detail.component.scss"]
})
export class ActionDetailComponent {
  inputIsValid: Signal<boolean> = computed(() => {
    const action = this.policyService.selectedActionDetail();
    const actionValue = this.policyService.selectedAction()?.value;
    if (action === null) return false;
    return this.policyService.actionValueIsValid(action, actionValue);
  });
  policyService = inject(PolicyService);

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
}
