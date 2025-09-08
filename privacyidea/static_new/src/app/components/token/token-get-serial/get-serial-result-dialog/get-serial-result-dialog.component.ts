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
import { MatButton } from "@angular/material/button";
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle
} from "@angular/material/dialog";

export type GetSerialResultDialogData = {
  foundSerial: string;
  otpValue: string;
  onClickSerial: () => void;
  reset: () => void;
};

@Component({
  selector: "app-get-serial-result-dialog",
  imports: [
    MatDialogContent,
    MatDialogTitle,
    MatDialogActions,
    MatButton,
    MatDialogClose
  ],
  templateUrl: "./get-serial-result-dialog.component.html",
  styleUrl: "./get-serial-result-dialog.component.scss",
  standalone: true
})
export class GetSerialResultDialogComponent {
  public readonly dialogRef: MatDialogRef<GetSerialResultDialogComponent> =
    inject(MatDialogRef);
  public readonly data: GetSerialResultDialogData = inject(MAT_DIALOG_DATA);
}
