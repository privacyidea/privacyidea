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

import { CommonModule } from "@angular/common";
import { Component, computed } from "@angular/core";
import { MatIconModule } from "@angular/material/icon";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "src/app/models/dialog";
import { ContainerTemplate } from "../../../../../services/container/container.service";

@Component({
  selector: "app-container-template-delete-dialog",
  standalone: true,
  imports: [CommonModule, MatIconModule, DialogWrapperComponent],
  templateUrl: "./container-template-delete-dialog.component.html",
  styleUrl: "./container-template-delete-dialog.component.scss"
})
export class ContainerTemplateDeleteDialogComponent extends AbstractDialogComponent<ContainerTemplate[], boolean> {
  readonly actions = computed<DialogAction<string>[]>(() => [
    {
      label: $localize`Delete`,
      value: "delete",
      icon: "delete_forever",
      type: "destruct"
    }
  ]);

  onAction(action: string): void {
    if (action === "delete") {
      this.dialogRef.close(true);
    }
  }
}
