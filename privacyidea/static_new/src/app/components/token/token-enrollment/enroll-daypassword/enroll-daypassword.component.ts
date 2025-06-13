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
  BasicEnrollmentOptions,
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { Observable } from 'rxjs';

export interface DaypasswordEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'daypassword';
  otpKey: string;
  otpLength: number;
  hashAlgorithm: string;
  timeStep: number | string;
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
      basicOptions: BasicEnrollmentOptions,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  otpKeyControl = new FormControl<string>('', [
    Validators.required,
    Validators.minLength(16),
  ]);
  otpLengthControl = new FormControl<number>(10, [Validators.required]);
  hashAlgorithmControl = new FormControl<string>('sha256', [
    Validators.required,
  ]);
  timeStepControl = new FormControl<number | string>(86400, [
    Validators.required,
  ]); // Default to 1 day

  daypasswordForm = new FormGroup({
    otpKey: this.otpKeyControl,
    otpLength: this.otpLengthControl,
    hashAlgorithm: this.hashAlgorithmControl,
    timeStep: this.timeStepControl,
  });

  // Options for the template
  readonly otpLengthOptions = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16];
  readonly hashAlgorithmOptions = [
    { value: 'sha1', viewValue: 'SHA1' },
    { value: 'sha256', viewValue: 'SHA256' },
    { value: 'sha512', viewValue: 'SHA512' },
  ];
  // Time step is usually fixed for daypassword or configured server-side,
  // but providing an input if it needs to be set.

  constructor(private tokenService: TokenService) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      otpKey: this.otpKeyControl,
      otpLength: this.otpLengthControl,
      hashAlgorithm: this.hashAlgorithmControl,
      timeStep: this.timeStepControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: BasicEnrollmentOptions,
  ): Observable<EnrollmentResponse> | undefined => {
    if (this.daypasswordForm.invalid) {
      this.daypasswordForm.markAllAsTouched();
      return undefined;
    }
    const enrollmentData: DaypasswordEnrollmentOptions = {
      ...basicOptions,
      type: 'daypassword',
      otpKey: this.otpKeyControl.value ?? '',
      otpLength: this.otpLengthControl.value ?? 10,
      hashAlgorithm: this.hashAlgorithmControl.value ?? 'sha256',
      timeStep: this.timeStepControl.value ?? 86400,
    };
    return this.tokenService.enrollToken(enrollmentData);
  };
}
