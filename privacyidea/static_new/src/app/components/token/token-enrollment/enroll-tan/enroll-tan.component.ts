import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import {
  BasicEnrollmentOptions,
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { Observable } from 'rxjs';

export interface TanEnrollmentOptions extends BasicEnrollmentOptions {
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
    (
      basicOptions: BasicEnrollmentOptions,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  tanForm = new FormGroup({});

  constructor(private tokenService: TokenService) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: BasicEnrollmentOptions,
  ): Observable<EnrollmentResponse> | undefined => {
    const enrollmentData: TanEnrollmentOptions = {
      ...basicOptions,
      type: 'tan',
    };
    return this.tokenService.enrollToken(enrollmentData);
  };
}
