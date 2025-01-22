import { Component, Input, signal } from '@angular/core';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatOption } from '@angular/material/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatSelect } from '@angular/material/select';
import { TokenService } from '../../../../services/token/token.service';
import { NotificationService } from '../../../../services/notification/notification.service';
import { HttpParams } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-token-get-serial',
  imports: [
    FormsModule,
    MatCard,
    MatCardContent,
    MatFormField,
    MatLabel,
    MatInput,
    MatSelect,
    MatOption,
  ],
  templateUrl: './token-get-serial.component.html',
  styleUrl: './token-get-serial.component.scss',
})
export class TokenGetSerial {
  @Input() otpValue = '';
  @Input() tokenType = '';
  @Input() assignmentState = '';
  @Input() serialSubstring = '';
  @Input() countWindow = '';

  // possible steps: init, count, searching, found
  currentStep: string = 'init';
  foundSerial: string = '';
  count: string = '';

  constructor(
    private tokenService: TokenService,
    private notificationService: NotificationService
  ) {}

  tokenTypes: Map<string, string> = new Map([
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
    ['assigned', 'The token is assigned to a user'],
    ['unassigned', 'The token is not assigned to a user'],
    ["don't care", 'It does not matter, if the token is assigned or not'],
  ]);

  getSerial(): void {
    if (this.otpValue === '') {
      this.notificationService.errorSnackBar('Please enter an OTP value.');
      return;
    }
    var params = new Map<string, string>();

    if (this.assignmentState === 'assigned') {
      params.set('assigned', '1');
    }
    if (this.assignmentState === 'unassigned') {
      params.set('unassigned', '1');
    }

    switch (this.currentStep) {
      case 'init':
      case 'found':
        this.initGetSerial(params);
        break;
      case 'count':
        this.countGetSerial(params);
        break;
      case 'searching':
        break;
    }
  }

  initGetSerial(params: Map<string, string>): void {
    params.delete('count');
    this.tokenService.getSerial(
      this.otpValue,
      new HttpParams({ fromObject: Object.fromEntries(params) }),
      this.getSerialCallback.bind(this)
    );
  }

  countGetSerial(params: Map<string, string>): void {
    params.set('count', '1');
    this.tokenService.getSerial(
      this.otpValue,
      new HttpParams({ fromObject: Object.fromEntries(params) }),
      this.getSerialCallback.bind(this)
    );
  }

  getSerialCallback(data: any): void {
    this.foundSerial = data.result.value.serial;
    this.count = data.result.value['count'];
    if (this.currentStep === 'searching') {
      this.currentStep = 'found';
    }
    console.log(data);
  }
}
