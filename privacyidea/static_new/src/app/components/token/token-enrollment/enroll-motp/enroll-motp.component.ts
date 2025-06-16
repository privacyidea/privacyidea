import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  ValidationErrors,
  AbstractControl,
  Validators,
} from '@angular/forms';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatCheckbox } from '@angular/material/checkbox';
import {
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';

import { Observable } from 'rxjs';
import { TokenEnrollmentData } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { MotpApiPayloadMapper } from '../../../../mappers/token-api-payload/motp-token-api-payload.mapper';

export interface MotpEnrollmentOptions extends TokenEnrollmentData {
  type: 'motp';
  generateOnServer: boolean;
  otpKey?: string;
  motpPin: string;
}

@Component({
  selector: 'app-enroll-motp',
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    MatFormField,
    MatInput,
    MatLabel,
    MatCheckbox,
    MatError,
  ],
  templateUrl: './enroll-motp.component.html',
  styleUrl: './enroll-motp.component.scss',
})
export class EnrollMotpComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'motp')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: TokenEnrollmentData,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  generateOnServerControl = new FormControl<boolean>(true, [
    Validators.required,
  ]);
  otpKeyControl = new FormControl<string>(''); // Validator is set dynamically
  motpPinControl = new FormControl<string>('', [
    Validators.required,
    Validators.minLength(4),
  ]);
  repeatMotpPinControl = new FormControl<string>('', [
    Validators.required,
    (control: AbstractControl) =>
      EnrollMotpComponent.motpPinMismatchValidator(
        this.motpPinControl,
        control,
      ),
  ]);

  static motpPinMismatchValidator(
    motpPin: AbstractControl,
    repeatMotpPin: AbstractControl,
  ): ValidationErrors | null {
    console.log('Validating motpPin: ', motpPin?.value);
    console.log('Validating repeatMotpPin: ', repeatMotpPin?.value);
    if (motpPin && repeatMotpPin && motpPin.value !== repeatMotpPin.value) {
      console.log(
        'Validating motpPin mismatch: ',
        motpPin.value,
        repeatMotpPin.value,
      );
      return { motpPinMismatch: true };
    }
    console.log(
      'Validating motpPin match: ',
      motpPin?.value,
      repeatMotpPin?.value,
    );
    return null;
  }

  constructor(
    private tokenService: TokenService,
    private enrollmentMapper: MotpApiPayloadMapper,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      generateOnServer: this.generateOnServerControl,
      otpKey: this.otpKeyControl,
      motpPin: this.motpPinControl,
      repeatMotpPin: this.repeatMotpPinControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.generateOnServerControl.valueChanges.subscribe((generate) => {
      if (!generate) {
        this.otpKeyControl.setValidators([Validators.required]);
      } else {
        this.otpKeyControl.clearValidators();
      }
      this.otpKeyControl.updateValueAndValidity();
    });

    // Explicitly trigger form re-validation when PIN controls change
    this.motpPinControl.valueChanges.subscribe(() => {
      this.repeatMotpPinControl.updateValueAndValidity();
    });
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse> | undefined => {
    const enrollmentData: MotpEnrollmentOptions = {
      ...basicOptions,
      type: 'motp',
      generateOnServer: !!this.generateOnServerControl.value,
      motpPin: this.motpPinControl.value ?? '',
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
