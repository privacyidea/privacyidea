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
import { Component, inject, Signal, WritableSignal } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { MAT_DIALOG_DATA, MatDialogContent, MatDialogRef, MatDialogTitle } from "@angular/material/dialog";
import { MatIcon } from "@angular/material/icon";
import { PiResponse } from "../../../../app.component";
import {
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface
} from "../../../../services/container/container.service";
import { LostTokenComponent } from "../../token-card/token-tab/lost-token/lost-token.component";
import { ContentService } from "../../../../services/content/content.service";

export type ContainerCreationDialogData = {
  response: PiResponse<ContainerRegisterData>;
  containerSerial: WritableSignal<string>;
  registerContainer: (containerSerial: string, regenerate: boolean) => void;
};


@Component({
  selector: "app-container-created-dialog",
  imports: [MatDialogContent, MatDialogTitle, MatButton, MatIcon],
  templateUrl: "./container-created-dialog.component.html",
  styleUrl: "./container-created-dialog.component.scss"
})
export class ContainerCreatedDialogComponent {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly dialogRef: MatDialogRef<ContainerCreatedDialogComponent> = inject(MatDialogRef);
  public readonly data: Signal<ContainerCreationDialogData> = inject(MAT_DIALOG_DATA);
  private contentService = inject(ContentService);

  constructor() {
    this.dialogRef.afterClosed().subscribe(() => {
      this.containerService.stopPolling();
    });
  }

  containerSelected(containerSerial: string) {
    this.dialogRef.close();
    this.contentService.containerSelected(containerSerial);
  }

  regenerateQRCode() {
    this.data().registerContainer(this.data().containerSerial(), true);
  }
}
