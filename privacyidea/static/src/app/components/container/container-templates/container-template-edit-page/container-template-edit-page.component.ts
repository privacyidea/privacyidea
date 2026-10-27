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

import {
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  linkedSignal,
  signal,
  untracked,
  viewChild
} from "@angular/core";

import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { MatButtonModule } from "@angular/material/button";
import { MatCardModule } from "@angular/material/card";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatListModule } from "@angular/material/list";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ContainerTemplateEditComponent } from "@components/container/container-templates/container-template-edit/container-template-edit.component";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "@services/container-template/container-template.service";
import { ContainerTemplate } from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { ContainerTemplateDeleteDialogComponent } from "@components/container/container-templates/dialogs/container-template-delete-dialog/container-template-delete-dialog.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
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
  imports: [
    MatInputModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
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
  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  readonly pendingChangesService: PendingChangesServiceInterface = inject(PendingChangesService);
  readonly router = inject(Router);
  readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);

  initTemplate = signal<ContainerTemplate | null>(null);
  // The template name of the route, resolved against the loaded templates.
  private readonly templateName = signal<string | null>(null);

  private readonly editComponent = viewChild(ContainerTemplateEditComponent);

  // --- State Signals ---
  // The template as loaded, with the first available container type for a template that has none.
  private readonly baseTemplate = computed<ContainerTemplate>(() => {
    const initialData = this.initTemplate() ?? this.containerTemplateService.emptyContainerTemplate;
    const defaultType = this.containerTemplateService.availableContainerTypes()[0] ?? "";
    return { ...initialData, container_type: initialData.container_type || defaultType };
  });
  readonly template = linkedSignal<ContainerTemplate>(() => deepCopy(this.baseTemplate()));

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const name = params.get("name");
      if (!name) this.initTemplate.set(null);
      this.templateName.set(name);
    });
    effect(() => {
      const name = this.templateName();
      const templates = this.containerTemplateService.templates();
      const loading = this.containerTemplateService.templatesResource.isLoading();
      if (!name) return;
      untracked(() => {
        const template = templates.find((p) => p.name === name);
        if (template) {
          if (this.initTemplate()?.name !== name) this.initTemplate.set(template);
          return;
        }
        this.initTemplate.set(null);
        if (!loading) console.warn("ContainerTemplateEditPageComponent: No template found with name ", name);
      });
    });
    this.pendingChangesService.registerHasChanges(this.isDirty);
    this.pendingChangesService.registerValidChanges(this.canSave);
    this.pendingChangesService.registerSave(() => this.persistTemplate());
  }

  // --- Pending Changes Implementations ---
  // The edit component holds the rules of the template, so the page can save only once it is mounted.
  readonly canSave = computed(() => this.editComponent()?.canSave() ?? false);
  readonly isDirty = computed(() => {
    return JSON.stringify(this.template()) !== JSON.stringify(this.baseTemplate());
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
  // The edit form is shown once the template of the route is known, so it never starts from an empty template.
  readonly templateReady = computed(
    () => !this.templateName() || !!this.initTemplate() || !this.containerTemplateService.templatesResource.isLoading()
  );

  // --- Action Handling ---
  async onAction(action: string): Promise<void> {
    if (action === "save") {
      const result = await this._saveTemplate();
      if (!result) return;
      this._navigateBack();
    }
  }

  // Saves without leaving the page, for the pending-changes guard that navigates on its own.
  async persistTemplate(): Promise<boolean> {
    try {
      return await this._saveTemplate();
    } catch {
      return false;
    }
  }

  // --- Private Helper Methods ---
  private async _saveTemplate(): Promise<boolean> {
    if (!this.canSave()) return false;
    // Pull the latest token payloads from each enrollment row before posting.
    const editComponent = this.editComponent();
    const tokens = editComponent?.collectTokens();
    if (tokens === null || tokens === undefined) {
      this.notificationService.warning(
        $localize`:@@container.thereInvalidToken:There are invalid token configurations.`
      );
      editComponent?.scrollToFirstInvalid();
      return false;
    }
    this.template.update((t) => ({
      ...t,
      template_options: { ...t.template_options, tokens }
    }));
    // An existing template is saved under its own name, so a changed name can not create a second template
    const initTemplate = this.initTemplate();
    return this.containerTemplateService.postTemplateEdits(
      initTemplate ? { ...this.template(), name: initTemplate.name } : this.template()
    );
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
          title: $localize`:@@common.discardChanges:Discard changes`,
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

  async deleteTemplate(): Promise<void> {
    const template = this.initTemplate();
    if (!template) {
      return;
    }
    const confirmed = await this.dialogService.openDialogAsync({
      component: ContainerTemplateDeleteDialogComponent,
      data: [template]
    });
    if (confirmed !== true) {
      return;
    }
    try {
      await this.containerTemplateService.deleteTemplate(template.name);
    } catch {
      return;
    }
    this._navigateBack();
  }

  private _navigateBack(): void {
    this.pendingChangesService.clearAllRegistrations();
    this.router.navigateByUrl(ROUTE_PATHS.CONTAINERS_TEMPLATES);
  }
}
