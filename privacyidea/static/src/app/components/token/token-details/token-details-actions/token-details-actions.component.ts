import {Component, Input, WritableSignal} from '@angular/core';
import {TokenService} from '../../../../services/token/token.service';
import {ValidateService} from '../../../../services/validate/validate.service';
import {FormsModule} from '@angular/forms';
import {MatIcon} from '@angular/material/icon';
import {MatFabButton, MatIconButton} from '@angular/material/button';
import {MatDivider} from '@angular/material/divider';
import {MatSuffix} from '@angular/material/form-field';

@Component({
  selector: 'app-token-details-actions',
  standalone: true,
  imports: [
    FormsModule,
    MatIcon,
    MatFabButton,
    MatDivider,
    MatIconButton,
    MatSuffix
  ],
  templateUrl: './token-details-actions.component.html',
  styleUrl: './token-details-actions.component.scss'
})
export class TokenDetailsActionsComponent {
  @Input() refreshTokenDetails!: WritableSignal<boolean>;
  @Input() serial!: WritableSignal<string>;
  fristOTPValue: string = '';
  secondOTPValue: string = '';
  otpOrPinToTest: string = '';
  hide: boolean = true;

  constructor(private tokenService: TokenService, private validateService: ValidateService) {
  }


  resyncOTPToken() {
    this.tokenService.resyncOTPToken(this.serial(), this.fristOTPValue, this.secondOTPValue).subscribe({
      next: () => {
        this.refreshTokenDetails.set(true);
      },
      error: error => {
        console.error('Failed to resync OTP token', error);
      }
    });
  }

  testToken() {
    this.validateService.testToken(this.serial(), this.otpOrPinToTest).subscribe({
      next: () => {
        this.refreshTokenDetails.set(true);
      },
      error: (error: any) => {
        console.error('Failed to test token', error);
      }
    });
  }

  verifyOTPValue() {
    this.validateService.testToken(this.serial(), this.otpOrPinToTest, "1").subscribe({
      next: () => {
        this.refreshTokenDetails.set(true);
      },
      error: (error: any) => {
        console.error('Failed to verify OTP value', error);
      }
    });
  }
}
