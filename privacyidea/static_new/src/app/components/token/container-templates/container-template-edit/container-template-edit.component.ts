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
import {
  ContainerService,
  ContainerServiceInterface,
  ContainerTemplate
} from "../../../../services/container/container.service";
import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "../../../../services/container-template/container-template.service";
import { TemplateAddTokenDropdownComponent } from "./template-add-token-row/template-add-token-dropdown/template-add-token-dropdown.component";
import { TemplateAddTokenButtonComponent } from "./template-add-token-row/template-add-token-button/template-add-token-button.component";
import { TemplateAddedTokenRowComponent } from "./template-added-token-row/template-added-token-row.component";
import { MatTooltipModule } from "@angular/material/tooltip";

@Component({
  selector: "app-container-template-edit",
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
    TemplateAddTokenDropdownComponent,
    TemplateAddTokenButtonComponent,
    TemplateAddedTokenRowComponent
  ],
  templateUrl: "./container-template-edit.component.html",
  styleUrl: "./container-template-edit.component.scss"
})
export class ContainerTemplateEditComponent {
  isDefault(arg0?: ContainerTemplate): boolean {
    return true;
  }
  onDefaultToggle(arg0?: ContainerTemplate | undefined): void {
    throw new Error("Method not implemented.");
  }
  onDefaultChange($event?: any): void {
    throw new Error("Method not implemented.");
  }
  onTypeChange(containerType?: string): void {
    throw new Error("Method not implemented.");
  }
  // Angular Inputs and Services
  containerTemplateService: ContainerTemplateService = inject(ContainerTemplateService);
  template = input<ContainerTemplate | undefined>(undefined);
  isNew = computed(() => this.template() === undefined);

  // Component State Signals
  isEditMode = this.containerTemplateService.isEditMode;
  selectedTemplate = computed(() => this.containerTemplateService.selectedTemplate());

  // Event Handlers
  handleExpansion(panel: MatExpansionPanel, templateName: string | undefined) {
    if (this.containerTemplateService.templateIsSelected(templateName)) {
      return;
    }
    if (this.isNew()) {
      this.containerTemplateService.initializeNewTemplate();
      this.isEditMode.set(true);
    } else if (templateName) {
      this.containerTemplateService.selectTemplateByName(templateName);
      this.isEditMode.set(false);
    }
  }

  handleCollapse(panel: MatExpansionPanel, templateName: string | undefined) {
    if (!this.containerTemplateService.templateIsSelected(templateName)) {
      return;
    }
    if (this.isNew()) {
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
    } else if (templateName) {
      if (!this.confirmDiscardChanges()) {
        panel.open();
        return;
      }
      this.containerTemplateService.deselectTemplate(templateName);
      this.isEditMode.set(false);
    }
  }

  onNameChange(name: string): void {
    this.containerTemplateService.updateSelectedTemplate({ name: name });
  }

  // Action Methods
  saveTemplate(panel?: MatExpansionPanel) {
    if (!this.canSaveTemplate()) return;
    if (this.isNew()) {
      this.containerTemplateService.saveTemplateEditsAsNew();
      this.isEditMode.set(false);
    } else {
      this.containerTemplateService.saveTemplateEdits();
    }
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
    console.log("isNew:", this.isNew());
    if (this.isNew()) this.containerTemplateService.deselectNewTemplate();
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
