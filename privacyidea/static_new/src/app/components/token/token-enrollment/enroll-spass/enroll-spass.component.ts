import { Component, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { SpassApiPayloadMapper } from "../../../../mappers/token-api-payload/spass-token-api-payload.mapper";

export interface SpassEnrollmentOptions extends TokenEnrollmentData {
  type: "spass";
}

@Component({
  selector: "app-enroll-spass",
  standalone: true,
  imports: [FormsModule, ReactiveFormsModule],
  templateUrl: "./enroll-spass.component.html",
  styleUrl: "./enroll-spass.component.scss"
})
export class EnrollSpassComponent implements OnInit {
  protected readonly enrollmentMapper: SpassApiPayloadMapper = inject(
    SpassApiPayloadMapper
  );
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === "spass")?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  spassForm = new FormGroup({});

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData
  ): Observable<EnrollmentResponse | null> => {
    const enrollmentData: SpassEnrollmentOptions = {
      ...basicOptions,
      type: "spass"
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
