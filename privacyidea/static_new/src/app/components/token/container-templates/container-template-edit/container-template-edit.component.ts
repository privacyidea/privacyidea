import { Component, computed, inject, linkedSignal, model, Signal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatCardModule } from "@angular/material/card";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatListModule } from "@angular/material/list";
import { MatTooltipModule } from "@angular/material/tooltip";
import { SelectorButtonsComponent } from "@components/policies/dialogs/edit-policy-dialog/policy-panels/edit-action-tab/selector-buttons/selector-buttons.component";

import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
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
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);

  readonly template = model<ContainerTemplate>({
    container_type: "",
    name: "",
    template_options: {
      tokens: []
    },
    default: false
  });

  readonly initTemplate: Signal<ContainerTemplate> = linkedSignal({
    source: this.template,
    computation: (template, previous) => {
      if (previous?.value) return previous.value;
      return template;
    }
  });

  readonly containerTypes = computed(() => this.containerTemplateService.availableContainerTypes());
  readonly containerTypesTitleCase = computed(() =>
    this.containerTemplateService.availableContainerTypes().map((type) => type.charAt(0).toUpperCase() + type.slice(1))
  );
  readonly availableTokenTypes = computed(() =>
    this.containerTemplateService.getTokenTypesForContainerType(this.template().container_type)
  );

  readonly tokens = computed(() => this.template().template_options.tokens);
  readonly hasToken = computed(() => this.tokens().length > 0);

  readonly nameConflict = computed(() => {
    if (this.template().name == this.initTemplate().name) {
      return false;
    }
    return this.containerTemplateService.templates().some((t) => t.name === this.template().name);
  });
  readonly canSaveTemplate = computed<boolean>(() => {
    return this.containerTemplateService.canSaveTemplate(this.template()) && !this.nameConflict();
  });
  readonly nameErrorMatcher = {
    isErrorState: () => this.nameConflict()
  };

  editTemplate(templateUpdates: Partial<ContainerTemplate>) {
    this.template.set({ ...this.template(), ...templateUpdates });
  }
}
