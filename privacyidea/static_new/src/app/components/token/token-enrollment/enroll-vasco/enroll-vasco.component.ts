import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatCheckbox } from '@angular/material/checkbox';
import { ErrorStateMatcher } from '@angular/material/core';
import { TokenService } from '../../../../services/token/token.service';

import { Observable, of } from 'rxjs';
import {
  EnrollmentResponse,
  TokenEnrollmentData,
} from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { VascoApiPayloadMapper } from '../../../../mappers/token-api-payload/vasco-token-api-payload.mapper';

export interface VascoEnrollmentOptions extends TokenEnrollmentData {
  type: 'vasco';
  otpKey?: string;
  useVascoSerial: boolean; // Keep original type
  vascoSerial?: string;
}

export class VascoErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid =
      control && control.value ? control.value.length !== 496 : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

@Component({
  selector: 'app-enroll-vasco',
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatCheckbox,
    MatError,
  ],
  templateUrl: './enroll-vasco.component.html',
  styleUrl: './enroll-vasco.component.scss',
})
export class EnrollVascoComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'vasco')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  otpKeyControl = new FormControl<string>(''); // Validator is set dynamically
  useVascoSerialControl = new FormControl<boolean>(false, [
    Validators.required,
  ]);
  vascoSerialControl = new FormControl<string>(''); // Validator is set dynamically

  vascoForm = new FormGroup({
    otpKey: this.otpKeyControl,
    useVascoSerial: this.useVascoSerialControl,
    vascoSerial: this.vascoSerialControl,
  });

  vascoErrorStatematcher = new VascoErrorStateMatcher();

  constructor(
    private tokenService: TokenService,
    private enrollmentMapper: VascoApiPayloadMapper,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      otpKey: this.otpKeyControl,
      useVascoSerial: this.useVascoSerialControl,
      vascoSerial: this.vascoSerialControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.useVascoSerialControl.valueChanges.subscribe((useSerial) => {
      if (useSerial) {
        this.vascoSerialControl.setValidators([Validators.required]);
        this.otpKeyControl.clearValidators();
      } else {
        this.otpKeyControl.setValidators([
          Validators.required,
          Validators.minLength(496), // Vasco OTP key length
          Validators.maxLength(496),
        ]);
        this.vascoSerialControl.clearValidators();
      }
      this.otpKeyControl.updateValueAndValidity();
      this.vascoSerialControl.updateValueAndValidity();
    });
    // Initial call to set validators based on default useVascoSerialControl value
    this.useVascoSerialControl.updateValueAndValidity();
  }

  static convertOtpKeyToVascoSerial(otpHex: string): string {
    let vascoOtpStr = '';
    if (!otpHex || otpHex.length !== 496) {
      // Expecting 248 bytes hex encoded
      return ''; // Or handle error appropriately
    }
    for (let i = 0; i < otpHex.length; i += 2) {
      vascoOtpStr += String.fromCharCode(parseInt(otpHex.slice(i, i + 2), 16));
    }
    return vascoOtpStr.slice(0, 10);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse | null> => {
    if (this.vascoForm.invalid) {
      this.vascoForm.markAllAsTouched();
      return of(null);
    }

    const enrollmentData: VascoEnrollmentOptions = {
      ...basicOptions,
      type: 'vasco',
      useVascoSerial: !!this.useVascoSerialControl.value,
    };

    if (enrollmentData.useVascoSerial) {
      enrollmentData.vascoSerial = this.vascoSerialControl.value ?? '';
    } else {
      enrollmentData.otpKey = this.otpKeyControl.value ?? '';
    }
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
