import { Component, computed, inject, input, Signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { parseBooleanValue } from "../../../../../utils/parse-boolean-value";

@Component({
  selector: "app-selected-actions-list",
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatSlideToggleModule],
  templateUrl: "./selected-actions-list.component.html",
  styleUrl: "./selected-actions-list.component.scss"
})
export class SelectedActionsListComponent {
  actions = input.required<{ name: string; value: string }[]>();
  parseBooleanValue = parseBooleanValue;
  policyService = inject(PolicyService);

  isEditMode = input.required<boolean>();

  isBooleanAction(actionName: string): boolean {
    return this.policyService.getDetailsOfAction(actionName)?.type === "bool";
  }

  onActionClick(action: { name: string; value: string }) {
    if (this.isBooleanAction(action.name)) return;
    if (this.isEditMode()) {
      this.policyService.selectedAction.set(action);
    }
  }

  onToggleChange(actionName: string, newValue: boolean): void {
    this.policyService.updateActionValue(actionName, newValue);
  }
}
