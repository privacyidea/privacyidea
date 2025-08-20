import { Component, ElementRef, inject, Renderer2, ViewChild } from "@angular/core";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatOption } from "@angular/material/core";
import { MatSelect } from "@angular/material/select";
import { FormsModule } from "@angular/forms";
import { MatInput } from "@angular/material/input";
import { MatCheckbox } from "@angular/material/checkbox";
import { ContainerCreateComponent } from "./container-create.component";
import { MatTooltip } from "@angular/material/tooltip";
import { NgClass } from "@angular/common";

@Component({
  selector: "app-container-create-self-service",
  imports: [
    MatButton,
    MatFormField,
    MatHint,
    MatIcon,
    MatOption,
    MatSelect,
    FormsModule,
    MatInput,
    MatLabel,
    MatCheckbox,
    MatIconButton,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelTitle,
    MatExpansionPanelHeader,
    MatTooltip,
    NgClass
  ],
  templateUrl: "./container-create.self-service.component.html",
  styleUrl: "./container-create.component.scss"
})
export class ContainerCreateSelfServiceComponent extends ContainerCreateComponent {
}
