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
import { NgClass } from "@angular/common";
import { SetPinActionComponent } from "./set-pin-action/set-pin-action.component";
import { ResyncTokenActionComponent } from "./resync-token-action/resync-token-action.component";
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
  protected readonly validateService: ValidateServiceInterface =
    inject(ValidateService);
  protected readonly overflowService: OverflowServiceInterface =
    inject(OverflowService);
  protected readonly notificationService: NotificationServiceInterface =
    inject(NotificationService);
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
            "Test successful. You would have been logged in as: " +
            (checkResponse.detail?.username ?? "Unknown User")
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
