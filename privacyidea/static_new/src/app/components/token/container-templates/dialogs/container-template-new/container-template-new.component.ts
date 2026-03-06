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
import { Component, inject, linkedSignal, computed } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatCardModule } from "@angular/material/card";
import { MatChipsModule } from "@angular/material/chips";
import { MatOptionModule } from "@angular/material/core";
import { MatExpansionModule } from "@angular/material/expansion";
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
import { TemplateAddedTokenRowComponent } from "../template-added-token-row/template-added-token-row.component";
import { ContainerTemplateAddTokenChipsComponent } from "../container-template-add-token-chips/container-template-add-token-chips.component";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { MatListModule } from "@angular/material/list";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { SelectorButtonsComponent } from "@components/policies/dialogs/edit-policy-dialog/policy-panels/edit-action-tab/selector-buttons/selector-buttons.component";

type ContainerTemplateNewComponentData = {
  // Define any data you want to pass to the dialog here, e.g.:
  // existingTemplate?: ContainerTemplate;
};

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
    MatChipsModule,
    MatListModule,
    DialogWrapperComponent,
    MatCheckboxModule,
    SelectorButtonsComponent
  ],
  templateUrl: "./container-template-new.component.html",
  styleUrl: "./container-template-new.component.scss"
})
export class ContainerTemplateNewComponent extends AbstractDialogComponent<
  ContainerTemplateNewComponentData,
  ContainerTemplate
> {
  setContainerType($event: string | undefined) {
    throw new Error("Method not implemented.");
  }
  // Angular Inputs and Services
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);
  readonly isEditMode = this.data ? true : false;
  readonly newTemplate = linkedSignal<any, ContainerTemplate>({
    source: () => ({
      emptyContainerTemplate: this.containerTemplateService.emptyContainerTemplate,
      containerType: this.containerTemplateService.availableContainerTypes()[0] ?? ""
    }),
    computation: (source) => deepCopy({ ...source.emptyContainerTemplate, container_type: source.containerType })
  });

  readonly isTemplateEdited = computed(() => {
    // Dont compare container type, only everything else
    return (
      JSON.stringify({ ...this.newTemplate(), container_type: "" }) !==
      JSON.stringify({
        ...this.containerTemplateService.emptyContainerTemplate,
        container_type: ""
      })
    );
  });

  readonly tokens = computed(() => this.newTemplate().template_options.tokens);
  readonly options = computed(() => this.newTemplate().template_options.options);

  readonly containerTypes = computed(() => this.containerTemplateService.availableContainerTypes());

  canSaveTemplate(): boolean {
    return this.containerTemplateService.canSaveTemplate(this.newTemplate());
  }

  // Action Methods
  saveTemplate() {
    if (!this.canSaveTemplate()) return;
    this.containerTemplateService.postTemplateEdits(this.newTemplate());
  }

  deleteTemplate(templateName: string): void {
    if (confirm(`Are you sure you want to delete the template "${templateName}"? This action cannot be undone.`)) {
      this.containerTemplateService.deleteTemplate(templateName);
    }
  }

  cancelEditMode() {
    if (!this.confirmDiscardChanges()) return;
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

  onTypeChange(newType: string | undefined) {
    this._editTemplate({ container_type: newType });
  }

  onDefaultToggle(): void {
    this._editTemplate({ default: !this.newTemplate().default });
    return;
  }

  onEditToken(patch: Partial<any>, index: number) {
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
    const updatedTokens = this.newTemplate().template_options.tokens.filter((_, i) => i !== index);
    this._editTemplate({
      template_options: {
        ...this.newTemplate().template_options,
        tokens: updatedTokens
      }
    });
  }

  _editTemplate(templateUpdates: Partial<ContainerTemplate>) {
    this.newTemplate.set({ ...this.newTemplate(), ...templateUpdates });
  }

  closeDialog() {
    super.close(this.newTemplate());
  }
}
