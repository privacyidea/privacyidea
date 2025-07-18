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
import { PaperApiPayloadMapper } from '../../../../mappers/token-api-payload/paper-token-api-payload.mapper';

export interface PaperEnrollmentOptions extends TokenEnrollmentData {
  type: 'paper';
}

@Component({
  selector: 'app-enroll-paper',
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-paper.component.html',
  styleUrl: './enroll-paper.component.scss',
})
export class EnrollPaperComponent implements OnInit {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper: PaperApiPayloadMapper = inject(
    PaperApiPayloadMapper,
  );

  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'paper')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  paperForm = new FormGroup({});

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse | null> => {
    const enrollmentData: PaperEnrollmentOptions = {
      ...basicOptions,
      type: 'paper',
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
