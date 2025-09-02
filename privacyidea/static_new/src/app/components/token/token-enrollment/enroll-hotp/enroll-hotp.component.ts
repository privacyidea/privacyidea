import { Component, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatInput } from "@angular/material/input";
import { MatError, MatFormField, MatHint, MatLabel, MatOption, MatSelect } from "@angular/material/select";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { HotpApiPayloadMapper } from "../../../../mappers/token-api-payload/hotp-token-api-payload.mapper";

export interface HotpEnrollmentOptions extends TokenEnrollmentData {
  type: "hotp";
  generateOnServer: boolean;
  otpLength: number;
  otpKey?: string;
  hashAlgorithm: string;
}

@Component({
  selector: "app-enroll-hotp",
  imports: [
    MatCheckbox,
    FormsModule,
    MatSelect,
    MatOption,
    MatLabel,
    MatFormField,
    MatInput,
    MatHint,
    MatError,
    ReactiveFormsModule
  ],
  templateUrl: "./enroll-hotp.component.html",
  styleUrl: "./enroll-hotp.component.scss",
  standalone: true
})
export class EnrollHotpComponent implements OnInit {
  protected readonly enrollmentMapper: HotpApiPayloadMapper = inject(HotpApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  readonly otpLengthOptions = [6, 8];
  readonly hashAlgorithmOptions = [
    { value: "sha1", viewValue: "SHA1" },
    { value: "sha256", viewValue: "SHA256" },
    { value: "sha512", viewValue: "SHA512" }
  ];
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();
  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  generateOnServerFormControl = new FormControl<boolean>(true, [Validators.required]);
  otpLengthFormControl = new FormControl<number>(6, [Validators.required]);
  otpKeyFormControl = new FormControl<string>({ value: "", disabled: true });
  hashAlgorithmFormControl = new FormControl<string>("sha1", [Validators.required]);

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      generateOnServer: this.generateOnServerFormControl,
      otpLength: this.otpLengthFormControl,
      otpKey: this.otpKeyFormControl,
      hashAlgorithm: this.hashAlgorithmFormControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.generateOnServerFormControl.valueChanges.subscribe((generate) => {
      if (!generate) {
        this.otpKeyFormControl.enable({ emitEvent: false });
        this.otpKeyFormControl.setValidators([Validators.required]);
      } else {
        this.otpKeyFormControl.disable({ emitEvent: false });
        this.otpKeyFormControl.clearValidators();
      }
      this.otpKeyFormControl.updateValueAndValidity();
    });
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    if (
      this.generateOnServerFormControl.invalid ||
      this.otpLengthFormControl.invalid ||
      this.hashAlgorithmFormControl.invalid ||
      (!this.generateOnServerFormControl.value && this.otpKeyFormControl.invalid)
    ) {
      this.generateOnServerFormControl.markAsTouched();
      this.otpLengthFormControl.markAsTouched();
      this.hashAlgorithmFormControl.markAsTouched();
      if (!this.generateOnServerFormControl.value) {
        this.otpKeyFormControl.markAsTouched();
      }
      return of(null);
    }

    const enrollmentData: HotpEnrollmentOptions = {
      ...basicOptions,
      type: "hotp",
      generateOnServer: !!this.generateOnServerFormControl.value,
      otpLength: this.otpLengthFormControl.value ?? 6,
      hashAlgorithm: this.hashAlgorithmFormControl.value ?? "sha1"
    };

    if (!enrollmentData.generateOnServer) {
      enrollmentData.otpKey = this.otpKeyFormControl.value?.trim() ?? "";
    }
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
