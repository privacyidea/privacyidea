import { Component, computed, inject, input, Signal } from "@angular/core";
import { ActionDetailComponent } from "../action-tab/action-detail/action-detail.component";
import { SelectedActionsListComponent } from "../action-tab/selected-actions-list/selected-actions-list.component";
import { ActionSelectorComponent } from "../action-tab/action-selector/action-selector.component";
import { PolicyService } from "../../../../services/policies/policies.service";

@Component({
  selector: "app-action-tab",
  standalone: true,
  imports: [SelectedActionsListComponent, ActionSelectorComponent, ActionDetailComponent],
  templateUrl: "./action-tab.component.html",
  styleUrl: "./action-tab.component.scss"
})
export class ActionTabComponent {
  isEditMode = input.required<boolean>();
  policyService = inject(PolicyService);

  actions: Signal<{ name: string; value: string }[]> = computed(() => {
    const policy = this.policyService.selectedPolicy();
    if (!policy || !policy.action) return [];
    return Object.entries(policy.action).map(([name, value]) => ({ name: name, value }));
  });
}
