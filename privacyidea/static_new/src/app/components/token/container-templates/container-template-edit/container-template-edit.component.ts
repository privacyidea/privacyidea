import { Component, inject, computed, model } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatCardModule } from "@angular/material/card";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatTooltipModule } from "@angular/material/tooltip";
import { MatInputModule } from "@angular/material/input";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatListModule } from "@angular/material/list";
import { SelectorButtonsComponent } from "@components/policies/dialogs/edit-policy-dialog/policy-panels/edit-action-tab/selector-buttons/selector-buttons.component";
import { ContainerTemplateAddTokenComponent } from "../dialogs/container-template-edit-dialog/container-template-add-token-chips/container-template-add-token.component";
import { TemplateAddedTokenRowComponent } from "../dialogs/container-template-edit-dialog/template-added-token-row/template-added-token-row.component";

import {
  ContainerTemplateServiceInterface,
  ContainerTemplateService
} from "src/app/services/container-template/container-template.service";
import { ContainerTemplate } from "src/app/services/container/container.service";
import { ContainerTemplateEditBodyComponent } from "./container-template-edit-body/container-template-edit-body.component";

@Component({
  selector: "app-container-template-edit",
  standalone: true,
  imports: [
    MatInputModule,
    MatCardModule,
    MatIconModule,
    FormsModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatListModule,
    MatCheckboxModule,
    SelectorButtonsComponent,
    ContainerTemplateEditBodyComponent
  ],
  templateUrl: "./container-template-edit.component.html",
  styleUrl: "./container-template-edit.component.scss"
})
export class ContainerTemplateEditComponent {
  // --- Services ---
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);

  // --- State Signals ---
  readonly template = model<ContainerTemplate>({
    container_type: "",
    name: "",
    template_options: {
      tokens: []
    },
    default: false
  });

  // --- Computed - General State ---
  readonly containerTypes = computed(() => this.containerTemplateService.availableContainerTypes());
  readonly containerTypesTitleCase = computed(() =>
    this.containerTemplateService.availableContainerTypes().map((type) => type.charAt(0).toUpperCase() + type.slice(1))
  );
  readonly availableTokenTypes = computed(() =>
    this.containerTemplateService.getTokenTypesForContainerType(this.template().container_type)
  );

  // --- Computed - Tokens ---
  readonly tokens = computed(() => this.template().template_options.tokens);
  readonly hasToken = computed(() => this.tokens().length > 0);

  // --- Computed - Validation & Conflict ---
  readonly nameConflict = computed(() =>
    this.containerTemplateService.templates().some((t) => t.name === this.template().name && t.name !== this.data?.name)
  );
  readonly canSaveTemplate = computed<boolean>(() => {
    return this.containerTemplateService.canSaveTemplate(this.template()) && !this.nameConflict();
  });
  readonly nameErrorMatcher = {
    isErrorState: () => this.nameConflict()
  };

  // --- Data Modification Methods ---
  editTemplate(templateUpdates: Partial<ContainerTemplate>) {
    this.template.set({ ...this.template(), ...templateUpdates });
  }

  // --- Inputs ---
  data?: ContainerTemplate;
}
