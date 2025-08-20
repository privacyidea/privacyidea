import { Component, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { IndexedSecretApiPayloadMapper } from "../../../../mappers/token-api-payload/indexedsecret-token-api-payload.mapper";

export interface IndexedSecretEnrollmentOptions extends TokenEnrollmentData {
  type: "indexedsecret";
  otpKey: string;
}

@Component({
  selector: "app-enroll-indexedsecret",
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatError
  ],
  templateUrl: "./enroll-indexedsecret.component.html",
  styleUrl: "./enroll-indexedsecret.component.scss"
})
export class EnrollIndexedsecretComponent implements OnInit {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper: IndexedSecretApiPayloadMapper = inject(
    IndexedSecretApiPayloadMapper
  );

  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === "indexedsecret")?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  otpKeyControl = new FormControl<string>("", [
    Validators.required,
    Validators.minLength(16)
  ]);

  indexedSecretForm = new FormGroup({
    otpKey: this.otpKeyControl
  });

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      otpKey: this.otpKeyControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData
  ): Observable<EnrollmentResponse | null> => {
    if (this.indexedSecretForm.invalid) {
      this.indexedSecretForm.markAllAsTouched();
      return of(null);
    }
    const enrollmentData: IndexedSecretEnrollmentOptions = {
      ...basicOptions,
      type: "indexedsecret",
      otpKey: this.otpKeyControl.value ?? ""
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
