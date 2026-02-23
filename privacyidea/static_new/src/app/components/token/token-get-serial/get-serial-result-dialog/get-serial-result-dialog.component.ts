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
import { Component, inject } from "@angular/core";
import { AbstractDialogComponent } from "../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "../../../../models/dialog";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "../../../../route_paths";
import { DialogServiceInterface, DialogService } from "../../../../services/dialog/dialog.service";

export type GetSerialResultDialogData = {
  foundSerial: string;
  otpValue: string;
};

export type GetSerialResultDialogReturn = "reset";

@Component({
  selector: "app-get-serial-result-dialog",
  imports: [DialogWrapperComponent],
  templateUrl: "./get-serial-result-dialog.component.html",
  styleUrl: "./get-serial-result-dialog.component.scss",
  standalone: true
})
export class GetSerialResultDialogComponent extends AbstractDialogComponent<
  GetSerialResultDialogData,
  GetSerialResultDialogReturn
> {
  readonly router = inject(Router);
  readonly dialogService: DialogServiceInterface = inject(DialogService);

  action: DialogAction<GetSerialResultDialogReturn> = {
    type: "confirm",
    label: $localize`OK`,
    value: "reset"
  };

  onClickSerial() {
    const serial = this.data.foundSerial;
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_DETAILS + serial);
    this.dialogService.closeAllDialogs();
  }

  onAction(value: GetSerialResultDialogReturn) {
    this.close(value);
  }
}
