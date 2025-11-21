import { Component, computed, inject, input, linkedSignal, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { FormsModule } from "@angular/forms";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelectModule } from "@angular/material/select";
import { MatOptionModule } from "@angular/material/core";
import { MatTooltipModule } from "@angular/material/tooltip";
import { TemplateAddedTokenRowComponent } from "../template-added-token-row/template-added-token-row.component";
import { TemplateAddTokenRowComponent } from "../template-add-token-row/template-add-token-row.component";
import { ContainerTemplate, ContainerTemplateToken } from "../../../../services/container/container.service";
import { ContainerTemplateService } from "../../../../services/container-template/container-template.service";
import { deepCopy } from "../../../../utils/deep-copy.utils";
import { ContainerTemplateAddTokenChipsComponent } from "../container-template-add-token-chips/container-template-add-token-chips.component";
import { MatChipsModule } from "@angular/material/chips";

@Component({
  selector: "app-container-template-new",
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    FormsModule,
    MatExpansionModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatSelectModule,
    MatOptionModule,
    TemplateAddedTokenRowComponent,

    ContainerTemplateAddTokenChipsComponent,
    MatChipsModule
  ],
  templateUrl: "./container-template-new.component.html",
  styleUrl: "./container-template-new.component.scss"
})
export class ContainerTemplateNewComponent {
  // Angular Inputs and Services
  protected readonly containerTemplateService: ContainerTemplateService = inject(ContainerTemplateService);
  protected readonly isEditMode = signal<boolean>(false);
  protected readonly newTemplate = linkedSignal<any, ContainerTemplate>({
    source: () => ({
      emptyContainerTemplate: this.containerTemplateService.emptyContainerTemplate,
      isEditMode: this.isEditMode(),
      containerType: this.containerTemplateService.availableContainerTypes()[0] ?? ""
    }),
    computation: (source) => deepCopy({ ...source.emptyContainerTemplate, container_type: source.containerType })
  });

  protected readonly isTemplateEdited = computed(() => {
    if (!this.isEditMode()) return false;
    // Dont compare container type, only everything else
    return (
      JSON.stringify({ ...this.newTemplate(), container_type: "" }) !==
      JSON.stringify({
        ...this.containerTemplateService.emptyContainerTemplate,
        container_type: ""
      })
    );
  });

  // Event Handlers
  handleExpansion() {
    this.isEditMode.set(true);
  }

  handleCollapse(panel: MatExpansionPanel) {
    if (!this.confirmDiscardChanges()) {
      panel.open();
      return;
    }
    this.isEditMode.set(false);
  }

  // Action Methods
  async saveTemplate(panel?: MatExpansionPanel) {
    if (!this.containerTemplateService.canSaveTemplate()) return;
    this.containerTemplateService.postTemplateEdits(this.newTemplate());
    this.isEditMode.set(false);
    if (panel) panel.close();
  }

  deleteTemplate(templateName: string): void {
    if (confirm(`Are you sure you want to delete the template "${templateName}"? This action cannot be undone.`)) {
      this.containerTemplateService.deleteTemplate(templateName);
    }
  }

  cancelEditMode() {
    if (!this.confirmDiscardChanges()) return;
    this.isEditMode.set(false);
  }

  confirmDiscardChanges(): boolean {
    if (
      this.isTemplateEdited() &&
      !confirm("Are you sure you want to discard the changes? All changes will be lost.")
    ) {
      return false;
    }
    return true;
  }

  onNameChange(newName: string) {
    this._editTemplate({ name: newName });
  }

  onTypeChange(newType: string) {
    this._editTemplate({ container_type: newType });
  }

  onDefaultChange(newDefault: boolean) {
    this._editTemplate({ default: newDefault });
  }
  onDefaultToggle(): void {
    this._editTemplate({ default: !this.newTemplate().default });
    return;
  }

  onEditToken(patch: Partial<any>, index: number) {
    if (!this.isEditMode()) return;
    const updatedTokens = this.newTemplate().template_options.tokens.map((token, i) =>
      i === index ? { ...token, ...patch } : token
    );
    this._editTemplate({
      template_options: {
        ...this.newTemplate().template_options,
        tokens: updatedTokens
      }
    });
  }
  onAddToken(tokenType: string) {
    if (!this.isEditMode()) return;
    const containerTemplateToken: any = {
      type: tokenType
    };
    const updatedTokens = [...this.newTemplate().template_options.tokens, containerTemplateToken];
    this._editTemplate({
      template_options: {
        ...this.newTemplate().template_options,
        tokens: updatedTokens
      }
    });
  }
  onDeleteToken(index: number) {
    if (!this.isEditMode()) return;
    const updatedTokens = this.newTemplate().template_options.tokens.filter((_, i) => i !== index);
    this._editTemplate({
      template_options: {
        ...this.newTemplate().template_options,
        tokens: updatedTokens
      }
    });
  }

  _editTemplate(templateUpdates: Partial<ContainerTemplate>) {
    if (!this.isEditMode()) return;
    this.newTemplate.set({ ...this.newTemplate(), ...templateUpdates });
  }
}
