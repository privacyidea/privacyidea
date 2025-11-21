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
import { ContainerTemplate, ContainerTemplateToken } from "../../../../services/container/container.service";
import { ContainerTemplateService } from "../../../../services/container-template/container-template.service";
import { TemplateAddedTokenRowComponent } from "../template-added-token-row/template-added-token-row.component";
import { MatTooltipModule } from "@angular/material/tooltip";
import { deepCopy } from "../../../../utils/deep-copy.utils";
import { ContainerTemplateAddTokenChipsComponent } from "../container-template-add-token-chips/container-template-add-token-chips.component";

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
    TemplateAddedTokenRowComponent,
    ContainerTemplateAddTokenChipsComponent
  ],
  templateUrl: "./container-template-edit.component.html",
  styleUrl: "./container-template-edit.component.scss"
})
export class ContainerTemplateEditComponent {
  // Angular Inputs and Services
  readonly templateOriginal = input.required<ContainerTemplate>();
  protected readonly containerTemplateService: ContainerTemplateService = inject(ContainerTemplateService);
  protected readonly templateEdited = linkedSignal({
    source: () => ({
      templateOrigianl: this.templateOriginal(),
      isEditMode: this.isEditMode()
    }),
    computation: (source) => {
      return deepCopy(source.templateOrigianl);
    }
  });
  protected readonly isEditMode = signal<boolean>(false);
  protected readonly currentTemplate = computed(() =>
    this.isEditMode() ? this.templateEdited() : this.templateOriginal()
  );

  protected readonly isTemplateEdited = computed(() => {
    if (!this.isEditMode()) return false;
    return JSON.stringify(this.templateOriginal()) !== JSON.stringify(this.templateEdited());
  });

  handleCollapse(panel: MatExpansionPanel) {
    if (!this._confirmDiscardChanges()) {
      panel.open();
      return;
    }
    this.isEditMode.set(false);
  }

  // Action Methods
  async saveTemplate() {
    if (!this.containerTemplateService.canSaveTemplate()) return;
    this.containerTemplateService.postTemplateEdits(this.templateEdited());
    this.isEditMode.set(false);
  }

  deleteTemplate(templateName: string): void {
    if (confirm(`Are you sure you want to delete the template "${templateName}"? This action cannot be undone.`)) {
      this.containerTemplateService.deleteTemplate(templateName);
    }
  }

  cancelEditMode() {
    if (!this._confirmDiscardChanges()) return;
    this.isEditMode.set(false);
  }

  private _confirmDiscardChanges(): boolean {
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

  onDefaultChange(): void {
    this._editTemplate({ default: !this.currentTemplate().default });
  }

  onAddToken(tokenType: string) {
    if (!this.isEditMode()) return;
    const containerTemplateToken: ContainerTemplateToken = {
      type: tokenType,
      genkey: false,
      hashlib: "",
      otplen: 6,
      timeStep: 0,
      user: false
    };
    const updatedTokens = [...this.templateEdited().template_options.tokens, containerTemplateToken];
    this._editTemplate({
      template_options: {
        ...this.templateEdited().template_options,
        tokens: updatedTokens
      }
    });
  }

  onEditToken(patch: Partial<ContainerTemplateToken>, index: number) {
    if (!this.isEditMode()) return;
    const updatedTokens = this.templateEdited().template_options.tokens.map((token, i) =>
      i === index ? { ...token, ...patch } : token
    );
    this._editTemplate({
      template_options: {
        ...this.templateEdited().template_options,
        tokens: updatedTokens
      }
    });
  }
  onDeleteToken(index: number) {
    if (!this.isEditMode()) return;
    const updatedTokens = this.templateEdited().template_options.tokens.filter((_, i) => i !== index);
    this._editTemplate({
      template_options: {
        ...this.templateEdited().template_options,
        tokens: updatedTokens
      }
    });
  }

  _editTemplate(template: Partial<ContainerTemplate>) {
    if (!this.isEditMode()) return;
    this.templateEdited.set({ ...this.templateEdited(), ...template });
  }
}
