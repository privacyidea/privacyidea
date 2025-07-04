import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import { TokenService } from '../../../../services/token/token.service';

import { Observable, of } from 'rxjs';
import {
  EnrollmentResponse,
  TokenEnrollmentData,
} from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { RegistrationApiPayloadMapper } from '../../../../mappers/token-api-payload/registration-token-api-payload.mapper';

export interface RegistrationEnrollmentOptions extends TokenEnrollmentData {
  type: 'registration';
  // No type-specific fields for initialization via EnrollmentOptions
}
@Component({
  selector: 'app-enroll-registration',
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-registration.component.html',
  styleUrl: './enroll-registration.component.scss',
})
export class EnrollRegistrationComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'registration')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  registrationForm = new FormGroup({});

  constructor(
    private tokenService: TokenService,
    private enrollmentMapper: RegistrationApiPayloadMapper,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse | null> => {
    const enrollmentData: RegistrationEnrollmentOptions = {
      ...basicOptions,
      type: 'registration',
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
