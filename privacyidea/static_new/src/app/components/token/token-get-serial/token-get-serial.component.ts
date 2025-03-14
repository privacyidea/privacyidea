import {
  Component,
  effect,
  Input,
  signal,
  WritableSignal,
} from '@angular/core';
import {
  MatError,
  MatFormField,
  MatHint,
  MatLabel,
} from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatOption, MatSelect } from '@angular/material/select';
import { HttpParams } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { TokenService } from '../../../services/token/token.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { TokenComponent, TokenSelectedContent } from '../token.component';
import { MatButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { LoadingService } from '../../../services/loading/loading-service';
import { MatDialog } from '@angular/material/dialog';
import { GetSerialResultDialogComponent } from './get-serial-result-dialog/get-serial-result-dialog.component';
import { ConfirmationDialogComponent } from '../../shared/confirmation-dialog/confirmation-dialog.component';

@Component({
  selector: 'app-token-get-serial',
  imports: [
    FormsModule,
    MatProgressBarModule,
    MatFormField,
    MatInput,
    MatSelect,
    CommonModule,
    MatIcon,
    MatButton,
    MatHint,
    MatOption,
    MatError,
    MatLabel,
  ],
  templateUrl: './token-get-serial.component.html',
  styleUrl: './token-get-serial.component.scss',
})
export class TokenGetSerial {
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  otpValue = signal<string>('');
  tokenType = signal<string>('');
  assignmentState = signal<string>('');
  serialSubstring = signal<string>('');
  countWindow = signal<number>(10);
  currentStep = signal('init');
  foundSerial = signal<string>('');
  tokenCount = signal<string>('');
  serialSubscription: Subscription | null = null;
  tokenTypes: { key: string; info: string }[] = [];
  assignmentStates = [
    { key: 'assigned', info: 'The token is assigned to a user' },
    { key: 'unassigned', info: 'The token is not assigned to a user' },
    {
      key: "don't care",
      info: 'It does not matter, if the token is assigned or not',
    },
  ];

  constructor(
    private tokenService: TokenService,
    private notificationService: NotificationService,
    private loadingService: LoadingService,
    private dialog: MatDialog,
  ) {
    const tokenWithOTP = [
      'hotp',
      'totp',
      'spass',
      'motp',
      'sshkey',
      'yubikey',
      'remote',
      'yubico',
      'radius',
      'sms',
    ];
    this.tokenTypes = TokenComponent.tokenTypes.filter((type) =>
      tokenWithOTP.includes(type.key),
    );

    effect(() => {
      this.otpValue();
      this.assignmentState();
      this.tokenType();
      this.serialSubstring();
      this.reset();
    });
  }

  onClickRunSearch(): void {
    switch (this.currentStep()) {
      case 'init':
      case 'found':
      case 'error':
        this.countTokens();
        break;
      case 'countDone':
      case 'counting':
      case 'searching':
        this.reset();
        break;
    }
  }

  getParams(): HttpParams {
    let params = new HttpParams();
    params = params.set('window', this.countWindow());

    if (this.assignmentState() === 'assigned') {
      params = params.set('assigned', '1');
    }
    if (this.assignmentState() === 'unassigned') {
      params = params.set('unassigned', '1');
    }
    if (this.tokenType() !== '') {
      params = params.set('type', this.tokenType());
    }
    if (this.serialSubstring() !== '') {
      params = params.set('serial', this.serialSubstring());
    }

    return params;
  }

  countTokens(): void {
    if (this.currentStep() !== 'init' && this.currentStep() !== 'found') {
      this.notificationService.openSnackBar('Invalid action.');
      return;
    }
    let params = this.getParams();
    params = params.set('count', '1');
    this.currentStep.set('counting');
    this.tokenService.getSerial(this.otpValue(), params).subscribe({
      next: (response) => {
        this.tokenCount.set(response.result.value.count);
        this.currentStep.set('countDone');
        if (this.countIsLarge()) {
          this.dialog
            .open(ConfirmationDialogComponent, {
              data: {
                title: 'Search Serial',
                action: 'search',
                numberOfTokens: this.tokenCount(),
              },
            })
            .afterClosed()
            .subscribe({
              next: (result) => {
                if (result) {
                  this.findSerial();
                } else {
                  this.reset();
                }
              },
            });
        } else {
          this.findSerial();
        }
      },
      error: (error) => {
        console.error('Failed to get count.', error);
        this.currentStep.set('error');
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to get count. ' + message,
        );
      },
    });
  }

  findSerial(): void {
    if (this.currentStep() !== 'countDone') {
      this.notificationService.openSnackBar('Invalid action.');
      return;
    }
    let params = this.getParams();
    params = params.delete('count');
    this.currentStep.set('searching');
    this.serialSubscription = this.tokenService
      .getSerial(this.otpValue(), params)
      .subscribe({
        next: (response) => {
          this.dialog.open(GetSerialResultDialogComponent, {
            data: {
              foundSerial: response.result.value.serial,
              otpValue: this.otpValue(),
              onClickSerial: () => {
                this.tokenSerial.set(response.result.value.serial);
                this.selectedContent.set('token_details');
                this.dialog.closeAll();
              },
              reset: () => {
                this.reset();
              },
            },
          });
          this.foundSerial.set(response.result.value.serial);
          this.currentStep.set('found');
        },
      });
  }

  reset(): void {
    this.serialSubscription?.unsubscribe();
    this.serialSubscription = null;
    this.loadingService.clearAllLoadings();
    this.currentStep.set('init');
    this.foundSerial.set('');
    this.tokenCount.set('');
  }

  countIsLarge(): boolean {
    return parseInt(this.tokenCount()) > 99;
  }
}
