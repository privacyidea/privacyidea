import { Component, computed, inject, input } from "@angular/core";
import { AddedActionsListComponent } from "../../dialogs/edit-policy-dialog/policy-panels/edit-action-tab/added-actions-list/added-actions-list.component";
import { PolicyService, PolicyServiceInterface } from "../../../../services/policies/policies.service";

@Component({
  selector: "app-view-action-column",
  standalone: true,
  templateUrl: "./view-action-column.component.html",
  styleUrl: "./view-action-column.component.scss"
})
export class PoliciesViewActionColumnComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);

  readonly actions = input.required<{ [actionName: string]: any }>();
  readonly actionsList = computed(() =>
    Object.entries(this.actions()).map(([name, value]) => ({ name: name, value: value }))
  );

  // Type Checking Methods
  isBooleanAction(actionName: string): boolean {
    return this.policyService.getDetailsOfAction(actionName)?.type === "bool";
  }
}
