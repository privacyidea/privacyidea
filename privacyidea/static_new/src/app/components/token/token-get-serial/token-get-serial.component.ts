import { Component, effect, Input, signal } from '@angular/core';
import { MatOption } from '@angular/material/core';
import { MatFormField } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatSelect } from '@angular/material/select';
import { HttpParams } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { TokenService } from '../../../services/token/token.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { CommonModule } from '@angular/common';
import { Observable } from 'rxjs';
import { ConfirmButton } from '../../universals/confirm-button/confirm-button.component';
import { AbortButton } from '../../universals/abort-button/abort-button.component';

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
    ConfirmButton,
    AbortButton,
  ],
  templateUrl: './token-get-serial.component.html',
  styleUrl: './token-get-serial.component.scss',
})
export class TokenGetSerial {
  otpValue = signal<string>('');
  tokenType = signal<string>('');
  assignmentState = signal<string>('');
  serialSubstring = signal<string>('');
  countWindow = signal<string>('');

  // possible steps: init, count, searching, found
  currentStep: string = 'init';
  foundSerial: string = '';
  count: string = '';

  constructor(
    private tokenService: TokenService,
    private notificationService: NotificationService
  ) {
    effect(() => {
      // Triggered when any of the following signals change
      this.otpValue();
      this.assignmentState();
      this.tokenType();
      this.serialSubstring();

      this.reset();
    });
  }

  tokenTypes: Map<string, string> = new Map([
    ['', ''],
    ['totp', 'TOTP: Time-based One Time Passwords'],
    ['hotp', 'HOTP: Counter-based One Time Passwords'],
    ['spass', 'SPass: Simple Pass token. Static passwords'],
    ['motp', 'mOTP: classical mobile One Time Passwords'],
    ['sshkey', 'SSH Public Key: The public SSH key'],
    ['yubikey', 'Yubikey AES mode: One Time Passwords with Yubikey'],
    [
      'remote',
      'Remote Token: Forward authentication request to another server',
    ],
    [
      'yubico',
      'Yubikey Cloud mode: Forward authentication request to YubiCloud',
    ],
    ['radius', 'RADIUS: Forward authentication request to a RADIUS server'],
    ['sms', 'SMS: Send a One Time Password to the users mobile phone'],
  ]);

  assignmentStates: Map<string, string> = new Map([
    ['', ''],
    ['assigned', 'The token is assigned to a user'],
    ['unassigned', 'The token is not assigned to a user'],
    ["don't care", 'It does not matter, if the token is assigned or not'],
  ]);

  onPressEnter(): void {
    if (this.otpValue() === '') {
      this.notificationService.errorSnackBar('Please enter an OTP value.');
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

  // Build the HttpParams object based on the current state of the component
  getParams(): HttpParams {
    var params = new HttpParams();

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
    if (this.countWindow() !== '') {
      params = params.set('window', this.countWindow());
    }
    return params;
  }

  // Can be used in the init and found state. Counts the tokens that match the current user input.
  countTokens(): void {
    if (this.currentStep !== 'init') {
      this.notificationService.errorSnackBar('Invalid action.');
      return;
    }
    var params = this.getParams();
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

  // Can be used in the counting state. Finds the serial of the token that matches the current user input.
  findSerial(): void {
    if (this.currentStep !== 'counting') {
      this.notificationService.errorSnackBar('Invalid action.');
      return;
    }
    var params = this.getParams();
    params = params.delete('count');
    this.currentStep = 'searching';
    this.fetchSerial(params).subscribe({
      next: (response) => {
        this.foundSerial = response.result.value.serial;
        this.currentStep = 'found';
      },
    });
  }

  // Communicates with the backend to fetch the serial of the token that matches the current user input.
  fetchSerial(params: HttpParams): Observable<any> {
    var observable = this.tokenService.getSerial(this.otpValue(), params);
    observable.subscribe({
      error: (error) => {
        console.error('Failed to get serial.', error);
        this.notificationService.errorSnackBar('Failed to get serial.');
      },
    });
    return observable;
  }

  // Resets the component to its initial state but keeps the user input.
  reset(): void {
    this.currentStep = 'init';
    this.foundSerial = '';
    this.count = '';
  }

  // Returns true if the count is relatively large.
  countIsLarge(): boolean {
    return parseInt(this.count) > 99;
  }
}
