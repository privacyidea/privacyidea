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
import { NgClass } from "@angular/common";
import { Component, computed, inject, Input, signal, WritableSignal } from "@angular/core";
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
import {
  SshMachineAssignDialogData,
  TokenSshMachineAssignDialogComponent
} from "../token-machine-attach-dialog/token-ssh-machine-attach-dialog/token-ssh-machine-attach-dialog";
import { ResyncTokenActionComponent } from "./resync-token-action/resync-token-action.component";
import { SetPinActionComponent } from "./set-pin-action/set-pin-action.component";
import { TestOtpPinActionComponent } from "./test-otp-pin-action/test-otp-pin-action.component";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import {
  MachineService,
  MachineServiceInterface,
  TokenApplications
} from "../../../../services/machine/machine.service";
import {
  HotpMachineAssignDialogData,
  TokenHotpMachineAssignDialogComponent
} from "../token-machine-attach-dialog/token-hotp-machine-attach-dialog/token-hotp-machine-attach-dialog";
import { lastValueFrom } from "rxjs";

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
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly machineService: MachineServiceInterface = inject(MachineService);
  protected readonly validateService: ValidateServiceInterface = inject(ValidateService);
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  @Input() setPinValue!: WritableSignal<string>;
  @Input() repeatPinValue!: WritableSignal<string>;
  @Input() tokenType!: WritableSignal<string>;
  tokenSerial = this.tokenService.tokenSerial;

  isAttachedToMachine = computed<boolean>(() => {
    const tokenApplications = this.machineService.tokenApplications();
    if (!tokenApplications) return false;
    if (tokenApplications.length === 0) return false;
    return true;
  });

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

  attachSshToMachineDialog() {
    const data: SshMachineAssignDialogData = {
      tokenSerial: this.tokenSerial(),
      tokenType: this.tokenType(),
      tokenDetails: this.tokenService.getTokenDetails(this.tokenSerial())
    };
    this.matDialog
      .open(TokenSshMachineAssignDialogComponent, {
        width: "600px",
        data: data,
        autoFocus: false,
        restoreFocus: false
      })
      .afterClosed()
      .subscribe((request) => {
        lastValueFrom(request).then(() => {
          this.machineService.tokenApplicationResource.reload();
        });
      });
  }
  attachHotpToMachineDialog() {
    const data: HotpMachineAssignDialogData = {
      tokenSerial: this.tokenSerial()
    };
    this.matDialog
      .open(TokenHotpMachineAssignDialogComponent, {
        width: "600px",
        data: data,
        autoFocus: false,
        restoreFocus: false
      })
      .afterClosed()
      .subscribe((request) => {
        if (request) {
          lastValueFrom(request).then(() => {
            this.machineService.tokenApplicationResource.reload();
          });
        }
      });
  }

  attachPasskeyToMachine() {
    this.machineService
      .postAssignMachineToToken({
        serial: this.tokenSerial(),
        application: "offline",
        machineid: 0,
        resolver: ""
      })
      .subscribe({
        next: (_) => {
          this.machineService.tokenApplicationResource.reload();
        },
        error: (error) => {
          console.error("Error during assignment request:", error);
        }
      });
  }

  removePasskeyFromMachine() {
    const mtid = this.machineService.tokenApplications()?.[0]?.id;
    this.machineService
      .deleteAssignMachineToToken({
        serial: this.tokenSerial(),
        application: "offline",
        mtid: `${mtid}`
      })
      .subscribe({
        next: (_) => {
          this.machineService.tokenApplicationResource.reload();
        },
        error: (error) => {
          console.error("Error during unassignment request:", error);
        }
      });
  }
}
