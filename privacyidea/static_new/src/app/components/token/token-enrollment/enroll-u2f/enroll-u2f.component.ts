import { Component, EventEmitter, Inject, OnInit, Output } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../../services/token/token.service';

import { Observable } from 'rxjs';
import {
  EnrollmentResponse,
  TokenEnrollmentData,
} from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { U2fApiPayloadMapper } from '../../../../mappers/token-api-payload/u2f-token-api-payload.mapper';

export interface U2fEnrollmentOptions extends TokenEnrollmentData {
  type: 'u2f';
  // No type-specific fields for initialization via EnrollmentOptions
}
@Component({
  selector: 'app-enroll-u2f',
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-u2f.component.html',
  styleUrl: './enroll-u2f.component.scss',
})
export class EnrollU2fComponent implements OnInit {
  text = this.tokenService.tokenTypeOptions().find((type) => type.key === 'u2f')
    ?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  u2fForm = new FormGroup({}); // No specific controls for U2F

  constructor(
    @Inject(TokenService)
    private readonly tokenService: TokenServiceInterface,
    private enrollmentMapper: U2fApiPayloadMapper,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse | null> => {
    const enrollmentData: U2fEnrollmentOptions = {
      ...basicOptions,
      type: 'u2f',
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
