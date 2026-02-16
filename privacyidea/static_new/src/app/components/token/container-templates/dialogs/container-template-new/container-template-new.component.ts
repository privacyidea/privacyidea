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
import { Component, inject, signal, linkedSignal, computed } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatCardModule } from "@angular/material/card";
import { MatChipsModule } from "@angular/material/chips";
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
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);
  readonly isEditMode = signal<boolean>(false);
  readonly newTemplate = linkedSignal<any, ContainerTemplate>({
    source: () => ({
      emptyContainerTemplate: this.containerTemplateService.emptyContainerTemplate,
      isEditMode: this.isEditMode(),
      containerType: this.containerTemplateService.availableContainerTypes()[0] ?? ""
    }),
    computation: (source) => deepCopy({ ...source.emptyContainerTemplate, container_type: source.containerType })
  });

  readonly isTemplateEdited = computed(() => {
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

  canSaveTemplate(): boolean {
    return this.containerTemplateService.canSaveTemplate(this.newTemplate());
  }

  // Action Methods
  saveTemplate(panel?: MatExpansionPanel) {
    if (!this.canSaveTemplate()) return;
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

  onTypeChange(newType: ContainerTypeOption) {
    this._editTemplate({ container_type: newType });
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
