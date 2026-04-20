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

import { Component, inject, computed, linkedSignal, signal } from "@angular/core";

import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatCardModule } from "@angular/material/card";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "src/app/models/dialog";
import { deepCopy } from "../../../../../utils/deep-copy.utils";
import {
  ContainerTemplateServiceInterface,
  ContainerTemplateService
} from "../../../../../services/container-template/container-template.service";
import { ContainerTemplate } from "../../../../../services/container/container.service";
import { PendingChangesDialogComponent } from "@components/shared/dialog/abstract-dialog/pending-changes-dialog.component";

@Component({
  selector: "app-container-template-copy-dialog",
  standalone: true,
  imports: [FormsModule, MatInputModule, MatButtonModule, MatCardModule, MatFormFieldModule, DialogWrapperComponent],
  templateUrl: "./container-template-copy-dialog.component.html",
  styleUrl: "./container-template-copy-dialog.component.scss"
})
export class ContainerTemplateCopyDialogComponent extends PendingChangesDialogComponent<string, string> {
  // --- Services ---
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);

  // --- State Signals ---
  readonly isNameDirty = signal(false);
  readonly template = linkedSignal<string, ContainerTemplate>({
    source: () => this.data,
    computation: (name) => {
      const original = this.containerTemplateService.templates().find((t) => t.name === name);
      return deepCopy({
        ...(original ?? this.containerTemplateService.emptyContainerTemplate),
        name: name,
        default: false
      });
    }
  });

  // --- Computed & Matchers ---
  readonly actions = computed<DialogAction<string>[]>(() => [
    {
      label: $localize`Copy Template`,
      value: "copy",
      type: "confirm",
      disabled: !this.canSave()
    }
  ]);

  readonly canSave = computed(() => {
    const newName = this.template().name.trim();
    const originalName = this.data;
    return newName.length > 0 && !this.nameConflict() && newName !== originalName;
  });

  readonly isDirty = computed(() => {
    return this.template().name !== this.data;
  });

  readonly nameConflict = computed(() => {
    if (!this.isNameDirty()) return false;
    return this.containerTemplateService.templates().some((t) => t.name === this.template().name);
  });

  readonly nameErrorMatcher = {
    isErrorState: () => this.nameConflict()
  };

  // --- Methods ---
  editName(newName: string) {
    this.isNameDirty.set(true);
    this.template.set({ ...this.template(), name: newName });
  }

  async onSave() {
    try {
      await this.onAction("copy");
      return true;
    } catch {
      return false;
    }
  }

  async onAction(action: string): Promise<void> {
    if (action === "copy") {
      const success = await this.containerTemplateService.postTemplateEdits(this.template());
      if (success) {
        this.dialogRef.close(this.template().name);
      }
    }
  }
}
