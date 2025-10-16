import { Component, computed, inject, Signal } from "@angular/core";
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
  actions: Signal<{ name: string; value: string }[]> = computed(() => {
    const policy = this.policyService.selectedPolicy();
    if (!policy || !policy.action) return [];
    return Object.entries(policy.action).map(([name, value]) => ({ name: name, value }));
  });
  parseBooleanValue = parseBooleanValue;
  policyService = inject(PolicyService);

  editModeEnabled(): boolean {
    return this.policyService.viewMode() === "edit" || this.policyService.viewMode() === "new";
  }

  isBooleanAction(actionName: string): boolean {
    return this.policyService.getDetailsOfAction(actionName)?.type === "bool";
  }

  onActionClick(action: { name: string; value: string }) {
    if (!this.editModeEnabled()) return;
    if (this.isBooleanAction(action.name)) return;
    if (this.policyService.viewMode()) {
      this.policyService.selectedAction.set(action);
    }
  }

  onToggleChange(actionName: string, newValue: boolean): void {
    this.policyService.updateActionValue(actionName, newValue);
  }
}
