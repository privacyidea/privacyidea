import { Component, Input, WritableSignal } from '@angular/core';
import { TokenService } from '../../../../services/token/token.service';
import { ValidateService } from '../../../../services/validate/validate.service';
import { FormsModule } from '@angular/forms';
import { MatIcon } from '@angular/material/icon';
import { MatFabButton, MatIconButton } from '@angular/material/button';
import { MatDivider } from '@angular/material/divider';
import { MatSuffix } from '@angular/material/form-field';
import { OverflowService } from '../../../../services/overflow/overflow.service';

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
  @Input() tokenType!: WritableSignal<string>;
  fristOTPValue: string = '';
  secondOTPValue: string = '';
  otpOrPinToTest: string = '';
  hide: boolean = true;

  constructor(
    private tokenService: TokenService,
    protected validateService: ValidateService,
    protected overflowService: OverflowService,
  ) {}

  resyncOTPToken() {
    this.tokenService
      .resyncOTPToken(
        this.tokenSerial(),
        this.fristOTPValue,
        this.secondOTPValue,
      )
      .subscribe({
        next: () => {
          this.refreshTokenDetails.set(true);
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
      });
  }

  verifyOTPValue() {
    this.validateService
      .testToken(this.tokenSerial(), this.otpOrPinToTest, '1')
      .subscribe({
        next: () => {
          this.refreshTokenDetails.set(true);
        },
      });
  }
}
