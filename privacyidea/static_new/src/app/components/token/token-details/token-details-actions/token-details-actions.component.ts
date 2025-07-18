import { Component, inject, Input, WritableSignal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFabButton, MatIconButton } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatDivider } from '@angular/material/divider';
import { MatSuffix } from '@angular/material/form-field';
import { MatIcon } from '@angular/material/icon';
import {
  NotificationService,
  NotificationServiceInterface,
} from '../../../../services/notification/notification.service';
import {
  OverflowService,
  OverflowServiceInterface,
} from '../../../../services/overflow/overflow.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../../services/token/token.service';
import {
  ValidateService,
  ValidateServiceInterface,
} from '../../../../services/validate/validate.service';
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
  private readonly matDialog: MatDialog = inject(MatDialog);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly validateService: ValidateServiceInterface =
    inject(ValidateService);
  protected readonly overflowService: OverflowServiceInterface =
    inject(OverflowService);
  protected readonly notificationService: NotificationServiceInterface =
    inject(NotificationService);

  tokenSerial = this.tokenService.tokenSerial;
  @Input() tokenType!: WritableSignal<string>;
  fristOTPValue: string = '';
  secondOTPValue: string = '';
  otpOrPinToTest: string = '';
  hide: boolean = true;

  constructor() {}

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
