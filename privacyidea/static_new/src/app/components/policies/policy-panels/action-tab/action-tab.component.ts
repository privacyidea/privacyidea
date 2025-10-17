import { Component, inject, Input, input, signal, WritableSignal } from "@angular/core";
import { PolicyDetail, PolicyService } from "../../../../services/policies/policies.service";
import { ActionDetailComponent } from "../action-tab/action-detail/action-detail.component";
import { PolicyDescriptionComponent } from "../action-tab/policy-description/policy-description.component";
import { SelectedActionsListComponent } from "../action-tab/selected-actions-list/selected-actions-list.component";
import { ActionSelectorComponent } from "../action-tab/action-selector/action-selector.component";
import { ConditionsUserComponent } from "../conditions-tab/conditions-user/conditions-user.component";
import { ConditionsNodesComponent } from "../conditions-tab/conditions-nodes/conditions-nodes.component";
import { Tab } from "../new-policy-panel/new-policy-panel.component";

@Component({
  selector: "app-action-tab",
  standalone: true,
  imports: [SelectedActionsListComponent, PolicyDescriptionComponent, ActionSelectorComponent, ActionDetailComponent],
  templateUrl: "./action-tab.component.html",
  styleUrl: "./action-tab.component.scss"
})
export class ActionTabComponent {
  @Input({ required: true }) isEditMode!: boolean;
}
