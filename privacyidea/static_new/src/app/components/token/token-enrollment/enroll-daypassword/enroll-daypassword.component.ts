import { Component, EventEmitter, inject, OnInit, Output } from "@angular/core";
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators
} from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { DaypasswordApiPayloadMapper } from "../../../../mappers/token-api-payload/daypassword-token-api-payload.mapper";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

export interface DaypasswordEnrollmentOptions extends TokenEnrollmentData {
  type: "daypassword";
  otpKey?: string;
  otpLength: number;
  hashAlgorithm: string;
  timeStep: number;
  generateOnServer: boolean;
}

@Component({
  selector: "app-enroll-daypassword",
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    ReactiveFormsModule,
    FormsModule,
    MatHint,
    MatError,
    MatCheckbox
  ],
  templateUrl: "./enroll-daypassword.component.html",
  styleUrl: "./enroll-daypassword.component.scss"
})
export class EnrollDaypasswordComponent implements OnInit {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper: DaypasswordApiPayloadMapper = inject(
    DaypasswordApiPayloadMapper
  );
  readonly otpLengthOptions = [6, 8];
  readonly hashAlgorithmOptions = [
    { value: "sha1", viewValue: "SHA1" },
    { value: "sha256", viewValue: "SHA256" },
    { value: "sha512", viewValue: "SHA512" }
  ];
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === "daypassword")?.text;
  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();
  otpKeyControl = new FormControl<string>("");
  hashAlgorithmControl = new FormControl<string>("sha256", [
    Validators.required
  ]);
  timeStepControl = new FormControl<number | string>(86400, [
    Validators.required
  ]);
  generateOnServerControl = new FormControl(true);
  otpLengthControl = new FormControl<number>(10, [Validators.required]);
  daypasswordForm = new FormGroup({
    otpKey: this.otpKeyControl,
    otpLength: this.otpLengthControl,
    hashAlgorithm: this.hashAlgorithmControl,
    timeStep: this.timeStepControl
  });

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      otpKey: this.otpKeyControl,
      otpLength: this.otpLengthControl,
      hashAlgorithm: this.hashAlgorithmControl,
      timeStep: this.timeStepControl,
      generateOnServer: this.generateOnServerControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.updateOtpKeyControlState(this.generateOnServerControl.value ?? true);

    this.generateOnServerControl.valueChanges.subscribe((generateOnServer) => {
      this.updateOtpKeyControlState(generateOnServer ?? true);
    });
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData
  ): Observable<EnrollmentResponse | null> => {
    if (this.daypasswordForm.invalid) {
      this.daypasswordForm.markAllAsTouched();
      return of(null);
    }
    const enrollmentData: DaypasswordEnrollmentOptions = {
      ...basicOptions,
      type: "daypassword",
      otpLength: this.otpLengthControl.value ?? 10,
      hashAlgorithm: this.hashAlgorithmControl.value ?? "sha256",
      timeStep:
        typeof this.timeStepControl.value === "string"
          ? parseInt(this.timeStepControl.value, 10)
          : (this.timeStepControl.value ?? 86400),
      generateOnServer: !!(this.generateOnServerControl.value ?? true)
    };
    if (!enrollmentData.generateOnServer) {
      enrollmentData.otpKey = this.otpKeyControl.value ?? "";
    }
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };

  private updateOtpKeyControlState(generateOnServer: boolean): void {
    if (generateOnServer) {
      this.otpKeyControl.disable({ emitEvent: false });
      this.otpKeyControl.clearValidators();
    } else {
      this.otpKeyControl.enable({ emitEvent: false });
      this.otpKeyControl.setValidators([
        Validators.required,
        Validators.minLength(16)
      ]);
    }
    this.otpKeyControl.updateValueAndValidity();
  }
}
