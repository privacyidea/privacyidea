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
import { PaperApiPayloadMapper } from '../../../../mappers/token-api-payload/paper-token-api-payload.mapper';

export interface PaperEnrollmentOptions extends TokenEnrollmentData {
  type: 'paper';
  // No type-specific fields for initialization via EnrollmentOptions // Keep original comment
}

@Component({
  selector: 'app-enroll-paper',
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-paper.component.html',
  styleUrl: './enroll-paper.component.scss',
})
export class EnrollPaperComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'paper')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();
  // Removed otpLengthControl and otpCountControl as per "DO NOT CHANGE OTHER LINES"

  // No specific FormControls needed for Paper Token.
  paperForm = new FormGroup({}); // Keep original form group

  constructor(
    private tokenService: TokenService,
    private enrollmentMapper: PaperApiPayloadMapper,
  ) {}

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
      // Removed otpLength and otpCount from enrollmentData as per "DO NOT CHANGE OTHER LINES"
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
