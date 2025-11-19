import { Component, computed, inject, input } from "@angular/core";
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
import { ContainerTemplate } from "../../../../services/container/container.service";
import { ContainerTemplateService } from "../../../../services/container-template/container-template.service";

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
    TemplateAddTokenRowComponent
  ],
  templateUrl: "./container-template-new.component.html",
  styleUrl: "./container-template-new.component.scss"
})
export class ContainerTemplateNewComponent {
  isDefault(arg0?: ContainerTemplate): boolean {
    return true;
  }
  onDefaultToggle(toggleTemplate?: ContainerTemplate): void {
    if (toggleTemplate) {
      this.containerTemplateService.setDefaultTemplate(toggleTemplate!, !toggleTemplate!.default);
    } else {
      const isDefault = this.selectedTemplate()?.default ?? true;
      this.containerTemplateService.updateSelectedTemplate({ default: !isDefault });
    }
  }
  onTypeChange(containerType?: string): void {
    this.containerTemplateService.updateSelectedTemplate({ container_type: containerType ?? "" });
  }
  // Angular Inputs and Services
  containerTemplateService: ContainerTemplateService = inject(ContainerTemplateService);
  template = input<ContainerTemplate | undefined>(undefined);

  // Component State Signals
  isEditMode = this.containerTemplateService.isEditMode;
  selectedTemplate = computed(() => this.containerTemplateService.selectedTemplate());

  // Event Handlers
  handleExpansion(panel: MatExpansionPanel) {
    this.containerTemplateService.initializeNewTemplate();
    this.isEditMode.set(true);
  }

  handleCollapse(panel: MatExpansionPanel) {
    if (!this.containerTemplateService.templateIsSelected(undefined)) {
      return;
    }
    if (this.containerTemplateService.isTemplateEdited()) {
      if (confirm("Are you sure you want to discard the new template? All changes will be lost.")) {
        this.containerTemplateService.deselectNewTemplate();
        this.isEditMode.set(false);
      } else {
        panel.open(); // Re-open if user cancels
      }
    } else {
      this.containerTemplateService.deselectNewTemplate();
      this.isEditMode.set(false);
    }
  }

  onNameChange(name: string): void {
    this.containerTemplateService.updateSelectedTemplate({ name: name });
  }

  // Action Methods
  saveTemplate(panel?: MatExpansionPanel) {
    if (!this.canSaveTemplate()) return;
    this.containerTemplateService.saveTemplateEditsAsNew();
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
    this.containerTemplateService.cancelEditMode();
    this.containerTemplateService.deselectNewTemplate();
  }

  // State-checking Methods
  canSaveTemplate(): boolean {
    // Simplified for now
    // TODO: Add more validation checks
    return true;
  }

  confirmDiscardChanges(): boolean {
    if (
      this.containerTemplateService.isTemplateEdited() &&
      !confirm("Are you sure you want to discard the changes? All changes will be lost.")
    ) {
      return false;
    }
    return true;
  }
}
