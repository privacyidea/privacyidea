import { Component, inject, Input, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatFabButton, MatIconButton } from "@angular/material/button";
import { MatDialog } from "@angular/material/dialog";
import { MatDivider } from "@angular/material/divider";
import { MatFormField, MatLabel, MatSuffix } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import {
  OverflowService,
  OverflowServiceInterface
} from "../../../../services/overflow/overflow.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import {
  ValidateService,
  ValidateServiceInterface
} from "../../../../services/validate/validate.service";
import { TokenSshMachineAssignDialogComponent } from "../token-ssh-machine-assign-dialog/token-ssh-machine-assign-dialog";
import { NgClass } from "@angular/common";
import { MatInput } from "@angular/material/input";

@Component({
  selector: "app-token-details-actions",
  standalone: true,
  imports: [
    FormsModule,
    MatIcon,
    MatFabButton,
    MatDivider,
    MatIconButton,
    MatSuffix,
    NgClass,
    MatFormField,
    MatLabel,
    MatInput
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
  @Input() setPinValue!: WritableSignal<string>;
  @Input() repeatPinValue!: WritableSignal<string>;
  @Input() tokenType!: WritableSignal<string>;
  tokenSerial = this.tokenService.tokenSerial;
  fristOTPValue: string = "";
  secondOTPValue: string = "";
  otpOrPinToTest: string = "";
  hide: boolean = true;

  resyncOTPToken() {
    this.tokenService
      .resyncOTPToken(
        this.tokenSerial(),
        this.fristOTPValue,
        this.secondOTPValue
      )
      .subscribe({
        next: () => {
          this.tokenService.tokenDetailResource.reload();
        }
      });
  }

  testToken() {
    this.validateService
      .testToken(this.tokenSerial(), this.otpOrPinToTest)
      .subscribe({
        next: (response) => {
          if (response.result?.authentication === "ACCEPT") {
            this.notificationService.openSnackBar(
              "OTP or Pin tested with token was accepted."
            );
          } else {
            this.notificationService.openSnackBar(
              "OTP or Pin tested with token was rejected."
            );
          }
          this.tokenService.tokenDetailResource.reload();
        }
      });
  }

  verifyOTPValue() {
    this.validateService
      .testToken(this.tokenSerial(), this.otpOrPinToTest, "1")
      .subscribe({
        next: () => {
          this.tokenService.tokenDetailResource.reload();
        }
      });
  }

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

  setPin() {
    if (this.setPinValue() !== this.repeatPinValue()) {
      console.error("PINs do not match.");
      this.notificationService.openSnackBar("PINs do not match.");
      return;
    }
    this.tokenService.setPin(this.tokenSerial(), this.setPinValue()).subscribe({
      next: () => {
        this.notificationService.openSnackBar("PIN set successfully.");
      }
    });
  }

  setRandomPin() {
    this.tokenService.setRandomPin(this.tokenSerial()).subscribe({
      next: () => {
        this.notificationService.openSnackBar("PIN set successfully.");
      }
    });
  }

  canSetRandomPin() {
    console.warn("canSetRandomPin Method not implemented.");
    return true;
  }
}
