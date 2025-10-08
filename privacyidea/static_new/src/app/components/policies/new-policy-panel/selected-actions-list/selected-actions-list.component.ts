import { Component, computed, EventEmitter, inject, Input, Output, Signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { PolicyActionDetail, PolicyService } from "../../../../services/policies/policies.service";

@Component({
  selector: "app-selected-actions-list",
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
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
  typeOfAction(actionName: string): string | null {
    return this.policyService.getDetailsOfAction(actionName)?.type ?? null;
  }
}
