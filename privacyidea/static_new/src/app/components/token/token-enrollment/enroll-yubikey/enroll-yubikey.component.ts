import { CommonModule } from "@angular/common";
import { Component, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";

import { MatOptionModule } from "@angular/material/core";
import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import {
  YubikeyApiPayloadMapper,
  YubikeyEnrollmentData
} from "../../../../mappers/token-api-payload/yubikey-token-api-payload.mapper";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

@Component({
  selector: "app-enroll-yubikey",
  templateUrl: "./enroll-yubikey.component.html",
  styleUrls: ["./enroll-yubikey.component.scss"],
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatOptionModule
  ]
})
export class EnrollYubikeyComponent implements OnInit {
  protected readonly enrollmentMapper: YubikeyApiPayloadMapper = inject(
    YubikeyApiPayloadMapper
  );
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  testYubiKeyControl = new FormControl("");
  otpKeyControl = new FormControl("", [
    Validators.required,
    Validators.minLength(32),
    Validators.maxLength(32)
  ]);
  otpLengthControl = new FormControl<number | null>(44, [Validators.required]);

  yubikeyForm = new FormGroup({
    otpKey: this.otpKeyControl,
    otpLength: this.otpLengthControl
  });

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      otpKey: this.otpKeyControl,
      otpLength: this.otpLengthControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData
  ): Observable<EnrollmentResponse | null> => {
    this.yubikeyForm.updateValueAndValidity();
    if (this.yubikeyForm.invalid) {
      console.log(this.otpKeyControl.value);
      console.log(this.yubikeyForm.value);
      this.yubikeyForm.markAllAsTouched();
      return of(null);
    }

    const enrollmentData: YubikeyEnrollmentData = {
      ...basicOptions,
      type: "yubikey",
      otpKey: this.otpKeyControl.value,
      otpLength: this.otpLengthControl.value
    };

    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
