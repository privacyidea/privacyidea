import { Component, EventEmitter, Output } from '@angular/core';
import {
  FormControl,
  FormsModule,
  AbstractControl,
  Validators,
  ReactiveFormsModule,
} from '@angular/forms';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatError } from '@angular/material/select';
import {
  BasicEnrollmentOptions,
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { Observable } from 'rxjs';

/*
Old ui request body example:
{
  "timeStep": 30,
  "otplen": 6,
  "genkey": true,
  "type": "sshkey",
  "hashlib": "sha1",
  "radius.system_settings": true,
  "2stepinit": false,
  "rollover": false,
  "sshkey": "ssh-rsa aaaaaaaaaaaaaaaaaaa",
  "description": "bbbbbbbbbbbbbbbbbbbbb",
  "validity_period_start": "",
  "validity_period_end": ""
}
*/

interface SshEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'sshkey';
  sshkey: string;
  hashlib: string;
  // 'radius.system_settings': boolean;
}

@Component({
  selector: 'app-enroll-sshkey',
  imports: [
    FormsModule,
    MatFormField,
    MatInput,
    MatLabel,
    MatError,
    ReactiveFormsModule,
  ],
  templateUrl: './enroll-sshkey.component.html',
  styleUrl: './enroll-sshkey.component.scss',
})
export class EnrollSshkeyComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'sshkey')?.text;

  sshPublicKeyFormControl = new FormControl<string>('', [
    Validators.required,
    EnrollSshkeyComponent.sshKeyValidator,
  ]);

  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: BasicEnrollmentOptions,
    ) => Observable<EnrollmentResponse> | undefined
  >();
  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();

  constructor(private tokenService: TokenService) {}

  ngOnInit() {
    this.aditionalFormFieldsChange.emit({
      sshPublicKey: this.sshPublicKeyFormControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: BasicEnrollmentOptions,
  ): Observable<EnrollmentResponse> | undefined => {
    console.log('clickEnroll called');
    if (this.sshPublicKeyFormControl.invalid) {
      console.log(
        'SSH Public Key form control is invalid:',
        this.sshPublicKeyFormControl.errors,
      );
      return;
    }
    console.log(
      'SSH Public Key form control is valid:',
      this.sshPublicKeyFormControl.value,
    );

    const sshPublicKey = this.sshPublicKeyFormControl?.value?.trim() ?? '';
    const parts = sshPublicKey.split(' ');
    const sshKeyDescriptionPart = parts.length >= 3 ? parts[2] : '';
    const fullDescription = basicOptions.description
      ? `${basicOptions.description}\n\n${sshKeyDescriptionPart}`.trim()
      : sshKeyDescriptionPart;
    console.log('Full description:', fullDescription);
    console.log('sskkey:', sshPublicKey);

    const response = this.tokenService.enrollToken<SshEnrollmentOptions>({
      sshkey: sshPublicKey,
      hashlib: 'sha1', // Default value, can be changed if needed
      // 'radius.system_settings': true, // Default value, can be changed if needed
      type: 'sshkey',
      description: fullDescription,
      container_serial: basicOptions.container_serial,
      validity_period_start: basicOptions.validity_period_start,
      validity_period_end: basicOptions.validity_period_end,
      user: basicOptions.user,
      pin: basicOptions.pin,
    });
    return response;
  };

  static sshKeyValidator(
    control: AbstractControl,
  ): { [key: string]: boolean } | null {
    const sshKeyPattern =
      /^ssh-(rsa|dss|ed25519|ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|ecdsa-sha2-nistp521) [A-Za-z0-9+/=]+( .+)?$/;
    if (control.value && !sshKeyPattern.test(control.value)) {
      return { invalidSshKey: true };
    }
    return null;
  }
}
