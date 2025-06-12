import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { MatCheckbox } from '@angular/material/checkbox';
import {
  FormControl,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import {
  MatError,
  MatFormField,
  MatHint,
  MatLabel,
  MatOption,
  MatSelect,
} from '@angular/material/select';
import { MatInput } from '@angular/material/input';
import {
  BasicEnrollmentOptions,
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { Observable } from 'rxjs';

export interface HotpEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'hotp';
  generateOnServer: boolean;
  otpLength: number;
  otpKey?: string; // Optional, da es von generateOnServer abhängt
  hashAlgorithm: string;
}

@Component({
  selector: 'app-enroll-hotp',
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
    ReactiveFormsModule,
  ],
  templateUrl: './enroll-hotp.component.html',
  styleUrl: './enroll-hotp.component.scss',
  standalone: true,
})
export class EnrollHotpComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'hotp')?.text;

  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: BasicEnrollmentOptions,
    ) => Observable<EnrollmentResponse> | undefined
  >();
  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();

  generateOnServerFormControl = new FormControl<boolean>(true, [
    Validators.required,
  ]);
  otpLengthFormControl = new FormControl<number>(6, [Validators.required]);
  otpKeyFormControl = new FormControl<string>(''); // Validator wird dynamisch in onClickEnroll geprüft
  hashAlgorithmFormControl = new FormControl<string>('sha1', [
    Validators.required,
  ]);

  // Optionen für das Template
  readonly otpLengthOptions = [6, 7, 8];
  readonly hashAlgorithmOptions = [
    { value: 'sha1', viewValue: 'SHA1' },
    { value: 'sha256', viewValue: 'SHA256' },
    { value: 'sha512', viewValue: 'SHA512' },
  ];

  constructor(private tokenService: TokenService) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      generateOnServer: this.generateOnServerFormControl,
      otpLength: this.otpLengthFormControl,
      otpKey: this.otpKeyFormControl,
      hashAlgorithm: this.hashAlgorithmFormControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    // OTP-Key Validierung basierend auf generateOnServer
    this.generateOnServerFormControl.valueChanges.subscribe((generate) => {
      if (!generate) {
        this.otpKeyFormControl.setValidators([Validators.required]);
      } else {
        this.otpKeyFormControl.clearValidators();
      }
      this.otpKeyFormControl.updateValueAndValidity();
    });
  }

  onClickEnroll = (
    basicOptions: BasicEnrollmentOptions,
  ): Observable<EnrollmentResponse> | undefined => {
    if (
      this.generateOnServerFormControl.invalid ||
      this.otpLengthFormControl.invalid ||
      this.hashAlgorithmFormControl.invalid ||
      (!this.generateOnServerFormControl.value &&
        this.otpKeyFormControl.invalid)
    ) {
      this.generateOnServerFormControl.markAsTouched();
      this.otpLengthFormControl.markAsTouched();
      this.hashAlgorithmFormControl.markAsTouched();
      if (!this.generateOnServerFormControl.value) {
        this.otpKeyFormControl.markAsTouched();
      }
      return undefined;
    }

    const enrollmentData: HotpEnrollmentOptions = {
      ...basicOptions,
      type: 'hotp',
      generateOnServer: !!this.generateOnServerFormControl.value, // Sicherstellen, dass es boolean ist
      otpLength: this.otpLengthFormControl.value ?? 6, // Standardwert, falls null
      hashAlgorithm: this.hashAlgorithmFormControl.value ?? 'sha1', // Standardwert, falls null
    };

    if (!enrollmentData.generateOnServer) {
      enrollmentData.otpKey = this.otpKeyFormControl.value?.trim() ?? '';
    }

    return this.tokenService.enrollToken(enrollmentData);
  };
}
