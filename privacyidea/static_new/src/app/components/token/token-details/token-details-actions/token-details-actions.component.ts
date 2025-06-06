import { Component, Input, WritableSignal } from '@angular/core';
import { TokenService } from '../../../../services/token/token.service';
import { ValidateService } from '../../../../services/validate/validate.service';
import { FormsModule } from '@angular/forms';
import { MatIcon } from '@angular/material/icon';
import { MatFabButton, MatIconButton } from '@angular/material/button';
import { MatDivider } from '@angular/material/divider';
import { MatSuffix } from '@angular/material/form-field';
import { OverflowService } from '../../../../services/overflow/overflow.service';
import { NotificationService } from '../../../../services/notification/notification.service';
import { MatDialog } from '@angular/material/dialog';
import { TokenSshMachineAssignDialogComponent } from '../token-ssh-machine-assign-dialog/token-ssh-machine-assign-dialog';

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
  tokenSerial = this.tokenService.tokenSerial;
  @Input() tokenType!: WritableSignal<string>;
  fristOTPValue: string = '';
  secondOTPValue: string = '';
  otpOrPinToTest: string = '';
  hide: boolean = true;

  constructor(
    private tokenService: TokenService,
    private matDialog: MatDialog,
    protected validateService: ValidateService,
    protected overflowService: OverflowService,
    protected notificationService: NotificationService,
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
          this.tokenService.tokenDetailResource.reload();
        },
      });
  }

  testToken() {
    this.validateService
      .testToken(this.tokenSerial(), this.otpOrPinToTest)
      .subscribe({
        next: () => {
          this.tokenService.tokenDetailResource.reload();
        },
      });
  }

  verifyOTPValue() {
    this.validateService
      .testToken(this.tokenSerial(), this.otpOrPinToTest, '1')
      .subscribe({
        next: () => {
          this.tokenService.tokenDetailResource.reload();
        },
      });
  }

  testPasskey() {
    this.validateService.authenticatePasskey({ isTest: true }).subscribe({
      next: (checkResponse) => {
        if (checkResponse.result?.value) {
          this.notificationService.openSnackBar(
            'Test successful. You would have been logged in as: ' +
              (checkResponse.detail?.username ?? 'Unknown User'),
          );
        } else {
          this.notificationService.openSnackBar('No user found.');
        }
      },
    });
  }

  assignSSHMachineDialog() {
    this.matDialog.open(TokenSshMachineAssignDialogComponent, {
      width: '600px',
      data: {
        tokenSerial: this.tokenSerial(),
        tokenDetails: this.tokenService.getTokenDetails(this.tokenSerial()),
        tokenType: this.tokenType(),
      },
      autoFocus: false,
      restoreFocus: false,
    });
  }
}
