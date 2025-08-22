import { Component, EventEmitter, inject, Output } from "@angular/core";
import { AbstractControl, FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatError } from "@angular/material/select";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { SshkeyApiPayloadMapper } from "../../../../mappers/token-api-payload/sshkey-token-api-payload.mapper";

export interface SshkeyEnrollmentOptions extends TokenEnrollmentData {
  type: "sshkey";
  sshPublicKey: string;
}

@Component({
  selector: "app-enroll-sshkey",
  imports: [
    FormsModule,
    MatFormField,
    MatInput,
    MatLabel,
    MatError,
    ReactiveFormsModule
  ],
  templateUrl: "./enroll-sshkey.component.html"
})
export class EnrollSshkeyComponent {
  protected readonly enrollmentMapper: SshkeyApiPayloadMapper = inject(
    SshkeyApiPayloadMapper
  );
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === "sshkey")?.text;

  sshPublicKeyFormControl = new FormControl<string>("", [
    Validators.required,
    EnrollSshkeyComponent.sshKeyValidator
  ]);

  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();
  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();

  static sshKeyValidator(
    control: AbstractControl
  ): { [key: string]: boolean } | null {
    const sshKeyPattern =
      /^ssh-(rsa|dss|ed25519|ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|ecdsa-sha2-nistp521) [A-Za-z0-9+/=]+( .+)?$/;
    if (control.value && !sshKeyPattern.test(control.value)) {
      return { invalidSshKey: true };
    }
    return null;
  }

  ngOnInit() {
    this.aditionalFormFieldsChange.emit({
      sshPublicKey: this.sshPublicKeyFormControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData
  ): Observable<EnrollmentResponse | null> => {
    if (this.sshPublicKeyFormControl.invalid) {
      this.sshPublicKeyFormControl.markAsTouched();
      return of(null);
    }

    const sshPublicKey = this.sshPublicKeyFormControl?.value?.trim() ?? "";
    const parts = sshPublicKey.split(" ");
    const sshKeyDescriptionPart = parts.length >= 3 ? parts[2] : "";
    const fullDescription = basicOptions.description
      ? `${basicOptions.description}\n\n${sshKeyDescriptionPart}`.trim()
      : sshKeyDescriptionPart;

    const enrollmentData: SshkeyEnrollmentOptions = {
      ...basicOptions,
      type: "sshkey",
      sshPublicKey: sshPublicKey,
      description: fullDescription
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
