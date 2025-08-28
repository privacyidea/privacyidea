import { Component, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { RegistrationApiPayloadMapper } from "../../../../mappers/token-api-payload/registration-token-api-payload.mapper";

export interface RegistrationEnrollmentOptions extends TokenEnrollmentData {
  type: "registration";
}

@Component({
  selector: "app-enroll-registration",
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: "./enroll-registration.component.html",
  styleUrl: "./enroll-registration.component.scss"
})
export class EnrollRegistrationComponent implements OnInit {
  protected readonly enrollmentMapper: RegistrationApiPayloadMapper = inject(RegistrationApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  registrationForm = new FormGroup({});

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    const enrollmentData: RegistrationEnrollmentOptions = {
      ...basicOptions,
      type: "registration"
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
