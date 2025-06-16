import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import {
  MatError,
  MatFormField,
  MatHint,
  MatLabel,
} from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatOption } from '@angular/material/core';
import { MatSelect } from '@angular/material/select';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import {
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { MatCheckbox } from '@angular/material/checkbox';
import { Observable } from 'rxjs';
import { TokenEnrollmentData } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { DaypasswordApiPayloadMapper } from '../../../../mappers/token-api-payload/daypassword-token-api-payload.mapper';
export interface DaypasswordEnrollmentOptions extends TokenEnrollmentData {
  type: 'daypassword';
  otpKey?: string;
  // Removed otplen, hashlib, timeStep, genkey as per "DO NOT CHANGE OTHER LINES"
  otpLength: number;
  hashAlgorithm: string;
  timeStep: number;
  generateOnServer: boolean;
}

@Component({
  selector: 'app-enroll-daypassword',
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
    MatCheckbox,
  ],
  templateUrl: './enroll-daypassword.component.html',
  styleUrl: './enroll-daypassword.component.scss',
})
export class EnrollDaypasswordComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'daypassword')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: TokenEnrollmentData,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  otpKeyControl = new FormControl<string>(''); // Validators set dynamically

  hashAlgorithmControl = new FormControl<string>('sha256', [
    // Keep original default
    Validators.required,
  ]);
  timeStepControl = new FormControl<number | string>(86400, [
    // Keep original default
    Validators.required,
  ]); // Default to 1 day
  generateOnServerControl = new FormControl(true);
  otpLengthControl = new FormControl<number>(10, [Validators.required]);
  daypasswordForm = new FormGroup({
    otpKey: this.otpKeyControl,
    otpLength: this.otpLengthControl,
    hashAlgorithm: this.hashAlgorithmControl,
    timeStep: this.timeStepControl,
  });

  // Options for the template
  readonly otpLengthOptions = [6, 8]; // Keep original options
  readonly hashAlgorithmOptions = [
    { value: 'sha1', viewValue: 'SHA1' },
    { value: 'sha256', viewValue: 'SHA256' },
    { value: 'sha512', viewValue: 'SHA512' },
  ];
  // Time step is usually fixed for daypassword or configured server-side,
  // but providing an input if it needs to be set.

  constructor(
    private tokenService: TokenService,
    private enrollmentMapper: DaypasswordApiPayloadMapper,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      otpKey: this.otpKeyControl,
      otpLength: this.otpLengthControl,
      hashAlgorithm: this.hashAlgorithmControl,
      timeStep: this.timeStepControl,
      generateOnServer: this.generateOnServerControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    // Initially set the state based on the default value
    this.updateOtpKeyControlState(this.generateOnServerControl.value ?? true);

    // Subscribe to changes to update the state dynamically
    this.generateOnServerControl.valueChanges.subscribe((generateOnServer) => {
      this.updateOtpKeyControlState(generateOnServer ?? true);
    });
  }

  private updateOtpKeyControlState(generateOnServer: boolean): void {
    if (generateOnServer) {
      this.otpKeyControl.disable({ emitEvent: false });
      this.otpKeyControl.clearValidators();
    } else {
      this.otpKeyControl.enable({ emitEvent: false });
      this.otpKeyControl.setValidators([
        Validators.required,
        Validators.minLength(16),
      ]);
    }
    this.otpKeyControl.updateValueAndValidity();
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse> | undefined => {
    if (this.daypasswordForm.invalid) {
      this.daypasswordForm.markAllAsTouched();
      return undefined;
    }
    const enrollmentData: DaypasswordEnrollmentOptions = {
      ...basicOptions,
      type: 'daypassword',
      otpLength: this.otpLengthControl.value ?? 10, // Keep original logic
      hashAlgorithm: this.hashAlgorithmControl.value ?? 'sha256', // Keep original logic
      timeStep:
        typeof this.timeStepControl.value === 'string'
          ? parseInt(this.timeStepControl.value, 10)
          : (this.timeStepControl.value ?? 86400), // Default to 1 day
      generateOnServer: !!(this.generateOnServerControl.value ?? true), // Keep original logic
    };
    if (!enrollmentData.generateOnServer) {
      enrollmentData.otpKey = this.otpKeyControl.value ?? '';
    }
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
