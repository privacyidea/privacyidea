import { Component, input } from "@angular/core";
import { ContainerTemplate } from "../../../../services/container/container.service";
import { MatButton } from "@angular/material/button";

@Component({
  selector: "app-container-templates-table-actions",
  standalone: true,
  templateUrl: "./container-templates-table-actions.component.html",
  styleUrl: "./container-templates-table-actions.component.scss",
  imports: [MatButton]
})
export class ContainerTemplatesTableActionsComponent {
  readonly selectedContainerTemplates = input.required<ContainerTemplate[]>();
}
