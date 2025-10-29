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

import { Component, inject } from "@angular/core";
import {
  MAT_DIALOG_DATA,
  MatDialogActions, MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle
} from "@angular/material/dialog";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { MatButton } from "@angular/material/button";

export type ContainerRegistrationCompletedDialogData = {
  containerSerial: string;
};

@Component({
  selector: "app-container-registration-completed-dialog",
  templateUrl: "./container-registration-completed-dialog.component.html",
  styleUrls: ["./container-registration-completed-dialog.component.scss"],
  imports: [
    MatDialogContent,
    MatDialogTitle,
    MatDialogActions,
    MatButton,
    MatDialogClose
  ]
})
export class ContainerRegistrationCompletedDialogComponent {
  public readonly data: ContainerRegistrationCompletedDialogData = inject(MAT_DIALOG_DATA);
  protected readonly dialogRef: MatDialogRef<ContainerRegistrationCompletedDialogComponent> = inject(MatDialogRef);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);

  containerSelected(containerSerial: string) {
    this.dialogRef.close();
    this.contentService.containerSelected(containerSerial);
  }
}