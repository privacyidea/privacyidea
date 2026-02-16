/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import { CommonModule } from "@angular/common";
import { Component, ViewEncapsulation, input, inject, linkedSignal, signal, computed } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatCardModule } from "@angular/material/card";
import { MatOptionModule } from "@angular/material/core";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatSelectModule } from "@angular/material/select";
import { MatTooltipModule } from "@angular/material/tooltip";
import {
  ContainerTemplateServiceInterface,
  ContainerTemplateService
} from "../../../../../services/container-template/container-template.service";
import { ContainerTemplate } from "../../../../../services/container/container.service";
import { deepCopy } from "../../../../../utils/deep-copy.utils";
import { ContainerTypeOption } from "../../../container-create/container-create.component";
import { TemplateAddedTokenRowComponent } from "../../template-added-token-row/template-added-token-row.component";
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
  styleUrl: "./container-template-edit.component.scss",
  encapsulation: ViewEncapsulation.ShadowDom
})
export class ContainerTemplateEditComponent {
  // Angular Inputs and Services
  readonly templateOriginal = input.required<ContainerTemplate>();
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);
  readonly templateEdited = linkedSignal({
    source: () => ({
      templateOriginal: this.templateOriginal(),
      isEditMode: this.isEditMode()
    }),
    computation: (source) => {
      return deepCopy(source.templateOriginal);
    }
  });
  readonly isEditMode = signal<boolean>(false);
  readonly currentTemplate = computed(() => (this.isEditMode() ? this.templateEdited() : this.templateOriginal()));

  readonly isTemplateEdited = computed(() => {
    if (!this.isEditMode()) return false;
    return JSON.stringify(this.templateOriginal()) !== JSON.stringify(this.templateEdited());
  });

  enableEditMode(panel: MatExpansionPanel) {
    this.isEditMode.set(true);
    panel.open();
  }

  handleCollapse(panel: MatExpansionPanel) {
    if (!this._confirmDiscardChanges()) {
      panel.open();
      return;
    }
    this.isEditMode.set(false);
  }

  canSaveTemplate(): boolean {
    return this.containerTemplateService.canSaveTemplate(this.templateEdited());
  }

  // Action Methods
  saveTemplate() {
    if (!this.canSaveTemplate()) return;
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

  onTypeChange(newType: ContainerTypeOption) {
    this._editTemplate({ container_type: newType });
  }

  onDefaultToggle(): void {
    this._editTemplate({ default: !this.currentTemplate().default });
  }

  onAddToken(tokenType: string) {
    if (!this.isEditMode()) return;
    const containerTemplateToken: any = {
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

  onEditToken(patch: Partial<any>, index: number) {
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

  getDefaultTooltip(): string {
    if (this.isEditMode()) {
      return this.templateEdited().default
        ? $localize`:@@containerTemplate.unsetAsDefaultTooltip:Unset as default template`
        : $localize`:@@containerTemplate.setAsDefaultTooltip:Set as default template`;
    } else {
      return this.currentTemplate().default
        ? $localize`:@@containerTemplate.DefaultTooltip:Default`
        : $localize`:@@containerTemplate.NonDefaultTooltip:Non-Default`;
    }
  }
}
