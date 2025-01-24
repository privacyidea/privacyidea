import {Component} from '@angular/core';
import {MatOption} from '@angular/material/core';
import {MatFormField} from '@angular/material/form-field';
import {MatInput} from '@angular/material/input';
import {MatSelect} from '@angular/material/select';
import {TokenComponent} from '../token.component';

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
  tokenTypes: { key: string; info: string }[] = [];

  assignmentStates: Map<string, string> = new Map([
    ['assigned', 'The token is assigned to a user'],
    ['unassigned', 'The token is not assigned to a user'],
    ["don't care", 'It does not matter, if the token is assigned or not'],
  ]);

  constructor() {
    const tokenWithOTP = ['hotp', 'totp', 'spass', 'motp', 'sshkey', 'yubikey', 'remote', 'yubico', 'radius', 'sms'];
    this.tokenTypes = TokenComponent.tokenTypes.filter((type) => tokenWithOTP.includes(type.key));
  }

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
