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
import { Component, inject, WritableSignal } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { MAT_DIALOG_DATA, MatDialogContent, MatDialogRef, MatDialogTitle } from "@angular/material/dialog";
import { MatIcon } from "@angular/material/icon";
import { Router } from "@angular/router";
import { PiResponse } from "../../../../app.component";
import { ROUTE_PATHS } from "../../../../route_paths";
import {
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface
} from "../../../../services/container/container.service";
import { LostTokenComponent } from "../../token-card/token-tab/lost-token/lost-token.component";

export type ContainerCreationDialogData = {
  response: PiResponse<ContainerRegisterData>;
  containerSerial: WritableSignal<string>;
  registerContainer: (containerSerial: string) => void;
};

@Component({
  selector: "app-container-registration-dialog",
  imports: [MatDialogContent, MatDialogTitle, MatButton, MatIcon],
  templateUrl: "./container-registration-dialog.component.html",
  styleUrl: "./container-registration-dialog.component.scss"
})
export class ContainerRegistrationDialogComponent {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  public readonly data: ContainerCreationDialogData = inject(MAT_DIALOG_DATA);
  private router = inject(Router);

  constructor(private dialogRef: MatDialogRef<LostTokenComponent>) {
    this.dialogRef.afterClosed().subscribe(() => {
      this.containerService.stopPolling();
    });
  }

  containerSelected(containerSerial: string) {
    this.dialogRef.close();
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + containerSerial);
    this.data.containerSerial.set(containerSerial);
  }

  regenerateQRCode() {
    this.data.registerContainer(this.data.containerSerial());
    this.dialogRef.close();
  }
}
