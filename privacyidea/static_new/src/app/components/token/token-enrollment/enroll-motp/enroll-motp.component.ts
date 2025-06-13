import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatCheckbox } from '@angular/material/checkbox';
import {
  BasicEnrollmentOptions,
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { Observable } from 'rxjs';

export interface MotpEnrollmentOptions extends BasicEnrollmentOptions {
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
      basicOptions: BasicEnrollmentOptions,
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
  repeatMotpPinControl = new FormControl<string>('', [Validators.required]);

  motpForm = new FormGroup({
    generateOnServer: this.generateOnServerControl,
    otpKey: this.otpKeyControl,
    motpPin: this.motpPinControl,
    repeatMotpPin: this.repeatMotpPinControl,
  });

  constructor(private tokenService: TokenService) {}

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
  }

  onClickEnroll = (
    basicOptions: BasicEnrollmentOptions,
  ): Observable<EnrollmentResponse> | undefined => {
    if (
      this.motpForm.invalid ||
      this.motpPinControl.value !== this.repeatMotpPinControl.value
    ) {
      this.motpForm.markAllAsTouched();
      return undefined;
    }
    const enrollmentData: MotpEnrollmentOptions = {
      ...basicOptions,
      type: 'motp',
      generateOnServer: !!this.generateOnServerControl.value,
      motpPin: this.motpPinControl.value ?? '',
    };
    if (!enrollmentData.generateOnServer) {
      enrollmentData.otpKey = this.otpKeyControl.value ?? '';
    }
    return this.tokenService.enrollToken(enrollmentData);
  };
}
