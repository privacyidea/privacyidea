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

import { Component, computed, inject, input } from "@angular/core";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ContainerTemplateCopyDialogComponent } from "@components/container/container-templates/dialogs/container-template-copy-dialog/container-template-copy-dialog.component";
import { ContainerTemplateDeleteDialogComponent } from "@components/container/container-templates/dialogs/container-template-delete-dialog/container-template-delete-dialog.component";
import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "@services/container-template/container-template.service";
import { ContainerTemplate } from "@services/container/container.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { TableAction, TableActionsComponent } from "@components/shared/table-actions/table-actions.component";
import { TableActionsHost } from "@components/shared/table-actions/table-actions-host";

@Component({
  selector: "app-container-templates-table-actions",
  standalone: true,
  templateUrl: "./container-templates-table-actions.component.html",
  imports: [TableActionsComponent]
})
export class ContainerTemplatesTableActionsComponent extends TableActionsHost {
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);
  readonly router = inject(Router);

  readonly selectedTemplates = input.required<ContainerTemplate[]>();

  protected readonly actions = computed<TableAction[]>(() => {
    const noSelection = this.selectedTemplates().length < 1;
    return [
      {
        id: "create",
        label: $localize`:@@common.createTemplate:Create Template`,
        tone: "primary",
        width: "m",
        icon: "note_add",
        run: () => this.onClickCreateTemplate()
      },
      {
        id: "copy",
        label: $localize`:@@common.copy:Copy`,
        tone: "secondary",
        width: "m",
        icon: "content_copy",
        disabled: noSelection,
        run: () => this.openCopyTemplateDialog()
      },
      {
        id: "delete",
        label: $localize`:@@common.delete:Delete`,
        tone: "delete-secondary",
        width: "m",
        icon: "delete",
        disabled: noSelection,
        run: () => this.openDeleteTemplateDialog()
      }
    ];
  });

  onClickCreateTemplate() {
    this.router.navigateByUrl(ROUTE_PATHS.CONTAINERS_TEMPLATES_CREATE);
  }

  async openCopyTemplateDialog() {
    const templatesToCopy = this.selectedTemplates();
    if (templatesToCopy.length === 0) return;

    for (const template of templatesToCopy) {
      const newName = await this.dialogService.openDialogAsync({
        component: ContainerTemplateCopyDialogComponent,
        data: template.name
      });
      if (newName && newName.trim() !== "" && newName !== template.name) {
        await this.containerTemplateService.copyTemplate(template, newName);
      }
    }
  }

  async openDeleteTemplateDialog() {
    const templatesToDelete = this.selectedTemplates();
    if (templatesToDelete.length === 0) return;

    const confirmed = await this.dialogService.openDialogAsync({
      component: ContainerTemplateDeleteDialogComponent,
      data: templatesToDelete
    });

    if (confirmed === true) {
      await this.containerTemplateService.deleteTemplates(templatesToDelete.map((t) => t.name));
    }
  }
}
