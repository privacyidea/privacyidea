import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import {
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';

import { Observable, of } from 'rxjs';
import { TokenEnrollmentData } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { TanApiPayloadMapper } from '../../../../mappers/token-api-payload/tan-token-api-payload.mapper';

export interface TanEnrollmentOptions extends TokenEnrollmentData {
  type: 'tan';
  // No type-specific fields for initialization via EnrollmentOptions
}
@Component({
  selector: 'app-enroll-tan',
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-tan.component.html',
  styleUrl: './enroll-tan.component.scss',
})
export class EnrollTanComponent implements OnInit {
  text = this.tokenService.tokenTypeOptions().find((type) => type.key === 'tan')
    ?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  tanForm = new FormGroup({});

  constructor(
    private tokenService: TokenService,
    private enrollmentMapper: TanApiPayloadMapper,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse | null> => {
    const enrollmentData: TanEnrollmentOptions = {
      ...basicOptions,
      type: 'tan',
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
