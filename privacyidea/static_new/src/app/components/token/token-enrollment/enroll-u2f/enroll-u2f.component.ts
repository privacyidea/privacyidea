import { Component, EventEmitter, OnInit, Output, inject } from '@angular/core';
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
}
@Component({
  selector: 'app-enroll-u2f',
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-u2f.component.html',
  styleUrl: './enroll-u2f.component.scss',
})
export class EnrollU2fComponent implements OnInit {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper: U2fApiPayloadMapper =
    inject(U2fApiPayloadMapper);

  text = this.tokenService.tokenTypeOptions().find((type) => type.key === 'u2f')
    ?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  u2fForm = new FormGroup({});

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
