import { Component, inject, input, Input } from "@angular/core";
import { ConditionsUserComponent } from "./conditions-user/conditions-user.component";
import { ConditionsNodesComponent } from "./conditions-nodes/conditions-nodes.component";
import { ConditionsAdditionalComponent } from "./conditions-additional/conditions-additional.component";
import { PolicyService } from "../../../../services/policies/policies.service";

@Component({
  selector: "app-conditions-tab",
  standalone: true,
  imports: [ConditionsUserComponent, ConditionsNodesComponent, ConditionsAdditionalComponent],
  templateUrl: "./conditions-tab.component.html",
  styleUrl: "./conditions-tab.component.scss"
})
export class ConditionsTabComponent {
  policyService = inject(PolicyService);

  isEditMode = this.policyService.isEditMode;
}
