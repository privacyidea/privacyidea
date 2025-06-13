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

export interface PushEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'push';
  // generateOnServer is implicitly true (genkey: 1 in service)
  // For consistency, we can add it if it might be configurable in the future.
  generateOnServer?: boolean; // Defaulted to true by service if not provided, but can be set.
}
@Component({
  selector: 'app-enroll-push',
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-push.component.html',
  styleUrl: './enroll-push.component.scss',
})
export class EnrollPushComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'push')?.text; // Corrected from 'spass' to 'push'

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: BasicEnrollmentOptions,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  // No specific FormControls needed for Push Token that the user sets directly.
  // generateOnServer is implicit or can be treated as a constant.
  pushForm = new FormGroup({});

  constructor(private tokenService: TokenService) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: BasicEnrollmentOptions,
  ): Observable<EnrollmentResponse> | undefined => {
    const enrollmentData: PushEnrollmentOptions = {
      ...basicOptions,
      type: 'push',
      generateOnServer: true, // Explicitly set, as it is typical for Push tokens
    };
    return this.tokenService.enrollToken(enrollmentData);
  };
}
