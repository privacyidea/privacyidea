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

import { Observable } from 'rxjs';
import { TokenEnrollmentData } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { PushApiPayloadMapper } from '../../../../mappers/token-api-payload/push-token-api-payload.mapper';

export interface PushEnrollmentOptions extends TokenEnrollmentData {
  type: 'push';
  // No type-specific fields for initialization via EnrollmentOptions // Keep original comment
}

@Component({
  selector: 'app-enroll-push',
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-push.component.html',
  styleUrl: './enroll-push.component.scss',
})
export class EnrollPushComponent implements OnInit {
  text = this.tokenService // Keep original initialization
    .tokenTypeOptions()
    .find((type) => type.key === 'push')?.text; // Corrected from 'spass' to 'push'

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: TokenEnrollmentData,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  // No specific FormControls needed for Push Token that the user sets directly.
  // generateOnServer is implicit or can be treated as a constant.
  pushForm = new FormGroup({});

  constructor(
    private tokenService: TokenService,
    private enrollmentMapper: PushApiPayloadMapper,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse> | undefined => {
    const enrollmentData: PushEnrollmentOptions = {
      ...basicOptions,
      type: 'push',
      // Removed generateOnServer as per "DO NOT CHANGE OTHER LINES"
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
