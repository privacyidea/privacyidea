import {Component, Input, WritableSignal} from '@angular/core';
import {TokenService} from '../../../../services/token/token.service';
import {ValidateService} from '../../../../services/validate/validate.service';
import {FormsModule} from '@angular/forms';
import {MatIcon} from '@angular/material/icon';
import {MatFabButton, MatIconButton} from '@angular/material/button';
import {MatDivider} from '@angular/material/divider';
import {MatSuffix} from '@angular/material/form-field';
import {OverflowService} from '../../../../services/overflow/overflow.service';
import {NotificationService} from '../../../../services/notification/notification.service';

@Component({
  selector: 'app-token-details-actions',
  standalone: true,
  imports: [
    FormsModule,
    MatIcon,
    MatFabButton,
    MatDivider,
    MatIconButton,
    MatSuffix,
  ],
  templateUrl: './token-details-actions.component.html',
  styleUrl: './token-details-actions.component.scss',
})
export class TokenDetailsActionsComponent {
  @Input() refreshTokenDetails!: WritableSignal<boolean>;
  @Input() tokenSerial!: WritableSignal<string>;
  fristOTPValue: string = '';
  secondOTPValue: string = '';
  otpOrPinToTest: string = '';
  hide: boolean = true;

  constructor(
    private tokenService: TokenService,
    private validateService: ValidateService,
    private notificationService: NotificationService,
    protected overflowService: OverflowService
  ) {
  }

  resyncOTPToken() {
    this.tokenService
      .resyncOTPToken(
        this.tokenSerial(),
        this.fristOTPValue,
        this.secondOTPValue
      )
      .subscribe({
        next: () => {
          this.refreshTokenDetails.set(true);
        },
        error: (error) => {
          console.error('Failed to resync OTP token.', error);
          this.notificationService.openSnackBar('Failed to resync OTP token.');
        },
      });
  }

  testToken() {
    this.validateService
      .testToken(this.tokenSerial(), this.otpOrPinToTest)
      .subscribe({
        next: () => {
          this.refreshTokenDetails.set(true);
        },
        error: (error: any) => {
          console.error('Failed to test token.', error);
          this.notificationService.openSnackBar('Failed to test token.');
        },
      });
  }

  verifyOTPValue() {
    this.validateService
      .testToken(this.tokenSerial(), this.otpOrPinToTest, '1')
      .subscribe({
        next: () => {
          this.refreshTokenDetails.set(true);
        },
        error: (error: any) => {
          console.error('Failed to verify OTP value.', error);
          this.notificationService.openSnackBar('Failed to verify OTP value.');
        },
      });
  }
}
