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

import { Component, computed, DestroyRef, inject, linkedSignal, signal, viewChild } from "@angular/core";

import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { MatButtonModule } from "@angular/material/button";
import { MatCardModule } from "@angular/material/card";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatListModule } from "@angular/material/list";
import { MatTooltipModule } from "@angular/material/tooltip";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ContainerTemplateEditComponent } from "@components/container/container-templates/container-template-edit/container-template-edit.component";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { NAVIGATION_ACCESSIBLE_DIALOG_CLASS } from "@constants/global.constants";
import { DialogAction } from "@models/dialog";
import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "@services/container-template/container-template.service";
import { ContainerTemplate } from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import {
  PendingChangesService,
  PendingChangesServiceInterface
} from "@services/pending-changes/pending-changes.service";
import { deepCopy } from "@utils/deep-copy.utils";

@Component({
  selector: "app-container-template-edit-page",
  standalone: true,
  host: {
    class: NAVIGATION_ACCESSIBLE_DIALOG_CLASS
  },
  imports: [
    MatInputModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatListModule,
    MatCheckboxModule,
    ContainerTemplateEditComponent,
    StickyHeaderDirective
  ],
  templateUrl: "./container-template-edit-page.component.html",
  styleUrl: "./container-template-edit-page.component.scss"
})
export class ContainerTemplateEditPageComponent {
  // --- Services ---
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);
  readonly contentService: ContentServiceInterface = inject(ContentService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  readonly pendingChangesService: PendingChangesServiceInterface = inject(PendingChangesService);
  readonly router = inject(Router);
  readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);

  initTemplate = signal<ContainerTemplate | null>(null);

  private readonly editComponent = viewChild(ContainerTemplateEditComponent);

  // --- State Signals ---
  readonly template = linkedSignal<any, ContainerTemplate>({
    source: () => ({
      initialData: this.initTemplate() ?? this.containerTemplateService.emptyContainerTemplate,
      defaultType: this.containerTemplateService.availableContainerTypes()[0] ?? ""
    }),
    computation: (source) => {
      const type = source.initialData.container_type || source.defaultType;
      return deepCopy({ ...source.initialData, container_type: type });
    }
  });

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const name = params.get("name");
      if (!name) {
        this.initTemplate.set(null);
        return;
      }
      const template = this.containerTemplateService.templates().find((p) => p.name === name);
      if (!template) {
        console.warn("ContainerTemplateEditPageComponent: No template found with name ", name);
        this.initTemplate.set(null);
        return;
      }
      this.initTemplate.set(template);
    });
  }

  // --- Pending Changes Implementations ---
  readonly canSave = computed(() => this.canSaveTemplate());
  readonly isDirty = computed(() => {
    const current = JSON.stringify(this.template());
    const base = JSON.stringify(this.initTemplate() ?? this.containerTemplateService.emptyContainerTemplate);
    return current !== base;
  });

  async onSave(): Promise<boolean> {
    try {
      await this.onAction("save");
      return true;
    } catch {
      return false;
    }
  }

  // --- Computed - General State ---
  readonly isNewTemplate = computed(() => !this.initTemplate());

  // --- Computed - Validation & Conflict ---
  readonly nameInvalidPattern = computed(() => !/^[a-zA-Z0-9._-]*$/.test(this.template().name));
  readonly nameConflict = computed(() =>
    this.containerTemplateService
      .templates()
      .some((t) => t.name === this.template().name && t.name !== this.initTemplate()?.name)
  );
  readonly canSaveTemplate = computed<boolean>(() => {
    return this.containerTemplateService.canSaveTemplate(this.template()) && !this.nameConflict();
  });
  readonly nameErrorMatcher = {
    isErrorState: () => this.nameConflict() || (this.template().name.length > 0 && this.nameInvalidPattern())
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
      if (!result) return;
      if (this.initTemplate() && this.initTemplate()?.name !== this.template().name) {
        await this.containerTemplateService.deleteTemplate(this.initTemplate()!.name);
      }
      this._navigateBack();
    }
  }

  // --- Private Helper Methods ---
  private async _saveTemplate(): Promise<boolean> {
    if (!this.canSaveTemplate()) return false;
    // Pull the latest token payloads from each enrollment row before posting.
    const editComponent = this.editComponent();
    const tokens = editComponent?.collectTokens();
    if (tokens === null || tokens === undefined) {
      this.notificationService.warning($localize`There are invalid token configurations.`);
      editComponent?.scrollToFirstInvalid();
      return false;
    }
    this.template.update((t) => ({
      ...t,
      template_options: { ...t.template_options, tokens }
    }));
    return this.containerTemplateService.postTemplateEdits(this.template());
  }

  onCancel(): void {
    if (!this.isDirty()) {
      this._navigateBack();
      return;
    }
    this.dialogService
      .openDialog({
        component: SaveAndExitDialogComponent,
        data: {
          title: $localize`Discard changes`,
          allowSaveExit: this.canSave(),
          saveExitDisabled: !this.canSave()
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result === "save-exit") {
          if (!this.canSave()) return;
          Promise.resolve(this.pendingChangesService.save()).then((success) => {
            if (success) {
              this._navigateBack();
            }
          });
        } else if (result === "discard") {
          this._navigateBack();
        }
      });
  }

  private _navigateBack(): void {
    this.pendingChangesService.clearAllRegistrations();
    this.router.navigateByUrl(ROUTE_PATHS.CONTAINERS_TEMPLATES);
  }
}
