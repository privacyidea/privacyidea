import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatCheckbox } from '@angular/material/checkbox';
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
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { TokenEnrollmentData } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { Observable, of } from 'rxjs';
import { TotpApiPayloadMapper } from '../../../../mappers/token-api-payload/totp-token-api-payload.mapper';

export interface TotpEnrollmentOptions extends TokenEnrollmentData {
  type: 'totp';
  generateOnServer: boolean;
  otpLength: number;
  otpKey?: string;
  hashAlgorithm: string;
  timeStep: number;
}
@Component({
  selector: 'app-enroll-totp',
  standalone: true,
  imports: [
    FormsModule,
    MatCheckbox,
    MatFormField,
    MatHint,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    MatError,
    ReactiveFormsModule,
  ],
  templateUrl: './enroll-totp.component.html',
  styleUrl: './enroll-totp.component.scss',
})
export class EnrollTotpComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'totp')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  generateOnServerControl = new FormControl<boolean>(true, [
    Validators.required,
  ]);
  otpLengthControl = new FormControl<number>(6, [Validators.required]);
  otpKeyControl = new FormControl<string>(''); // Validator is set dynamically
  hashAlgorithmControl = new FormControl<string>('sha1', [Validators.required]);
  timeStepControl = new FormControl<number | string>(30, [Validators.required]);

  totpForm = new FormGroup({
    generateOnServer: this.generateOnServerControl,
    otpLength: this.otpLengthControl,
    otpKey: this.otpKeyControl,
    hashAlgorithm: this.hashAlgorithmControl,
    timeStep: this.timeStepControl,
  });

  readonly otpLengthOptions = [6, 8];
  readonly hashAlgorithmOptions = [
    // Keep original options
    { value: 'sha1', viewValue: 'SHA1' },
    { value: 'sha256', viewValue: 'SHA256' },
    { value: 'sha512', viewValue: 'SHA512' },
  ];
  readonly timeStepOptions = [30, 60];

  constructor(
    private tokenService: TokenService,
    private enrollmentMapper: TotpApiPayloadMapper,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      generateOnServer: this.generateOnServerControl,
      otpLength: this.otpLengthControl,
      otpKey: this.otpKeyControl,
      hashAlgorithm: this.hashAlgorithmControl,
      timeStep: this.timeStepControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.generateOnServerControl.valueChanges.subscribe((generate) => {
      if (!generate) {
        this.otpKeyControl.setValidators([
          Validators.required,
          Validators.minLength(16),
        ]);
      } else {
        this.otpKeyControl.clearValidators();
      }
      this.otpKeyControl.updateValueAndValidity();
    });
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse | null> => {
    if (this.totpForm.invalid) {
      this.totpForm.markAllAsTouched();
      return of(null);
    }
    const timeStepValue =
      typeof this.timeStepControl.value === 'string'
        ? parseInt(this.timeStepControl.value, 10)
        : (this.timeStepControl.value ?? 30);

    const enrollmentData: TotpEnrollmentOptions = {
      ...basicOptions,
      type: 'totp',
      generateOnServer: !!this.generateOnServerControl.value,
      otpLength: this.otpLengthControl.value ?? 6,
      hashAlgorithm: this.hashAlgorithmControl.value ?? 'sha1',
      timeStep: timeStepValue,
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
