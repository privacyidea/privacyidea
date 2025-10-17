import { Component, Input } from "@angular/core";
import { ConditionsUserComponent } from "./conditions-user/conditions-user.component";
import { ConditionsNodesComponent } from "./conditions-nodes/conditions-nodes.component";

@Component({
  selector: "app-conditions-tab",
  standalone: true,
  imports: [ConditionsUserComponent, ConditionsNodesComponent],
  templateUrl: "./conditions-tab.component.html",
  styleUrl: "./conditions-tab.component.scss"
})
export class ConditionsTabComponent {
  @Input({ required: true }) isEditMode!: boolean;
}
