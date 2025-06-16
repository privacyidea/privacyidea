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
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';

import { Observable } from 'rxjs';
import { TokenEnrollmentData } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { SshkeyApiPayloadMapper } from '../../../../mappers/token-api-payload/sshkey-token-api-payload.mapper';

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

export interface SshkeyEnrollmentOptions extends TokenEnrollmentData {
  type: 'sshkey';
  sshPublicKey: string;
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
      basicOptions: TokenEnrollmentData,
    ) => Observable<EnrollmentResponse> | undefined
  >();
  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();

  constructor(
    private tokenService: TokenService,
    private enrollmentMapper: SshkeyApiPayloadMapper,
  ) {}

  ngOnInit() {
    this.aditionalFormFieldsChange.emit({
      // Keep original emit
      sshPublicKey: this.sshPublicKeyFormControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse> | undefined => {
    if (this.sshPublicKeyFormControl.invalid) {
      this.sshPublicKeyFormControl.markAsTouched(); // Keep original touch logic
      return undefined;
    }

    const sshPublicKey = this.sshPublicKeyFormControl?.value?.trim() ?? '';
    const parts = sshPublicKey.split(' ');
    const sshKeyDescriptionPart = parts.length >= 3 ? parts[2] : '';
    const fullDescription = basicOptions.description
      ? `${basicOptions.description}\n\n${sshKeyDescriptionPart}`.trim()
      : sshKeyDescriptionPart;

    const enrollmentData: SshkeyEnrollmentOptions = {
      // Keep original data structure
      ...basicOptions,
      type: 'sshkey',
      sshPublicKey: sshPublicKey,
      description: fullDescription,
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    }); // Apply the requested change
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
