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

import { Component, inject, input } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { ContainerTemplate } from "../../../../services/container/container.service";
import { DialogServiceInterface, DialogService } from "src/app/services/dialog/dialog.service";
import { ContainerTemplateEditDialogComponent } from "../dialogs/container-template-edit-dialog/container-template-edit-dialog.component";
import { ContainerTemplateCopyDialogComponent } from "../dialogs/container-template-copy-dialog/container-template-copy-dialog.component";
import { ContainerTemplateDeleteDialogComponent } from "../dialogs/container-template-delete-dialog/container-template-delete-dialog.component";
import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "../../../../services/container-template/container-template.service";

@Component({
  selector: "app-container-templates-table-actions",
  standalone: true,
  templateUrl: "./container-templates-table-actions.component.html",
  styleUrl: "./container-templates-table-actions.component.scss",
  imports: [MatButtonModule, MatIconModule]
})
export class ContainerTemplatesTableActionsComponent {
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);

  readonly selectedTemplates = input.required<ContainerTemplate[]>();

  openNewTemplateDialog() {
    this.dialogService.openDialog({
      component: ContainerTemplateEditDialogComponent
    });
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
