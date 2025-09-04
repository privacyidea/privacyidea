/**
 * (c) NetKnights GmbH 2024,  https://netknights.it
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
import { NgClass } from "@angular/common";
import { Component, inject, Input, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatFabButton } from "@angular/material/button";
import { MatDialog } from "@angular/material/dialog";
import { MatDivider } from "@angular/material/divider";
import { MatIcon } from "@angular/material/icon";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import { OverflowService, OverflowServiceInterface } from "../../../../services/overflow/overflow.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { ValidateService, ValidateServiceInterface } from "../../../../services/validate/validate.service";
import { TokenSshMachineAssignDialogComponent } from "../token-ssh-machine-assign-dialog/token-ssh-machine-assign-dialog";
import { ResyncTokenActionComponent } from "./resync-token-action/resync-token-action.component";
import { SetPinActionComponent } from "./set-pin-action/set-pin-action.component";
import { TestOtpPinActionComponent } from "./test-otp-pin-action/test-otp-pin-action.component";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";

@Component({
  selector: "app-token-details-actions",
  standalone: true,
  imports: [
    FormsModule,
    MatIcon,
    MatFabButton,
    MatDivider,
    NgClass,
    SetPinActionComponent,
    ResyncTokenActionComponent,
    TestOtpPinActionComponent
  ],
  templateUrl: "./token-details-actions.component.html",
  styleUrl: "./token-details-actions.component.scss"
})
export class TokenDetailsActionsComponent {
  private readonly matDialog: MatDialog = inject(MatDialog);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly validateService: ValidateServiceInterface = inject(ValidateService);
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  @Input() setPinValue!: WritableSignal<string>;
  @Input() repeatPinValue!: WritableSignal<string>;
  @Input() tokenType!: WritableSignal<string>;
  tokenSerial = this.tokenService.tokenSerial;

  testPasskey() {
    this.validateService.authenticatePasskey({ isTest: true }).subscribe({
      next: (checkResponse) => {
        if (checkResponse.result?.value) {
          this.notificationService.openSnackBar(
            "Test successful. You would have been logged in as: " + (checkResponse.detail?.username ?? "Unknown User")
          );
        } else {
          this.notificationService.openSnackBar("No user found.");
        }
      }
    });
  }

  assignSSHMachineDialog() {
    this.matDialog.open(TokenSshMachineAssignDialogComponent, {
      width: "600px",
      data: {
        tokenSerial: this.tokenSerial(),
        tokenDetails: this.tokenService.getTokenDetails(this.tokenSerial()),
        tokenType: this.tokenType()
      },
      autoFocus: false,
      restoreFocus: false
    });
  }
}
