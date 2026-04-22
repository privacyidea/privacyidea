/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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

import { Component, inject, computed, linkedSignal, effect } from "@angular/core";

import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatCardModule } from "@angular/material/card";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatTooltipModule } from "@angular/material/tooltip";
import { MatInputModule } from "@angular/material/input";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatListModule } from "@angular/material/list";
import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "../../../../../services/container-template/container-template.service";
import { ContainerTemplate } from "../../../../../services/container/container.service";
import { deepCopy } from "../../../../../utils/deep-copy.utils";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { SelectorButtonsComponent } from "@components/policies/dialogs/edit-policy-dialog/policy-panels/edit-action-tab/selector-buttons/selector-buttons.component";
import { DialogAction } from "src/app/models/dialog";
import { ContainerTemplateAddTokenComponent } from "./container-template-add-token-chips/container-template-add-token.component";
import { TemplateAddedTokenRowComponent } from "./template-added-token-row/template-added-token-row.component";
import { PendingChangesDialogComponent } from "@components/shared/dialog/abstract-dialog/pending-changes-dialog.component";
import { TokenEnrollmentPayload } from "src/app/mappers/token-api-payload/_token-api-payload.mapper";
import { TokenTypeKey } from "src/app/services/token/token.service";
import { ROUTE_PATHS } from "../../../../../route_paths";
import { ContentService, ContentServiceInterface } from "../../../../../services/content/content.service";
import { NAVIGATION_ACCESSIBLE_DIALOG_CLASS } from "../../../../../constants/global.constants";
import { ContainerTemplateEditComponent } from "../../container-template-edit/container-template-edit.component";

/**
 * Dialog component for editing container templates. Used for both creating new templates and editing existing ones.
 * When the dialog closes with the "Save" action, the edited template is saved via the ContainerTemplateService and returned as the dialog result.
 * When the edit was cancelled, the dialog simply closes without saving, and no data is returned.
 */
@Component({
  selector: "app-container-template-edit-dialog",
  standalone: true,
  host: {
    class: NAVIGATION_ACCESSIBLE_DIALOG_CLASS
  },
  imports: [
    MatInputModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    FormsModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatListModule,
    DialogWrapperComponent,
    MatCheckboxModule,
    ContainerTemplateEditComponent
  ],
  templateUrl: "./container-template-edit-dialog.component.html",
  styleUrl: "./container-template-edit-dialog.component.scss"
})
export class ContainerTemplateEditDialogComponent extends PendingChangesDialogComponent<
  ContainerTemplate | undefined,
  ContainerTemplate
> {
  // --- Services ---
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);
  readonly contentService: ContentServiceInterface = inject(ContentService);

  // --- State Signals ---
  readonly template = linkedSignal<any, ContainerTemplate>({
    source: () => ({
      initialData: this.data ?? this.containerTemplateService.emptyContainerTemplate,
      defaultType: this.containerTemplateService.availableContainerTypes()[0] ?? ""
    }),
    computation: (source) => {
      const type = source.initialData.container_type || source.defaultType;
      return deepCopy({ ...source.initialData, container_type: type });
    }
  });

  constructor() {
    super();

    // Close dialog if user navigates away from the container templates route (after pending changes guard allows it)
    effect(() => {
      if (
        this.contentService.routeUrl() !== ROUTE_PATHS.TOKENS_CONTAINERS_TEMPLATES &&
        this.contentService.routeUrl() !== ROUTE_PATHS.TOKENS_CONTAINERS_CREATE
      ) {
        console.log(
          "Effect: Closing the ContainerTemplateEditDialogComponent due to incorrect route: ",
          this.contentService.routeUrl()
        );
        this.dialogRef?.close();
      }
    });
  }

  // --- Pending Changes Implementations ---
  override readonly canSave = computed(() => this.canSaveTemplate());
  override readonly isDirty = computed(() => {
    const current = JSON.stringify(this.template());
    const base = JSON.stringify(this.data ?? this.containerTemplateService.emptyContainerTemplate);
    return current !== base;
  });

  override async onSave(): Promise<boolean> {
    try {
      await this.onAction("save");
      return true;
    } catch {
      return false;
    }
  }

  // --- Computed - General State ---
  readonly isNewTemplate = computed(() => !this.data);

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

  // --- Computed - Dialog Actions ---
  readonly actions = computed<DialogAction<string>[]>(() => [
    {
      label: $localize`Save`,
      value: "save",
      icon: "save",
      type: "confirm",
      disabled: !this.canSaveTemplate()
    }
  ]);

  // --- Action Handling ---
  async onAction(action: string): Promise<void> {
    if (action === "save") {
      const result = await this._saveTemplate();
      if (result) {
        if (this.data && this.data.name !== this.template().name) {
          await this.containerTemplateService.deleteTemplate(this.data.name);
        }
        this.dialogRef.close(this.template());
      }
    }
  }

  // --- Private Helper Methods ---
  private async _saveTemplate(): Promise<boolean> {
    if (this.canSaveTemplate()) {
      return this.containerTemplateService.postTemplateEdits(this.template());
    }
    return false;
  }
}
