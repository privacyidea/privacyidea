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

import { Component, computed, effect, inject, linkedSignal } from "@angular/core";
import { form, FormField, validate } from "@angular/forms/signals";

import { MatButtonModule } from "@angular/material/button";
import { MatCardModule } from "@angular/material/card";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { PendingChangesDialogComponent } from "@components/shared/dialog/abstract-dialog/pending-changes-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";
import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "@services/container-template/container-template.service";
import { ContainerTemplate } from "@services/container/container.service";
import { deepCopy } from "@utils/deep-copy.utils";
import { ERR, identifierName } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";

@Component({
  selector: "app-container-template-copy-dialog",
  standalone: true,
  imports: [MatInputModule, MatButtonModule, MatCardModule, MatFormFieldModule, FormField, DialogWrapperComponent],
  templateUrl: "./container-template-copy-dialog.component.html",
  styleUrl: "./container-template-copy-dialog.component.scss"
})
export class ContainerTemplateCopyDialogComponent extends PendingChangesDialogComponent<string, string> {
  // --- Services ---
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);

  // --- State Signals ---
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

  readonly hasError = hasError;
  readonly ERR = ERR;

  readonly form = form(this.template, (f) => {
    identifierName(f.name);
    validate(f.name, (ctx) => (ctx.value() === this.data ? [{ kind: "notChanged" }] : []));
    // The unchanged original name is reported as "notChanged" only.
    validate(f.name, (ctx) =>
      ctx.value() !== this.data && this.containerTemplateService.templates().some((t) => t.name === ctx.value())
        ? [{ kind: ERR.nameTaken }]
        : []
    );
  });

  // --- Computed ---
  readonly canSave = computed(() => this.form().valid());
  readonly isDirty = computed(() => this.template().name !== this.data);

  readonly actions = computed<DialogAction<string>[]>(() => [
    {
      label: $localize`:@@container.copyTemplate:Copy Template`,
      value: "copy",
      type: "confirm",
      disabled: !this.canSave()
    }
  ]);

  // Set once the name has differed from the original, so that an error is shown from then on even when the
  // user types the original name back.
  private edited = false;

  constructor() {
    super();
    // Copy is disabled for an invalid name, so the reason shows while the field still has focus.
    effect(() => {
      if (this.isDirty()) {
        this.edited = true;
      }
      if (this.edited && !this.canSave()) {
        this.form.name().markAsTouched();
      }
    });
  }

  // --- Methods ---
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
