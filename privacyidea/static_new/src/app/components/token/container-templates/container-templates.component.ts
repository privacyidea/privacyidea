import { Component, inject } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { ContainerTemplateEditComponent } from "./container-template-edit/container-template-edit.component";
import { ContainerTemplateService } from "../../../services/container-template/container-template.service";
import { ContainerTemplateNewComponent } from "./container-template-new/container-template-new.component";

@Component({
  selector: "app-container-templates",
  standalone: true,
  imports: [
    CommonModule,
    MatExpansionModule,
    MatIconModule,
    ContainerTemplateEditComponent,
    ContainerTemplateNewComponent
  ],
  templateUrl: "./container-templates.component.html",
  styleUrl: "./container-templates.component.scss"
})
export class ContainerTemplatesComponent {
  containerTemplateService: ContainerTemplateService = inject(ContainerTemplateService);
}
