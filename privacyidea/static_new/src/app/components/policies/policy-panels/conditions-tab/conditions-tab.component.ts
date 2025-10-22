import { Component, input, Input } from "@angular/core";
import { ConditionsUserComponent } from "./conditions-user/conditions-user.component";
import { ConditionsNodesComponent } from "./conditions-nodes/conditions-nodes.component";
import { ConditionsAdditionalComponent } from "./conditions-additional/conditions-additional.component";

@Component({
  selector: "app-conditions-tab",
  standalone: true,
  imports: [ConditionsUserComponent, ConditionsNodesComponent, ConditionsAdditionalComponent],
  templateUrl: "./conditions-tab.component.html",
  styleUrl: "./conditions-tab.component.scss"
})
export class ConditionsTabComponent {
  isEditMode = input.required<boolean>();
}
