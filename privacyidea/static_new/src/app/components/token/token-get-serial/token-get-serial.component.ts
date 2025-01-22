import {Component} from '@angular/core';
import {MatOption} from '@angular/material/core';
import {MatFormField} from '@angular/material/form-field';
import {MatInput} from '@angular/material/input';
import {MatSelect} from '@angular/material/select';

@Component({
  selector: 'app-token-get-serial',
  imports: [
    MatFormField,
    MatInput,
    MatSelect,
    MatOption,
  ],
  templateUrl: './token-get-serial.component.html',
  styleUrl: './token-get-serial.component.scss',
})
export class TokenGetSerial {
  otpValue: string = '';
  tokenType: string = '';
  assignmentState: string = '';
  serialSubstring: string = '';
  countWindow: string = '';

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
    console.log(
      'Getting serial based on values: [ otpValue: ' +
      this.otpValue +
      ', tokenType: ' +
      this.tokenType +
      ', assignmentState: ' +
      this.assignmentState +
      ', serialSubstring: ' +
      this.serialSubstring +
      ', countWindow: ' +
      this.countWindow +
      ' ]'
    );
  }
}
