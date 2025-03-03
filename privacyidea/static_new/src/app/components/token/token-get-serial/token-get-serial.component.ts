import { Component, effect, signal } from '@angular/core';
import { MatError, MatFormField, MatHint } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatOption, MatSelect } from '@angular/material/select';
import { HttpParams } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { TokenService } from '../../../services/token/token.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { CommonModule } from '@angular/common';
import { Observable } from 'rxjs';
import { TokenComponent } from '../token.component';
import { MatButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { LoadingService } from '../../../services/loading/loading-service';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmGetSerialDialogComponent } from './confirm-get-serial-dialog/confirm-get-serial-dialog.component';

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
    MatError,
    MatOption,
  ],
  templateUrl: './token-get-serial.component.html',
  styleUrl: './token-get-serial.component.scss',
})
export class TokenGetSerial {
  otpValue = signal<string>('');
  tokenType = signal<string>('');
  assignmentState = signal<string>('');
  serialSubstring = signal<string>('');
  countWindow = signal<number>(10);
  currentStep = signal<
    'init' | 'counting' | 'countDone' | 'searching' | 'found' | 'error'
  >('init');
  tokenTypes: { key: string; info: string }[] = [];
  foundSerial = signal<string>('');
  tokenCount = signal<string>('');

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

  onPressEnter(inputElement: HTMLInputElement): void {
    if (this.otpValue() === '') {
      inputElement.focus();
      if (inputElement instanceof MatInput) {
        inputElement.updateErrorState();
      }
      return;
    }
    switch (this.currentStep()) {
      case 'init':
      case 'found':
      case 'error':
        this.countTokens();
        break;
      case 'countDone':
        this.findSerial();
        break;
      case 'counting':
      case 'searching':
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
    this.loadingService.addLoading('token-get-serial');
    this.fetchSerial(params).subscribe({
      next: (response) => {
        this.tokenCount.set(response.result.value.count);
        this.currentStep.set('countDone');
        this.loadingService.removeLoading('token-get-serial');
        if (this.countIsLarge()) {
          this.dialog.open(ConfirmGetSerialDialogComponent, {
            data: {
              numberOfTokens: this.tokenCount(),
              onAbort: () => {
                this.reset();
              },
              onConfirm: () => {
                this.findSerial();
              },
            },
          });
        } else {
          this.findSerial();
        }
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
    this.loadingService.addLoading('token-get-serial');
    this.fetchSerial(params).subscribe({
      next: (response) => {
        this.foundSerial.set(response.result.value.serial);
        this.currentStep.set('found');
        this.loadingService.removeLoading('token-get-serial');
      },
    });
  }

  fetchSerial(params: HttpParams): Observable<any> {
    let observable = this.tokenService.getSerial(this.otpValue(), params);
    observable.subscribe({
      error: (error) => {
        console.error('Failed to get serial.', error);
        this.loadingService.removeLoading('token-get-serial');
        this.currentStep.set('error');
        this.notificationService.openSnackBar('Failed to get serial.');
      },
    });
    return observable;
  }

  reset(): void {
    this.currentStep.set('init');
    this.foundSerial.set('');
    this.tokenCount.set('');
  }

  countIsLarge(): boolean {
    return parseInt(this.tokenCount()) > 99;
  }
}
