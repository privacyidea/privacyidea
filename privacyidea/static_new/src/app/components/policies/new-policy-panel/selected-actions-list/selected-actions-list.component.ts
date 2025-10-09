import { Component, computed, inject, Signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { PolicyService } from "../../../../services/policies/policies.service";
import { parseBooleanValue } from "../../../../utils/parse-boolean-value";

@Component({
  selector: "app-selected-actions-list",
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatSlideToggleModule],
  templateUrl: "./selected-actions-list.component.html",
  styleUrls: ["./selected-actions-list.component.scss"]
})
export class SelectedActionsListComponent {
  policyService = inject(PolicyService);
  actions: Signal<{ name: string; value: string }[]> = computed(() => {
    // this.policyService.selectedPolicy()?.action ?? [];
    const policy = this.policyService._selectedPolicy();
    if (!policy || !policy.action) return [];
    return Object.entries(policy.action).map(([name, value]) => ({ name: name, value }));
  });
  onActionClick(action: { name: string; value: string }) {
    if (this.isBooleanAction(action.name)) return;
    if (this.policyService.editModeEnabled()) {
      this.policyService.selectedAction.set(action);
    }
  }

  isBooleanAction(actionName: string): boolean {
    return this.policyService.getDetailsOfAction(actionName)?.type === "bool";
  }
  onToggleChange(actionName: string, newValue: boolean): void {
    this.policyService.updateActionValue(actionName, newValue);
  }
  parseBooleanValue = parseBooleanValue;
}
