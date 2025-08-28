import { Component, inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput, MatSuffix } from "@angular/material/input";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../../services/notification/notification.service";
import { TokenService, TokenServiceInterface } from "../../../../../services/token/token.service";
import { ValidateService, ValidateServiceInterface } from "../../../../../services/validate/validate.service";

@Component({
  selector: "app-test-otp-pin-action",
  imports: [MatFormField, MatLabel, MatInput, FormsModule, MatSuffix, MatButtonModule, MatIcon],
  templateUrl: "./test-otp-pin-action.component.html",
  styleUrl: "./test-otp-pin-action.component.scss"
})
export class TestOtpPinActionComponent {
  private readonly validateService: ValidateServiceInterface = inject(ValidateService);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  hide: boolean = true;
  otpOrPinToTest: string = "";

  testToken() {
    this.validateService.testToken(this.tokenService.tokenSerial(), this.otpOrPinToTest).subscribe({
      next: (response) => {
        if (response.result?.authentication === "ACCEPT") {
          this.notificationService.openSnackBar("OTP or Pin tested with token was accepted.");
        } else {
          this.notificationService.openSnackBar("OTP or Pin tested with token was rejected.");
        }
        this.tokenService.tokenDetailResource.reload();
      }
    });
  }

  verifyOTPValue() {
    this.validateService.testToken(this.tokenService.tokenSerial(), this.otpOrPinToTest, "1").subscribe({
      next: () => {
        this.tokenService.tokenDetailResource.reload();
      }
    });
  }
}
