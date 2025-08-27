import { Component, inject, Input, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatIcon } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../../services/notification/notification.service";
import { TokenService, TokenServiceInterface } from "../../../../../services/token/token.service";
import { SimpleDialogComponent, SimpleDialogData } from "../../../../shared/simple-dialog/simple-dialog.component";
import { MatDialog } from "@angular/material/dialog";
import { AuthService, AuthServiceInterface } from "../../../../../services/auth/auth.service";

@Component({
  selector: "app-set-pin-action",
  imports: [FormsModule, MatIcon, MatButtonModule],
  templateUrl: "./set-pin-action.component.html",
  styleUrl: "./set-pin-action.component.scss"
})
export class SetPinActionComponent {
  private readonly notificationService: NotificationServiceInterface =
    inject(NotificationService);
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
    this.tokenService
      .setPin(this.tokenService.tokenSerial(), this.setPinValue())
      .subscribe({
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
          data: result.detail.pin}
        this.dialog.open(SimpleDialogComponent, {data: dialogData});
      }
    });
  }

  canSetRandomPin() {
    return this.authService.rights().includes("setrandompin") &&
           this.authService.rights().includes("otp_pin_set_random");
  }
}
