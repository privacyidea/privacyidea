import { Component, EventEmitter, inject, OnInit, Output } from "@angular/core";
import {
  AbstractControl,
  FormControl,
  FormsModule,
  ReactiveFormsModule,
  ValidationErrors,
  Validators
} from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { MotpApiPayloadMapper } from "../../../../mappers/token-api-payload/motp-token-api-payload.mapper";

export interface MotpEnrollmentOptions extends TokenEnrollmentData {
  type: "motp";
  generateOnServer: boolean;
  otpKey?: string;
  motpPin: string;
}

@Component({
  selector: "app-enroll-motp",
  standalone: true,
  imports: [FormsModule, ReactiveFormsModule, MatFormField, MatInput, MatLabel, MatCheckbox, MatError],
  templateUrl: "./enroll-motp.component.html",
  styleUrl: "./enroll-motp.component.scss"
})
export class EnrollMotpComponent implements OnInit {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper: MotpApiPayloadMapper = inject(MotpApiPayloadMapper);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  generateOnServerControl = new FormControl<boolean>(true, [Validators.required]);
  otpKeyFormControl = new FormControl<string>({ value: "", disabled: true });
  motpPinControl = new FormControl<string>("", [Validators.required, Validators.minLength(4)]);
  repeatMotpPinControl = new FormControl<string>("", [
    Validators.required,
    (control: AbstractControl) => EnrollMotpComponent.motpPinMismatchValidator(this.motpPinControl, control)
  ]);

  static motpPinMismatchValidator(motpPin: AbstractControl, repeatMotpPin: AbstractControl): ValidationErrors | null {
    if (motpPin && repeatMotpPin && motpPin.value !== repeatMotpPin.value) {
      return { motpPinMismatch: true };
    }
    return null;
  }

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      generateOnServer: this.generateOnServerControl,
      otpKey: this.otpKeyFormControl,
      motpPin: this.motpPinControl,
      repeatMotpPin: this.repeatMotpPinControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.generateOnServerControl.valueChanges.subscribe((generate) => {
      if (!generate) {
        this.otpKeyFormControl.enable({ emitEvent: false });
        this.otpKeyFormControl.setValidators([Validators.required]);
      } else {
        this.otpKeyFormControl.disable({ emitEvent: false });
        this.otpKeyFormControl.clearValidators();
      }
      this.otpKeyFormControl.updateValueAndValidity();
    });

    this.motpPinControl.valueChanges.subscribe(() => {
      this.repeatMotpPinControl.updateValueAndValidity();
    });
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    const enrollmentData: MotpEnrollmentOptions = {
      ...basicOptions,
      type: "motp",
      generateOnServer: !!this.generateOnServerControl.value,
      motpPin: this.motpPinControl.value ?? ""
    };
    if (!enrollmentData.generateOnServer) {
      enrollmentData.otpKey = this.otpKeyFormControl.value ?? "";
    }
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
