import { Component, effect, signal } from '@angular/core';
import { MatOption } from '@angular/material/core';
import { MatFormField, MatHint } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatSelect } from '@angular/material/select';
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

@Component({
  selector: 'app-token-get-serial',
  imports: [
    FormsModule,
    MatProgressBarModule,
    MatFormField,
    MatInput,
    MatSelect,
    MatOption,
    CommonModule,
    MatIcon,
    MatButton,
    MatHint,
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
  tokenTypes: { key: string; info: string }[] = [];

  currentStep: string = 'init';
  foundSerial: string = '';
  count: string = '';
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

  onPressEnter(): void {
    if (this.otpValue() === '') {
      this.notificationService.openSnackBar('Please enter an OTP value.');
      return;
    }

    switch (this.currentStep) {
      case 'init':
      case 'found':
        this.countTokens();
        break;
      case 'counting':
        this.findSerial();
        break;
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
    if (this.currentStep !== 'init') {
      this.notificationService.openSnackBar('Invalid action.');
      return;
    }
    let params = this.getParams();
    params = params.set('count', '1');
    this.currentStep = 'counting';
    this.fetchSerial(params).subscribe({
      next: (response) => {
        this.count = response.result.value.count;
        if (!this.countIsLarge()) {
          this.findSerial();
        }
      },
    });
  }

  findSerial(): void {
    if (this.currentStep !== 'counting') {
      this.notificationService.openSnackBar('Invalid action.');
      return;
    }
    let params = this.getParams();
    params = params.delete('count');
    this.currentStep = 'searching';
    this.fetchSerial(params).subscribe({
      next: (response) => {
        this.foundSerial = response.result.value.serial;
        this.currentStep = 'found';
      },
    });
  }

  fetchSerial(params: HttpParams): Observable<any> {
    let observable = this.tokenService.getSerial(this.otpValue(), params);
    observable.subscribe({
      error: (error) => {
        console.error('Failed to get serial.', error);
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to get serial. ' + message,
        );
      },
    });
    return observable;
  }

  reset(): void {
    this.currentStep = 'init';
    this.foundSerial = '';
    this.count = '';
  }

  countIsLarge(): boolean {
    return parseInt(this.count) > 99;
  }
}
