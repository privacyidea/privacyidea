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
import { AuthService, AuthServiceInterface } from "../../../../../services/auth/auth.service";
import { Component, inject, Input, WritableSignal } from "@angular/core";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../../services/notification/notification.service";
import { SimpleDialogComponent, SimpleDialogData } from "../../../../shared/simple-dialog/simple-dialog.component";
import { TokenService, TokenServiceInterface } from "../../../../../services/token/token.service";

import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatDialog } from "@angular/material/dialog";
import { MatIcon } from "@angular/material/icon";

@Component({
  selector: "app-set-pin-action",
  imports: [FormsModule, MatIcon, MatButtonModule],
  templateUrl: "./set-pin-action.component.html",
  styleUrl: "./set-pin-action.component.scss"
})
export class SetPinActionComponent {
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly dialog: MatDialog = inject(MatDialog);
  @Input() setPinValue!: WritableSignal<string>;
  @Input() repeatPinValue!: WritableSignal<string>;

  setPin() {
    if (this.setPinValue() !== this.repeatPinValue()) {
      console.error("PINs do not match.");
      this.notificationService.openSnackBar("PINs do not match.");
      return;
    }
    this.tokenService.setPin(this.tokenService.tokenSerial(), this.setPinValue()).subscribe({
      next: () => {
        this.notificationService.openSnackBar("PIN set successfully.");
        this.setPinValue.set("");
        this.repeatPinValue.set("");
      }
    });
  }

  setRandomPin() {
    this.tokenService.setRandomPin(this.tokenService.tokenSerial()).subscribe({
      next: (result) => {
        const dialogData: SimpleDialogData = {
          header: "PIN Set Successfully",
          text: "Randomly generated PIN:",
          data: result.detail.pin
        };
        this.dialog.open(SimpleDialogComponent, { data: dialogData });
      }
    });
  }
}
